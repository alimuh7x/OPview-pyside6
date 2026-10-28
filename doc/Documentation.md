# OPView User Guide

## Overview
The OpenPhase Post-Processing Suite is an interactive application for inspecting simulation outputs through four primary work modes:

- **Single View** for detailed inspection of one active dataset.
- **Multi View** for side-by-side comparison across multiple selected files.
- **Multi Property** for viewing several properties of one file side by side.
- **Custom Graph** for plotting trends from `TextData` files.

Use the **Documentation** button in the header or **Help > Documentation** from the menu to open this local guide at any time.

Supported visualization file types are: `.vtk`, `.vti`, `.vtp`, `.vts`, `.vtu`.
Supported text-data file types for **Custom Graph** are: `.txt`, `.dat`, `.csv`, `.opd`.

## Interface Overview
- **Sidebar** (left): project list, **Add Folder**, **Reload**, the **ADD PANEL** data-type selector, and the text-file browser with **Add External Text File**. Use the toggle button in the header to hide or show the sidebar.
- **Header**: top tabs (`Single View`, `Multi View`, `Multi Property`, `Custom Graph`) and the **Documentation** button.
- **Content area**: the active tab. Each added panel opens in its own closable tab.

### Project Discovery
A project folder is any folder that contains a `VTK/` and/or `TextData/` subfolder. At startup, OPView scans the folder passed on the command line (or the working folder) and lists every project found below it. Files are not watched automatically: click **Reload** in the sidebar after new simulation output is written.

VTK files that match a known OpenPhase output pattern are grouped into named data types (for example PhaseField). Any other VTK file is grouped by file name under **Other Files**, so unknown outputs still appear.

## Starting OPView
```bash
# Linux
./opview.sh [project_or_projects_folder]

# Windows
opview.bat [project_or_projects_folder]
```

| Option / variable | Effect |
|---|---|
| `project_folder` (optional argument) | Folder, or folder containing projects, to scan at startup. |
| `--version` | Prints the OPView version. |
| `OPVIEW_NO_GPU=1` | Forces software rendering. Use on VMs or machines without a usable GPU. On Windows use `OPview-No-GPU.bat`. |
| `OPVIEW_DEBUG=1` | Prints `[DEBUG]` tracing to the console. Off by default. |

## Getting Started
1. In the **PROJECTS** sidebar, select one or more project entries to load data into the app context.
2. If your project is not listed, click **Add Folder** and select the folder.
3. Choose the top tab based on your task:
   - **Single View** for one dataset.
   - **Multi View** for comparison.
   - **Multi Property** for several properties of one file.
   - **Custom Graph** for `TextData` analysis.
4. Use the relevant **ADD PANEL** selector to add the data type/panel you want to work with.
5. In **Custom Graph**, check the text-data projects you want available, then create a graph tab and choose project, folder, and file inside that tab.

## Common Viewer Controls
The main heatmap viewers (used in `Single View`, `Multi View`, and `Multi Property`) share these controls:

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
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>Select Points</strong> (Single View; <em>Range Selection on Map</em> in Multi View)</td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Enables range picking from map clicks. Selected range limits are applied to the current view.</td>
    </tr>
    <tr>
      <td style="border:1px solid #cfd6e4; padding:8px;"><strong>palette</strong> dropdown</td>
      <td style="border:1px solid #cfd6e4; padding:8px;">Changes the color palette. The heatmap recolors with the selected palette. Choose <strong>Discrete Custom</strong> for hard color bands (see <em>Discrete Palette</em> below).</td>
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

### Colour Maps
Choose a colour map in the **palette** dropdown. The same selection exists in `Single View`, `Multi View`, and `Multi Property`.

![Colour maps](images/colour_maps.png)

### Discrete Palette
Select **Discrete Custom** in the palette dropdown to show the field as hard color bands instead of a smooth gradient.

- **+** / **-** add or remove a band (2 to 10 bands). The current band count is shown between the buttons.
- The legend mode selector switches between **Bar** (continuous-style colorbar) and **Boxes** (numbered color boxes).
- The palette is available in `Single View`, `Multi View`, and `Multi Property`.

### Plot Types
| Plot type | Description | Available in |
|---|---|---|
| Heatmap | Continuous color map of the field. | All viewers |
| Contour Lines | Isolines only. | All viewers |
| Contour Filled | Discrete color bands between isolines. | All viewers |
| Contour Filled + Values | Color bands with labelled contour values. | All viewers |
| Heatmap + Contour | Heatmap with isolines on top. | All viewers |
| Threshold | Shows only values inside the selected range as solid color; selected phase fractions can be overlaid. | Single View |
| Difference (next - current) | Difference between the next file and the current file. | Single View |
| \|grad\| | Gradient magnitude of the field. | Single View |

