# OPview PySide6 — Conversion Plan

Source: `/mnt/e/RUB/OpenPhase/OPView/` (Dash)
Target: `/mnt/e/RUB/OpenPhase/OPview-pyside6/` (PySide6)

---

## Implementation Rules

- Use an OOP structure everywhere.
- Always create dedicated classes first, then instantiate and call them from higher-level classes.
- Avoid flat procedural UI code except for the minimal application entry point in `main.py`.
- Keep responsibilities separated: UI widgets, state objects, readers/loaders, and coordination logic must live in different classes.

## App Overview

Three-tab desktop application for visualizing OpenPhase simulation output.

| Tab | Dash name | Function |
|-----|-----------|----------|
| Single View | `current` | One project, N dataset panels (heatmap slices) |
| Multi View | `comparison` | Compare N projects side-by-side |
| Custom Graph | `custom-graph` | TextData `.txt/.csv` line charts |

---

## Technology Mapping (Dash → PySide6)

| Dash / Plotly | PySide6 equivalent |
|---|---|
| `dcc.Tabs` | `QTabWidget` |
| `dcc.Dropdown` | `QComboBox` |
| `dcc.Checklist` | List of `QCheckBox` |
| `dcc.Slider` | `QSlider` |
| `dcc.RangeSlider` (dual) | Two `QSlider` widgets |
| `dcc.Input` (number) | `QDoubleSpinBox` / `QSpinBox` |
| `html.Button` | `QPushButton` |
| `dmc.Switch` | `QCheckBox` styled as toggle |
| `dmc.SegmentedControl` | `QButtonGroup` with toggle buttons |
| `dcc.Graph` (Plotly heatmap) | `matplotlib` via `FigureCanvasQTAgg` |
| `dcc.Graph` (Plotly line chart) | `matplotlib` via `FigureCanvasQTAgg` |
| `dcc.Store` | Python dataclass / dict in-memory |
| `dmc.Modal` | `QDialog` |
| Dash callbacks | Qt signals/slots |
| `html.Div` layout | `QSplitter`, `QHBoxLayout`, `QVBoxLayout` |
| VTK file reading | `pyvista` (used by existing `VTKReader`) |
| Colorscales | `matplotlib` colormaps (custom LinearSegmentedColormap) |
| Assets (PNG logos) | Qt resource system or direct file paths |

---

## File Structure (Target)

```
OPview-pyside6/
├── main.py                         # Entry point
├── app/
│   ├── __init__.py
│   └── main_window.py              # QMainWindow, QTabWidget (3 tabs)
├── config/
│   ├── __init__.py
│   ├── tabs.py                     # TAB_CONFIGS (identical to Dash version)
│   └── constants.py                # Colors, palettes, defaults, extensions
├── data/
│   ├── __init__.py
│   └── text_sources.py             # GenericTextDataSource, TextDataLoader
├── utils/
│   ├── __init__.py
│   ├── vtk_reader.py               # VTKReader (pyvista + scipy, port from Dash)
│   ├── vtk_utils.py                # ReaderCache singleton, get_reader(), list_vtk_files()
│   ├── project_scanner.py          # scan_project_folders(), group_projects_by_parent()
│   └── dataset_detector.py         # DatasetRegistry, detect_available_datasets()
├── viewer/
│   ├── __init__.py
│   ├── state.py                    # ViewerState dataclass (identical to Dash)
│   ├── defaults.py                 # DEFAULTS dict (identical to Dash)
│   ├── colorscale.py               # make_dynamic_colorscale() → matplotlib
│   ├── heatmap_canvas.py           # matplotlib FigureCanvas for heatmap
│   ├── linescan_canvas.py          # matplotlib FigureCanvas for line scan
│   ├── histogram_canvas.py         # matplotlib FigureCanvas for histogram
│   └── panel_widget.py             # Full dataset panel widget
├── single_view/
│   ├── __init__.py
│   └── tab_widget.py               # Single View tab
├── multi_view/
│   ├── __init__.py
│   └── tab_widget.py               # Multi View tab
├── graphs/
│   ├── __init__.py
│   ├── tab_widget.py               # Custom Graph tab
│   └── graph_canvas.py             # matplotlib canvas for line charts
├── sidebar/
│   ├── __init__.py
│   └── sidebar_widget.py           # Project tree + Add Panel controls
├── assets/                         # PNG icons (same as Dash assets/)
├── requirements.txt
├── opview.bat
└── plan.md
```

---

## UI Layout Diagrams

### A — Full Application Window

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  [OP Logo]  OPV iew                                          Documentation ↗    │  ← top bar
├──────────────────────────────────────────────────────────────────────────────────┤
│  VTK  Tabs:  [ Single View ]  [ Multi View ]  [ Custom Graph ]                  │  ← main tab row
├──────────────┬───────────────────────────────────────────────────────────────────┤
│   SIDEBAR    │                    MAIN CONTENT AREA                              │
│   (~220px)   │              (active tab widget here)                             │
│              │                                                                   │
│  (see B)     │  (see C / D / E depending on active tab)                         │
│              │                                                                   │
│              │                                                                   │
└──────────────┴───────────────────────────────────────────────────────────────────┘
```

---

### B — Sidebar (all tabs share this)

```
┌──────────────────────┐
│  PROJECTS            │  ← bold label
├──────────────────────┤
│ ▾ Project1           │  ← project name (non-clickable header)
│   ☑  Project1/VTK    │  ← QCheckBox, indented
│   ☑  Project1/TextD  │  ← QCheckBox, indented
│ ▾ Project2           │
│   ☐  Project2/VTK    │
├──────────────────────┤
│ [+] Add Project Fold │  ← QPushButton, full width
│ [⊞] Paste Project Pa │  ← QPushButton, full width
│ [↺] Reload VTK Files │  ← QPushButton, full width
├──────────────────────┤
│  ADD PANEL           │  ← bold label (hidden on Custom Graph tab)
│ [Select a data type▼]│  ← QComboBox, grouped by module
│  ● No project loaded │  ← status label, green text
└──────────────────────┘
```

ADD PANEL dropdown options (populated by DatasetRegistry):
```
── Mechanics ──────────────
   Stress Tensor
   Elastic Strains
