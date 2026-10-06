# Changelog

All notable changes to OPView are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.1.0] - 2026-10-06

Changes since **v1.0.0** (`ce42b833`).

### Highlights

- New **Multi Property** tab: view several properties of a single file side by side.
- **Discrete colour palette** with numbered colour-box legend, in Single View, Multi View and Multi Property.
- **Custom Graph reveal animation** with MP4 export.
- **Vector-field overlays** (arrows) and **line-scan direction / heatmap rotation** controls in Single View.
- **Software-rendering mode** (`OPVIEW_NO_GPU`) for VMs and machines without usable GPU.
- Reload now picks up new VTK files, drops deleted ones and clears stale cache.

### New features

#### Multi Property tab
- Fourth top-level tab (Single View, Multi View, Multi Property, Custom Graph).
- One-file, multi-property heatmap panel with its own colourbar, controls and PNG export renderer.
- Closable per-dataset tabs.

#### Colour and colourbars
- New `discrete-custom` palette: hard-banded colours, 2–10 bands, add/remove with `+` / `-` buttons.
- Colourbar mode selector for discrete data: **Bar** or **Boxes** (numbered colour-box legend).
- New **Contour Filled + Values** plot type: discrete colour bands with labelled contour values.
- Colourbar tick labels formatted from tick spacing (integer, fixed decimals or scientific notation as appropriate).

#### Single View
- Vector-field overlay: arrow plot for vector arrays, thinned to a readable density and following heatmap rotation.
- Heatmap rotation buttons (0° / 90° / 180° / 270°) and line-scan direction (horizontal / vertical) icon buttons.
- Whole-field **selected-scalar average over time**, shown below the VTK view next to phase fractions.
- Unconfigured VTK arrays are listed automatically, including vector components and norms.
- Initial scalar prefers `PhaseFields` for PhaseField panels.
- Line-scan position is kept at the same relative location when the file extent changes between timesteps.
- Collapsible **Settings** panel with a rotated rail label.
- High-resolution PNG export (device scale 2, 300 DPI) that matches the visible layout; empty side margins are cropped.

#### Multi View
- Larger rework of the comparison panel and cells (≈300 lines of changes), with shared colourbar and discrete-legend support.

#### Custom Graph
- **Reveal animation** dialog: left-to-right line reveal with play, pause, stop, frame slider and FPS selector. Final axis ranges stay locked. MP4 export via ffmpeg.
- Value conversion for Y data: As-is, %, MPa, GPa, Log10 (X conversion also supported).
- Long traces are downsampled for responsiveness; axis ranges are padded.
- Layout and settings panel rework.

#### Reload and file watching
- Explicit reload clears the in-memory VTK cache.
- Reload discovers new VTK files in the active dataset folder (scoped to that dataset).
- Reload skips and removes VTK files that no longer exist.

### Improvements

- Dataset dropdown and sidebar labels no longer show an empty `: ` prefix for unconfigured datasets.
- Sidebar accent buttons gain hover and pressed states.
- Histogram and line-scan canvases refreshed (more consistent styling and tick handling).
- Fonts: unsupported or corrupt font files are skipped, and the app falls back to the system font if Roboto Condensed cannot be loaded.
- Debug output is now opt-in: set `OPVIEW_DEBUG=1` to enable `[DEBUG]` tracing (previously always on).
- `opview.sh` forwards `OPVIEW_NO_GPU`.

### Packaging and platform

- CMake/CPack packaging: PyInstaller freeze to Linux `.deb`, AppImage and Windows NSIS installer.
- GitHub Actions release pipeline (`.github/workflows/release.yml`) for Linux and Windows.
- Fixed NSIS installer targeting `Program Files (x86)` instead of `Program Files`.
- Fixed Windows package filename (`win32` to `win64`).
- Bundled libtiff, libpcre and libmpdec in the frozen Linux app.
- OPStudio embedding: installs under `opview/` and uses `GNUInstallDirs` when built as a subproject.
- Software-rendering mode: `OPVIEW_NO_GPU=1` forces Qt and QtWebEngine software rendering (also `OPview-No-GPU.bat` on Windows).
- Project path can be passed as a launcher argument.

### Fixes

- Fixed PNG image export.
- Fixed animation with threshold on phase fractions.
- Added missing PNG asset icons.

### Documentation

- `doc/Documentation.md` rewritten as a full user guide: interface overview, project discovery, startup options and environment variables (`OPVIEW_NO_GPU`, `OPVIEW_DEBUG`), plot types, colour maps, discrete palette, rotation, unit conversion, playback and animation, plot over time, line scan, histogram, reloading, troubleshooting and FAQ.
- New sections for the **Multi Property** tab and the Custom Graph **reveal animation**.
- 14 annotated screenshots added in `doc/images/` (Single View, Multi View, Multi Property, Custom Graph, colour maps, plot types, rotation, unit conversion).

### Known issues

- `assets/fonts/RobotoCondensed.ttf` is not a font: it is a saved GitHub HTML page. The app skips it and uses the system font, so text metrics differ from the intended design. Replace it with the real Roboto Condensed file.

### Testing

- New tests: colourbar tick formatting, colour palettes, debug gating, Multi Property view, discrete colourbar in Multi View, time series, VTK cache.
- Expanded tests for Custom Graph, Single View data flow and export, animation player, app width constraints.
- Known: some older unit tests are stale relative to the code (see `CLAUDE.md`).

## [1.0.0] - 2026-08-03

Initial release: Single View heatmaps, Multi View comparison and Custom Graph plotting of OpenPhase `VTK` and `TextData` output.
