# Packaging OPView

OPView is frozen with PyInstaller (onedir) and packaged by CMake/CPack:
Linux produces a `.deb` and an AppImage, Windows an NSIS installer.
The frozen bundle is self-contained — end users do not need Python.

## Prerequisites

- CMake >= 3.22
- Python 3.10–3.14 (3.14 requires vtk >= 9.6.2, which is the first release
  with cp314 wheels). If your default `python3` is unsuitable, pass
  `-DOPVIEW_PYTHON_EXECUTABLE=/path/to/python3.12`.
- Linux packaging: `dpkg` (for the .deb); the AppImage target downloads
  `appimagetool` automatically, or pass `-DOPVIEW_APPIMAGETOOL=/path/to/appimagetool`.
- Windows packaging: NSIS (`makensis` on PATH).

## Linux

**Build on the oldest distro you want to support** (Ubuntu 22.04). PyInstaller
bundles system libraries from the build host (e.g. `libglib-2.0`) but never
glibc itself, so a bundle frozen on a newer distro demands that distro's glibc
at runtime and fails on older targets with errors like
`GLIBC_2.43 not found`. Packages built on 22.04 run on 22.04 and newer.
A containerized build does this reproducibly:

```bash
docker run --rm -v "$PWD:/src" -w /src ubuntu:22.04 bash packaging/build_linux_packages.sh [build_dir] [version]
# artifacts land in <build_dir>/packages/ (default build-linux/)
```

Manual build (on a suitably old machine):

```bash
cmake -S . -B build [-DOPVIEW_PYTHON_EXECUTABLE=/usr/bin/python3] [-DOPVIEW_VERSION=2.0.0]
cmake --build build            # venv -> pip -> PyInstaller freeze
ctest --test-dir build -R opview_frozen --output-on-failure
cpack --config build/CPackConfig.cmake -B build/packages   # -> opview_<version>_amd64.deb
cmake --build build --target opview_appimage               # -> build/packages/OPView-<version>-x86_64.AppImage
```

## Windows

```bat
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build -R opview_frozen --output-on-failure
cpack --config build\CPackConfig.cmake -B build\packages   :: -> OPView-<version>-win64.exe
```

`-G Ninja` matters: this project has `LANGUAGES NONE` (no compiler, just
venv/pip/PyInstaller/CPack orchestration), so the default multi-config Visual
Studio generator adds nothing but friction — `ctest` then fails with "Test
not available without configuration" unless every downstream `ctest`/`cpack`
call also gets an explicit `-C <config>`. Ninja needs to be on `PATH`
(`choco install ninja`).

Note: on Windows the app is built windowed (no console), so `OPView --version`
prints nothing but still exits 0 — the ctest smoke test relies on the exit code.

## CI (GitHub Actions)

`.github/workflows/release.yml` runs both platforms above and uploads the
resulting `.deb`, AppImage, and `.exe` as downloadable run artifacts on
every manual trigger (Actions tab → "Run workflow"), and additionally
publishes them to a GitHub Release when triggered by a `vX.Y.Z` tag push.

## Version

The package version defaults to 2.0.0 and can be overridden with
`-DOPVIEW_VERSION=x.y.z`. When this project is built as a subdirectory of the
OPStudio superproject it inherits `OPStudio_VERSION` automatically. The version
is baked into the bundle as `version.txt`; `opview --version` reports it.

## Layout

| File | Purpose |
|---|---|
| `opview.spec` | PyInstaller spec (datas, VTK hidden imports, excludes) |
| `linux/install_merged.cmake` | Installs the frozen tree into OPStudio's shared `lib/`, reusing OPStudio's Qt6 libraries (embedded builds only) |
| `linux/opview.desktop` | Desktop entry (used by .deb and AppImage) |
| `linux/AppRun` | AppImage entry point |

## GPU-less machines / VMs

Set `OPVIEW_NO_GPU=1` before launching (`main.py` and AppRun append
`--disable-gpu` to `QTWEBENGINE_CHROMIUM_FLAGS`), matching `OPview-No-GPU.bat`.

## Release checklist

1. Update the CMake default version, changelog, and release notes together.
2. Run the source tests and check documentation links.
3. Push the release commit and run the Release workflow manually on that branch to validate both packages.
4. Create and push the annotated `vX.Y.Z` tag at the validated commit. The tag selects the package version and triggers release builds.
5. Confirm the Windows installer, Linux `.deb`, and AppImage are attached to the release before announcing it.

A successful frozen smoke test checks startup, version handling, and Linux library dependencies. Interactive installation, rendering, and export still need platform testing.