![Plot types](images/plot_types.png)

### Rotation
Click one of the four axis buttons to rotate the map. The heatmap, overlays, click lookup, and line scans follow the selected orientation.

![Rotation](images/rotation.png)

### Colorbar Ticks
Colorbar tick labels are formatted from the tick spacing: integers where possible, fixed decimals otherwise, and scientific notation for very large or small values.

## Single View
### Purpose
Use **Single View** for focused analysis of one dataset panel at a time.

![Single View: map, line scan and histogram](images/single_view_overview.png)

### Workflow
1. Open **Single View**.
2. In **ADD PANEL**, select a data type.
3. In the panel controls, choose **Select Folder**, **Select File**, and **Select Field**.
4. Adjust **Range:** values, **Range slider**, and **palette**.
5. Toggle **Full Scale**, **Interfaces Overlay**, **Line Scan**, and **Show Line** as needed.
6. Click **Reset** to return range settings to default.
7. Click **PNG** to export the current view.

### Additional Single View Features
- **Symbols in labels**: click the **σ** button inside a label field to insert Greek letters, math signs, powers, ion charges (**¹⁺, ²⁺, ³⁺, ⁴⁺**), or SI units at the cursor. This is available in Single View and Multi View colorbar labels, Multi View legends, Multi Property analysis value labels and property rename dialogs, and phase rename dialogs. The same picker is used in Custom Graph. Rename dialogs still require **OK** to apply the name.
- **Full label editor**: the **σ** button opens the complete existing label in an editable text field, with a live formatted preview at the top. The dialog and the original label field synchronize text, cursor and selection in both directions. Move the cursor, select existing text, type replacements, delete text or insert symbols directly in this dialog. Changes are live; **Done**, Enter or closing the popup keeps them. There is no separate insertion buffer.
- **Subscripts and superscripts**: select any part of the full label and click **x₂ Subscript**, **x² Superscript** or **Normal**. With no selection, Subscript and Superscript insert an empty notation template at the cursor so you can type its contents. Label fields use `_` and `^`, for example `σ_xx`, `ε^p`, `σ^xx_yy`, `σ_{x y}` or `ε^{p + 1}`. Previews, plots and exports render the formatting. Older labels with HTML formatting are converted to readable notation when the picker is attached.
- **Editing controls**: **Backspace** removes the selected text or the visible character before the dialog cursor, **Clear** empties both fields, and **Normal** removes formatting from the selected text. Undo/redo in either field updates the other. Blank text stays editable while the popup is open; on closing, the view's usual automatic-title rules still apply. To mix formats, select `xx` and choose Superscript, then select `yy` and choose Subscript; other text keeps its formatting.
- **Greek colorbar text**: on-screen colorbar titles use the same bundled STIX Two Text Italic Greek symbols as Custom Graph. Latin letters and units keep their usual font.
- **Greek graph labels**: line scans and frequency histograms in all three data views, plus Single View time and phase-history graphs, use that same Greek font in axis labels and legends.
- **Vector overlay**: when the selected array is a vector field, arrows are drawn over the heatmap. Arrow density is thinned automatically and the arrows follow the heatmap rotation.
- **Line Scan direction**: choose horizontal or vertical with the direction buttons next to **Line Scan**. The line keeps its relative position when the file extent changes between files.
- **Rotation** buttons (0, 90, 180, 270 degrees) rotate the heatmap, overlays, and line scans together.
- **Average over time**: the history plot below the heatmap shows PhaseField fractions or the whole-field average of the selected scalar for every timestep.
- **Settings** panel: collapse it with the toggle to give the heatmap more room; it shows as a rotated **Settings** rail when collapsed.
- **Unconfigured arrays**: scalar, vector norm, and vector component arrays that have no predefined entry are listed automatically in **Select Field**.
- **Plot types**: see the plot type table above.
- **Unit conversion (from → to)**: two dropdowns next to the colorbar label. *From* follows the data (`Mega (M)` for stresses and CRSS, which are in MPa; a field with no unit offers every prefix and `percent`); pick another if the data is in a different scale. *To* shows the same scale as *from* without the unit chosen there (`—` for no conversion, then `milli`, `base`, `kilo`, ...), so you can go from kilo to base, milli to Mega and so on. The heatmap, colorbar, line scan, histogram and PNG export all use the converted values, and the colorbar title shows the *to* unit. Choosing another scalar resets the pair to that scalar's own unit. Temperature (`K`, `°C`) needs an offset and is only available in Custom Graph.