── Plasticity ─────────────
   CRSS
   Plastic Strain
── (Unconfigured) ─────────
   PhaseField
   Interfaces
```

---

### C — Single View Tab

```
┌───────────────────────────────────────────────────────────────────────┐
│  [ Stress Tensor × ]  [ Elastic Strains × ]  [ + ]                   │  ← inner QTabBar (closeable tabs)
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌── CONTROLS ──────────────────────────────────────────────────┐   │
│   │ [Project 1     ▼]  [Stresses_00032.vts ▼]  [σ_xx (MPa)   ▼] │   │  ← Row 1
│   │ Range: [  -150.0 ] [ 320.5 ]  [↺ Reset]  [○ Range Select]   │   │  ← Row 2
│   │ [Aqua Fire      ▼]  [●────────────────●]  [○ Full Scale]     │   │  ← Row 3 (dual slider)
│   │ Slice (Y-axis):     [●──────────────────●] [  64  ]          │   │  ← Row 4 (hidden for 2D)
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌── HEATMAP ───────────────────────────────────────────────────┐   │
│   │  σ_xx (MPa) — Stresses_00032.vts    [○ Interfaces] [↓ PNG]  │   │  ← top bar
│   │  ┌──────┐  ┌──────────────────────────┐  ┌──────┐          │   │
│   │  │      │  │                          │  │  320 │          │   │
│   │  │  OP  │  │     Heatmap Canvas       │  │  ··· │          │   │  ← logo | heatmap | colorbar
│   │  │ Logo │  │  (aspect-correct, click) │  │  0.0 │          │   │
│   │  │      │  │                          │  │ -150 │          │   │
│   │  └──────┘  └──────────────────────────┘  └──────┘          │   │
│   │  [ Click heatmap to select range (1st click) ]             │   │  ← toast info
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌── LINE SCAN & HISTOGRAM ANALYSIS ──────────────────────────┐    │
│   │  [○ Line Scan]  [○ Show Line]  [ ↔ Horiz. | ↕ Vert. ]     │    │  ← toolbar
│   │  ┌──────────────────────────────────────────────────────┐  │    │
│   │  │            Line Scan Canvas                          │  │    │
│   │  └──────────────────────────────────────────────────────┘  │    │
│   │  Histogram Field: [ σ_xx (MPa) ▼ ]   Bins: [●──────●] 30  │    │
│   │  ┌──────────────────────────────────────────────────────┐  │    │
│   │  │            Histogram Canvas                          │  │    │
│   │  └──────────────────────────────────────────────────────┘  │    │
│   └────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘
```

---

### D — Multi View Tab

```
┌───────────────────────────────────────────────────────────────────────┐
│  SHARED CONTROLS (applies to all panels below):                       │
│  [σ_xx (MPa) ▼]  Slice: [●──────●] [64]  [Aqua Fire ▼]             │
│  Range: [-150.0] [320.5]  [↺]  [○ Full Scale]                        │
├───────────────────────────────────────────────────────────────────────┤
│  [ Stress Tensor × ]  [ + ]          (inner tabs, same as Single)    │
├───────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐           │
│  │  Project1               │  │  Project2               │           │  ← 2-column grid
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │           │
│  │  │   Heatmap Canvas  │  │  │  │   Heatmap Canvas  │  │           │
│  │  └───────────────────┘  │  │  └───────────────────┘  │           │
│  │  [↓ PNG]                │  │  [↓ PNG]                │           │
│  └─────────────────────────┘  └─────────────────────────┘           │
│  ┌─────────────────────────┐  ┌─────────────────────────┐           │
│  │  Project3               │  │  Project4               │           │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │           │
│  │  │   Heatmap Canvas  │  │  │  │   Heatmap Canvas  │  │           │
│  │  └───────────────────┘  │  │  └───────────────────┘  │           │
│  │  [↓ PNG]                │  │  [↓ PNG]                │           │
│  └─────────────────────────┘  └─────────────────────────┘           │
│  ↑ QScrollArea (vertical scroll when > 2 rows)                       │
└───────────────────────────────────────────────────────────────────────┘
```

Each multi-view panel card (no independent controls — all shared from top bar):
```
┌───────────────────────────────────────┐
│  Project1 / Stresses_00032.vts        │  ← project name + file
│  ┌─────────────────────┐  ┌────────┐  │
│  │                     │  │   320  │  │
│  │   Heatmap Canvas    │  │   ···  │  │  ← heatmap + colorbar side by side
│  │                     │  │  -150  │  │
│  └─────────────────────┘  └────────┘  │
│  [↓ PNG]                              │
└───────────────────────────────────────┘
```

---

### E — Custom Graph Tab

```
┌───────────────────────────────────────────────────────────────────────┐
│  [+ Add or Select Text File]   [+ Add Data]                           │  ← toolbar
├───────────────────────────────────────────────────────────────────────┤
│  ↓ QScrollArea                                                        │
│                                                                       │
│  ┌── Panel 1 (file mode) ─────────────────────────────────────── [×]┐│
│  │ Files (max 3):                                                    ││
│  │   [Project1/StressStrain.txt ▼]  [+ add file]                    ││
│  │                                                                   ││
│  │ X-axis:  [ Epsilon_xx          ▼]   X-title: [ Strain      ]     ││
│  │                                                                   ││
│  │ Columns from StressStrain.txt:                                    ││
│  │   [☑ Sigma_xx]  [☑ Sigma_yy]  [☐ Sigma_zz]  [☐ Sigma_xy]       ││
│  │   Sigma_xx → Y-Axis: [Left  ▼]   Legend: [ Sigma xx     ]        ││
│  │   Sigma_yy → Y-Axis: [Right ▼]   Legend: [ Sigma yy     ]        ││
│  │                                                                   ││
│  │ Y1 title: [ Stress (MPa) ]    Y1 units: [ MPa ▼]                 ││
│  │ Y2 title: [ Stress (MPa) ]    Y2 units: [ MPa ▼]                 ││
│  │                                                                   ││
│  │ Trace: [Lines ▼]  Style: [Solid ▼]  Legend pos: [Top Left ▼]     ││
│  │ [☑ Show Grid]  [☑ Show Legend]  [☐ Intersections]  [☐ Roots]     ││
│  │                                                                   ││
│  │ ┌────────────────────────────────────────────────────────────┐   ││
│  │ │                  Graph Canvas                              │   ││
│  │ │              (dual Y-axis line chart)                      │   ││
│  │ └────────────────────────────────────────────────────────────┘   ││
│  └───────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌── Panel 2 (data/paste mode) ───────────────────────────────── [×]┐│
│  │ Paste data:                                                       ││
│  │  ┌──────────────────────────────────────────────────────────┐    ││
│  │  │ Epsilon_xx  Sigma_xx  Sigma_yy                           │    ││  ← QTextEdit
│  │  │ 0.000       0.0       0.0                                │    ││
│  │  │ 0.001       52.3      48.1                               │    ││
│  │  └──────────────────────────────────────────────────────────┘    ││
│  │ (same column selection + settings UI as file mode below paste)   ││
│  └───────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────┘
```

---

### F — Add Panel Dropdown (ADD PANEL in sidebar)

When a project is loaded and a dataset detected:
```
┌────────────────────────┐
│ ADD PANEL              │
│ [Select a data type  ▼]│
│  ──── Mechanics ─────  │
│     Stress Tensor      │  ← only shown if Stresses_*.vts files exist
│     Elastic Strains    │
│  ──── Plasticity ────  │
│     CRSS               │
│     Plastic Strain     │
│  ── Unconfigured ───   │
│     PhaseField         │  ← auto-detected, not in TAB_CONFIGS
│  ● 5 datasets detected │  ← status label, green
└────────────────────────┘
```

---

### G — Heatmap Controls Detail (Rows 1–4)

```
ROW 1 — File selection
┌─────────────────┐  ┌──────────────────────────┐  ┌──────────────────┐
│ Project 1     ▼ │  │ Stresses_00032.vts      ▼ │  │ σ_xx (MPa)     ▼ │
│ (QComboBox)     │  │ (QComboBox, sorted files)  │  │ (QComboBox,      │
│ hidden if only  │  │ label = filename,           │  │  scalar fields)  │
│ 1 project       │  │ value = abs path            │  │                  │
└─────────────────┘  └──────────────────────────┘  └──────────────────┘

