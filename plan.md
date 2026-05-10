# OPview PySide6 — Conversion Plan

Source: `/mnt/e/RUB/OpenPhase/OPView/` (Dash)
Target: `/mnt/e/RUB/OpenPhase/OPview-pyside6/` (PySide6)

\---

## Implementation Rules

* Use an OOP structure everywhere.
* Always create dedicated classes first, then instantiate and call them from higher-level classes.
* Avoid flat procedural UI code except for the minimal application entry point in `main.py`.
* Keep responsibilities separated: UI widgets, state objects, readers/loaders, and coordination logic must live in different classes.

## App Overview

Three-tab desktop application for visualizing OpenPhase simulation output.

|Tab|Dash name|Function|
|-|-|-|
|Single View|`current`|One project, N dataset panels (heatmap slices)|
|Multi View|`comparison`|Compare N projects side-by-side|
|Custom Graph|`custom-graph`|TextData `.txt/.csv` line charts|

\---

## Technology Mapping (Dash → PySide6)

|Dash / Plotly|PySide6 equivalent|
|-|-|
|`dcc.Tabs`|`QTabWidget`|
|`dcc.Dropdown`|`QComboBox`|
|`dcc.Checklist`|List of `QCheckBox`|
|`dcc.Slider`|`QSlider`|
|`dcc.RangeSlider` (dual)|Two `QSlider` widgets|
|`dcc.Input` (number)|`QDoubleSpinBox` / `QSpinBox`|
|`html.Button`|`QPushButton`|
|`dmc.Switch`|`QCheckBox` styled as toggle|
|`dmc.SegmentedControl`|`QButtonGroup` with toggle buttons|
|`dcc.Graph` (Plotly heatmap)|`matplotlib` via `FigureCanvasQTAgg`|
|`dcc.Graph` (Plotly line chart)|`matplotlib` via `FigureCanvasQTAgg`|
|`dcc.Store`|Python dataclass / dict in-memory|
|`dmc.Modal`|`QDialog`|
|Dash callbacks|Qt signals/slots|
|`html.Div` layout|`QSplitter`, `QHBoxLayout`, `QVBoxLayout`|
|VTK file reading|`pyvista` (used by existing `VTKReader`)|
|Colorscales|`matplotlib` colormaps (custom LinearSegmentedColormap)|
|Assets (PNG logos)|Qt resource system or direct file paths|

\---

## File Structure (Target)

```
OPview-pyside6/
├── main.py                         # Entry point
├── app/
│   ├── \_\_init\_\_.py
│   └── main\_window.py              # QMainWindow, QTabWidget (3 tabs)
├── config/
│   ├── \_\_init\_\_.py
│   ├── tabs.py                     # TAB\_CONFIGS (identical to Dash version)
│   └── constants.py                # Colors, palettes, defaults, extensions
├── data/
│   ├── \_\_init\_\_.py
│   └── text\_sources.py             # GenericTextDataSource, TextDataLoader
├── utils/
│   ├── \_\_init\_\_.py
│   ├── vtk\_reader.py               # VTKReader (pyvista + scipy, port from Dash)
│   ├── vtk\_utils.py                # ReaderCache singleton, get\_reader(), list\_vtk\_files()
│   ├── project\_scanner.py          # scan\_project\_folders(), group\_projects\_by\_parent()
│   └── dataset\_detector.py         # DatasetRegistry, detect\_available\_datasets()
├── viewer/
│   ├── \_\_init\_\_.py
│   ├── state.py                    # ViewerState dataclass (identical to Dash)
│   ├── defaults.py                 # DEFAULTS dict (identical to Dash)
│   ├── colorscale.py               # make\_dynamic\_colorscale() → matplotlib
│   ├── heatmap\_canvas.py           # matplotlib FigureCanvas for heatmap
│   ├── linescan\_canvas.py          # matplotlib FigureCanvas for line scan
│   ├── histogram\_canvas.py         # matplotlib FigureCanvas for histogram
│   └── panel\_widget.py             # Full dataset panel widget
├── single\_view/
│   ├── \_\_init\_\_.py
│   └── tab\_widget.py               # Single View tab
├── multi\_view/
│   ├── \_\_init\_\_.py
│   └── tab\_widget.py               # Multi View tab
├── graphs/
│   ├── \_\_init\_\_.py
│   ├── tab\_widget.py               # Custom Graph tab
│   └── graph\_canvas.py             # matplotlib canvas for line charts
├── sidebar/
│   ├── \_\_init\_\_.py
│   └── sidebar\_widget.py           # Project tree + Add Panel controls
├── assets/                         # PNG icons (same as Dash assets/)
├── requirements.txt
├── opview.bat
└── plan.md
```

\---

## UI Layout Diagrams