![Unit conversion](images/single_view_unit_conversion.png)
- **Slice**: for 3D data choose the slice axis (`X`, `Y`, `Z`) and move the slice index.
- **PNG export** produces a high-resolution image (2x scale, 300 DPI) matching the visible layout. When the map is zoomed, the PNG shows the visible region (sampled at a higher resolution so it stays sharp) with the colorbar you currently see. The selection rectangle is drawn only when **Show Rectangle** is on.

### Colors and Region Selection
The colors follow the region you are looking at **automatically**; there is nothing to switch on. With no zoom or selection the colorbar shows the minimum and maximum of the heatmap as drawn (not of the raw dataset). The data itself is never changed.

The **Range** row (min, max, reset) also holds the three region controls, in this order:
- **Select Points** (on by default): click two points on the map to set the color range, as before.
- **Select Rectangle** (off by default): drag a rectangle **without zooming**. The whole sample stays visible, and the colors rescale to the minimum and maximum of the rectangle (values outside it use the end colors of the colorbar). A new drag replaces the rectangle, and **Reset** removes it. Off: drag pans, and mouse-wheel or toolbar zoom works as usual.
- **Show Rectangle** (off by default): draw a thin outline around the selected rectangle. Hiding it only hides the outline; the selection and the colors do not change. The PNG export respects the setting.

The labels shorten (*Points*, *Rectangle*, *Show*) when the panel is narrow so that everything stays on the Range row; hover for the full names. Only a very narrow panel moves the three toggles onto a line just below the Range row.

How they interact:
- **Zoom, pan, Home**: the toolbar above the heatmap (zoom in, zoom out, pan, Home) is always visible. When you zoom or pan, the colors rescale to the visible region; zooming all the way out or pressing **Home** returns to the heatmap's minimum and maximum. The colorbar, the **Range** boxes and the slider update together, without redrawing the heatmap.
- **Manual limits are held**: a range you type, drag on the slider, or pick with **Select Points** stays until you zoom, pan or select a rectangle, which hands the colors back to the automatic range. Changing the time step keeps your manual limits, for example to compare steps on one fixed scale.
- **Reset** always restores the minimum and maximum of the drawn heatmap, however the range was set, including while zoomed or with a rectangle selected. It removes the selected rectangle but keeps the zoom, and the full range is held until you next zoom, pan or select.
- **Select Rectangle** and the click-based modes (**Select Points**, **Line Scan**, **Add Point**) exclude each other, because a drag-select consumes the clicks. Switching one on switches the other off; switching **Select Rectangle** off brings back **Select Points**.
- **Time steps**: the zoom and the selected rectangle are kept when you change the file or play through frames. The colors are recalculated for the new time step.
- **Full Scale** replaces the automatic colors while it is on.
- The automatic colors apply to the **Heatmap** and **Gradient magnitude** plot types with a continuous palette and the **Bar** colorbar. They are not applied for Threshold, Difference, contour plot types, the discrete palette, the **Boxes** legend and phase-fraction fields.
- **Animation** (MP4) uses the single range that is set when you start it, so every frame is read on the same scale.

### Linked Single View Tabs
Changing the timestep in one dataset tab selects that same numeric timestep in the other tabs when it exists. File-list order does not need to match; tabs without that timestep keep their current file. Rotation selections are also shared across Single View dataset tabs.

### Playback and Animation
When a dataset has several files (timesteps), the playback bar below the heatmap provides:
- **First**, **Previous**, **Next**, and **Last** frame buttons and a frame slider with tick marks. The frame label shows the current and total frame.
- **Animate**: opens the animation player, which loads all frames and plays them with play, pause, stop, a frame slider, and an FPS selector. **MP4** exports the animation as a video (requires `ffmpeg`).
- With the **Threshold** plot type, the animation applies the threshold range and any selected phase-fraction overlays to every frame.

### History Plots Below the Heatmap
![Average over time](images/single_view_average_over_time.png)