ROW 2 — Range controls
 Range:  ┌────────┐  ┌────────┐  ┌──────┐  ┌────────────────────────┐
         │ -150.0 │  │  320.5 │  │  ↺   │  │ ○  Range Selection     │
         │(QDblSp)│  │(QDblSp)│  │(QPB) │  │    on Map (QCheckBox)  │
         └────────┘  └────────┘  └──────┘  └────────────────────────┘

ROW 3 — Color map
 ┌───────────────┐  ┌────────────────────────────────────┐  ┌──────────────────┐
 │ Aqua Fire   ▼ │  │  ●──────────────────────────────●  │  │ ○  Full Scale    │
 │ (QComboBox)   │  │  (Two QSliders acting as dual handle│  │   (QCheckBox)    │
 └───────────────┘  │   slider for blue_cut / red_cut)   │  └──────────────────┘
                    └────────────────────────────────────┘

ROW 4 — Slice (hidden when mesh is 2D)
 Slice (Y-axis):  ┌─────────────────────────────────────┐  ┌─────┐
                  │  ●────────────────────────────────   │  │  64 │
                  │  (QSlider, min=0, max=ny-1)          │  │(QSp)│
                  └─────────────────────────────────────┘  └─────┘
```

---

### H — Line Scan Card Detail

```
┌── LINE SCAN & HISTOGRAM ANALYSIS ─────────────────────────────────────┐
│                                                                        │
│  Toolbar:                                                              │
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ ○ Line Scan    │  │ ○ Show Line │  │ [ ↔ Horiz. | ↕ Vert. ] │   │
│  │  (QCheckBox)   │  │ (QCheckBox) │  │  (QButtonGroup toggle)   │   │
│  └────────────────┘  └─────────────┘  └─────────────────────────┘   │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     Line Scan Canvas                            │  │
│  │   value                                                         │  │
│  │   320 ┤ ·····                                                   │  │
│  │     0 ┤──────────────·····──────────                            │  │
│  │  -150 ┤                                                         │  │
│  │       └──────────────────────────────── position               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  [ Click heatmap in Line Scan mode to set position ]                  │
│                                                                        │
│  Histogram Field: [ σ_xx (MPa) ▼ ]   Bins: ──●──────────── 30        │
│                                              (QSlider 10-200)         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     Histogram Canvas                            │  │
│  │  count                                                          │  │
│  │  150 ┤   ██                                                     │  │
│  │  100 ┤  ████                                                    │  │
│  │   50 ┤ ██████ ████                                              │  │
│  │    0 └────────────────────────────────── σ_xx (MPa)            │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### I — "Paste Project Path" Dialog

