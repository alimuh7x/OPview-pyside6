# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OPView** is a PySide6 desktop application for post-processing OpenPhase simulation output: VTK heatmaps (Single View), side-by-side VTK comparison (Multi View), and plots of tabular `TextData` files (Custom Graph). It is a standalone git repository, even though it sits inside the OPStudio checkout at `external/OPview-pyside6`.

## Packaging Status — NEXT STEP: Windows NSIS installer (untested)

Branch `feature/packaging-installers` (2026-07-03) added CMake/CPack packaging:
PyInstaller onedir freeze → Linux `.deb` + AppImage + Windows NSIS installer.
See `packaging/README.md` for the full build documentation.

**Done and verified (Linux):** `.deb` and AppImage built via
`docker run --rm -v "$PWD:/src" -w /src ubuntu:22.04 bash packaging/build_linux_packages.sh`
install and launch on clean ubuntu:22.04 (GL path) and ubuntu:24.04
(`OPVIEW_NO_GPU=1` software-rendering path). Linux release builds MUST happen in
the 22.04 container — a freeze from a newer distro carries that distro's glibc
requirement and fails on older targets.

**Added:** `.github/workflows/release.yml` — GitHub Actions pipeline that
builds both platforms (Linux in an `ubuntu:22.04` container via the script
above, Windows via the steps below) and uploads them as run artifacts on
`workflow_dispatch`, or as GitHub Release assets on a `vX.Y.Z` tag push. This
gives the Windows NSIS job its first automated run — trigger it manually
from the Actions tab before cutting a real tag, since that path is still
unverified on real hardware/CI.

**Not done — continue here on Windows:**

1. Prerequisites: CMake >= 3.22, NSIS (`makensis` on PATH), Python 3.10–3.14
   (3.14 needs vtk >= 9.6.2), all on PATH.
2. Build and package (from the repo root, PowerShell or cmd):
   ```bat
   cmake -S . -B build
   cmake --build build          :: venv -> pip -> PyInstaller freeze
   ctest --test-dir build -R opview_frozen_version --output-on-failure
   cpack --config build\CPackConfig.cmake -B build\packages
   ```
   Expected artifact: `build\packages\OPView-2.1.0-win64.exe`.
3. Verify the freeze before packaging: `build\dist\OPView\OPView.exe --version`
   exits 0 but prints nothing (windowed exe, no console — expected); check
   `build\dist\OPView\_internal\` contains `assets\`, `doc\`, `version.txt`,
   `plotly\package_data\plotly.min.js`, and `PySide6\QtWebEngineProcess.exe`.
4. Verify the installer: install → Start-menu shortcut "OPView" launches; open
   `Project1\` and confirm the Single View heatmap renders (exercises the
   bundled plotly.min.js + QtWebEngine end to end); install-over-install
   upgrades cleanly; uninstall removes `%ProgramFiles%\OPView` + shortcut.
5. If the frozen app fails to start, run `OPView.exe` from a console anyway —
   PyInstaller shows missing-module/DLL errors in a dialog; also consider
   temporarily setting `console=True` in `packaging/opview.spec` to debug.

**Known caveats:**
- 16 of 144 unit tests fail on `main` and the branch alike — the tests are
  stale relative to the code (e.g. expect `HistogramCanvas._axes`, removed when
  canvases moved off matplotlib). Pre-existing; not a packaging regression. The
  packaging gate is the `opview_frozen_version` ctest, not `opview_unittests`.
- Long-term follow-up (not started): build OPView into the OPStudio installer —
  `add_subdirectory(OPview-pyside6)` from opstudio's `external/CMakeLists.txt`,
  add component `opview` to the parent `CPACK_COMPONENTS_ALL`, switch the
  Windows install DESTINATION from `.` to `opview/` (see the CPack section at
  the bottom of `CMakeLists.txt`).
- No LICENSE file in this repo yet, so the NSIS license page is skipped
  (`CPACK_RESOURCE_FILE_LICENSE` deliberately unset).

## Setup and Running

```bash
# First run: creates ./venv, installs requirements.txt, launches the app
./opview.sh

# Optionally pass a project folder (or a folder containing projects) to scan
./opview.sh /path/to/project-or-projects-folder