- **Phase fractions**: for PhaseField data, the volume fraction of each phase is plotted for every timestep. The **dt** field sets the time step used for the time axis. For other scalars the plot shows the whole-field average of the selected scalar.
- **Plot Over Time**: click **Add Point** (it shows **Add Point: ON** while active), then click the heatmap to pick one or more points. Each point is labelled P1, P2, ... and can be removed with its **X** button. **Calculate** plots one curve per point over all timesteps; **Use Same Points** makes this panel follow the points picked in other Single View panels; **Manual** lets you enter point coordinates; **Cancel** aborts picking; **Clear** removes the points; the **Show points** checkbox toggles the point markers on the heatmap.

![Plot over time](images/single_view_plot_over_time.png)

### Analysis Panel
The **Analysis** section next to the heatmap contains:
- **Line Scan**: click the heatmap to sample a profile along a horizontal or vertical line (**Direction:**).

![Line scan](images/single_view_line_scan.png)

- **Histogram**: value distribution of the current field; **Bins:** sets the number of bins (fewer bins give a coarse shape, more bins show detail).

![Histogram](images/single_view_histogram.png)

### Reloading Data
Click **Reload** in the sidebar to refresh after the simulation writes new output. Files are not watched automatically. Reload clears cached VTK data, adds newly created files of the active dataset to **Select File**, and removes files that were deleted from disk.

### Typical Use Cases
- Inspecting one dataset at one time/file state.
- Fine-tuning range and palette for feature visibility.
- Producing a single publication or report figure.

## Multi View
### Purpose
Use **Multi View** when you need direct visual comparison across multiple selected files.

![Multi View: several time steps side by side](images/multi_view_overview.png)

### Workflow
1. Open **Multi View**.
2. In **ADD PANEL**, select a data type to compare.
3. In the comparison card, choose **Select Folder** and one or more files in **Select File**.
4. Set **Select Field** for the comparison.
5. Adjust **Range:**, **Range slider**, **palette**, **Full Scale**, and **Show Interfaces**.
6. Use **Reset** when needed.
7. Use the comparison **PNG** export control to capture the current comparison state.

### Layout Behavior
- Files are added one at a time with **Select file to add**; each file gets its own heatmap and a shared colorbar.
- Use the unit **Conversion** (*from* → *to* dropdowns, as in Single View) and the **Label:** field to adjust the displayed units and colorbar title. Multi View and Multi Property show the stored values (stress and CRSS are in Pa), so *from* reads `base`; choose `Mega (M)` in *to* to see MPa or `Giga (G)` for GPa. The colorbar title shows the unit you chose.
- Vector arrays can be shown as arrows with the vector toggle.
- Line scan (with **Direction:**), histogram (with **Number of Bins**), and rotation controls apply to the comparison. Each file gets its own colour in the line scan and histogram.

![Multi View line scans and histograms](images/multi_view_line_scan_histogram.png)
- Multiple heatmaps are displayed in the comparison area for selected files.
- Controls apply at the active comparison group level and update the corresponding comparison views.
- Comparison selection persists while navigating between top tabs during the same session.

### Typical Comparison Workflows
- Compare the same field across different files.
- Compare different projects under consistent palette/range settings.
- Export side-by-side comparison images for reports.

## Multi Property
### Purpose
Use **Multi Property** to view several properties of a single file side by side, with shared file selection and per-property range and palette controls.

![Multiple properties of one file](images/multi_property_selection.png)

### Workflow
1. Open **Multi Property**.
2. In **ADD PANEL**, select a dataset. A new tab opens for it.
3. Choose **Project** and **Select file**.
4. Open the **Add Property** dropdown and tick the properties to show (one panel per property), or click **Add All** to add every property in the file.
5. For each property, adjust **Range**, **palette**, plot type, and the unit conversion (*from* → *to*). One conversion applies to all properties; *from* follows the first selected property's unit.
6. Use the discrete palette **+** / **-** buttons and **Bar** / **Boxes** legend mode for banded data.
7. Use **Reset** (selected property) or **Reset All**; **Clear** removes all properties.
8. Click **Export PNG** to save the combined view.

### Analysis Tools
Line scans (with direction and value label), frequency histograms (with **Number of Bins**), and rotation buttons are available. Each property gets its own colour.

![Multi Property line scan and histogram](images/multi_property_line_scan_histogram.png)

## Custom Graph
### Purpose
Use **Custom Graph** to analyze `TextData` numerically and build multi-series trend plots.

![Custom graph with settings panel](images/custom_graph.png)

