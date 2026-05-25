# OpenPhase Post-Processing Suite

## Overview
The OpenPhase Post-Processing Suite is an interactive application for inspecting simulation outputs through three primary work modes:

- **Single View** for detailed inspection of one active dataset.
- **Multi View** for side-by-side comparison across multiple selected files.
- **Custom Graph** for plotting trends from `TextData` files.

Use the **Documentation** button in the header or **Help > Documentation** from the menu to open this local guide at any time.

Supported visualization file types are: `.vtk`, `.vti`, `.vtp`, `.vtr`, `.vts`.

## Getting Started
1. In the **PROJECTS** sidebar, select one or more project entries to load data into the app context.
2. If your project is not listed, click **Add Project Folder** and select the folder.
3. Choose the top tab based on your task:
   - **Single View** for one dataset.
   - **Multi View** for comparison.
   - **Custom Graph** for `TextData` analysis.
4. Use the relevant **ADD PANEL** selector to add the data type/panel you want to work with.
5. In **Custom Graph**, check the text-data projects you want available, then create a graph tab and choose project, folder, and file inside that tab.

## Common Viewer Controls
The main heatmap viewers (used in `Single View` and `Multi View`) share these controls:

<table style="width:100%; border-collapse:collapse;">
  <thead>
    <tr>
      <th style="border:1px solid #cfd6e4; padding:8px; text-align:left;">Control</th>
      <th style="border:1px solid #cfd6e4; padding:8px; text-align:left;">Outcome</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Select Folder</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Chooses the active project folder for that panel. The available file list updates to that folder.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Select File</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Chooses the VTK file used for rendering. The heatmap updates to the selected file.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Select Field</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Chooses the scalar/component to display. The rendered field and colorbar update.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Range:</strong> (<code>Min</code>, <code>Max</code>, and <strong>Reset</strong>)</td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Sets explicit value bounds. The heatmap contrast and clipping update immediately.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Range Selection on Map</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Enables range picking from map clicks. Selected range limits are applied to the current view.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>palette</strong> dropdown</td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Changes the color palette. The heatmap recolors with the selected palette.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Range slider</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Interactively narrows or widens the visible value interval. Values outside the interval are clipped.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Full Scale</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Restores full-range scaling for the active field. The slider and rendering return to full data span.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Rotation</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Rotates 2D heatmaps by 0, 90, 180, or 270 degrees. Heatmap, overlay, click lookup, and line scans follow the selected orientation.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Interfaces Overlay</strong> / <strong>Show Interfaces</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Toggles interface overlay visibility. Interface boundaries appear/disappear on the map.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Line Scan</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Enables line-scan interaction mode. Click behavior switches to profile sampling.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Show Line</strong></td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Toggles the line marker visibility. The scan line appears/disappears in the view.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Reset</strong> button</td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Restores default range state for the active panel.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>PNG</strong> button</td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Exports the currently shown heatmap as a PNG image.</td>
    </tr>
  </tbody>
</table>

## Single View
### Purpose
Use **Single View** for focused analysis of one dataset panel at a time.

### Workflow
1. Open **Single View**.
2. In **ADD PANEL**, select a data type.
3. In the panel controls, choose **Select Folder**, **Select File**, and **Select Field**.
4. Adjust **Range:** values, **Range slider**, and **palette**.
5. Toggle **Full Scale**, **Interfaces Overlay**, **Line Scan**, and **Show Line** as needed.
6. Click **Reset** to return range settings to default.
7. Click **PNG** to export the current view.

### Typical Use Cases
- Inspecting one dataset at one time/file state.
- Fine-tuning range and palette for feature visibility.
- Producing a single publication or report figure.

## Multi View
### Purpose
Use **Multi View** when you need direct visual comparison across multiple selected files.

### Workflow
1. Open **Multi View**.
2. In **ADD PANEL**, select a data type to compare.
3. In the comparison card, choose **Select Folder** and one or more files in **Select File**.
4. Set **Select Field** for the comparison.
5. Adjust **Range:**, **Range slider**, **palette**, **Full Scale**, and **Show Interfaces**.
6. Use **Reset** when needed.
7. Use the comparison **PNG** export control to capture the current comparison state.

### Layout Behavior
- Multiple heatmaps are displayed in the comparison area for selected files.
- Controls apply at the active comparison group level and update the corresponding comparison views.
- Comparison selection persists while navigating between top tabs during the same session.

