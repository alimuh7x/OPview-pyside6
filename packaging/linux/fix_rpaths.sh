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
# (e.g. the PySide6 imageformats plugins such as libqjpeg.so) already carry a
# correct, working rpath for their own direct deps, and clobbering it would
# trade one missing-library bug for another.
set -euo pipefail

DIST="$1"
INTERNAL="$DIST/_internal"

# ICU rename-and-repatch fallback (collision-check fallback mechanism, see
# ../../../QT6_MIGRATION_PLAN.md Phase 4): once merged with OPStudio's own
# runtime into a single shared lib/, OPView's private ICU build collides by
# filename with OPStudio's Qt6-vendored ICU - and unlike the Qt6 module
# libraries themselves (Core/Gui/Widgets/...), which the Qt6-sharing spike
# verified are ABI-compatible across the commercial/PySide6 builds, ICU was
# never part of that spike and its content genuinely differs (a few KB off
# in each of the three libs - most likely a different ICU point build, not
# just a stripped/unstripped difference). Keep OPView's own copies rather
# than risk sharing an unverified transitive dependency: rename them out of
# collision with OPStudio's identically-named files and repoint every
# consumer's NEEDED entry accordingly.
ICU_LIBS="libicudata.so.73 libicui18n.so.73 libicuuc.so.73"
for icu in $ICU_LIBS; do
    find "$DIST" -type f -name "$icu" -print0 | while IFS= read -r -d '' f; do
        newname="${icu}.opview"
        mv "$f" "$(dirname "$f")/$newname"
        patchelf --set-soname "$newname" "$(dirname "$f")/$newname"
    done
done
find "$DIST" -type f -print0 | while IFS= read -r -d '' f; do
    file "$f" | grep -q "ELF" || continue
    needed=$(patchelf --print-needed "$f" 2>/dev/null) || continue
    for icu in $ICU_LIBS; do
        if grep -qx "$icu" <<< "$needed"; then
            patchelf --replace-needed "$icu" "${icu}.opview" "$f"
        fi
    done
done

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