### Workflow
1. Open **Custom Graph**.
2. In **PROJECTS**, check the folders/projects that contain text data files (`.txt`, `.dat`, `.csv`, `.opd`).
3. Click the **+** tab to create an empty graph workspace.
4. In the graph tab, choose **Project**, **Folder**, and **Text File**, then click **Add To Graph**.
5. In **Data Sources:**, select columns to plot from the added file sections.
6. Configure graph settings in the right **Settings** area:
   - **X-Axis**: choose **Column** and edit **Title**. The X column defaults to a `Time` column when the file has one.
   - **Display**: set **Legend Pos:**, toggle **Legend** / **Grid**, choose trace mode, and choose line style.
   - **Y-Axis**: edit Y1 and Y2 axis titles. Titles are filled in automatically from the plotted columns and their units (for example `Sigma_xx (MPa)` or `Sigma_xx, Mises`); type your own to keep it, or clear the field to return to automatic.
   - **Column Settings**: set legend labels, trace color, unit conversion, and assign each selected column to `Y1` or `Y2`.
   - Every legend and axis-title field has a small **σ** button: click it to insert Greek letters, math signs or SI units (for example **σ**, **ε**, **N/m²**) at the cursor.
7. Interact directly with the graph (zoom/pan/hover) and repeat adjustments until the plot is final.
8. Optionally open the **reveal animation** from the graph toolbar (see below).

### Supported text files
Files are read with automatic detection, so most exports load without changes:
- **Delimiters**: spaces, tabs, commas or semicolons; decimal commas (`1,5`) are understood.
- **Header**: the first text line holds the column names. A commented header (`# time stress`) also works, and a file with no header at all gets the names `Column 1`, `Column 2`, ...
- **Comments**: lines starting with `#`, `%` or `//` are ignored.
- **Units row**: a row of units under the header (`[s] [Pa]`) is not plotted as data; the units are used in the axis titles.
- **Ragged rows** are padded with empty values, duplicate column names are numbered (`Time`, `Time_2`), and columns without any numbers are skipped.
- If a file cannot be loaded, the file section says why (for example, no numeric columns, or a single line of numbers without a header).

### Controls and Outcomes
- **+** tab: creates an empty graph workspace.
- **Project / Folder / Text File** selectors: choose a checked project, one of its text-data folders, and a supported file.
- **Add External Text File**: loads a text-data file from any location, outside the checked projects.
- **PNG**: downloads the graph as an image. **Animate**: opens the reveal animation.
- **Add To Graph**: loads the selected text file into the current graph tab. Column selectors populate for added files.
- Column checklists: selects plotted series. Traces are added/removed from the graph.
- **X-Axis Column**: changes x-data source. All traces replot against the selected x-axis column.
- **Legend Pos:**: moves legend location. It supports plot corners and **Right Outside**.
- **Legend** / **Grid** toggles: show/hide legend and grid lines.
- **Trace:** renders lines, markers, or lines plus sampled markers.
- **Style:** changes the line dash pattern.
- **Column Settings**: routes each trace to an axis, updates label text, chooses line color, and applies a conversion.

  **Conversions.** Each column has two dropdowns, **from** and **to**. *From* is the unit the data is in the file; it is pre-filled from the file's units row when there is one (for example `MPa`), otherwise pick it. *To* lists the units of the same kind (`MPa` to `GPa`, `kN` to `MN`, `J` to `kJ`, `s` to `min`, `K` to `°C`, `-` to `%`, ...). Leave *to* on the same unit for no change. The X axis has the same two dropdowns next to **X Convert**.

  **Units.** *From* and *to* name scales, not units. The unit you choose in *from* is not listed again in *to*; *to* starts on `—`, which means no conversion, so choose `—` to undo a conversion. The names are `milli (m)`, `base`, `kilo (k)`, `Mega (M)`, `Giga (G)`, and so on, from small to large, so you can go from kilo to base or milli to Mega. The unit itself (Pa, m, N, ...) comes from the data and is not repeated; the converted unit appears in the axis title (`MPa`). The scale depends on the unit: pressure `milli` to `Giga`; length `nano` to `kilo` (with `centi`); force, energy and power `milli` to `Giga`; mass `micro` to `kilo`; time `milli`, `base`, `minute`, `hour`, `day`; temperature `Kelvin`, `Celsius`. When a file gives **no unit**, the dropdowns offer every prefix plus `percent`, and `s`, `K`, `°C` at the end (seconds and temperature): pick one to say what the data is (for example `s` for a Time column), then *to* shows the scale of that unit without it (`milli`, `minute`, `hour`, `day` for seconds). The *from* list itself does not change while you pick from it; choose `base` again to go back to data with no unit. *Custom…* is the last entry of *to*. Any other SI prefix in a file's units row (`TPa`, `dm`, `ns`) also converts.

  **Custom formulas.** The last entry of the *to* dropdown is **Custom…**. *From* keeps the source unit. After applying a formula, *to* shows **Custom (unit)** (for example **Custom (GPa)**), or **Custom…** when no result unit was entered. It opens the **Formula Editor**, a light rounded window you can drag by its header and resize from its edges. Write the formula in the large multiline editor, which colours functions, columns and numbers. The first button carries the name of the column being converted; click it to insert that column (`Stress / 1000`). The other buttons insert operators (`+ - * / ^ ( )`) and functions (`sqrt`, `abs`, `log10`, `ln`, `exp`, `pi`) followed by a space; a function button wraps selected text. Other columns of the same file can be typed by name, with names that contain spaces or symbols in square brackets (`Stress * Time`, `[Epsilon xx]`). Formulas written with `x` for the column still work. The preview shows example values or the reason a formula is invalid; **Apply Formula** (Ctrl+Enter) is enabled only for a valid formula. An optional unit label appears in the axis title. Choose Custom again in *to* to edit the formula, or choose a regular target in *to* to go back to unit conversion. Cancelling the editor restores the previous target and keeps the previous formula. This works for both X and Y conversions.