### Typical Comparison Workflows
- Compare the same field across different files.
- Compare different projects under consistent palette/range settings.
- Export side-by-side comparison images for reports.

## Custom Graph
### Purpose
Use **Custom Graph** to analyze `TextData` numerically and build multi-series trend plots.

### Workflow
1. Open **Custom Graph**.
2. In **PROJECTS**, check the folders/projects that contain text data files (`.txt`, `.dat`, `.csv`, `.opd`).
3. Click the **+** tab to create an empty graph workspace.
4. In the graph tab, choose **Project**, **Folder**, and **Text File**, then click **Add To Graph**.
5. In **Data Sources:**, select columns to plot from the added file sections.
6. Configure graph settings in the right **Settings** area:
   - **X-Axis**: choose **Column** and edit **Title**.
   - **Display**: set **Legend Pos:**, toggle **Legend** / **Grid**, choose trace mode, and choose line style.
   - **Y-Axis**: edit Y1 and Y2 axis titles.
   - **Column Settings**: set legend labels, trace color, unit conversion, and assign each selected column to `Y1` or `Y2`.
7. Interact directly with the graph (zoom/pan/hover) and repeat adjustments until the plot is final.

### Controls and Outcomes
- **+** tab: creates an empty graph workspace.
- **Project / Folder / Text File** selectors: choose a checked project, one of its text-data folders, and a supported file.
- **Add To Graph**: loads the selected text file into the current graph tab. Column selectors populate for added files.
- Column checklists: selects plotted series. Traces are added/removed from the graph.
- **X-Axis Column**: changes x-data source. All traces replot against the selected x-axis column.
- **Legend Pos:**: moves legend location. It supports plot corners and **Right Outside**.
- **Legend** / **Grid** toggles: show/hide legend and grid lines.
- **Trace:** renders lines, markers, or lines plus sampled markers.
- **Style:** changes the line dash pattern.
- **Column Settings**: routes each trace to an axis, updates label text, chooses line color, and applies conversion (`As-is`, `%`, `MPa`, or `GPa`).

### Typical Use Cases
- Plotting stress/strain or other tabular trends from `TextData`.
- Overlaying multiple files in one chart for trend comparison.
- Preparing graph outputs for analysis notes and publications.

## Exporting Results
- Heatmaps: click the **PNG** button in `Single View` or `Multi View` controls.
- Graphs: use the graph toolbar export action in each `Custom Graph` panel.
- Exported files are saved through your browser/system download flow.

Recommended usage:
- Capture final figure states after setting range/palette/overlays.
- Export comparison snapshots from `Multi View` with consistent settings.
- Export graph images after final axis/unit/legend configuration.

## Troubleshooting
### Empty view
- Confirm a project is selected in **PROJECTS**.
- Confirm a panel is added through **ADD PANEL**.
- Confirm **Select File** and **Select Field** are set.

### Controls disabled
- Ensure the correct top tab is active (`Single View`, `Multi View`, or `Custom Graph`).
- In `Multi View`, select files first; field/range controls remain limited until files are selected.

### Graph not updating
- Ensure `Custom Graph` panel has selected files and columns.
- Check that the selected x-axis column exists in the loaded data.

### Slow interaction
- Reduce the number of simultaneously selected comparison files.
- Reduce active graph traces in `Custom Graph` panels.
- Apply updates in smaller steps (range, then field, then overlays).

## FAQ
**Q: When should I use `Single View` vs `Multi View`?**  
A: Use `Single View` for deep inspection of one panel; use `Multi View` for side-by-side comparison.

**Q: Why do I not see any files in selectors?**  
A: Select a valid project in **PROJECTS** or add one with **Add Project Folder**.

**Q: What is the fastest way to recover display settings?**  
A: Click **Reset** in the active heatmap control area.

**Q: How do I compare several files in one place?**  
A: Open `Multi View`, add a comparison panel, and select multiple entries in **Select File**.

**Q: How do I build a graph from text output?**  
A: Open `Custom Graph`, check the text-data project in **PROJECTS**, click the **+** tab, then choose project/folder/file inside the tab and click **Add To Graph**.

**Q: How do I export what I see?**  
A: Use **PNG** for heatmaps and graph toolbar export for plots.