# Run directly once the venv exists
venv/bin/python main.py [project_path]
```

Windows uses `opview.bat` (venv dir `venv-windows`) or `OPview-No-GPU.bat` (disables GPU-accelerated QtWebEngine rendering for VMs). Python 3.8+ required; Python 3.14 needs vtk >= 9.6.2 (first release with cp314 wheels).

Pyright is configured (`pyrightconfig.json`) to resolve imports against `./venv`.

## Running Tests

Tests use stdlib `unittest` and must run from the repo root — they resolve the bundled sample project `Project1/` via relative paths and `Path.cwd()`. GUI tests run headless by setting `QT_QPA_PLATFORM=offscreen` themselves.

```bash
# Full suite
venv/bin/python -m unittest discover tests -v

# Single module / single test
venv/bin/python -m unittest tests.test_single_view_data_flow -v
venv/bin/python -m unittest tests.test_single_view_data_flow.SingleViewDataFlowTests.test_dataset_registry_detects_vtk_datasets
```

`Project1/` (with `VTK/` and `TextData/` subfolders) is test fixture data — several tests assert on its specific files, so don't rename or prune it casually.

## Architecture

### Startup flow

`main.py` → `app/startup_args.py` (argparse, deliberately Qt-free) → `app/application_bootstrap.py` (QApplication, bundled Roboto Condensed fonts from `assets/fonts/`, stylesheet from `app/styles.py`) → `app/main_window.py` (`MainWindow` coordinates the sidebar and the three content tabs).

### Data discovery pipeline

1. `utils/project_scanner.scan_project_folders()` — finds project folders (those containing `VTK/` and/or `TextData/`) below the startup path, shown in `sidebar/sidebar_widget.py`.
2. `config/tabs.py` `TAB_CONFIGS` — the declarative registry mapping file globs (e.g. `PhaseField_*.vts`) to physics modules, datasets, and scalar/component descriptors. **Adding support for a new OpenPhase output file is usually just a new entry here.**
3. `config/dataset_registry.py` `DatasetRegistry` — matches a project's VTK folder against `TAB_CONFIGS`; VTK files matching no config are auto-grouped by basename into `auto-*` datasets under an "Other Files" module, so unknown files still appear.
4. `utils/vtk_utils.get_reader()` / `utils/vtk_reader.py` — reads `.vti`/`.vts`/`.vtu`/`.vtk` and extracts interpolated 2D slices for display.

### Rendering: Plotly inside QtWebEngine

Heatmaps (`viewer/heatmap_canvas.py`, `multi_view/multi_view_cell.py`) and Custom Graph plots (`graphs/graph_canvas.py`) are Plotly figures rendered in a `QWebEngineView`, using the offline `plotly.min.js` bundled with the `plotly` package (no network). JS→Python events (clicks, hovers) flow through a `QWebChannel` bridge object (`_PlotlyBridge`); JS console output is forwarded via a `QWebEnginePage` subclass. `viewer/matplotlib_heatmap_canvas.py` and `viewer/pyqtgraph_heatmap_canvas.py` are alternative backends not wired into the app.

### Single View panel stack (`viewer/`)

One dataset panel = `viewer/panel_widget.py` (`PanelWidget`), composed of `HeatmapCanvas`, `PanelControlsWidget`, `HistogramCanvas`, `LineScanCanvas`, and `AnimationPlayer`, all mediated by `viewer/heatmap_controller.py` (`HeatmapController`). Per-panel state lives in the serialisable `ViewerState` dataclass (`viewer/state.py`). Panels are loaded off the UI thread by `utils/panel_load_worker.py` (`PanelLoadWorker`, a QThread) and delivered via the `panel_ready` signal on `single_view/tab_widget.py`. `utils/file_watcher.py` (`FileWatcherService`) refreshes views when simulation output files change on disk.

### Custom Graph

`graphs/tab_widget.py` → `graphs/graph_panel_widget.py` → `graphs/graph_canvas.py`, fed by `data/text_sources.py` (`GenericTextDataSource`), which parses arbitrary whitespace/CSV numeric tables from `TextData` files.

## Conventions

- Nearly every method traces its execution with `app.debug.debug_print()` (`[DEBUG] ...` to stdout). Follow this convention in new code.
- Modules that must work without a running QApplication (arg parsing, scanners, data sources, configs) intentionally avoid Qt imports — keep it that way.
- User-facing documentation lives in `doc/Documentation.md` and is shown in-app via Help > Documentation; update it when changing user-visible behavior.