```
┌── Select Path ─────────────────────────────────┐
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  C:\Users\ali\Simulations\Project1        │  │  ← QLineEdit
│  └───────────────────────────────────────────┘  │
│                                                 │
│                    [ Cancel ]  [ Add ]          │
└─────────────────────────────────────────────────┘
```

---

### J — Widget Sizing Reference

| Widget | Size / Policy |
|--------|--------------|
| Sidebar | Fixed 220px width |
| Top bar | Fixed ~50px height |
| Main tab row | Fixed ~36px height |
| Inner tab bar (Single/Multi) | Fixed ~32px height |
| Controls panel (rows 1–4) | Fixed ~130px height |
| Heatmap card (logo+map+colorbar) | Fixed 380px height, width dynamic |
| Logo card | Fixed 80px × 380px |
| Colorbar card | Fixed 110px × 380px |
| Heatmap canvas | 380px height, width = 380 × (nx/ny), max 1200px |
| Line scan canvas | ~200px height, full width |
| Histogram canvas | ~200px height, full width |
| Graph canvas (Custom Graph) | ~400px height, full width |
| Multi-view panel card | Min 400px wide, 2-column grid |

---

## Phase 1 — App Shell (Structure Only, No Logic)

**Goal:** Running window with correct layout skeleton. No VTK. No data. Placeholders everywhere.

### 1.1 `main.py`
- `QApplication` init
- Instantiate `MainWindow`, show, exec

### 1.2 `app/main_window.py` — `MainWindow(QMainWindow)`
- Top bar: OP logo + "OPView" title label (left), "Documentation" link label (right)
- Tab row below top bar: `QTabWidget` with three tabs
  - Tab 0: "Single View"
  - Tab 1: "Multi View"
  - Tab 2: "Custom Graph"
- Below tabs: `QSplitter` (horizontal)
  - Left: `SidebarWidget` (fixed ~220px)
  - Right: stacked area that shows the active tab's content widget

### 1.3 `sidebar/sidebar_widget.py` — `SidebarWidget(QWidget)`
Sections (vertical layout, top to bottom):

**PROJECTS section**
- Label: "PROJECTS"
- `QScrollArea` containing `QWidget` with `QVBoxLayout`
  - For each project: bold `QLabel` (project name) + indented `QCheckBox` per VTK folder
- Three buttons (full-width):
  - "Add Project Folder" (opens `QFileDialog`)
  - "Paste Project Path" (opens `QDialog` with `QLineEdit`)
  - "Reload VTK Files"

**ADD PANEL section** (context-sensitive — shows relevant controls per active tab)
- "ADD PANEL" label
- `QComboBox` — "Select a data type" placeholder
- Detection status label: "No project loaded" (green text)

### 1.4 `single_view/tab_widget.py` — `SingleViewTab(QWidget)`
- Placeholder `QLabel("Add a module from the dropdown to get started")`
- Inner tab row: `QTabBar` for dynamic panel tabs (empty for now)
- Main content area: `QStackedWidget` for panel contents

### 1.5 `multi_view/tab_widget.py` — `MultiViewTab(QWidget)`
- Same skeleton as `SingleViewTab`
- Placeholder label

### 1.6 `graphs/tab_widget.py` — `CustomGraphTab(QWidget)`
- Placeholder label
- Two buttons: "Add or Select Text File", "Add Data"
- Empty panels container (`QScrollArea`)

### 1.7 `config/tabs.py`
Copy TAB_CONFIGS exactly from Dash version — same `tensor_scalars()`, `TabConfig`, `ConfigManager`.

### 1.8 `config/constants.py`
```python
DEFAULTS = {
    "axis": "y",
    "interpolation_resolution": 400,
    "colorA": "blue",
    "colorB": "red",
    "zsmooth": "best",
    "range_selection_mode": "two_click",
    "slice_axis_label": "Slice Index (Y-axis)",
}

PALETTES = {
    "aqua-fire":          ["#00328f", "#00afb8", "#fffbdf", "#ffbc3c", "#a51717"],
    "blue-to-red":        ["#a51717", "#fbbc3c", "#fffbe0", "#00afb8", "#00328f"],
    "spectral-lowblue":   ["#5e4fa2", "#3f96b7", "#b3e0a3", "#fdd280", "#9e0142"],
    "cool-warm-extended": ["#000059", "#295698", "#fcf5e6", "#f7d5b2", "#590c36"],
    "steel":              ["#0b2545", "#3e5c76", "#f6f9ff", "#f4c06a", "#b3541e"],
    "ice-sunset":         ["#1c3d5a", "#3aa0c8", "#ffffff", "#f9d976", "#f47068"],
}

ALLOWED_VTK_EXTENSIONS = {'.vts', '.vtu', '.vti', '.vtk', '.vtp'}
ALLOWED_TEXTDATA_EXTENSIONS = ['.txt', '.csv', '.dat', '.opd']

TEXTDATA_FOLDER_VARIANTS = ["TextData", "Textdata", "textdata", "TEXTDATA"]

SKIP_FOLDERS = {
    '.git', '.vscode', '.claude', '__pycache__',
    'venv', 'assets', 'utils', 'viewer', 'node_modules',
}

TENSOR_COMPONENTS = ['xx', 'yy', 'zz', 'xy', 'yz', 'zx']
```