### A — Full Application Window

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  \[OP Logo]  OPV iew                                          Documentation ↗    │  ← top bar
├──────────────────────────────────────────────────────────────────────────────────┤
│  VTK  Tabs:  \[ Single View ]  \[ Multi View ]  \[ Custom Graph ]                  │  ← main tab row
├──────────────┬───────────────────────────────────────────────────────────────────┤
│   SIDEBAR    │                    MAIN CONTENT AREA                              │
│   (\~220px)   │              (active tab widget here)                             │
│              │                                                                   │
│  (see B)     │  (see C / D / E depending on active tab)                         │
│              │                                                                   │
│              │                                                                   │
└──────────────┴───────────────────────────────────────────────────────────────────┘
```

\---

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
│ \[+] Add Project Fold │  ← QPushButton, full width
│ \[⊞] Paste Project Pa │  ← QPushButton, full width
│ \[↺] Reload VTK Files │  ← QPushButton, full width
├──────────────────────┤
│  ADD PANEL           │  ← bold label (hidden on Custom Graph tab)
│ \[Select a data type▼]│  ← QComboBox, grouped by module
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

\---

### C — Single View Tab

```
┌───────────────────────────────────────────────────────────────────────┐
│  \[ Stress Tensor × ]  \[ Elastic Strains × ]  \[ + ]                   │  ← inner QTabBar (closeable tabs)
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌── CONTROLS ──────────────────────────────────────────────────┐   │
│   │ \[Project 1     ▼]  \[Stresses\_00032.vts ▼]  \[σ\_xx (MPa)   ▼] │   │  ← Row 1
│   │ Range: \[  -150.0 ] \[ 320.5 ]  \[↺ Reset]  \[○ Range Select]   │   │  ← Row 2
│   │ \[Aqua Fire      ▼]  \[●────────────────●]  \[○ Full Scale]     │   │  ← Row 3 (dual slider)
│   │ Slice (Y-axis):     \[●──────────────────●] \[  64  ]          │   │  ← Row 4 (hidden for 2D)
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌── HEATMAP ───────────────────────────────────────────────────┐   │
│   │  σ\_xx (MPa) — Stresses\_00032.vts    \[○ Interfaces] \[↓ PNG]  │   │  ← top bar
│   │  ┌──────┐  ┌──────────────────────────┐  ┌──────┐          │   │
│   │  │      │  │                          │  │  320 │          │   │
│   │  │  OP  │  │     Heatmap Canvas       │  │  ··· │          │   │  ← logo | heatmap | color bar
│   │  │ Logo │  │  (aspect-correct, click) │  │  0.0 │          │   │
│   │  │      │  │                          │  │ -150 │          │   │
│   │  └──────┘  └──────────────────────────┘  └──────┘          │   │
│   │  \[ Click heatmap to select range (1st click) ]             │   │  ← toast info
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌── LINE SCAN \& HISTOGRAM ANALYSIS ──────────────────────────┐    │
│   │  \[○ Line Scan]  \[○ Show Line]  \[ ↔ Horiz. | ↕ Vert. ]     │    │  ← toolbar
│   │  ┌──────────────────────────────────────────────────────┐  │    │
│   │  │            Line Scan Canvas                          │  │    │
│   │  └──────────────────────────────────────────────────────┘  │    │
│   │  Histogram Field: \[ σ\_xx (MPa) ▼ ]   Bins: \[●──────●] 30  │    │
│   │  ┌──────────────────────────────────────────────────────┐  │    │
│   │  │            Histogram Canvas                          │  │    │
│   │  └──────────────────────────────────────────────────────┘  │    │
│   └────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────┘
```

\---

### D — Multi View Tab

```
┌───────────────────────────────────────────────────────────────────────┐
│  SHARED CONTROLS (applies to all panels below):                       │
│  \[σ\_xx (MPa) ▼]  Slice: \[●──────●] \[64]  \[Aqua Fire ▼]             │
│  Range: \[-150.0] \[320.5]  \[↺]  \[○ Full Scale]                        │
├───────────────────────────────────────────────────────────────────────┤
│  \[ Stress Tensor × ]  \[ + ]          (inner tabs, same as Single)    │
├───────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐           │
│  │  Project1               │  │  Project2               │           │  ← 2-column grid
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │           │
│  │  │   Heatmap Canvas  │  │  │  │   Heatmap Canvas  │  │           │
│  │  └───────────────────┘  │  │  └───────────────────┘  │           │
│  │  \[↓ PNG]                │  │  \[↓ PNG]                │           │
│  └─────────────────────────┘  └─────────────────────────┘           │
│  ┌─────────────────────────┐  ┌─────────────────────────┐           │
│  │  Project3               │  │  Project4               │           │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │           │
│  │  │   Heatmap Canvas  │  │  │  │   Heatmap Canvas  │  │           │
│  │  └───────────────────┘  │  │  └───────────────────┘  │           │
│  │  \[↓ PNG]                │  │  \[↓ PNG]                │           │
│  └─────────────────────────┘  └─────────────────────────┘           │
│  ↑ QScrollArea (vertical scroll when > 2 rows)                       │
└───────────────────────────────────────────────────────────────────────┘
```

Each multi-view panel card (no independent controls — all shared from top bar):

```
┌───────────────────────────────────────┐
│  Project1 / Stresses\_00032.vts        │  ← project name + file
│  ┌─────────────────────┐  ┌────────┐  │
│  │                     │  │   320  │  │
│  │   Heatmap Canvas    │  │   ···  │  │  ← heatmap + color bar side by side
│  │                     │  │  -150  │  │
│  └─────────────────────┘  └────────┘  │
│  \[↓ PNG]                              │
└───────────────────────────────────────┘
```

\---

### E — Custom Graph Tab

```
┌───────────────────────────────────────────────────────────────────────┐
│  \[+ Add or Select Text File]   \[+ Add Data]                           │  ← toolbar
├───────────────────────────────────────────────────────────────────────┤
│  ↓ QScrollArea                                                        │
│                                                                       │
│  ┌── Panel 1 (file mode) ─────────────────────────────────────── \[×]┐│
│  │ Files (max 3):                                                    ││
│  │   \[Project1/StressStrain.txt ▼]  \[+ add file]                    ││
│  │                                                                   ││
│  │ X-axis:  \[ Epsilon\_xx          ▼]   X-title: \[ Strain      ]     ││
│  │                                                                   ││
│  │ Columns from StressStrain.txt:                                    ││
│  │   \[☑ Sigma\_xx]  \[☑ Sigma\_yy]  \[☐ Sigma\_zz]  \[☐ Sigma\_xy]       ││
│  │   Sigma\_xx → Y-Axis: \[Left  ▼]   Legend: \[ Sigma xx     ]        ││
│  │   Sigma\_yy → Y-Axis: \[Right ▼]   Legend: \[ Sigma yy     ]        ││
│  │                                                                   ││
│  │ Y1 title: \[ Stress (MPa) ]    Y1 units: \[ MPa ▼]                 ││
│  │ Y2 title: \[ Stress (MPa) ]    Y2 units: \[ MPa ▼]                 ││
│  │                                                                   ││
│  │ Trace: \[Lines ▼]  Style: \[Solid ▼]  Legend pos: \[Top Left ▼]     ││
│  │ \[☑ Show Grid]  \[☑ Show Legend]  \[☐ Intersections]  \[☐ Roots]     ││
│  │                                                                   ││
│  │ ┌────────────────────────────────────────────────────────────┐   ││
│  │ │                  Graph Canvas                              │   ││
│  │ │              (dual Y-axis line chart)                      │   ││
│  │ └────────────────────────────────────────────────────────────┘   ││
│  └───────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌── Panel 2 (data/paste mode) ───────────────────────────────── \[×]┐│
│  │ Paste data:                                                       ││
│  │  ┌──────────────────────────────────────────────────────────┐    ││
│  │  │ Epsilon\_xx  Sigma\_xx  Sigma\_yy                           │    ││  ← QTextEdit
│  │  │ 0.000       0.0       0.0                                │    ││
│  │  │ 0.001       52.3      48.1                               │    ││
│  │  └──────────────────────────────────────────────────────────┘    ││
│  │ (same column selection + settings UI as file mode below paste)   ││
│  └───────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────┘
```

\---

### F — Add Panel Dropdown (ADD PANEL in sidebar)

When a project is loaded and a dataset detected:

```
┌────────────────────────┐
│ ADD PANEL              │
│ \[Select a data type  ▼]│
│  ──── Mechanics ─────  │
│     Stress Tensor      │  ← only shown if Stresses\_\*.vts files exist
│     Elastic Strains    │
│  ──── Plasticity ────  │
│     CRSS               │
│     Plastic Strain     │
│  ── Unconfigured ───   │
│     PhaseField         │  ← auto-detected, not in TAB\_CONFIGS
│  ● 5 datasets detected │  ← status label, green
└────────────────────────┘
```

\---

### G — Heatmap Controls Detail (Rows 1–4)

```
ROW 1 — File selection
┌─────────────────┐  ┌──────────────────────────┐  ┌──────────────────┐
│ Project 1     ▼ │  │ Stresses\_00032.vts      ▼ │  │ σ\_xx (MPa)     ▼ │
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
 └───────────────┘  │   slider for blue\_cut / red\_cut)   │  └──────────────────┘
                    └────────────────────────────────────┘

