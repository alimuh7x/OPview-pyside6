# OPView PySide6

A desktop post-processing application for inspecting OpenPhase simulation output through heatmaps, side-by-side comparison, and custom text-data graphs.

## Features

- Single View heatmaps with range controls, rotation, overlays, line scans, and histogram analysis.
- Multi View comparison across selected VTK files with shared orientation/range controls.
- Custom Graph panels for plotting `TextData` files with per-series colors, conversions, Y-axis routing, markers, and legend placement.
- Local in-app documentation from **Help > Documentation** or the header **Documentation** button.

## Setup

### First-time setup (Linux / macOS / WSL)

```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
python main.py
```

### Running the application

```bash
source venv/bin/activate
python main.py
```

When done, deactivate the virtual environment:
```bash
deactivate
```

## Dependencies

- PySide6 (Qt for Python)
- VTK (Visualization Toolkit)
- NumPy
- Plotly

## Usage

1. Start the app with `python main.py`.
2. Select or add a project in the sidebar.
3. Choose **Single View**, **Multi View**, or **Custom Graph** from the top tabs.
4. Use **Help > Documentation** for the complete local guide.

## Supported File Formats

- `.vti` - VTK Image Data
- `.vts` - VTK Structured Grid
- `.vtu` - VTK Unstructured Grid
- `.vtk` - Legacy VTK format

## Python Version

Requires Python 3.8 or higher (Python 3.14 is not compatible with VTK).