### 1.9 `requirements.txt`
```
PySide6>=6.6.0
vtk>=9.3.0
pyvista>=0.43.0
numpy>=1.24.0
matplotlib>=3.8.0
pandas>=2.0.0
scipy>=1.11.0
```

**Deliverable:** `python main.py` opens a window. Three tabs switch. Sidebar visible. No errors.

---

## Phase 2 — Single View (VTK Panel + Heatmap)

**Goal:** Load a project folder, pick a dataset, display a 2D heatmap slice with full controls.

### 2.1 `utils/project_scanner.py` — `scan_project_folders()`
Port from Dash `utils/project_scanner.py` verbatim:
- Scans a base directory for subdirs containing `VTK/` or `TextData/` subfolders
- Returns `dict[name → {path, has_vtk, has_textdata, vtk_path, textdata_path, is_subdirectory, parent_folder}]`
- **Three entries per project**: `"Project1"` (root), `"Project1/VTK"` (vtk-only), `"Project1/TextData"` (text-only)
- Skips `SKIP_FOLDERS` and hidden directories
- `group_projects_by_parent(folders)` → groups entries by parent for hierarchical sidebar display
  - Top-level: project name as header label
  - Nested: VTK and TextData subfolders as checkboxes indented below

### 2.2 `utils/dataset_detector.py` — `DatasetRegistry`
Port from Dash `config/dataset_registry.py` + `utils/dataset_detector.py`:
- `detect(vtk_folder, tab_configs)` → list of `DatasetInfo` (configured + unconfigured)
- Each `DatasetInfo`: id, label, file_glob, files (sorted), tab_id
- Unconfigured VTK files get auto-created generic panel entries
- `get_dropdown_options()` → grouped `QComboBox` options for ADD PANEL

### 2.3 `utils/vtk_reader.py` — `VTKReader` + `utils/vtk_utils.py` — `ReaderCache`
Port from Dash `utils/vtk_reader.py` + `utils/vtk_utils.py` verbatim:

**`VTKReader`**:
- Uses `pyvista` for file reading
- `load_file()` — reads `.vts/.vtu/.vti/.vtk`, detects dimensions, is_3d
- `get_interpolated_slice(axis, index, scalar_name, component, resolution=400)` → `(X_grid, Y_grid, Z_grid, stats)`
  - For 2D meshes: `_extract_2d_data()` — detects active axes from std deviation
  - For 3D meshes: PyVista slice normal, then **`scipy.interpolate.griddata`** bilinear interpolation to resolution×resolution grid
  - Internal cache: `_interpolation_cache` keyed by `(scalar_name, component, axis, index, resolution)`
- `_select_component(array, component)` → picks column from tensor array; if `component=None` → `np.linalg.norm(axis=1)`
- `scalar_fields` property → `list(mesh.array_names)`
- `dimensions` attribute → `(nx, ny, nz)` tuple
- `is_3d` attribute → bool (True only if all three dims > 1)
- Auto-axis detection in `panel_widget` (not reader): if `dz≤1` → axis='z', if `dy≤1` → axis='y', if `dx≤1` → axis='x'

**`ReaderCache`** (global singleton in `vtk_utils.py`):
```python
reader_cache = ReaderCache()   # global dict[file_path → VTKReader]
```
- `get_reader(file_path)` → returns cached reader or creates new one
- `reader_cache.clear()` → called by "Reload VTK Files" button
- Prevents re-reading large VTK files on every interaction

### 2.4 `viewer/state.py`
Copy `ViewerState` dataclass verbatim from Dash version. Full field list:
```python
@dataclass
class ViewerState:
    scalar_key: str
    scalar_label: str
    axis: str
    slice_index: int
    colorA: str
    colorB: str
    palette: str
    threshold: float
    range_min: float
    range_max: float
    file_path: str
    scale: float = 1.0
    units: Optional[str] = None
    click_count: int = 0
    first_click: Optional[float] = None
    clicked_message: Optional[str] = None
    colorscale_mode: str = "normal"        # "normal" or "dynamic"
    line_scan_y: Optional[float] = None
    line_scan_x: Optional[float] = None
    line_scan_direction: str = "horizontal"
    click_mode: str = "range"              # "range" or "linescan"
    line_overlay_visible: bool = True
    interfaces_overlay_visible: bool = False
```
Copy `initial_state()` and `from_dict()` verbatim.

### 2.5 `viewer/colorscale.py`
Port `make_dynamic_colorscale()` from Dash `viewer/panel.py`:
- Same 4-case logic (normal / black-prepend / green-append / both)
- Output: `matplotlib.colors.LinearSegmentedColormap` for use with `imshow()`
- Separate helper: `palette_to_cmap(palette_name)` → returns correct colormap per mode