ROW 4 — Slice (hidden when mesh is 2D)
 Slice (Y-axis):  ┌─────────────────────────────────────┐  ┌─────┐
                  │  ●────────────────────────────────   │  │  64 │
                  │  (QSlider, min=0, max=ny-1)          │  │(QSp)│
                  └─────────────────────────────────────┘  └─────┘
```

\---

### H — Line Scan Card Detail

```
┌── LINE SCAN \& HISTOGRAM ANALYSIS ─────────────────────────────────────┐
│                                                                        │
│  Toolbar:                                                              │
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ ○ Line Scan    │  │ ○ Show Line │  │ \[ ↔ Horiz. | ↕ Vert. ] │   │
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
│  \[ Click heatmap in Line Scan mode to set position ]                  │
│                                                                        │
│  Histogram Field: \[ σ\_xx (MPa) ▼ ]   Bins: ──●──────────── 30        │
│                                              (QSlider 10-200)         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     Histogram Canvas                            │  │
│  │  count                                                          │  │
│  │  150 ┤   ██                                                     │  │
│  │  100 ┤  ████                                                    │  │
│  │   50 ┤ ██████ ████                                              │  │
│  │    0 └────────────────────────────────── σ\_xx (MPa)            │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

\---

### I — "Paste Project Path" Dialog

```
┌── Select Path ─────────────────────────────────┐
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  C:\\Users\\ali\\Simulations\\Project1        │  │  ← QLineEdit
│  └───────────────────────────────────────────┘  │
│                                                 │
│                    \[ Cancel ]  \[ Add ]          │
└─────────────────────────────────────────────────┘
```

\---

### J — Widget Sizing Reference

