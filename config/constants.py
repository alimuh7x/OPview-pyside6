"""Static configuration values."""

DEFAULTS = {
    "axis": "y",
    "interpolation_resolution": 160,
    "palette": "aqua-fire",
}

PALETTES = {
    "aqua-fire": ["#00328f", "#00afb8", "#fffbdf", "#ffbc3c", "#a51717"],
    "blue-to-red": ["#a51717", "#fbbc3c", "#fffbe0", "#00afb8", "#00328f"],
    "spectral-lowblue": ["#5e4fa2", "#3f96b7", "#b3e0a3", "#fdd280", "#9e0142"],
    "cool-warm-extended": ["#000059", "#295698", "#fcf5e6", "#f7d5b2", "#590c36"],
    "steel": ["#0b2545", "#3e5c76", "#f6f9ff", "#f4c06a", "#b3541e"],
    "ice-sunset": ["#1c3d5a", "#3aa0c8", "#ffffff", "#f9d976", "#f47068"],
}

ALLOWED_VTK_EXTENSIONS = {".vts", ".vtu", ".vti", ".vtk", ".vtp"}
ALLOWED_TEXTDATA_EXTENSIONS = [".txt", ".csv", ".dat", ".opd"]

SKIP_FOLDERS = {
    ".git",
    ".vscode",
    ".claude",
    "__pycache__",
    "venv",
    "assets",
    "utils",
    "viewer",
    "node_modules",
}

TENSOR_COMPONENTS = ["xx", "yy", "zz", "xy", "yz", "zx"]