### 2.6 `viewer/heatmap_canvas.py` — `HeatmapCanvas(FigureCanvasQTAgg)`
- Single matplotlib figure
- `ax_map`: main heatmap (aspect-correct, no axis ticks)
- `ax_colorbar`: colorbar axis (separate, right side)
- `update(Z_grid, cmap, vmin, vmax, title, x_label, y_label)` — redraws without recreating figure
- Preserves aspect ratio from data dimensions: `fig_width = effective_height * (nx / ny)`
- Interfaces overlay: `ax_map.contourf()` call added on top when enabled
- Click handling: `mpl_connect('button_press_event', ...)` → emits Qt signal with (x, y) point
- Line overlay: `ax_map.axhline()` or `ax_map.axvline()` drawn at scan position
- `save_png(path)` — export at 4× scale (matching Dash `toImageButtonOptions: {scale: 4}`)

### 2.7 `viewer/linescan_canvas.py` — `LineScanCanvas(FigureCanvasQTAgg)`
Port `_build_line_scan_figure()` from Dash `viewer/panel.py`:
- Horizontal scan: extract row from Z_grid at nearest Y position → plot vs X
- Vertical scan: extract column from Z_grid at nearest X position → plot vs Y
- Shows scan line overlay on `heatmap_canvas` when `line_overlay_visible`

### 2.8 `viewer/histogram_canvas.py` — `HistogramCanvas(FigureCanvasQTAgg)`
Port `_build_histogram_figure()` from Dash `viewer/panel.py`:
- `ax.hist(Z_grid.flatten(), bins=n_bins)` with scalar label + units on x-axis
- Bins count: 10–200 (controlled by `QSlider`)

### 2.9 `viewer/panel_widget.py` — `PanelWidget(QWidget)`
Full panel layout — see diagrams **C** (Single View), **G** (controls detail), **H** (line scan detail).

Summary (vertical stack):
```
Controls panel  (rows 1–4, ~130px)  ← see diagram G
Heatmap area    (logo + map + colorbar, 380px fixed height)
  └─ top bar: title + [○ Interfaces Overlay] + [↓ PNG]
Line Scan card  (toolbar + LineScanCanvas + histogram controls + HistogramCanvas)
```

**Scalar field auto-discovery** (when dataset not in TAB_CONFIGS):
- After loading a file, read `reader.scalar_fields`
- For each array: detect if scalar (1D) or tensor/vector (2D)
- Tensor: add `(Norm)` entry + each component (`[xx]`, `[yy]` etc.)
- Infer component labels from VTK metadata or by count: 6→Voigt, 9→full 3×3, 3→vector

**Two-click range selection** (click_mode = "range"):
- First click: sets `range_min`
- Second click: sets `range_max`  
- Updates min/max inputs and dual slider simultaneously
- Toast notification: "Range selected: [lo, hi]"

**Interfaces overlay**:
- Toggle `interfaces_overlay_visible` in state
- Locate matching `PhaseField_XXXXXXXX.vts` from same VTK dir at same timestep
- Draw `contourf()` band from 1.5–3.5 in semi-transparent black on top of heatmap
- `_phase_overlay_file()` strategy: exact match → 8-digit padded → numeric search

**Signals/slots replacing Dash callbacks:**
- `scalar_combo.currentIndexChanged` → reload data, redraw
- `file_combo.currentIndexChanged` → reload file, reset range, redraw
- `project_combo.currentIndexChanged` → update file list, reload
- `slice_slider.valueChanged` / `slice_input.valueChanged` → extract new slice, redraw
- `range_min_spin.valueChanged` / `range_max_spin.valueChanged` → update range, redraw
- `range_slider (dual).valueChanged` → sync min/max inputs, redraw
- `reset_btn.clicked` → restore range from data stats
- `palette_combo.currentIndexChanged` → rebuild colormap, redraw
- `fullscale_check.toggled` → toggle dynamic colorscale mode
- `interfaces_check.toggled` → toggle overlay, redraw
- `linescan_check.toggled` → switch click_mode
- `show_line_check.toggled` → show/hide line on heatmap
- `direction_btn_group` (↔/↕) → change scan direction
- `histogram_field_combo.currentIndexChanged` → recompute histogram
- `bins_slider.valueChanged` → recompute histogram
- `download_btn.clicked` → `HeatmapCanvas.save_png()`
- `heatmap_canvas.clicked` → dispatch to range-select or line-scan handler

State: `ViewerState` instance per panel, updated via `dataclasses.replace()` on every change.

### 2.10 `single_view/tab_widget.py` — Full implementation
- `add_panel(dataset_info)`:
  - Creates `PanelWidget(dataset_info)`
  - Adds a closeable tab to inner `QTabBar` + panel to `QStackedWidget`
- Sidebar "ADD PANEL" combo → `add_panel()`
- Project checkboxes → `on_projects_changed()` → update file options in all panels
- Inner tab close (×) button → remove panel
- Dataset registry updates the ADD PANEL dropdown options with detected datasets

**Deliverable:** Load project → select dataset → heatmap renders → all controls work → line scan → histogram.

---

## Phase 3 — Multi View

**Goal:** Same panel layout as Single View but N projects displayed side-by-side.

### 3.1 `multi_view/tab_widget.py` — `MultiViewTab(QWidget)`
- Uses same `PanelWidget` from Phase 2
- **Shared controls** across all panels: scalar field, slice index, palette, range min/max
  - One `QComboBox` (scalar), one `QSlider` (slice), one range pair, one palette combo
  - All panels update together when shared controls change
- Layout: `QScrollArea` → `QWidget` with `QGridLayout` (2 columns)
- Each panel is locked to one project (no project picker inside panel)
- Panel header: shows project name prominently