|Widget|Size / Policy|
|-|-|
|Sidebar|Fixed 220px width|
|Top bar|Fixed \~50px height|
|Main tab row|Fixed \~36px height|
|Inner tab bar (Single/Multi)|Fixed \~32px height|
|Controls panel (rows 1–4)|Fixed \~130px height|
|Heatmap card (logo+map+colorbar)|Fixed 380px height, width dynamic|
|Logo card|Fixed 80px × 380px|
|Colorbar card|Fixed 110px × 380px|
|Heatmap canvas|380px height, width = 380 × (nx/ny), max 1200px|
|Line scan canvas|\~200px height, full width|
|Histogram canvas|\~200px height, full width|
|Graph canvas (Custom Graph)|\~400px height, full width|
|Multi-view panel card|Min 400px wide, 2-column grid|

\---

## Phase 1 — App Shell (Structure Only, No Logic)

**Goal:** Running window with correct layout skeleton. No VTK. No data. Placeholders everywhere.

### 1.1 `main.py`

* `QApplication` init
* Instantiate `MainWindow`, show, exec

### 1.2 `app/main\_window.py` — `MainWindow(QMainWindow)`

* Top bar: OP logo + "OPView" title label (left), "Documentation" link label (right)
* Tab row below top bar: `QTabWidget` with three tabs

  * Tab 0: "Single View"
  * Tab 1: "Multi View"
  * Tab 2: "Custom Graph"
* Below tabs: `QSplitter` (horizontal)

  * Left: `SidebarWidget` (fixed \~220px)
  * Right: stacked area that shows the active tab's content widget

### 1.3 `sidebar/sidebar\_widget.py` — `SidebarWidget(QWidget)`

Sections (vertical layout, top to bottom):

**PROJECTS section**

* Label: "PROJECTS"
* `QScrollArea` containing `QWidget` with `QVBoxLayout`

  * For each project: bold `QLabel` (project name) + indented `QCheckBox` per VTK folder
* Three buttons (full-width):

  * "Add Project Folder" (opens `QFileDialog`)
  * "Paste Project Path" (opens `QDialog` with `QLineEdit`)
  * "Reload VTK Files"

**ADD PANEL section** (context-sensitive — shows relevant controls per active tab)

* "ADD PANEL" label
* `QComboBox` — "Select a data type" placeholder
* Detection status label: "No project loaded" (green text)

### 1.4 `single\_view/tab\_widget.py` — `SingleViewTab(QWidget)`

* Placeholder `QLabel("Add a module from the dropdown to get started")`
* Inner tab row: `QTabBar` for dynamic panel tabs (empty for now)
* Main content area: `QStackedWidget` for panel contents

### 1.5 `multi\_view/tab\_widget.py` — `MultiViewTab(QWidget)`

* Same skeleton as `SingleViewTab`
* Placeholder label

### 1.6 `graphs/tab\_widget.py` — `CustomGraphTab(QWidget)`

* Placeholder label
* Two buttons: "Add or Select Text File", "Add Data"
* Empty panels container (`QScrollArea`)

### 1.7 `config/tabs.py`

Copy TAB\_CONFIGS exactly from Dash version — same `tensor\_scalars()`, `TabConfig`, `ConfigManager`.

### 1.8 `config/constants.py`