### Reveal Animation
The animation dialog reveals every trace from left to right. Use play, pause, stop, the frame slider, and the FPS selector to preview it. Axis ranges stay fixed to the final data range. Click **Export MP4** to save the animation (requires `ffmpeg`). The graph itself is not modified.

### Typical Use Cases
- Plotting stress/strain or other tabular trends from `TextData`.
- Overlaying multiple files in one chart for trend comparison.
- Preparing graph outputs for analysis notes and publications.

## Exporting Results
- Heatmaps: click the **PNG** button in `Single View` or `Multi View` controls, or **Export PNG** in `Multi Property`.
- Animations: use **Export MP4** in the `Custom Graph` animation dialog.
- Graphs: use the camera/export action in the line-scan, histogram, history, or Custom Graph toolbar.
- On-screen Greek typography uses the bundled STIX font. Heatmap PNG export uses a separate rendering path, so its text font can differ.
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
- Ensure the correct top tab is active (`Single View`, `Multi View`, `Multi Property`, or `Custom Graph`).
- In `Multi View`, select files first; field/range controls remain limited until files are selected.

### Graph not updating
- Ensure `Custom Graph` panel has selected files and columns.
- Check that the selected x-axis column exists in the loaded data.

### Missing or outdated files
- Click **Reload** in the sidebar to rescan projects. Reload in a viewer adds new files of the active dataset and removes deleted ones.
- Folders without `VTK/` or `TextData/` subfolders are not recognised as projects.

### Animation export fails
- MP4 export requires `ffmpeg` to be installed and on the `PATH`.

### Slow interaction
- Reduce the number of simultaneously selected comparison files.
- Reduce active graph traces in `Custom Graph` panels.
- Apply updates in smaller steps (range, then field, then overlays).

### Rendering problems on a VM or without GPU
Start OPView with `OPVIEW_NO_GPU=1` (Linux) or `OPview-No-GPU.bat` (Windows) to force software rendering.

### Console debug output
Set `OPVIEW_DEBUG=1` before launching to print `[DEBUG]` tracing. It is off by default.

## FAQ
**Q: When should I use `Single View` vs `Multi View`?**  
A: Use `Single View` for deep inspection of one panel; use `Multi View` for side-by-side comparison.

**Q: Why do I not see any files in selectors?**  
A: Select a valid project in **PROJECTS** or add one with **Add Folder**.

**Q: What is the fastest way to recover display settings?**  
A: Click **Reset** in the active heatmap control area.

**Q: How do I compare several files in one place?**  
A: Open `Multi View`, add a comparison panel, and select multiple entries in **Select File**.

**Q: How do I see several properties of one file together?**  
A: Open `Multi Property`, add a dataset, choose a file, then use **Add Property** or **Add All**.

**Q: How do I build a graph from text output?**  
A: Open `Custom Graph`, check the text-data project in **PROJECTS**, click the **+** tab, then choose project/folder/file inside the tab and click **Add To Graph**.

**Q: How do I export what I see?**  
A: Use **PNG** for heatmaps and graph toolbar export for plots.