### 3.2 Grid cache for performance
Port `comparison_grid_cache_data` from Dash:
```python
_grid_cache: dict[tuple, tuple] = {}  # (file_path, scalar_key, slice_index) → (X, Y, Z, stats)
```
Cache invalidated on "Reload VTK Files".

### 3.3 PNG export
- "Export All" button → saves each panel heatmap as `{project}_{dataset}_{timestep}.png`

### 3.4 Differences from Single View
| Feature | Single View | Multi View |
|---------|-------------|------------|
| Projects per panel | 1 (switchable) | 1 fixed per panel |
| Panel count | 1 per dataset type | 1 per selected project |
| Shared controls | No (each panel independent) | Yes (scalar, slice, range, palette) |
| Scroll | No | Yes (QScrollArea) |
| Grid cache | No | Yes |

**Deliverable:** Check two projects → panels appear side-by-side → shared controls sync all panels.

---

## Phase 4 — Custom Graph (TextData)

**Goal:** Load `.txt` / `.csv` / `.dat` / `.opd` TextData files and plot selected columns as line charts.

### 4.1 `data/text_sources.py` — `GenericTextDataSource`
Port from Dash `data/sources.py`:
- Auto-detects separator (tab, space, comma) and header row using `pandas`
- `load(file_path)` → `DataFrame`
- `get_columns()` → list of column names
- `get_column_data(name)` → numpy array

### 4.2 `utils/project_scanner.py` — TextData discovery extension
- `get_textdata_files(project_folders)`:
  - For each loaded project, scan `TextData/` subdir
  - Also scan non-VTK subdirs (fallback)
  - Returns sorted, deduplicated list of file paths matching `ALLOWED_TEXTDATA_EXTENSIONS`

### 4.3 `graphs/graph_canvas.py` — `GraphCanvas(FigureCanvasQTAgg)`
Port from Dash `ui/graphs.py`:
- Multi-line matplotlib plot with dual Y-axis support
- `update(panel_state)` → redraws from panel state dict
- Respects: `trace_mode` (lines/markers/lines+markers), `line_style` (solid/dash/dot)
- Legend: position (`top-left`, `top-right`, etc.), custom title, show/hide
- Grid: show/hide toggle
- Dual Y-axis: each column assigned to Y1 or Y2, each with own title + units label
- `show_intersections`: draw vertical lines at intersection points between traces
- `show_roots_intercepts`: mark zero-crossings
- `extend_two_point_lines`: extrapolate 2-point datasets as infinite lines within `line_range_min/max`

### 4.4 `graphs/tab_widget.py` — `CustomGraphTab(QWidget)` (full)
Port from Dash `ui/graphs.py` + `callbacks/graphs_manager.py`:

**Toolbar (top):**
- "Add or Select Text File" → creates panel in `source_mode='file'`
- "Add Data" → creates panel in `source_mode='data'` (paste text directly)

**Panel state dict** (complete — carried in memory per panel):
```python
{
  'files': [],                  # Up to 3 file paths
  'columns_by_file': {},        # {file_path: [col_names_selected]}
  'column_settings': {},        # {file_path: {col: {yaxis, legend_label}}}
  'source_mode': 'file',        # 'file' or 'data'
  'pasted_data': '',            # Raw text when source_mode='data'
  'x_axis_column': None,        # Column used as X
  'x_axis_title': 'x',
  'y_axis_title': 'y',
  'yaxis_titles': {},           # {1: 'title', 2: 'title'}
  'yaxis1_units': 'Raw',
  'yaxis2_units': 'Raw',
  'separate_yaxes': False,      # Whether dual Y is active
  'legend_position': 'top-left',
  'legend_title': '',
  'show_grid': True,
  'show_legend': True,
  'trace_mode': 'lines',        # 'lines', 'markers', 'lines+markers'
  'line_style': 'solid',        # 'solid', 'dash', 'dot', 'dashdot'
  'extend_two_point_lines': False,
  'show_intersections': False,
  'show_roots_intercepts': False,
  'line_range_min': 0.0,
  'line_range_max': 1.0,
  'pasted_point_mode': 'line_only',
  'pasted_marker_count': 25,
  'panel_number': 1,
}
```

**Per graph card (file mode):**
```
┌─────────────────────────────────────────────────────┐
│ Panel 1                                        [×]  │
│ Files (max 3): [file1.txt▼] [file2.txt▼]           │
│ X-axis column: [column▼]  X-title: [____]          │
│ Columns: [☑ col1] [☑ col2] [☐ col3] ...            │
│ Column settings:                                    │
│   col1: Y-Axis [Left▼]  Legend label [____]        │
│   col2: Y-Axis [Right▼] Legend label [____]        │
│ Y1 title: [____]  Y1 units: [Raw▼]                 │
│ Y2 title: [____]  Y2 units: [Raw▼]                 │
│ Trace: [Lines▼]  Style: [Solid▼]                   │
│ Display: [☑ Grid] [☑ Legend] [☐ Intersections]     │
│                                                     │
│           GraphCanvas (line chart)                  │
└─────────────────────────────────────────────────────┘
```

**Per graph card (data/paste mode):**
- `QTextEdit` for direct paste of tabular data
- Auto-parses on change → same column selection UI below

Signals:
- File selector changed → reload columns, redraw
- Column checkboxes → redraw
- Any setting changed → redraw
- Close button → remove card

**Deliverable:** File mode and paste mode both work → dual Y-axis → all style controls work.