```python
DEFAULTS = {
    "axis": "y",
    "interpolation\_resolution": 400,
    "colorA": "blue",
    "colorB": "red",
    "zsmooth": "best",
    "range\_selection\_mode": "two\_click",
    "slice\_axis\_label": "Slice Index (Y-axis)",
}

PALETTES = {
    "aqua-fire":          \["#00328f", "#00afb8", "#fffbdf", "#ffbc3c", "#a51717"],
    "blue-to-red":        \["#a51717", "#fbbc3c", "#fffbe0", "#00afb8", "#00328f"],
    "spectral-lowblue":   \["#5e4fa2", "#3f96b7", "#b3e0a3", "#fdd280", "#9e0142"],
    "cool-warm-extended": \["#000059", "#295698", "#fcf5e6", "#f7d5b2", "#590c36"],
    "steel":              \["#0b2545", "#3e5c76", "#f6f9ff", "#f4c06a", "#b3541e"],
    "ice-sunset":         \["#1c3d5a", "#3aa0c8", "#ffffff", "#f9d976", "#f47068"],
}

ALLOWED\_VTK\_EXTENSIONS = {'.vts', '.vtu', '.vti', '.vtk', '.vtp'}
ALLOWED\_TEXTDATA\_EXTENSIONS = \['.txt', '.csv', '.dat', '.opd']

TEXTDATA\_FOLDER\_VARIANTS = \["TextData", "Textdata", "textdata", "TEXTDATA"]

SKIP\_FOLDERS = {
    '.git', '.vscode', '.claude', '\_\_pycache\_\_',
    'venv', 'assets', 'utils', 'viewer', 'node\_modules',
}

TENSOR\_COMPONENTS = \['xx', 'yy', 'zz', 'xy', 'yz', 'zx']
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

\---

## Phase 2 — Single View (VTK Panel + Heatmap)

**Goal:** Load a project folder, pick a dataset, display a 2D heatmap slice with full controls.

### 2.1 `utils/project\_scanner.py` — `scan\_project\_folders()`

Port from Dash `utils/project\_scanner.py` verbatim:

* Scans a base directory for subdirs containing `VTK/` or `TextData/` subfolders
* Returns `dict\[name → {path, has\_vtk, has\_textdata, vtk\_path, textdata\_path, is\_subdirectory, parent\_folder}]`
* **Three entries per project**: `"Project1"` (root), `"Project1/VTK"` (vtk-only), `"Project1/TextData"` (text-only)
* Skips `SKIP\_FOLDERS` and hidden directories
* `group\_projects\_by\_parent(folders)` → groups entries by parent for hierarchical sidebar display

  * Top-level: project name as header label
  * Nested: VTK and TextData subfolders as checkboxes indented below

### 2.2 `utils/dataset\_detector.py` — `DatasetRegistry`

Port from Dash `config/dataset\_registry.py` + `utils/dataset\_detector.py`:

* `detect(vtk\_folder, tab\_configs)` → list of `DatasetInfo` (configured + unconfigured)
* Each `DatasetInfo`: id, label, file\_glob, files (sorted), tab\_id
* Unconfigured VTK files get auto-created generic panel entries
* `get\_dropdown\_options()` → grouped `QComboBox` options for ADD PANEL

### 2.3 `utils/vtk\_reader.py` — `VTKReader` + `utils/vtk\_utils.py` — `ReaderCache`

Port from Dash `utils/vtk\_reader.py` + `utils/vtk\_utils.py` verbatim:

**`VTKReader`**:

* Uses `pyvista` for file reading
* `load\_file()` — reads `.vts/.vtu/.vti/.vtk`, detects dimensions, is\_3d
* `get\_interpolated\_slice(axis, index, scalar\_name, component, resolution=400)` → `(X\_grid, Y\_grid, Z\_grid, stats)`

  * For 2D meshes: `\_extract\_2d\_data()` — detects active axes from std deviation
  * For 3D meshes: PyVista slice normal, then **`scipy.interpolate.griddata`** bilinear interpolation to resolution×resolution grid
  * Internal cache: `\_interpolation\_cache` keyed by `(scalar\_name, component, axis, index, resolution)`
* `\_select\_component(array, component)` → picks column from tensor array; if `component=None` → `np.linalg.norm(axis=1)`
* `scalar\_fields` property → `list(mesh.array\_names)`
* `dimensions` attribute → `(nx, ny, nz)` tuple
* `is\_3d` attribute → bool (True only if all three dims > 1)
* Auto-axis detection in `panel\_widget` (not reader): if `dz≤1` → axis='z', if `dy≤1` → axis='y', if `dx≤1` → axis='x'

**`ReaderCache`** (global singleton in `vtk\_utils.py`):

```python
reader\_cache = ReaderCache()   # global dict\[file\_path → VTKReader]
```

* `get\_reader(file\_path)` → returns cached reader or creates new one
* `reader\_cache.clear()` → called by "Reload VTK Files" button
* Prevents re-reading large VTK files on every interaction

### 2.4 `viewer/state.py`

Copy `ViewerState` dataclass verbatim from Dash version. Full field list:

```python
@dataclass
class ViewerState:
    scalar\_key: str
    scalar\_label: str
    axis: str
    slice\_index: int
    colorA: str
    colorB: str
    palette: str
    threshold: float
    range\_min: float
    range\_max: float
    file\_path: str
    scale: float = 1.0
    units: Optional\[str] = None
    click\_count: int = 0
    first\_click: Optional\[float] = None
    clicked\_message: Optional\[str] = None
    colorscale\_mode: str = "normal"        # "normal" or "dynamic"
    line\_scan\_y: Optional\[float] = None
    line\_scan\_x: Optional\[float] = None
    line\_scan\_direction: str = "horizontal"
    click\_mode: str = "range"              # "range" or "linescan"
    line\_overlay\_visible: bool = True
    interfaces\_overlay\_visible: bool = False
```

Copy `initial\_state()` and `from\_dict()` verbatim.

### 2.5 `viewer/colorscale.py`

Port `make\_dynamic\_colorscale()` from Dash `viewer/panel.py`:

* Same 4-case logic (normal / black-prepend / green-append / both)
* Output: `matplotlib.colors.LinearSegmentedColormap` for use with `imshow()`
* Separate helper: `palette\_to\_cmap(palette\_name)` → returns correct colormap per mode

### 2.6 `viewer/heatmap\_canvas.py` — `HeatmapCanvas(FigureCanvasQTAgg)`

* Single matplotlib figure
* `ax\_map`: main heatmap (aspect-correct, no axis ticks)
* `ax\_colorbar`: colorbar axis (separate, right side)
* `update(Z\_grid, cmap, vmin, vmax, title, x\_label, y\_label)` — redraws without recreating figure
* Preserves aspect ratio from data dimensions: `fig\_width = effective\_height \* (nx / ny)`
* Interfaces overlay: `ax\_map.contourf()` call added on top when enabled
* Click handling: `mpl\_connect('button\_press\_event', ...)` → emits Qt signal with (x, y) point
* Line overlay: `ax\_map.axhline()` or `ax\_map.axvline()` drawn at scan position
* `save\_png(path)` — export at 4× scale (matching Dash `toImageButtonOptions: {scale: 4}`)

### 2.7 `viewer/linescan\_canvas.py` — `LineScanCanvas(FigureCanvasQTAgg)`

Port `\_build\_line\_scan\_figure()` from Dash `viewer/panel.py`:

* Horizontal scan: extract row from Z\_grid at nearest Y position → plot vs X
* Vertical scan: extract column from Z\_grid at nearest X position → plot vs Y
* Shows scan line overlay on `heatmap\_canvas` when `line\_overlay\_visible`

### 2.8 `viewer/histogram\_canvas.py` — `HistogramCanvas(FigureCanvasQTAgg)`

Port `\_build\_histogram\_figure()` from Dash `viewer/panel.py`:

* `ax.hist(Z\_grid.flatten(), bins=n\_bins)` with scalar label + units on x-axis
* Bins count: 10–200 (controlled by `QSlider`)

### 2.9 `viewer/panel\_widget.py` — `PanelWidget(QWidget)`

Full panel layout — see diagrams **C** (Single View), **G** (controls detail), **H** (line scan detail).

Summary (vertical stack):

```
Controls panel  (rows 1–4, \~130px)  ← see diagram G
Heatmap area    (logo + map + colorbar, 380px fixed height)
  └─ top bar: title + \[○ Interfaces Overlay] + \[↓ PNG]
