# OPView PySide6

A desktop post-processing application for inspecting OpenPhase simulation output through heatmaps, side-by-side comparison, and custom text-data graphs.

## Features

- Single View heatmaps with range controls, rotation, overlays, line scans, and histogram analysis.
- Multi View comparison across selected VTK files with shared orientation/range controls.
- Custom Graph panels for plotting `TextData` files with per-series colors, conversions, Y-axis routing, markers, and legend placement.
- Local in-app documentation from **Help > Documentation** or the header **Documentation** button.

## Screenshots

### Single View

![OPView Single View](assets/Single_View.png)

### Multi View

![OPView Multi View](assets/Multi-View.png)

### Custom Graph

![OPView Custom Graph](assets/Custom-Graph.png)

## Setup

### Windows

Double-click `opview.bat`, or run it from Command Prompt:

```bat
opview.bat
```

The batch file checks for Python, creates the virtual environment if needed, installs dependencies from `requirements.txt`, prints setup and launch status messages, and starts OPView.

### First-time setup (Linux / macOS / WSL)

```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
python main.py
```

### Running the application

On Windows, use:

```bat
opview.bat
```

On Linux / macOS / WSL, use:

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
- Matplotlib
- Plotly
- PyVista
- SciPy

## Usage

1. Start the app with `opview.bat` on Windows or `python main.py` on Linux / macOS / WSL.
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
