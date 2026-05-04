# VTK Previewer (PySide6)

A desktop application for viewing VTK files using PySide6 and VTK.

## Features

- Load and visualize VTK files (.vti, .vts, .vtu, .vtk)
- Interactive 3D rendering with mouse controls
- Display dataset information (type, points, cells, arrays)
- Reset camera view
- Clear scene functionality

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

## Usage

1. Click "Load VTK File" to open a VTK file
2. Use mouse to interact with the 3D view:
   - Left click + drag: Rotate
   - Middle click + drag: Pan
   - Scroll: Zoom
3. Click "Reset Camera" to reset the view
4. Click "Clear Scene" to clear the current visualization

## Supported File Formats

- `.vti` - VTK Image Data
- `.vts` - VTK Structured Grid
- `.vtu` - VTK Unstructured Grid
- `.vtk` - Legacy VTK format

## Python Version

Requires Python 3.8 or higher (Python 3.14 is not compatible with VTK).