Line Scan card  (toolbar + LineScanCanvas + histogram controls + HistogramCanvas)
```

**Scalar field auto-discovery** (when dataset not in TAB\_CONFIGS):

* After loading a file, read `reader.scalar\_fields`
* For each array: detect if scalar (1D) or tensor/vector (2D)
* Tensor: add `(Norm)` entry + each component (`\[xx]`, `\[yy]` etc.)
* Infer component labels from VTK metadata or by count: 6→Voigt, 9→full 3×3, 3→vector

**Two-click range selection** (click\_mode = "range"):

* First click: sets `range\_min`
* Second click: sets `range\_max`
* Updates min/max inputs and dual slider simultaneously
* Toast notification: "Range selected: \[lo, hi]"

**Interfaces overlay**:

* Toggle `interfaces\_overlay\_visible` in state
* Locate matching `PhaseField\_XXXXXXXX.vts` from same VTK dir at same timestep
* Draw `contourf()` band from 1.5–3.5 in semi-transparent black on top of heatmap
* `\_phase\_overlay\_file()` strategy: exact match → 8-digit padded → numeric search

**Signals/slots replacing Dash callbacks:**

* `scalar\_combo.currentIndexChanged` → reload data, redraw
* `file\_combo.currentIndexChanged` → reload file, reset range, redraw
* `project\_combo.currentIndexChanged` → update file list, reload
* `slice\_slider.valueChanged` / `slice\_input.valueChanged` → extract new slice, redraw
* `range\_min\_spin.valueChanged` / `range\_max\_spin.valueChanged` → update range, redraw
* `range\_slider (dual).valueChanged` → sync min/max inputs, redraw
* `reset\_btn.clicked` → restore range from data stats
* `palette\_combo.currentIndexChanged` → rebuild colormap, redraw
* `fullscale\_check.toggled` → toggle dynamic colorscale mode
* `interfaces\_check.toggled` → toggle overlay, redraw
* `linescan\_check.toggled` → switch click\_mode
* `show\_line\_check.toggled` → show/hide line on heatmap
* `direction\_btn\_group` (↔/↕) → change scan direction
* `histogram\_field\_combo.currentIndexChanged` → recompute histogram
* `bins\_slider.valueChanged` → recompute histogram
* `download\_btn.clicked` → `HeatmapCanvas.save\_png()`
* `heatmap\_canvas.clicked` → dispatch to range-select or line-scan handler

State: `ViewerState` instance per panel, updated via `dataclasses.replace()` on every change.

### 2.10 `single\_view/tab\_widget.py` — Full implementation

* `add\_panel(dataset\_info)`:

  * Creates `PanelWidget(dataset\_info)`
  * Adds a closeable tab to inner `QTabBar` + panel to `QStackedWidget`
* Sidebar "ADD PANEL" combo → `add\_panel()`
* Project checkboxes → `on\_projects\_changed()` → update file options in all panels
* Inner tab close (×) button → remove panel
* Dataset registry updates the ADD PANEL dropdown options with detected datasets

**Deliverable:** Load project → select dataset → heatmap renders → all controls work → line scan → histogram.

\---

## Phase 3 — Multi View

**Goal:** Same panel layout as Single View but N projects displayed side-by-side.

### 3.1 `multi\_view/tab\_widget.py` — `MultiViewTab(QWidget)`

* Uses same `PanelWidget` from Phase 2
* **Shared controls** across all panels: scalar field, slice index, palette, range min/max

  * One `QComboBox` (scalar), one `QSlider` (slice), one range pair, one palette combo
  * All panels update together when shared controls change
* Layout: `QScrollArea` → `QWidget` with `QGridLayout` (2 columns)
* Each panel is locked to one project (no project picker inside panel)
* Panel header: shows project name prominently

### 3.2 Grid cache for performance

Port `comparison\_grid\_cache\_data` from Dash:

```python
\_grid\_cache: dict\[tuple, tuple] = {}  # (file\_path, scalar\_key, slice\_index) → (X, Y, Z, stats)
```

Cache invalidated on "Reload VTK Files".

### 3.3 PNG export

* "Export All" button → saves each panel heatmap as `{project}\_{dataset}\_{timestep}.png`

### 3.4 Differences from Single View

|Feature|Single View|Multi View|
|-|-|-|
|Projects per panel|1 (switchable)|1 fixed per panel|
|Panel count|1 per dataset type|1 per selected project|
|Shared controls|No (each panel independent)|Yes (scalar, slice, range, palette)|
|Scroll|No|Yes (QScrollArea)|
|Grid cache|No|Yes|

**Deliverable:** Check two projects → panels appear side-by-side → shared controls sync all panels.

\---

## Phase 4 — Custom Graph (TextData)

**Goal:** Load `.txt` / `.csv` / `.dat` / `.opd` TextData files and plot selected columns as line charts.

### 4.1 `data/text\_sources.py` — `GenericTextDataSource`

Port from Dash `data/sources.py`:

* Auto-detects separator (tab, space, comma) and header row using `pandas`
* `load(file\_path)` → `DataFrame`
* `get\_columns()` → list of column names
* `get\_column\_data(name)` → numpy array

### 4.2 `utils/project\_scanner.py` — TextData discovery extension

* `get\_textdata\_files(project\_folders)`:

  * For each loaded project, scan `TextData/` subdir
  * Also scan non-VTK subdirs (fallback)
  * Returns sorted, deduplicated list of file paths matching `ALLOWED\_TEXTDATA\_EXTENSIONS`

### 4.3 `graphs/graph\_canvas.py` — `GraphCanvas(FigureCanvasQTAgg)`

Port from Dash `ui/graphs.py`:

* Multi-line matplotlib plot with dual Y-axis support
* `update(panel\_state)` → redraws from panel state dict
* Respects: `trace\_mode` (lines/markers/lines+markers), `line\_style` (solid/dash/dot)
* Legend: position (`top-left`, `top-right`, etc.), custom title, show/hide
* Grid: show/hide toggle
* Dual Y-axis: each column assigned to Y1 or Y2, each with own title + units label
* `show\_intersections`: draw vertical lines at intersection points between traces
* `show\_roots\_intercepts`: mark zero-crossings
* `extend\_two\_point\_lines`: extrapolate 2-point datasets as infinite lines within `line\_range\_min/max`

### 4.4 `graphs/tab\_widget.py` — `CustomGraphTab(QWidget)` (full)

Port from Dash `ui/graphs.py` + `callbacks/graphs\_manager.py`:

**Toolbar (top):**

* "Add or Select Text File" → creates panel in `source\_mode='file'`
* "Add Data" → creates panel in `source\_mode='data'` (paste text directly)

**Panel state dict** (complete — carried in memory per panel):

```python
{
  'files': \[],                  # Up to 3 file paths
  'columns\_by\_file': {},        # {file\_path: \[col\_names\_selected]}
  'column\_settings': {},        # {file\_path: {col: {yaxis, legend\_label}}}
  'source\_mode': 'file',        # 'file' or 'data'
  'pasted\_data': '',            # Raw text when source\_mode='data'
  'x\_axis\_column': None,        # Column used as X
  'x\_axis\_title': 'x',
  'y\_axis\_title': 'y',
  'yaxis\_titles': {},           # {1: 'title', 2: 'title'}
  'yaxis1\_units': 'Raw',
  'yaxis2\_units': 'Raw',
  'separate\_yaxes': False,      # Whether dual Y is active
  'legend\_position': 'top-left',
  'legend\_title': '',
  'show\_grid': True,
  'show\_legend': True,
  'trace\_mode': 'lines',        # 'lines', 'markers', 'lines+markers'
  'line\_style': 'solid',        # 'solid', 'dash', 'dot', 'dashdot'
  'extend\_two\_point\_lines': False,
  'show\_intersections': False,
  'show\_roots\_intercepts': False,
  'line\_range\_min': 0.0,
  'line\_range\_max': 1.0,
  'pasted\_point\_mode': 'line\_only',
  'pasted\_marker\_count': 25,
  'panel\_number': 1,
}
```

**Per graph card (file mode):**

```
┌─────────────────────────────────────────────────────┐
│ Panel 1                                        \[×]  │
│ Files (max 3): \[file1.txt▼] \[file2.txt▼]           │
│ X-axis column: \[column▼]  X-title: \[\_\_\_\_]          │
│ Columns: \[☑ col1] \[☑ col2] \[☐ col3] ...            │
│ Column settings:                                    │
│   col1: Y-Axis \[Left▼]  Legend label \[\_\_\_\_]        │
│   col2: Y-Axis \[Right▼] Legend label \[\_\_\_\_]        │
│ Y1 title: \[\_\_\_\_]  Y1 units: \[Raw▼]                 │
│ Y2 title: \[\_\_\_\_]  Y2 units: \[Raw▼]                 │
│ Trace: \[Lines▼]  Style: \[Solid▼]                   │
│ Display: \[☑ Grid] \[☑ Legend] \[☐ Intersections]     │
│                                                     │
│           GraphCanvas (line chart)                  │
└─────────────────────────────────────────────────────┘
```

**Per graph card (data/paste mode):**

* `QTextEdit` for direct paste of tabular data
* Auto-parses on change → same column selection UI below

Signals:

* File selector changed → reload columns, redraw
* Column checkboxes → redraw
* Any setting changed → redraw
* Close button → remove card

**Deliverable:** File mode and paste mode both work → dual Y-axis → all style controls work.

\---

## Implementation Order

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4
  Shell      Single       Multi       Graphs
  only       View         View
```