---

## Implementation Order

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4
  Shell      Single       Multi       Graphs
  only       View         View
```

Each phase is independently runnable. Do not start next phase until current phase is verified working.

---

## Key Design Decisions

1. **No web server** — pure desktop, all state in Python objects.
2. **ViewerState stays identical** — same dataclass fields as Dash; enables shared logic.
3. **pyvista for VTK** — same library as Dash `VTKReader`; no change to reading logic.
4. **matplotlib for rendering** — replaces Plotly heatmaps/charts; `FigureCanvasQTAgg` embeds in Qt.
5. **Signals/slots replace callbacks** — each widget owns its signal connections; no global registry.
6. **Immutable state** — `dataclasses.replace()` for every state change (same pattern as Dash).
7. **TAB_CONFIGS identical** — copy verbatim; defines all dataset types, file globs, scalar fields.
8. **Grid cache for Multi View** — avoids re-reading VTK on shared-control changes.
9. **One file per concern** — max ~400 lines per file.
10. **Auto-discovery**: panels auto-detect scalars/tensors from VTK file when not in TAB_CONFIGS.

---

## Features Per Phase (Complete Checklist)

### Phase 2 Single View
- [x] Project folder scanning (`scan_project_folders`)
- [x] Dataset detection from VTK folder (`DatasetRegistry`)
- [x] VTK file reading with pyvista (`VTKReader`)
- [x] 2D slice extraction with bilinear interpolation (resolution=400)
- [x] Auto-axis detection for flat meshes (dx/dy/dz ≤ 1)
- [x] Scalar field selector (configured + auto-discovered)
- [x] Auto-discovery: tensors (Voigt 6, full 9, vector 3) + scalar
- [x] Timestep file selector (sorted by filename)
- [x] Slice slider + numeric input (hidden for 2D meshes)
- [x] Range min/max inputs + dual slider (synchronized)
- [x] Reset range button (restores from data stats)
- [x] Two-click range selection on heatmap click
- [x] Palette selector (6 palettes)
- [x] Full Scale (dynamic colorscale) toggle
- [x] Dynamic colorscale: 4 cases (normal/black-prepend/green-append/both)
- [x] Aspect-ratio-correct heatmap (width = height × nx/ny)
- [x] Separate colorbar (5 tick labels, scalar label + units)
- [x] Interfaces overlay (PhaseField contour band 1.5–3.5, semi-transparent black)
- [x] Phase overlay file matching by timestep (3-strategy: exact, 8-digit, numeric)
- [x] Map title display
- [x] Line Scan mode toggle (click_mode: range ↔ linescan)
- [x] Horizontal/Vertical scan direction selector
- [x] Show/hide line overlay on heatmap
- [x] Line scan chart (row or column profile)
- [x] Histogram: field selector, bins slider (10–200), chart
- [x] PNG export (4× scale)
- [x] Dynamic inner tabs (add/close panels)

### Phase 3 Multi View
- [x] Same PanelWidget per project
- [x] Shared controls (scalar, slice, range, palette)
- [x] Grid cache (file_path, scalar, slice) → (X, Y, Z, stats)
- [x] 2-column scrollable grid layout
- [x] "Export All" PNG

### Phase 2 Single View (additions)
- [x] `ReaderCache` singleton — avoids re-reading VTK files (keyed by file path)
- [x] `group_projects_by_parent()` — hierarchical sidebar: project header + indented VTK/TextData subfolders
- [x] Project scanner creates 3 entries per project: root, `/VTK`, `/TextData`
- [x] `scipy.interpolate.griddata` for bilinear interpolation to regular grid
- [x] `VTKReader._interpolation_cache` — avoids re-interpolating same slice

### Phase 4 Custom Graph
- [x] TextData file discovery (TextData/ subdir + fallback subdirs)
- [x] Auto-parsing (pandas, auto-separator, auto-header)
- [x] Max 3 files per panel
- [x] `source_mode='file'` — file picker (QFileDialog or project list)
- [x] `source_mode='data'` — direct paste via QTextEdit ("Add Data" button)
- [x] X-axis column selector + custom X-axis title
- [x] Y-axis column multi-select (checkboxes per file)
- [x] Per-column settings: Y-axis side (left/right) + custom legend label
- [x] Dual Y-axis matplotlib chart with per-axis title + units label
- [x] `trace_mode`: lines / markers / lines+markers
- [x] `line_style`: solid / dash / dot / dashdot
- [x] `show_grid`, `show_legend`, `legend_position`, `legend_title`
- [x] `extend_two_point_lines`: extrapolate 2-point datasets within range
- [x] `show_intersections`: vertical lines at trace intersections
- [x] `show_roots_intercepts`: mark zero-crossings
- [x] `line_range_min/max`: domain limit for extrapolation
- [x] Multi-file aggregation per panel (up to 3 files)
- [x] Add/close graph cards

---

## What Is NOT Ported

| Dash feature | Reason |
|---|---|
| `dcc.Location` / URL routing | Desktop app, not needed |
| `dcc.Store` session/local persistence | Use in-memory state; add QSettings later if needed |
| Floating chat (`build_floating_chat`) | Out of scope for v1 |
| Calculation Notebook tab | Separate app (OPPre), out of scope |
| Initializations Explorer | Separate app, out of scope |
| Mechanical Loads Explorer | Separate app, out of scope |
| Server session tracking | No server |
| Dash clientside callbacks | N/A |
| Formula Graphs tab | Out of scope for v1 |
