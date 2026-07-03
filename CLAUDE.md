# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OPView** is a PySide6 desktop application for post-processing OpenPhase simulation output: VTK heatmaps (Single View), side-by-side VTK comparison (Multi View), and plots of tabular `TextData` files (Custom Graph). It is a standalone git repository, even though it sits inside the OPStudio checkout at `external/OPview-pyside6`.

## Setup and Running

```bash
# First run: creates ./venv, installs requirements.txt, launches the app
./opview.sh

# Optionally pass a project folder (or a folder containing projects) to scan
./opview.sh /path/to/project-or-projects-folder

# Run directly once the venv exists
venv/bin/python main.py [project_path]
```

Windows uses `opview.bat` (venv dir `venv-windows`) or `OPview-No-GPU.bat` (disables GPU-accelerated QtWebEngine rendering for VMs). Python 3.8+ required; Python 3.14 is incompatible with VTK.

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