Each phase is independently runnable. Do not start next phase until current phase is verified working.

\---

## Key Design Decisions

1. **No web server** — pure desktop, all state in Python objects.
2. **ViewerState stays identical** — same dataclass fields as Dash; enables shared logic.
3. **pyvista for VTK** — same library as Dash `VTKReader`; no change to reading logic.
4. **matplotlib for rendering** — replaces Plotly heatmaps/charts; `FigureCanvasQTAgg` embeds in Qt.
5. **Signals/slots replace callbacks** — each widget owns its signal connections; no global registry.
6. **Immutable state** — `dataclasses.replace()` for every state change (same pattern as Dash).
7. **TAB\_CONFIGS identical** — copy verbatim; defines all dataset types, file globs, scalar fields.
8. **Grid cache for Multi View** — avoids re-reading VTK on shared-control changes.
9. **One file per concern** — max \~400 lines per file.
10. **Auto-discovery**: panels auto-detect scalars/tensors from VTK file when not in TAB\_CONFIGS.

\---

## Features Per Phase (Complete Checklist)

### Phase 2 Single View

* \[x] Project folder scanning (`scan\_project\_folders`)
* \[x] Dataset detection from VTK folder (`DatasetRegistry`)
* \[x] VTK file reading with pyvista (`VTKReader`)
* \[x] 2D slice extraction with bilinear interpolation (resolution=400)
* \[x] Auto-axis detection for flat meshes (dx/dy/dz ≤ 1)
* \[x] Scalar field selector (configured + auto-discovered)
* \[x] Auto-discovery: tensors (Voigt 6, full 9, vector 3) + scalar
* \[x] Timestep file selector (sorted by filename)
* \[x] Slice slider + numeric input (hidden for 2D meshes)
* \[x] Range min/max inputs + dual slider (synchronized)
* \[x] Reset range button (restores from data stats)
* \[x] Two-click range selection on heatmap click
* \[x] Palette selector (6 palettes)
* \[x] Full Scale (dynamic colorscale) toggle
* \[x] Dynamic colorscale: 4 cases (normal/black-prepend/green-append/both)
* \[x] Aspect-ratio-correct heatmap (width = height × nx/ny)
* \[x] Separate colorbar (5 tick labels, scalar label + units)
* \[x] Interfaces overlay (PhaseField contour band 1.5–3.5, semi-transparent black)
* \[x] Phase overlay file matching by timestep (3-strategy: exact, 8-digit, numeric)
* \[x] Map title display
* \[x] Line Scan mode toggle (click\_mode: range ↔ linescan)
* \[x] Horizontal/Vertical scan direction selector
* \[x] Show/hide line overlay on heatmap
* \[x] Line scan chart (row or column profile)
* \[x] Histogram: field selector, bins slider (10–200), chart
* \[x] PNG export (4× scale)
* \[x] Dynamic inner tabs (add/close panels)

