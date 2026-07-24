#!/bin/bash
# Additive rpath sweep for the PyInstaller onedir bundle.
#
# Usage: fix_rpaths.sh <dist-dir>
#
# PyInstaller's onedir bootloader sets LD_LIBRARY_PATH to the top-level
# _internal/ directory at process launch, so most bundled files resolve
# their siblings fine at runtime. But a bare `ldd <file>` (as OPStudio's
# deb-install CI check runs, and as the dynamic linker itself would for a
# direct dlopen()) never sees that env var, and some files genuinely need a
# baked-in path: e.g. a private vendored copy one level down in
# numpy.libs/scipy.libs/pillow.libs/, or a system lib generically collected
# into the top-level _internal/ dir but only reachable from a Qt plugin
# subdirectory like PySide6/Qt/plugins/imageformats/.
#
# This appends ($ORIGIN + a relative path back to _internal/, the directory
# PyInstaller's onedir COLLECT step puts every bundled file in other than the
# top-level launcher executable itself) to every ELF file's rpath.
# Deliberately uses --add-rpath, never --set-rpath/--remove-rpath: some files
# (e.g. libqtiff.so) already carry a correct, working rpath for their own
# direct deps, and clobbering it would trade one missing-library bug for
# another.
set -euo pipefail

DIST="$1"
INTERNAL="$DIST/_internal"

find "$DIST" -type f -print0 | while IFS= read -r -d '' f; do
    file "$f" | grep -q "ELF" || continue
    # Skip files with no dynamic section at all (e.g. static data files that
    # happen to look ELF-ish, or objects patchelf can't touch).
    patchelf --print-rpath "$f" >/dev/null 2>&1 || continue

    dir=$(dirname "$f")
    relback=$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$INTERNAL" "$dir")
    if [ "$relback" = "." ]; then
        newpath='$ORIGIN'
    else
        newpath="\$ORIGIN:\$ORIGIN/$relback"
    fi
    patchelf --add-rpath "$newpath" "$f"
done