### Phase 3 Multi View

* \[x] Same PanelWidget per project
* \[x] Shared controls (scalar, slice, range, palette)
* \[x] Grid cache (file\_path, scalar, slice) → (X, Y, Z, stats)
* \[x] 2-column scrollable grid layout
* \[x] "Export All" PNG

### Phase 2 Single View (additions)

* \[x] `ReaderCache` singleton — avoids re-reading VTK files (keyed by file path)
* \[x] `group\_projects\_by\_parent()` — hierarchical sidebar: project header + indented VTK/TextData subfolders
* \[x] Project scanner creates 3 entries per project: root, `/VTK`, `/TextData`
* \[x] `scipy.interpolate.griddata` for bilinear interpolation to regular grid
* \[x] `VTKReader.\_interpolation\_cache` — avoids re-interpolating same slice

### Phase 4 Custom Graph

* \[x] TextData file discovery (TextData/ subdir + fallback subdirs)
* \[x] Auto-parsing (pandas, auto-separator, auto-header)
* \[x] Max 3 files per panel
* \[x] `source\_mode='file'` — file picker (QFileDialog or project list)
* \[x] `source\_mode='data'` — direct paste via QTextEdit ("Add Data" button)
* \[x] X-axis column selector + custom X-axis title
* \[x] Y-axis column multi-select (checkboxes per file)
* \[x] Per-column settings: Y-axis side (left/right) + custom legend label
* \[x] Dual Y-axis matplotlib chart with per-axis title + units label
* \[x] `trace\_mode`: lines / markers / lines+markers
* \[x] `line\_style`: solid / dash / dot / dashdot
* \[x] `show\_grid`, `show\_legend`, `legend\_position`, `legend\_title`
* \[x] `extend\_two\_point\_lines`: extrapolate 2-point datasets within range
* \[x] `show\_intersections`: vertical lines at trace intersections
* \[x] `show\_roots\_intercepts`: mark zero-crossings
* \[x] `line\_range\_min/max`: domain limit for extrapolation
* \[x] Multi-file aggregation per panel (up to 3 files)
* \[x] Add/close graph cards

\---

## What Is NOT Ported

|Dash feature|Reason|
|-|-|
|`dcc.Location` / URL routing|Desktop app, not needed|
|`dcc.Store` session/local persistence|Use in-memory state; add QSettings later if needed|
|Floating chat (`build\_floating\_chat`)|Out of scope for v1|
|Calculation Notebook tab|Separate app (OPPre), out of scope|
|Initializations Explorer|Separate app, out of scope|
|Mechanical Loads Explorer|Separate app, out of scope|
|Server session tracking|No server|
|Dash clientside callbacks|N/A|
|Formula Graphs tab|Out of scope for v1|



