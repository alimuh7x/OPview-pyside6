"""Controller for panel UI state and rendering updates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
from matplotlib.colors import Normalize
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from app.debug import debug_print
from config.constants import DEFAULTS
from utils.time_series import collect_same_series_files
from utils.vtk_utils import get_reader
from viewer.colorscale import make_dynamic_colormap, palette_to_cmap
from viewer.heatmap_canvas import _CANVAS_HEIGHT
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.manual_point_dialog import ManualPointDialog
from viewer.state import ViewerState, initial_state

_PHASE_FRACTION_COLORS = [
    "#d62728",
    "#1f77b4",
    "#2ca02c",
    "#f0a202",
    "#9467bd",
    "#17becf",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#8c564b",
]


class HeatmapController:
    """Bridge between controls, state, and rendering."""

    def __init__(
        self,
        *,
        controls_widget,
        heatmap_canvas,
        line_scan_canvas,
        histogram_canvas,
        line_mode_check,
        show_line_check,
        direction_combo,
        histogram_bins_slider,
        interfaces_check,
        export_button,
        colorbar_label_edit,
        unit_scale_combo,
        dataset_info: dict,
        time_plot_canvas=None,
        time_plot_add_point_btn=None,
        time_plot_manual_btn=None,
        time_plot_calculate_btn=None,
        time_plot_cancel_btn=None,
        time_plot_clear_btn=None,
        time_plot_show_points_check=None,
        time_plot_selected_label=None,
        time_plot_points_container=None,
        time_plot_points_layout=None,
        time_plot_progress=None,
        phase_fraction_history_canvas=None,
        phase_fraction_history_separator=None,
        phase_history_dt_spin=None,
        phase_history_time_unit_combo=None,
        export_widget=None,
    ) -> None:
        """Store all widget references, initialise default state, and populate controls."""
        debug_print("HeatmapController.__init__ start")
        self.controls_widget = controls_widget
        self.heatmap_canvas = heatmap_canvas
        self.line_scan_canvas = line_scan_canvas
        self.histogram_canvas = histogram_canvas
        self.line_mode_check = line_mode_check
        self.show_line_check = show_line_check
        self.direction_combo = direction_combo
        self.histogram_bins_slider = histogram_bins_slider
        self.interfaces_check = interfaces_check
        self.export_button = export_button
        self.colorbar_label_edit = colorbar_label_edit
        self.unit_scale_combo    = unit_scale_combo
        self.time_plot_canvas = time_plot_canvas
        self.time_plot_add_point_btn = time_plot_add_point_btn
        self.time_plot_manual_btn = time_plot_manual_btn
        self.time_plot_calculate_btn = time_plot_calculate_btn
        self.time_plot_cancel_btn = time_plot_cancel_btn
        self.time_plot_clear_btn = time_plot_clear_btn
        self.time_plot_show_points_check = time_plot_show_points_check
        self.time_plot_selected_label = time_plot_selected_label
        self.time_plot_points_container = time_plot_points_container
        self.time_plot_points_layout = time_plot_points_layout
        self.time_plot_progress = time_plot_progress
        self.phase_fraction_history_canvas = phase_fraction_history_canvas
        self.phase_fraction_history_separator = phase_fraction_history_separator
        self.phase_history_dt_spin = phase_history_dt_spin
        self.phase_history_time_unit_combo = phase_history_time_unit_combo
        self.export_widget = export_widget
        self.dataset_info = dataset_info
        self._file_loaded_callback = None
        self._file_options_changed_callback = None
        self._time_plot_points_changed_callback = None
        self.reader = None
        self.scalar_defs: list[dict] = []
        self._last_grids = None
        self._last_display_grids = None
        self._last_scaled_grid = None
        self._histogram_cache: dict | None = None
        self._time_plot_running = False
        self._time_plot_cancel_requested = False
        self._time_plot_series = []
        self._time_plot_index = 0
        self._time_plot_success = 0
        self._time_plot_failed = 0
        self._time_plot_scalar_def = None
        self._time_plot_display_scale = 1.0
        self._time_plot_display_label = ""
        self._time_plot_series_data: list[dict] = []
        self._time_plot_steps: list[int] = []
        self._time_plot_values: list[float] = []
        self._time_plot_errors: list[str] = []
        self._phase_fraction_ranges: dict[str, tuple[float, float]] = {}
        self._phase_fraction_history_cache: dict | None = None
        self.state = ViewerState(
            dataset_id=dataset_info.get("id", ""),
            dataset_label=dataset_info.get("label", "Untitled"),
            scalar_key="",
            scalar_label="",
            axis="y",
            slice_index=0,
            file_path="",
        )
        self._initialize_controls()
        debug_print(f"HeatmapController initial state={self.state}")
        debug_print("HeatmapController.__init__ complete")

    def get_file_count(self) -> int:
        """Return number of files currently loaded in the file combo."""
        return self.controls_widget.file_combo.count()

    def connect_signals(self) -> None:
        """Wire all Qt signals from controls and canvases to their handler methods."""
        debug_print("HeatmapController.connect_signals called")
        self.controls_widget.refresh_requested.connect(self.refresh_view)
        self.controls_widget.range_slider_changed.connect(self._handle_range_slider_signal)
        self.line_mode_check.toggled.connect(self._on_line_mode_toggled)
        self.controls_widget.click_mode_range_check.toggled.connect(self._on_range_mode_toggled)
        self.show_line_check.toggled.connect(lambda *_: self._refresh_from_toolbar("line-overlay"))
        self.direction_combo.currentIndexChanged.connect(lambda *_: self._refresh_from_toolbar("line-direction"))
        self.controls_widget.scalar_combo.currentIndexChanged.connect(self.refresh_view)
        self.controls_widget.phase_fraction_selection_changed.connect(
            lambda *_: self._refresh_from_toolbar("phase-fraction-selection")
        )
        self.histogram_bins_slider.valueChanged.connect(lambda *_: self._refresh_from_toolbar("histogram-bins"))
        self.interfaces_check.toggled.connect(lambda *_: self._refresh_from_toolbar("interfaces"))
        self.export_button.clicked.connect(self._export_png)
        self.heatmap_canvas.heatmap_clicked.connect(self._handle_heatmap_click)
        self.colorbar_label_edit.editingFinished.connect(lambda *_: self._refresh_from_toolbar("colorbar-label"))
        self.unit_scale_combo.currentIndexChanged.connect(lambda *_: self._refresh_from_toolbar("unit-scale"))
        if self.phase_history_dt_spin is not None:
            self.phase_history_dt_spin.valueChanged.connect(
                lambda *_: self._on_time_axis_control_changed("phase-history-dt")
            )
        if self.phase_history_time_unit_combo is not None:
            self.phase_history_time_unit_combo.currentIndexChanged.connect(
                lambda *_: self._on_time_axis_control_changed("phase-history-time-unit")
            )
        if self.time_plot_add_point_btn is not None:
            self.time_plot_add_point_btn.toggled.connect(self._on_time_plot_add_point_toggled)
        if self.time_plot_manual_btn is not None:
            self.time_plot_manual_btn.clicked.connect(self._manual_time_plot_point)
        if self.time_plot_calculate_btn is not None:
            self.time_plot_calculate_btn.clicked.connect(self._start_time_plot)
        if self.time_plot_cancel_btn is not None:
            self.time_plot_cancel_btn.clicked.connect(self._cancel_time_plot_worker)
        if self.time_plot_clear_btn is not None:
            self.time_plot_clear_btn.clicked.connect(self._clear_time_plot)
        if self.time_plot_show_points_check is not None:
            self.time_plot_show_points_check.toggled.connect(self._on_time_plot_show_points_toggled)
        debug_print("HeatmapController connected all signals")

    def _refresh_from_toolbar(self, trigger: str) -> None:
        """Refresh after toolbar widgets that are not owned by PanelControlsWidget change."""
        debug_print("HeatmapController._refresh_from_toolbar called")
        debug_print(f"HeatmapController toolbar trigger={trigger}")
        self.controls_widget.set_last_trigger(trigger)
        self.refresh_view()
        debug_print("HeatmapController toolbar refresh complete")

    def _on_time_axis_control_changed(self, trigger: str) -> None:
        """Refresh views that use the shared dt/time-unit axis."""
        debug_print("HeatmapController._on_time_axis_control_changed called")
        debug_print(f"HeatmapController time axis trigger={trigger}")
        self._refresh_from_toolbar(trigger)
        if self._time_plot_series_data:
            debug_print("PlotOverTime rerendering existing data with new time axis")
            self._render_time_plot_values()
        else:
            debug_print("PlotOverTime no existing data to rerender")

    def _initialize_controls(self) -> None:
        """Populate project and file dropdowns, then load the first file."""
        debug_print("HeatmapController._initialize_controls called")
        available_projects = self.dataset_info.get("available_projects", [])
        if available_projects:
            self.controls_widget.set_project_options(available_projects)
            files = available_projects[0].get("files", [])
            # Seed dataset_info with first project context for display helpers
            self.dataset_info["vtk_folder"] = available_projects[0].get("vtk_folder", "")
            self.dataset_info["project_name"] = available_projects[0].get("project_name", "")
        else:
            files = self.dataset_info.get("files", [])
        self.controls_widget.set_file_options(files)
        if files:
            self._load_reader(files[0])
        else:
            self.controls_widget.set_status_text("No VTK files available")
        self._sync_line_mode()

    def refresh_view(self) -> None:
        """Read current control values, update state, slice the data, and re-render all canvases."""
        debug_print("HeatmapController.refresh_view called")
        if self.controls_widget.last_trigger() == "project":
            project_info = self.controls_widget.current_project_info()
            debug_print("HeatmapController project change detected")
            if project_info:
                self.dataset_info["vtk_folder"] = project_info.get("vtk_folder", "")
                self.dataset_info["project_name"] = project_info.get("project_name", "")
                files = project_info.get("files", [])
                debug_print(f"HeatmapController project file count={len(files)}")
                self.controls_widget.set_file_options(files)
                if self._file_options_changed_callback:
                    debug_print("HeatmapController notifying file options changed")
                    self._file_options_changed_callback()
                debug_print(
                    "HeatmapController project first file="
                    f"{self.controls_widget.current_file_path()}"
                )
            self.controls_widget.set_last_trigger("file")
        file_path = self.controls_widget.current_file_path()
        debug_print(f"Controller file_path={file_path}")
        if not file_path:
            self.controls_widget.set_status_text("Select a VTK file first")
            self.heatmap_canvas.render_status("No file selected")
            return
        if self.reader is None or self.state.file_path != file_path:
            self._load_reader(file_path)

        scalar_key   = self.controls_widget.current_scalar_key()
        scalar_label = self.controls_widget.current_scalar_label()
        axis         = self.controls_widget.current_axis()
        slice_index  = self.controls_widget.current_slice_index()
        palette      = self.controls_widget.current_palette()
        plot_type    = self.controls_widget.current_plot_type()
        debug_print(f"Controller read scalar_key={scalar_key}")
        debug_print(f"Controller read scalar_label={scalar_label}")
        debug_print(f"Controller read axis={axis}")
        debug_print(f"Controller read slice_index={slice_index}")
        debug_print(f"Controller read plot_type={plot_type}")
        scalar_def = self._get_scalar_def(scalar_key)
        if scalar_def is None:
            self.controls_widget.set_status_text("No scalar selected")
            self.heatmap_canvas.render_status("No scalar selected")
            return

        previous_state                        = replace(self.state)
        self.state.scalar_key                 = scalar_key
        self.state.scalar_label               = scalar_label
        self.state.axis                       = axis
        self.state.slice_index                = slice_index
        self.state.file_path                  = file_path
        self.state.palette                    = palette
        self.state.rotation_degrees           = self.controls_widget.current_rotation_degrees()
        self.state.scale                      = scalar_def.get("scale", 1.0) or 1.0
        self.state.units                      = scalar_def.get("units")
        self.state.colorscale_mode            = "dynamic" if self.controls_widget.full_scale_enabled() else "normal"
        self.state.line_overlay_visible       = self.show_line_check.isChecked()
        self.state.line_scan_direction        = self.direction_combo.currentData() or "horizontal"
        self.state.interfaces_overlay_visible = self.interfaces_check.isChecked()
        if self.line_mode_check.isChecked():
            self.state.click_mode = "linescan"
        elif self.controls_widget.click_mode_range_check.isChecked():
            self.state.click_mode = "range"
        else:
            self.state.click_mode = "none"
        debug_print(f"Controller click_mode={self.state.click_mode}")
        if previous_state.rotation_degrees != self.state.rotation_degrees:
            self.state.line_scan_x = None
            self.state.line_scan_y = None
            self.state.click_count = 0
            self.state.first_click = None

        x_grid, y_grid, z_grid, stats_scaled = self._load_display_grid(
            self.reader,
            scalar_def,
            axis,
            slice_index,
            plot_type=plot_type,
        )
        grid_rows, grid_cols = np.asarray(z_grid).shape[:2]
        debug_print(f"Controller heatmap grid rows={grid_rows}")
        debug_print(f"Controller heatmap grid cols={grid_cols}")
        self._last_grids = (x_grid, y_grid, z_grid, stats_scaled)
        self._last_scaled_grid = z_grid

        trigger = self.controls_widget.last_trigger()
        if (
            previous_state.scalar_key != self.state.scalar_key
            or previous_state.file_path != self.state.file_path
            or previous_state.axis != self.state.axis
            or trigger == "plot-type"
        ):
            self._reset_range_from_stats(stats_scaled)
        elif trigger == "reset":
            self._reset_range_from_stats(stats_scaled)
        else:
            range_min, range_max = self.controls_widget.current_range()
            lo, hi = sorted([range_min, range_max])
            debug_print(f"Controller manual range raw={range_min}..{range_max}")
            debug_print(f"Controller manual range sorted={lo}..{hi}")
            self.state.range_min = lo
            self.state.range_max = hi
            self.state.threshold = (lo + hi) / 2
            self.controls_widget.set_range_values(lo, hi)
        self._sync_phase_fraction_range(scalar_key, trigger, stats_scaled)

        message = (
            f"Dataset={self.state.dataset_label} | "
            f"scalar={scalar_label or 'not-selected'} | "
            f"axis={axis} | "
            f"slice={slice_index} | "
            f"grid={grid_cols}x{grid_rows} | "
            f"min={self.state.range_min:.4g} | "
            f"max={self.state.range_max:.4g}"
        )
        self.state.status_message = message
        debug_print(f"Controller updated state={self.state}")
        self.controls_widget.set_status_text(message)
        extra_scale, display_label = self._get_display_params(scalar_label)
        display_label = self._display_label_for_plot_type(display_label, plot_type)
        self._render_heatmap(x_grid, y_grid, z_grid, extra_scale, display_label)
        self._render_phase_fraction_history()
        self._render_line_scan(x_grid, y_grid, z_grid, extra_scale, display_label)
        self._render_histogram(extra_scale, display_label)
        debug_print("Controller requested all canvas updates")

    def _load_reader(self, file_path: str) -> None:
        """Open a VTK file, detect slice axis, build scalar definitions, and sync all UI controls."""
        debug_print("HeatmapController._load_reader called")
        self._cancel_time_plot_worker()
        self._histogram_cache = None
        previous_state = replace(self.state)
        previous_time_points = [dict(point) for point in self.state.time_plot_points]
        self.reader      = get_reader(file_path)
        axis             = self._detect_axis()
        self.scalar_defs = self._build_scalar_defs()
        first_scalar     = self.scalar_defs[0] if self.scalar_defs else {"value": "", "label": ""}
        fallback_state   = self._build_state(self.reader, file_path, first_scalar["value"], axis)
        data_range_min = fallback_state.range_min
        data_range_max = fallback_state.range_max
        debug_print(f"HeatmapController loaded data range min={data_range_min}")
        debug_print(f"HeatmapController loaded data range max={data_range_max}")
        self.state       = self._preserve_file_change_state(fallback_state, previous_state, previous_time_points)
        self.controls_widget.set_axis(axis)
        is_effective_2d = Heatmap2DOrientation.is_2d(self.reader.dimensions)
        max_slice_index = 0 if is_effective_2d else self.reader.get_max_slice_index(axis)
        self.controls_widget.set_slice_range(0, max_slice_index)
        self.controls_widget.set_slice_controls_visible(not is_effective_2d and max_slice_index > 0)
        prev_scalar_key = self.controls_widget.current_scalar_key()
        self.controls_widget.set_scalar_options(self.scalar_defs)
        restored = self.controls_widget.scalar_combo.findData(prev_scalar_key)
        if restored >= 0:
            self.controls_widget.scalar_combo.blockSignals(True)
            self.controls_widget.scalar_combo.setCurrentIndex(restored)
            self.controls_widget.scalar_combo.blockSignals(False)

        self.controls_widget.set_slider_bounds(data_range_min, data_range_max)
        self.controls_widget.set_range_values(self.state.range_min, self.state.range_max)
        self.controls_widget.set_status_text(f"Loaded {Path(file_path).name}")
        if self._file_loaded_callback:
            self._file_loaded_callback(file_path)
        debug_print("HeatmapController reader and controls updated")

    def _preserve_file_change_state(
        self,
        next_state: ViewerState,
        previous_state: ViewerState,
        previous_time_points: list[dict],
    ) -> ViewerState:
        """Carry user overlay state across VTK file changes."""
        debug_print("HeatmapController._preserve_file_change_state called")
        debug_print(f"Preserve previous file={previous_state.file_path}")
        debug_print(f"Preserve next file={next_state.file_path}")
        debug_print(f"Preserve previous range min={previous_state.range_min}")
        debug_print(f"Preserve previous range max={previous_state.range_max}")
        debug_print(f"Preserve next data range min={next_state.range_min}")
        debug_print(f"Preserve next data range max={next_state.range_max}")
        debug_print(f"Preserve line_scan_x={previous_state.line_scan_x}")
        debug_print(f"Preserve line_scan_y={previous_state.line_scan_y}")
        debug_print(f"Preserve time point count={len(previous_time_points)}")
        if previous_state.file_path:
            debug_print("Preserving range because previous file exists")
            next_state.range_min = previous_state.range_min
            next_state.range_max = previous_state.range_max
            next_state.threshold = previous_state.threshold
        else:
            debug_print("Using data range because this is the first file load")
        previous_scalar = next(
            (scalar for scalar in self.scalar_defs if scalar.get("value") == previous_state.scalar_key),
            None,
        )
        if previous_scalar is not None:
            debug_print(f"Preserving scalar across file change={previous_state.scalar_key}")
            next_state.scalar_key = previous_state.scalar_key
            next_state.scalar_label = previous_scalar.get("label", previous_state.scalar_label)
        else:
            debug_print("Using first scalar because previous scalar is unavailable")
        debug_print(f"Final file-change range min={next_state.range_min}")
        debug_print(f"Final file-change range max={next_state.range_max}")
        next_state.line_scan_x = previous_state.line_scan_x
        next_state.line_scan_y = previous_state.line_scan_y
        next_state.line_scan_direction = previous_state.line_scan_direction
        next_state.line_overlay_visible = previous_state.line_overlay_visible
        next_state.click_mode = previous_state.click_mode
        next_state.time_plot_x = previous_state.time_plot_x
        next_state.time_plot_y = previous_state.time_plot_y
        next_state.time_plot_points = previous_time_points
        next_state.time_plot_points_visible = previous_state.time_plot_points_visible
        next_state.time_plot_pick_mode = previous_state.time_plot_pick_mode
        debug_print(f"Preserved time points visible={next_state.time_plot_points_visible}")
        debug_print("HeatmapController._preserve_file_change_state complete")
        return next_state

    def _project_display_text(self) -> str:
        """Return a human-readable 'parent/folder' label for the project header."""
        debug_print("HeatmapController._project_display_text called")
        vtk_folder = self.dataset_info.get("vtk_folder")
        if vtk_folder:
            folder = Path(vtk_folder)
            return f"{folder.parent.name}/{folder.name}"
        if self.dataset_info.get("project_name"):
            return str(self.dataset_info["project_name"])
        file_path = self.dataset_info.get("files", [""])
        first_file = file_path[0] if file_path else ""
        if first_file:
            file_parent = Path(first_file).parent
            return f"{file_parent.parent.name}/{file_parent.name}"
        return "Project/VTK"

    def _build_scalar_defs(self) -> list[dict]:
        """Build the list of scalar field definitions from dataset config or auto-detected VTK arrays."""
        debug_print("HeatmapController._build_scalar_defs called")
        configured = self.dataset_info.get("dataset_config", {}).get("scalars")
        scale = self.dataset_info.get("dataset_config", {}).get("scale", 1.0)
        units = self.dataset_info.get("dataset_config", {}).get("units")
        if configured:
            scalar_defs = []
            for index, descriptor in enumerate(configured):
                scalar_defs.append(
                    {
                        "label": descriptor["label"],
                        "value": f"scalar-{index}",
                        "array": descriptor["array"],
                        "component": descriptor.get("component"),
                        "scale": descriptor.get("scale", scale),
                        "units": descriptor.get("units", units),
                    }
                )
            configured_arrays = {scalar_def["array"] for scalar_def in scalar_defs}
            assert self.reader is not None
            for array_name in self._phase_fraction_array_names():
                if array_name in configured_arrays:
                    debug_print(f"Configured phase fraction already present={array_name}")
                    continue
                scalar_defs.append(
                    {
                        "label": array_name,
                        "value": array_name,
                        "array": array_name,
                        "component": None,
                        "scale": 1.0,
                        "units": None,
                    }
                )
                debug_print(f"Added auto phase fraction scalar={array_name}")
            debug_print(f"HeatmapController using configured scalar_defs={len(scalar_defs)}")
            return scalar_defs
        auto_defs: list[dict] = []
        assert self.reader is not None
        for array_name in self.reader.scalar_fields:
            array = self.reader.mesh[array_name]
            if getattr(array, "ndim", 1) == 1:
                auto_defs.append({"label": array_name, "value": array_name, "array": array_name, "component": None, "scale": 1.0, "units": None})
            elif getattr(array, "ndim", 1) == 2:
                auto_defs.append({"label": f"{array_name} (norm)", "value": f"{array_name}-norm", "array": array_name, "component": None, "scale": 1.0, "units": None})
                for component_index in range(array.shape[1]):
                    auto_defs.append({"label": f"{array_name}[{component_index}]", "value": f"{array_name}-{component_index}", "array": array_name, "component": component_index, "scale": 1.0, "units": None})
        debug_print(f"HeatmapController auto scalar_defs={len(auto_defs)}")
        return auto_defs

    def _phase_fraction_array_names(self) -> list[str]:
        """Return detected PhaseFraction_* array names in numeric order where possible."""
        debug_print("HeatmapController._phase_fraction_array_names called")
        assert self.reader is not None
        names = [name for name in self.reader.scalar_fields if str(name).startswith("PhaseFraction_")]
        debug_print(f"HeatmapController raw phase fraction names={names}")

        def sort_key(name: str):
            suffix = str(name).removeprefix("PhaseFraction_")
            return (0, int(suffix)) if suffix.isdigit() else (1, str(name))

        ordered = sorted(names, key=sort_key)
        debug_print(f"HeatmapController ordered phase fraction names={ordered}")
        return ordered

    def _is_phase_field_dataset(self) -> bool:
        """Return True for the Phase Field dataset/tab where phase history should be shown."""
        debug_print("HeatmapController._is_phase_field_dataset called")
        dataset_id = str(self.dataset_info.get("id", "")).lower()
        dataset_label = str(self.dataset_info.get("label", "")).lower().replace(" ", "")
        config_label = str(self.dataset_info.get("dataset_config", {}).get("label", "")).lower().replace(" ", "")
        debug_print(f"HeatmapController phase history dataset_id={dataset_id}")
        debug_print(f"HeatmapController phase history dataset_label={dataset_label}")
        debug_print(f"HeatmapController phase history config_label={config_label}")
        result = "phase-field" in dataset_id or dataset_label == "phasefield" or config_label == "phasefield"
        debug_print(f"HeatmapController is phase field dataset={result}")
        return result

    def _current_phase_history_step(self, files) -> int | None:
        """Return the timestep corresponding to the currently selected file."""
        debug_print("HeatmapController._current_phase_history_step called")
        current_path = str(Path(self.state.file_path).resolve()) if self.state.file_path else ""
        debug_print(f"HeatmapController phase history current path={current_path}")
        for item in files:
            item_path = str(Path(item.path).resolve())
            debug_print(f"HeatmapController phase history compare path={item_path}")
            if item_path == current_path:
                debug_print(f"HeatmapController phase history current step={item.step}")
                return int(item.step)
        debug_print("HeatmapController phase history current step not found")
        return None

    def _phase_fraction_history_cache_key(self, files, phase_names: list[str]) -> tuple:
        """Build a cache key for one phase-fraction file series."""
        debug_print("HeatmapController._phase_fraction_history_cache_key called")
        key = (
            tuple(str(Path(item.path).resolve()) for item in files),
            tuple(phase_names),
        )
        debug_print(f"HeatmapController phase history cache file count={len(key[0])}")
        debug_print(f"HeatmapController phase history cache phase count={len(key[1])}")
        return key

    def _phase_history_time_axis(self) -> tuple[float, str, str]:
        """Return factor and labels for converting filename timestep to displayed time."""
        debug_print("HeatmapController._phase_history_time_axis called")
        dt = 1.0
        if self.phase_history_dt_spin is not None:
            dt = float(self.phase_history_dt_spin.value())
        unit = "timestep"
        if self.phase_history_time_unit_combo is not None:
            unit = str(self.phase_history_time_unit_combo.currentText() or "timestep")
        if unit == "timestep":
            factor = 1.0
            x_label = "Timestep"
            hover_x_label = "timestep"
        else:
            unit_factor = {"s": 1.0, "min": 1.0 / 60.0, "hr": 1.0 / 3600.0}.get(unit, 1.0)
            factor = dt * unit_factor
            x_label = f"Time [{unit}]"
            hover_x_label = "time"
        debug_print(f"HeatmapController phase history dt={dt}")
        debug_print(f"HeatmapController phase history unit={unit}")
        debug_print(f"HeatmapController phase history factor={factor}")
        debug_print(f"HeatmapController phase history x_label={x_label}")
        debug_print(f"HeatmapController phase history hover_x_label={hover_x_label}")
        return factor, x_label, hover_x_label

    def _convert_phase_fraction_history_axis(
        self,
        series: list[dict],
        current_step: int | None,
    ) -> tuple[list[dict], float | None, str, str]:
        """Convert raw timestep x-values to user-selected physical time units."""
        debug_print("HeatmapController._convert_phase_fraction_history_axis called")
        factor, x_label, hover_x_label = self._phase_history_time_axis()
        converted_series = []
        for index, item in enumerate(series):
            debug_print(f"HeatmapController converting phase history series index={index}")
            converted_item = dict(item)
            converted_item["steps"] = [float(step) * factor for step in item.get("steps", [])]
            debug_print(f"HeatmapController converted steps count={len(converted_item['steps'])}")
            converted_series.append(converted_item)
        converted_current = None if current_step is None else float(current_step) * factor
        debug_print(f"HeatmapController converted current step={converted_current}")
        return converted_series, converted_current, x_label, hover_x_label

    def _converted_time_plot_series(self) -> tuple[list[dict], str, str]:
        """Return Plot Over Time data converted from raw timesteps to selected time units."""
        debug_print("HeatmapController._converted_time_plot_series called")
        factor, x_label, hover_x_label = self._phase_history_time_axis()
        converted_series = []
        for index, item in enumerate(self._time_plot_series_data):
            debug_print(f"PlotOverTime converting series index={index}")
            converted_item = dict(item)
            converted_item["steps"] = [float(step) * factor for step in item.get("steps", [])]
            debug_print(f"PlotOverTime converted steps count={len(converted_item['steps'])}")
            converted_series.append(converted_item)
        debug_print(f"PlotOverTime converted x_label={x_label}")
        return converted_series, x_label, hover_x_label

    def _build_phase_fraction_history_series(self, files, phase_names: list[str]) -> list[dict]:
        """Calculate whole-mesh phase-fraction percentages for every timestep."""
        debug_print("HeatmapController._build_phase_fraction_history_series called")
        debug_print(f"HeatmapController phase history files={len(files)}")
        debug_print(f"HeatmapController phase history phases={phase_names}")
        series = [
            {
                "label": self.controls_widget.phase_fraction_display_label(name, name),
                "key": name,
                "steps": [],
                "values": [],
                "color": _PHASE_FRACTION_COLORS[index % len(_PHASE_FRACTION_COLORS)],
            }
            for index, name in enumerate(phase_names)
        ]
        for file_index, item in enumerate(files):
            debug_print(f"HeatmapController phase history reading index={file_index}")
            debug_print(f"HeatmapController phase history path={item.path}")
            reader = get_reader(item.path)
            available = set(reader.scalar_fields)
            debug_print(f"HeatmapController phase history available arrays={len(available)}")
            for phase_index, phase_name in enumerate(phase_names):
                debug_print(f"HeatmapController phase history phase={phase_name}")
                series[phase_index]["steps"].append(int(item.step))
                if phase_name not in available:
                    debug_print("HeatmapController phase history missing phase in file")
                    series[phase_index]["values"].append(float("nan"))
                    continue
                values = np.asarray(reader.mesh[phase_name], dtype=float)
                finite_count = int(np.count_nonzero(np.isfinite(values)))
                debug_print(f"HeatmapController phase history finite count={finite_count}")
                if finite_count == 0:
                    debug_print("HeatmapController phase history no finite values")
                    series[phase_index]["values"].append(float("nan"))
                    continue
                percent = float(np.nanmean(values) * 100.0)
                debug_print(f"HeatmapController phase history percent={percent}")
                series[phase_index]["values"].append(percent)
        debug_print("HeatmapController._build_phase_fraction_history_series complete")
        return series

    def _render_phase_fraction_history(self) -> None:
        """Show Phase Field phase-fraction percentage history below the VTK view."""
        debug_print("HeatmapController._render_phase_fraction_history called")
        if self.phase_fraction_history_canvas is None:
            debug_print("HeatmapController phase history skipped no canvas")
            return
        if self.reader is None or not self._is_phase_field_dataset():
            debug_print("HeatmapController phase history hidden non phase field/no reader")
            self.phase_fraction_history_canvas.hide()
            if self.phase_fraction_history_separator is not None:
                debug_print("HeatmapController hiding phase history separator")
                self.phase_fraction_history_separator.hide()
            return
        phase_names = self._phase_fraction_array_names()
        debug_print(f"HeatmapController phase history detected phases={phase_names}")
        if not phase_names:
            debug_print("HeatmapController phase history hidden no PhaseFraction arrays")
            self.phase_fraction_history_canvas.hide()
            if self.phase_fraction_history_separator is not None:
                debug_print("HeatmapController hiding phase history separator")
                self.phase_fraction_history_separator.hide()
            return
        files = collect_same_series_files(self.state.file_path, self._current_file_paths())
        debug_print(f"HeatmapController phase history same-series files={len(files)}")
        if not files:
            debug_print("HeatmapController phase history hidden no files")
            self.phase_fraction_history_canvas.hide()
            if self.phase_fraction_history_separator is not None:
                debug_print("HeatmapController hiding phase history separator")
                self.phase_fraction_history_separator.hide()
            return
        cache_key = self._phase_fraction_history_cache_key(files, phase_names)
        if self._phase_fraction_history_cache and self._phase_fraction_history_cache.get("key") == cache_key:
            debug_print("HeatmapController phase history cache hit")
            series = self._phase_fraction_history_cache["series"]
        else:
            debug_print("HeatmapController phase history cache miss")
            series = self._build_phase_fraction_history_series(files, phase_names)
            self._phase_fraction_history_cache = {"key": cache_key, "series": series}
            debug_print("HeatmapController phase history cache stored")
        current_step = self._current_phase_history_step(files)
        debug_print(f"HeatmapController phase history render current_step={current_step}")
        series, current_step, x_label, hover_x_label = self._convert_phase_fraction_history_axis(
            series,
            current_step,
        )
        debug_print(f"HeatmapController phase history converted x_label={x_label}")
        if self.phase_fraction_history_separator is not None:
            debug_print("HeatmapController showing phase history separator")
            self.phase_fraction_history_separator.show()
        self.phase_fraction_history_canvas.show()
        self.phase_fraction_history_canvas.render_phase_fraction_history(
            series,
            current_step=current_step,
            x_label=x_label,
            hover_x_label=hover_x_label,
        )
        debug_print("HeatmapController phase history rendered")

    def _get_scalar_def(self, scalar_key: str) -> dict | None:
        """Return the scalar definition matching scalar_key, or the first available as a fallback."""
        debug_print("HeatmapController._get_scalar_def called")
        for scalar_def in self.scalar_defs:
            if scalar_def["value"] == scalar_key:
                return scalar_def
        return self.scalar_defs[0] if self.scalar_defs else None

    def _detect_axis(self) -> str:
        """Choose the slice axis by finding which dimension of the dataset is flat enough."""
        debug_print("HeatmapController._detect_axis called")
        assert self.reader is not None
        return Heatmap2DOrientation.detect_axis(self.reader.dimensions)

    def _build_state(self, reader, file_path: str, scalar_key: str, axis: str) -> ViewerState:
        """Read an initial data slice and construct a ViewerState with real min/max statistics."""
        debug_print("HeatmapController._build_state called")
        descriptor = self._get_scalar_def(scalar_key) or self.scalar_defs[0]
        slice_index = 0 if Heatmap2DOrientation.is_2d(reader.dimensions) else reader.get_max_slice_index(axis) // 2
        scale = descriptor.get("scale", 1.0) or 1.0
        x_grid, y_grid, z_grid, stats_scaled = self._load_display_grid(
            reader,
            descriptor,
            axis,
            slice_index,
            scale_override=scale,
        )
        return initial_state(
            dataset_id=self.dataset_info.get("id", ""),
            dataset_label=self.dataset_info.get("label", "Untitled"),
            scalar_key=descriptor["value"],
            scalar_label=descriptor["label"],
            axis=axis,
            slice_index=slice_index,
            stats=stats_scaled,
            file_path=file_path,
            scale=scale,
            units=descriptor.get("units"),
        )

    def _load_display_grid(
        self,
        reader,
        scalar_def: dict,
        axis: str,
        slice_index: int,
        *,
        scale_override: float | None = None,
        plot_type: str = "heatmap",
    ):
        """Load a scalar grid, applying display scale and optional |grad| transform."""
        debug_print("HeatmapController._load_display_grid called")
        debug_print(f"HeatmapController loading scalar label={scalar_def.get('label')}")
        debug_print(f"HeatmapController loading plot_type={plot_type}")
        x_grid, y_grid, z_grid, stats = reader.get_interpolated_slice(
            axis=axis,
            index=slice_index,
            scalar_name=scalar_def["array"],
            component=scalar_def.get("component"),
            resolution=self._selected_resolution(),
        )
        scale = scale_override if scale_override is not None else (scalar_def.get("scale", 1.0) or 1.0)
        debug_print(f"HeatmapController display grid scale={scale}")
        z_grid = z_grid * scale
        stats_scaled = {key: stats[key] * scale for key in stats}
        if plot_type == "gradient_magnitude":
            debug_print("HeatmapController applying |grad| transform")
            z_grid, stats_scaled = reader.gradient_magnitude_from_grid(x_grid, y_grid, z_grid)
        debug_print(f"HeatmapController display grid min={stats_scaled['min']}")
        debug_print(f"HeatmapController display grid max={stats_scaled['max']}")
        return x_grid, y_grid, z_grid, stats_scaled

    def _is_phase_fraction_key(self, scalar_key: str) -> bool:
        debug_print("HeatmapController._is_phase_fraction_key called")
        result = self.controls_widget.is_phase_fraction_key(scalar_key)
        debug_print(f"HeatmapController is phase fraction key={scalar_key} result={result}")
        return result

    def _sync_phase_fraction_range(self, scalar_key: str, trigger: str, stats_scaled: dict[str, float]) -> None:
        """Keep the existing range controls as the per-PhaseFraction threshold range."""
        debug_print("HeatmapController._sync_phase_fraction_range called")
        debug_print(f"HeatmapController phase range scalar_key={scalar_key}")
        debug_print(f"HeatmapController phase range trigger={trigger}")
        if not self._is_phase_fraction_key(scalar_key):
            debug_print("HeatmapController phase range skipped non phase fraction")
            return
        if trigger in {"range", "range-slider", "reset"}:
            current_range = (float(self.state.range_min), float(self.state.range_max))
            self._phase_fraction_ranges[scalar_key] = current_range
            debug_print(f"HeatmapController saved phase range key={scalar_key} range={current_range}")
            return
        if scalar_key not in self._phase_fraction_ranges:
            default_range = (float(stats_scaled["min"]), float(stats_scaled["max"]))
            self._phase_fraction_ranges[scalar_key] = default_range
            debug_print(f"HeatmapController initialized phase range key={scalar_key} range={default_range}")
            return
        if trigger in {"scalar", "phase-fraction-selection"}:
            lo, hi = self._phase_fraction_ranges[scalar_key]
            self.state.range_min = lo
            self.state.range_max = hi
            self.state.threshold = (lo + hi) / 2
            self.controls_widget.set_slider_bounds(float(stats_scaled["min"]), float(stats_scaled["max"]))
            self.controls_widget.set_range_values(lo, hi)
            debug_print(f"HeatmapController restored phase range key={scalar_key} range={(lo, hi)}")

    def _selected_phase_fraction_defs(self) -> list[dict]:
        """Return scalar defs for checked PhaseFraction_* entries when a phase is active."""
        debug_print("HeatmapController._selected_phase_fraction_defs called")
        if not self._is_phase_fraction_key(self.state.scalar_key):
            debug_print("HeatmapController selected phase defs skipped inactive")
            return []
        selected_keys = self.controls_widget.selected_phase_fraction_keys()
        if not selected_keys and self.state.scalar_key:
            selected_keys = [self.state.scalar_key]
            debug_print("HeatmapController no checked phases; using active phase")
        defs = [scalar_def for scalar_def in self.scalar_defs if scalar_def["value"] in selected_keys]
        debug_print(f"HeatmapController selected phase defs count={len(defs)}")
        for scalar_def in defs:
            debug_print(f"HeatmapController selected phase def={scalar_def['value']}")
        return defs

    def _build_phase_fraction_overlays(self, orientation: Heatmap2DOrientation, extra_scale: float) -> list[dict]:
        """Load thresholded grids for all checked phase fractions."""
        debug_print("HeatmapController._build_phase_fraction_overlays called")
        if self.reader is None:
            debug_print("HeatmapController phase overlays skipped no reader")
            return []
        if self.controls_widget.current_plot_type() != "threshold":
            debug_print("HeatmapController phase overlays skipped non-threshold plot")
            return []
        overlays: list[dict] = []
        for index, scalar_def in enumerate(self._selected_phase_fraction_defs()):
            key = scalar_def["value"]
            lo, hi = self._phase_fraction_ranges.get(
                key,
                (float(self.state.range_min), float(self.state.range_max)),
            )
            debug_print(f"HeatmapController phase overlay key={key}")
            debug_print(f"HeatmapController phase overlay threshold={lo}..{hi}")
            x_grid, y_grid, phase_grid, _ = self._load_display_grid(
                self.reader,
                scalar_def,
                self.state.axis,
                self.state.slice_index,
                plot_type="heatmap",
            )
            if extra_scale != 1.0:
                phase_grid = phase_grid * extra_scale
                lo = lo * extra_scale
                hi = hi * extra_scale
                debug_print(f"HeatmapController phase overlay scaled threshold={lo}..{hi}")
            display = orientation.apply_grid(x_grid, y_grid, phase_grid)
            visible_count = int(np.count_nonzero((display.z >= lo) & (display.z <= hi)))
            debug_print(f"HeatmapController phase overlay visible count={visible_count}")
            overlays.append(
                {
                    "label": self.controls_widget.phase_fraction_display_label(key, scalar_def["label"]),
                    "key": key,
                    "x": display.x,
                    "y": display.y,
                    "z": display.z,
                    "range": (lo, hi),
                    "color": _PHASE_FRACTION_COLORS[index % len(_PHASE_FRACTION_COLORS)],
                }
            )
        debug_print(f"HeatmapController phase overlay count={len(overlays)}")
        return overlays

    def phase_fraction_animation_specs(self) -> list[dict]:
        """Return selected PhaseFraction render settings for animation frames."""
        debug_print("HeatmapController.phase_fraction_animation_specs called")
        if self.controls_widget.current_plot_type() != "threshold":
            debug_print("HeatmapController animation specs skipped non-threshold")
            return []
        specs: list[dict] = []
        for index, scalar_def in enumerate(self._selected_phase_fraction_defs()):
            key = scalar_def["value"]
            lo, hi = self._phase_fraction_ranges.get(
                key,
                (float(self.state.range_min), float(self.state.range_max)),
            )
            label = self.controls_widget.phase_fraction_display_label(key, scalar_def["label"])
            color = _PHASE_FRACTION_COLORS[index % len(_PHASE_FRACTION_COLORS)]
            debug_print(f"HeatmapController animation phase key={key}")
            debug_print(f"HeatmapController animation phase label={label}")
            debug_print(f"HeatmapController animation phase range={lo}..{hi}")
            debug_print(f"HeatmapController animation phase color={color}")
            specs.append(
                {
                    "label": label,
                    "array": scalar_def["array"],
                    "component": scalar_def.get("component"),
                    "scale": scalar_def.get("scale", 1.0) or 1.0,
                    "range": (lo, hi),
                    "color": color,
                }
            )
        debug_print(f"HeatmapController animation phase spec count={len(specs)}")
        return specs

    def _display_label_for_plot_type(self, display_label: str, plot_type: str) -> str:
        """Return the colorbar/analysis label for the selected map mode."""
        debug_print("HeatmapController._display_label_for_plot_type called")
        debug_print(f"HeatmapController display label base={display_label}")
        debug_print(f"HeatmapController display label plot_type={plot_type}")
        if plot_type == "gradient_magnitude":
            label = f"{display_label} |grad|"
            debug_print(f"HeatmapController display label gradient={label}")
            return label
        return display_label

    def _reset_range_from_stats(self, stats_scaled: dict[str, float]) -> None:
        """Reset the color range slider and state bounds to the data's actual min/max values."""
        debug_print("HeatmapController._reset_range_from_stats called")
        self.state.range_min = stats_scaled["min"]
        self.state.range_max = stats_scaled["max"]
        self.state.threshold = (stats_scaled["min"] + stats_scaled["max"]) / 2
        self.state.click_count = 0
        self.state.first_click = None
        self.controls_widget.set_slider_bounds(self.state.range_min, self.state.range_max)
        self.controls_widget.set_range_values(self.state.range_min, self.state.range_max)

    def _slice_dimensions(self, axis: str) -> tuple[int, int]:
        """Return (nx, ny) cell counts of the slice plane to compute the correct canvas aspect ratio."""
        if self.reader is None or not self.reader.dimensions:
            return 1, 1
        dx, dy, dz = self.reader.dimensions
        axis = Heatmap2DOrientation.detect_axis(self.reader.dimensions) if Heatmap2DOrientation.is_2d(self.reader.dimensions) else (axis or "y").lower()
        if axis == "x":
            return max(dy, 1), max(dz, 1)
        if axis == "y":
            return max(dx, 1), max(dz, 1)
        return max(dx, 1), max(dy, 1)


    def _get_display_params(self, scalar_label: str) -> tuple[float, str]:
        """Read UI controls and return (extra_scale, display_label) for all canvases."""
        custom_name = self.colorbar_label_edit.text().strip()
        extra_scale, unit_suffix = self.unit_scale_combo.currentData() or (1.0, "")
        name = custom_name if custom_name else scalar_label
        if unit_suffix:
            label = f"{name} ({unit_suffix})"
        elif self.state.units:
            label = f"{name} ({self.state.units})"
        else:
            label = name
        return extra_scale, label

    def _selected_resolution(self):
        """Return the automatic heatmap resolution used for live view and PNG export."""
        debug_print("HeatmapController._selected_resolution called")
        resolution = int(DEFAULTS["interpolation_resolution"])
        debug_print(f"Heatmap automatic resolution value={resolution}")
        return resolution

    def _render_heatmap(self, x_grid, y_grid, z_grid, extra_scale: float, display_label: str) -> None:
        """Build the colormap and pass all grid/overlay data to the heatmap canvas for drawing."""
        debug_print("HeatmapController._render_heatmap called")
        if self.state.colorscale_mode == "dynamic":
            debug_print("Controller using full-scale render range")
            cmap = make_dynamic_colormap(
                float(np.nanmin(z_grid)),
                float(np.nanmax(z_grid)),
                self.state.range_min,
                self.state.range_max,
                self.state.palette,
            )
            vmin = float(np.nanmin(z_grid))
            vmax = float(np.nanmax(z_grid))
        else:
            debug_print("Controller using manual render range")
            cmap = palette_to_cmap(self.state.palette)
            vmin = self.state.range_min
            vmax = self.state.range_max
        debug_print(f"Controller render vmin={vmin}")
        debug_print(f"Controller render vmax={vmax}")

        orientation = self._orientation()
        overlay_grid = orientation.apply_overlay(self._build_overlay_grid())
        display = orientation.apply_grid(x_grid, y_grid, z_grid)
        x_grid, y_grid, z_grid = display.x, display.y, display.z
        self._last_display_grids = (x_grid, y_grid, z_grid)
        phase_fraction_overlays = self._build_phase_fraction_overlays(orientation, extra_scale)

        line_overlay = None
        if self.state.line_overlay_visible:
            line_overlay = Heatmap2DOrientation.line_overlay(
                self.state.line_scan_direction,
                self.state.line_scan_x,
                self.state.line_scan_y,
            )
            if line_overlay is None:
                if self.state.line_scan_direction == "horizontal":
                    line_overlay = ("horizontal", float(np.nanmean(y_grid)))
                else:
                    line_overlay = ("vertical", float(np.nanmean(x_grid)))

        time_plot_points = self._time_plot_marker_points()
        debug_print(f"PlotOverTime overlay point count={len(time_plot_points)}")
        fig_width = orientation.plot_width_for_height(x_grid, y_grid, _CANVAS_HEIGHT)
        self.heatmap_canvas.set_canvas_width(fig_width)

        if extra_scale != 1.0:
            z_grid = z_grid * extra_scale
            vmin   = vmin   * extra_scale
            vmax   = vmax   * extra_scale
        colorbar_label = display_label

        plot_type = self.controls_widget.current_plot_type()
        if plot_type == "difference":
            diff = self._compute_difference_grid()
            if diff is not None:
                diff = orientation.apply_grid(self._last_grids[0], self._last_grids[1], diff).z
                if extra_scale != 1.0:
                    diff = diff * extra_scale
                abs_max        = max(abs(float(np.nanmin(diff))), abs(float(np.nanmax(diff))), 1e-12)
                z_grid         = diff
                vmin           = -abs_max
                vmax           =  abs_max
                colorbar_label = f"Δ {display_label}"
                cmap           = palette_to_cmap("ice-sunset")
            else:
                self.controls_widget.set_status_text("No next file available for difference plot")
                return

        self.heatmap_canvas.render_heatmap(
            x_grid=x_grid,
            y_grid=y_grid,
            z_grid=z_grid,
            cmap=cmap,
            status_message=self.state.status_message,
            vmin=vmin,
            vmax=vmax,
            line_overlay=line_overlay,
            overlay_grid=overlay_grid,
            time_plot_points=time_plot_points,
            colorbar_label=colorbar_label,
            plot_type=self.controls_widget.current_plot_type(),
            phase_fraction_overlays=phase_fraction_overlays,
        )

    def _time_plot_marker_points(self) -> list[dict[str, float | str]]:
        """Return selected Plot Over Time points when heatmap markers are enabled."""
        debug_print("HeatmapController._time_plot_marker_points called")
        if not self.state.time_plot_points_visible:
            debug_print("PlotOverTime markers disabled")
            return []
        points = [
            {"label": str(point["label"]), "x": float(point["x"]), "y": float(point["y"])}
            for point in self.state.time_plot_points
        ]
        for point in points:
            debug_print(f"PlotOverTime marker point={point}")
        return points

    def _compute_difference_grid(self) -> "np.ndarray | None":
        """Load the next file in the file combo and return (z_next − z_current)."""
        current_idx = self.controls_widget.file_combo.currentIndex()
        next_idx    = current_idx + 1
        if next_idx >= self.controls_widget.file_combo.count():
            return None
        next_path  = self.controls_widget.file_combo.itemData(next_idx)
        next_reader = get_reader(next_path)
        scalar_def  = self._get_scalar_def(self.state.scalar_key)
        if scalar_def is None or self._last_grids is None:
            return None
        _, _, z_next, _ = self._load_display_grid(
            next_reader,
            scalar_def,
            self.state.axis,
            self.state.slice_index,
            plot_type=self.controls_widget.current_plot_type(),
        )
        z_current = self._last_grids[2]
        return z_next - z_current

    def _render_line_scan(self, x_grid, y_grid, z_grid, extra_scale: float, display_label: str) -> None:
        """Extract a 1-D row or column from the slice grid and draw it on the line-scan canvas."""
        debug_print("HeatmapController._render_line_scan called")
        display = self._orientation().apply_grid(x_grid, y_grid, z_grid)
        position = self.state.line_scan_y if self.state.line_scan_direction == "horizontal" else self.state.line_scan_x
        x_data, z_data, title, x_label = Heatmap2DOrientation.extract_line_scan(
            display.x,
            display.y,
            display.z,
            self.state.line_scan_direction,
            position,
        )
        if extra_scale != 1.0:
            z_data = z_data * extra_scale
        self.line_scan_canvas.render_line(
            x_data,
            z_data,
            title=title,
            x_label=x_label,
            y_label=display_label,
        )

    def _render_histogram(self, extra_scale: float = 1.0, display_label: str = "") -> None:
        """Draw the histogram, reusing cached slice data where possible."""
        debug_print("HeatmapController._render_histogram called")
        if not self._last_grids:
            return
        scalar_key = self.state.scalar_key
        scalar_def = self._get_scalar_def(scalar_key)
        if scalar_def is None:
            return
        scale = scalar_def.get("scale", 1.0) or 1.0
        cache_key = (
            scalar_key,
            self.state.axis,
            self.state.slice_index,
            self.state.file_path,
            self._selected_resolution(),
        )
        is_same_field = scalar_key == self.state.scalar_key
        if is_same_field:
            z_grid = self._last_grids[2]
        elif self._histogram_cache and self._histogram_cache["key"] == cache_key:
            z_grid = self._histogram_cache["z_grid"]
        else:
            _, _, z_grid, _ = self.reader.get_interpolated_slice(
                axis=self.state.axis,
                index=self.state.slice_index,
                scalar_name=scalar_def["array"],
                component=scalar_def.get("component"),
                resolution=self._selected_resolution(),
            )
            z_grid = z_grid * scale
            self._histogram_cache = {"key": cache_key, "z_grid": z_grid}

        # Apply display scale and label — only when showing the same field as the heatmap
        if is_same_field and extra_scale != 1.0:
            z_grid = z_grid * extra_scale
        hist_label = display_label if (is_same_field and display_label) else scalar_def["label"]
        self.histogram_canvas.render_histogram(
            z_grid,
            label=hist_label,
            bins=int(self.histogram_bins_slider.value()),
        )

    def _handle_heatmap_click(self, x_value: float, y_value: float) -> None:
        """Handle a click on the heatmap: set the color range with two clicks, or reposition the line scan."""
        debug_print("HeatmapController._handle_heatmap_click called")
        if not self._last_grids:
            return
        x_grid, y_grid, z_grid = self._last_display_grids or self._last_grids[:3]
        try:
            snap_x, snap_y, clicked_value = Heatmap2DOrientation.nearest_point(x_grid, y_grid, z_grid, x_value, y_value)
        except ValueError:
            self.controls_widget.set_status_text("Click ignored: no valid value")
            return
        debug_print(f"Heatmap click raw x={x_value}")
        debug_print(f"Heatmap click raw y={y_value}")
        debug_print(f"Heatmap click snapped x={snap_x}")
        debug_print(f"Heatmap click snapped y={snap_y}")
        debug_print(f"Heatmap click nearest value={clicked_value}")
        if self.state.time_plot_pick_mode:
            self._set_time_plot_point(snap_x, snap_y, clicked_value, source="click")
            return
        if self.state.click_mode == "range":
            if self.state.click_count == 0:
                self.state.first_click = clicked_value
                self.state.click_count = 1
                self.state.clicked_message = f"First click: {clicked_value:.6f} (click again to finish range)"
                self.controls_widget.set_status_text(self.state.clicked_message)
                self.heatmap_canvas.render_status(self.state.clicked_message)
            else:
                lo, hi = sorted([self.state.first_click, clicked_value])
                self.state.range_min = lo
                self.state.range_max = hi
                self.state.threshold = (lo + hi) / 2
                self.state.click_count = 0
                self.state.first_click = None
                self.state.clicked_message = f"Range selected: [{lo:.6f}, {hi:.6f}]"
                self.controls_widget.set_range_values(lo, hi)
                self.refresh_view()
        elif self.state.click_mode == "linescan":
            if self.state.line_scan_direction == "horizontal":
                self.state.line_scan_y = y_value
            else:
                self.state.line_scan_x = x_value
            self.refresh_view()
        else:
            debug_print("Heatmap click ignored because click mode is none")
            self.controls_widget.set_status_text("Heatmap click ignored: enable Range Selection or Line Scan")

    def _on_line_mode_toggled(self, checked: bool) -> None:
        """Line Scan toggled — turn off Range Selection, refresh immediately."""
        debug_print("HeatmapController._on_line_mode_toggled called")
        debug_print(f"HeatmapController line mode checked={checked}")
        if checked:
            self._disable_time_plot_pick_mode("line-mode-selected")
            self.controls_widget.click_mode_range_check.blockSignals(True)
            self.controls_widget.click_mode_range_check.setChecked(False)
            self.controls_widget.click_mode_range_check.blockSignals(False)
            debug_print("HeatmapController disabled range mode for line scan")
        self.state.click_count = 0
        self.state.first_click = None
        self.controls_widget.set_last_trigger("line-mode")
        self.refresh_view()

    def _on_range_mode_toggled(self, checked: bool) -> None:
        """Range Selection toggled — turn off Line Scan, refresh immediately."""
        debug_print("HeatmapController._on_range_mode_toggled called")
        debug_print(f"HeatmapController range mode checked={checked}")
        if checked:
            self._disable_time_plot_pick_mode("range-mode-selected")
            self.line_mode_check.blockSignals(True)
            self.line_mode_check.setChecked(False)
            self.line_mode_check.blockSignals(False)
            debug_print("HeatmapController disabled line mode for range selection")
        self.state.click_count = 0
        self.state.first_click = None
        self.controls_widget.set_last_trigger("range-mode")
        self.refresh_view()

    def _sync_line_mode(self) -> None:
        """Keep the range-mode checkbox inverse-synced with the line-scan-mode checkbox."""
        debug_print("HeatmapController._sync_line_mode called")
        if self.line_mode_check.isChecked() and self.controls_widget.click_mode_range_check.isChecked():
            self.controls_widget.click_mode_range_check.blockSignals(True)
            self.controls_widget.click_mode_range_check.setChecked(False)
            self.controls_widget.click_mode_range_check.blockSignals(False)

    def _build_overlay_grid(self):
        """Load the PhaseField VTK file and return its grid data for drawing the interfaces overlay."""
        debug_print("HeatmapController._build_overlay_grid called")
        if not self.interfaces_check.isChecked():
            return None
        phase_file = self._phase_overlay_file(self.state.file_path)
        if not phase_file:
            return None
        try:
            phase_reader = get_reader(str(phase_file))
            x_grid, y_grid, z_grid, _ = phase_reader.get_interpolated_slice(
                axis=self.state.axis,
                index=self.state.slice_index,
                scalar_name="Interfaces",
                component=None,
                resolution=self._selected_resolution(),
            )
            debug_print(f"Overlay band min={float(np.min(z_grid))}")
            debug_print(f"Overlay band max={float(np.max(z_grid))}")
            interfaces_band = np.logical_and(np.asarray(z_grid) >= 1.5, np.asarray(z_grid) <= 3.5)
            debug_print(f"Overlay fill count={int(np.count_nonzero(interfaces_band))}")
            return {"x": x_grid, "y": y_grid, "z": np.asarray(z_grid)}
        except Exception as exc:
            debug_print(f"Overlay build failed: {exc}")
            return None

    def _orientation(self) -> Heatmap2DOrientation:
        return Heatmap2DOrientation(getattr(self.state, "rotation_degrees", 0))

    def _phase_overlay_file(self, file_path: str):
        """Resolve the PhaseField_*.vts file that corresponds to the currently loaded data file."""
        debug_print("HeatmapController._phase_overlay_file called")
        if not file_path:
            return None
        file_name = Path(file_path).name
        if file_name.startswith("PhaseField_"):
            return Path(file_path)
        suffix = file_name.split("_")[-1]
        candidate = Path(file_path).with_name(f"PhaseField_{suffix}")
        if candidate.exists():
            return candidate
        return None

    def _on_time_plot_add_point_toggled(self, checked: bool) -> None:
        """Toggle heatmap point picking for Plot Over Time."""
        debug_print("HeatmapController._on_time_plot_add_point_toggled called")
        debug_print(f"PlotOverTime add point toggled={checked}")
        self._set_time_plot_add_point_button_text(checked)
        self.state.time_plot_pick_mode = bool(checked)
        self.state.click_count = 0
        self.state.first_click = None
        debug_print("PlotOverTime reset click_count and first_click")
        if checked:
            self.controls_widget.click_mode_range_check.blockSignals(True)
            self.controls_widget.click_mode_range_check.setChecked(False)
            self.controls_widget.click_mode_range_check.blockSignals(False)
            debug_print("PlotOverTime disabled range mode")
            self.line_mode_check.blockSignals(True)
            self.line_mode_check.setChecked(False)
            self.line_mode_check.blockSignals(False)
            debug_print("PlotOverTime disabled line mode")
            self.state.click_mode = "time-plot"
            debug_print("PlotOverTime state click_mode=time-plot")
            if self.time_plot_selected_label is not None:
                self.time_plot_selected_label.setText("Click heatmap to add points")
            self.controls_widget.set_status_text("Plot Over Time: click heatmap to add points")
            debug_print("PlotOverTime add point mode enabled")
        else:
            self.controls_widget.click_mode_range_check.blockSignals(True)
            self.controls_widget.click_mode_range_check.setChecked(True)
            self.controls_widget.click_mode_range_check.blockSignals(False)
            debug_print("PlotOverTime restored range mode after toggle off")
            self.line_mode_check.blockSignals(True)
            self.line_mode_check.setChecked(False)
            self.line_mode_check.blockSignals(False)
            debug_print("PlotOverTime kept line mode disabled after toggle off")
            self.state.click_mode = "range"
            debug_print("PlotOverTime state click_mode=range")
            self._update_time_plot_selected_label()
            self.controls_widget.set_status_text("Plot Over Time point selection off")
            debug_print("PlotOverTime add point mode disabled")

    def _disable_time_plot_pick_mode(self, reason: str) -> None:
        """Turn off Plot Over Time heatmap point picking without disturbing selected points."""
        debug_print("HeatmapController._disable_time_plot_pick_mode called")
        debug_print(f"PlotOverTime disable reason={reason}")
        self.state.time_plot_pick_mode = False
        self.state.click_count = 0
        self.state.first_click = None
        if self.time_plot_add_point_btn is not None and self.time_plot_add_point_btn.isChecked():
            debug_print("PlotOverTime unchecking Add Point button")
            self.time_plot_add_point_btn.blockSignals(True)
            self.time_plot_add_point_btn.setChecked(False)
            self.time_plot_add_point_btn.blockSignals(False)
        self._set_time_plot_add_point_button_text(False)
        debug_print("PlotOverTime pick mode disabled")

    def _set_time_plot_add_point_button_text(self, checked: bool) -> None:
        """Show the Plot Over Time point-pick toggle state in the button label."""
        debug_print("HeatmapController._set_time_plot_add_point_button_text called")
        debug_print(f"PlotOverTime Add Point button checked={checked}")
        if self.time_plot_add_point_btn is None:
            debug_print("PlotOverTime Add Point button text skipped no button")
            return
        label = "Add Point: ON" if checked else "Add Point"
        self.time_plot_add_point_btn.setText(label)
        debug_print(f"PlotOverTime Add Point button text={label}")

    def _on_time_plot_show_points_toggled(self, checked: bool) -> None:
        """Show or hide selected Plot Over Time points on the heatmap."""
        debug_print("HeatmapController._on_time_plot_show_points_toggled called")
        debug_print(f"PlotOverTime show points toggled={checked}")
        self.state.time_plot_points_visible = bool(checked)
        self.controls_widget.set_last_trigger("time-plot-show-points")
        self.refresh_view()

    def _manual_time_plot_point(self) -> None:
        """Ask for an x/y point and store it for Plot Over Time."""
        debug_print("HeatmapController._manual_time_plot_point called")
        parent = self.export_widget or self.heatmap_canvas
        dialog = ManualPointDialog(
            x_value=self.state.time_plot_x if self.state.time_plot_x is not None else 0.0,
            y_value=self.state.time_plot_y if self.state.time_plot_y is not None else 0.0,
            parent=parent,
        )
        debug_print("PlotOverTime manual dialog created")
        if dialog.exec() != dialog.DialogCode.Accepted:
            debug_print("PlotOverTime manual point cancelled")
            return
        x_value, y_value = dialog.point_values()
        debug_print(f"PlotOverTime manual x={x_value}")
        debug_print(f"PlotOverTime manual y={y_value}")
        clicked_value = None
        snapped_x = float(x_value)
        snapped_y = float(y_value)
        if self._last_display_grids:
            try:
                snapped_x, snapped_y, clicked_value = Heatmap2DOrientation.nearest_point(
                    self._last_display_grids[0],
                    self._last_display_grids[1],
                    self._last_display_grids[2],
                    x_value,
                    y_value,
                )
                debug_print(f"PlotOverTime manual snapped x={snapped_x}")
                debug_print(f"PlotOverTime manual snapped y={snapped_y}")
                debug_print(f"PlotOverTime manual snapped value={clicked_value}")
            except ValueError:
                debug_print("PlotOverTime manual point nearest value unavailable")
        self._set_time_plot_point(snapped_x, snapped_y, clicked_value, source="manual")
        debug_print(f"PlotOverTime manual point accepted x={snapped_x} y={snapped_y}")

    def _set_time_plot_point(self, x_value: float, y_value: float, clicked_value, *, source: str) -> None:
        """Store a selected point and update Plot Over Time UI."""
        debug_print("HeatmapController._set_time_plot_point called")
        debug_print(f"PlotOverTime selected point x={x_value} y={y_value}")
        debug_print(f"PlotOverTime selected point source={source}")
        debug_print(f"PlotOverTime selected point value={clicked_value}")
        self.state.time_plot_x = float(x_value)
        self.state.time_plot_y = float(y_value)
        point_index = len(self.state.time_plot_points) + 1
        point = {
            "label": f"P{point_index}",
            "x": float(x_value),
            "y": float(y_value),
        }
        self.state.time_plot_points.append(point)
        self._refresh_time_plot_point_list()
        self._notify_time_plot_points_changed()
        self.state.time_plot_pick_mode = bool(
            self.time_plot_add_point_btn is not None
            and self.time_plot_add_point_btn.isChecked()
        )
        debug_print(f"PlotOverTime pick mode after point add={self.state.time_plot_pick_mode}")
        self.state.click_count = 0
        self.state.first_click = None
        value_text = "" if clicked_value is None else f" | value={float(clicked_value):.6g}"
        count = len(self.state.time_plot_points)
        label = f"{count} point selected: {point['label']} x={float(x_value):.4f}, y={float(y_value):.4f}{value_text}"
        if count != 1:
            label = f"{count} points selected | last: {point['label']} x={float(x_value):.4f}, y={float(y_value):.4f}{value_text}"
        if self.time_plot_selected_label is not None:
            self.time_plot_selected_label.setText(label)
        self.controls_widget.set_status_text(f"Plot Over Time point selected: x={float(x_value):.4f}, y={float(y_value):.4f}")
        if self.time_plot_canvas is not None:
            self.time_plot_canvas.render_placeholder("Press Calculate to plot value over time")
        if self.state.time_plot_points_visible:
            debug_print("PlotOverTime refreshing heatmap after point add")
            self.refresh_view()

    def _refresh_time_plot_point_list(self) -> None:
        """Rebuild the selected Plot Over Time point rows."""
        debug_print("HeatmapController._refresh_time_plot_point_list called")
        if self.time_plot_points_layout is None:
            debug_print("PlotOverTime point list refresh skipped no layout")
            return
        while self.time_plot_points_layout.count():
            item = self.time_plot_points_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                debug_print("PlotOverTime deleting old point row")
                widget.setParent(None)
                widget.deleteLater()
        for index, point in enumerate(self.state.time_plot_points):
            debug_print(f"PlotOverTime building point row index={index}")
            debug_print(f"PlotOverTime row point={point}")
            row = QWidget()
            row.setObjectName("timePlotPointRow")
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 6, 4)
            row_layout.setSpacing(8)
            label = QLabel(f"{point['label']}   x={float(point['x']):.4f}   y={float(point['y']):.4f}")
            label.setObjectName("timePlotPointLabel")
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            remove_button = QPushButton("X")
            remove_button.setObjectName("timePlotRemovePointButton")
            remove_button.setToolTip("Remove point")
            remove_button.setFixedSize(22, 22)
            remove_button.clicked.connect(lambda _checked=False, row_index=index: self._remove_time_plot_point(row_index))
            row_layout.addWidget(label)
            row_layout.addWidget(remove_button)
            self.time_plot_points_layout.addWidget(row)
        if self.time_plot_points_container is not None:
            self.time_plot_points_container.setVisible(bool(self.state.time_plot_points))
        debug_print(f"PlotOverTime point row count={len(self.state.time_plot_points)}")

    def _remove_time_plot_point(self, index: int) -> None:
        """Remove one selected Plot Over Time point by row index."""
        debug_print("HeatmapController._remove_time_plot_point called")
        debug_print(f"PlotOverTime remove index={index}")
        if index < 0 or index >= len(self.state.time_plot_points):
            debug_print("PlotOverTime remove skipped invalid index")
            return
        if self._time_plot_running:
            debug_print("PlotOverTime remove requested while running")
            self._cancel_time_plot_worker()
        removed = self.state.time_plot_points.pop(index)
        debug_print(f"PlotOverTime removed point={removed}")
        for point_index, point in enumerate(self.state.time_plot_points, start=1):
            point["label"] = f"P{point_index}"
            debug_print(f"PlotOverTime relabeled point={point}")
        if self.state.time_plot_points:
            last_point = self.state.time_plot_points[-1]
            self.state.time_plot_x = float(last_point["x"])
            self.state.time_plot_y = float(last_point["y"])
        else:
            self.state.time_plot_x = None
            self.state.time_plot_y = None
        self._time_plot_steps = []
        self._time_plot_values = []
        self._time_plot_series_data = []
        self._time_plot_errors = []
        self._refresh_time_plot_point_list()
        self._notify_time_plot_points_changed()
        self._update_time_plot_selected_label()
        if self.time_plot_progress is not None:
            self.time_plot_progress.setValue(0)
            self.time_plot_progress.setFormat("Ready")
        if self.time_plot_canvas is not None:
            message = "Press Calculate to plot value over time" if self.state.time_plot_points else "Add a point to plot value over time"
            self.time_plot_canvas.render_placeholder(message)
        self.controls_widget.set_status_text(f"Plot Over Time point removed: {removed['label']}")
        if self.state.time_plot_points_visible:
            debug_print("PlotOverTime refreshing heatmap after point remove")
            self.refresh_view()
        debug_print("PlotOverTime remove complete")

    def _update_time_plot_selected_label(self) -> None:
        """Update the summary label for selected Plot Over Time points."""
        debug_print("HeatmapController._update_time_plot_selected_label called")
        count = len(self.state.time_plot_points)
        if self.time_plot_selected_label is None:
            debug_print("PlotOverTime selected label skipped no widget")
            return
        if count == 0:
            self.time_plot_selected_label.setText("No point selected")
            debug_print("PlotOverTime selected label no points")
            return
        point = self.state.time_plot_points[-1]
        label = f"{count} point selected: {point['label']} x={float(point['x']):.4f}, y={float(point['y']):.4f}"
        if count != 1:
            label = f"{count} points selected | last: {point['label']} x={float(point['x']):.4f}, y={float(point['y']):.4f}"
        self.time_plot_selected_label.setText(label)
        debug_print(f"PlotOverTime selected label={label}")

    def _clear_time_plot(self) -> None:
        """Clear selected Plot Over Time point and graph data."""
        debug_print("HeatmapController._clear_time_plot called")
        self._cancel_time_plot_worker()
        self._disable_time_plot_pick_mode("clear-time-plot")
        self.state.time_plot_x = None
        self.state.time_plot_y = None
        self.state.time_plot_points = []
        self._refresh_time_plot_point_list()
        self._notify_time_plot_points_changed()
        self._time_plot_steps = []
        self._time_plot_values = []
        self._time_plot_series_data = []
        self._time_plot_errors = []
        if self.time_plot_selected_label is not None:
            self.time_plot_selected_label.setText("No point selected")
        if self.time_plot_progress is not None:
            self.time_plot_progress.setValue(0)
            self.time_plot_progress.setFormat("Ready")
        if self.time_plot_canvas is not None:
            self.time_plot_canvas.render_placeholder("Add a point to plot value over time")
        self.controls_widget.set_status_text("Plot Over Time cleared")
        if self.state.time_plot_points_visible:
            debug_print("PlotOverTime refreshing heatmap after clear")
            self.refresh_view()
        debug_print("PlotOverTime cleared")

    def time_plot_points_snapshot(self) -> list[dict]:
        """Return a copy of selected Plot Over Time points."""
        debug_print("HeatmapController.time_plot_points_snapshot called")
        snapshot = [dict(point) for point in self.state.time_plot_points]
        debug_print(f"PlotOverTime snapshot count={len(snapshot)}")
        return snapshot

    def set_time_plot_points(self, points: list[dict], *, source: str = "external", notify: bool = False) -> None:
        """Replace selected Plot Over Time points from an external/shared source."""
        debug_print("HeatmapController.set_time_plot_points called")
        debug_print(f"PlotOverTime set points source={source}")
        debug_print(f"PlotOverTime set point count={len(points)}")
        if self._time_plot_running:
            debug_print("PlotOverTime set points cancels running calculation")
            self._cancel_time_plot_worker()
        cleaned_points: list[dict] = []
        for index, point in enumerate(points, start=1):
            debug_print(f"PlotOverTime importing point index={index} point={point}")
            cleaned_points.append({
                "label": str(point.get("label") or f"P{index}"),
                "x": float(point["x"]),
                "y": float(point["y"]),
            })
        self.state.time_plot_points = cleaned_points
        if cleaned_points:
            last_point = cleaned_points[-1]
            self.state.time_plot_x = float(last_point["x"])
            self.state.time_plot_y = float(last_point["y"])
        else:
            self.state.time_plot_x = None
            self.state.time_plot_y = None
        self._time_plot_steps = []
        self._time_plot_values = []
        self._time_plot_series_data = []
        self._time_plot_errors = []
        self._refresh_time_plot_point_list()
        self._update_time_plot_selected_label()
        if self.time_plot_progress is not None:
            self.time_plot_progress.setValue(0)
            self.time_plot_progress.setFormat("Ready")
        if self.time_plot_canvas is not None:
            message = "Press Calculate to plot value over time" if cleaned_points else "Add a point to plot value over time"
            self.time_plot_canvas.render_placeholder(message)
        if self.state.time_plot_points_visible:
            debug_print("PlotOverTime refreshing heatmap after shared point import")
            self.refresh_view()
        if notify:
            self._notify_time_plot_points_changed()
        debug_print("PlotOverTime set points complete")

    def _notify_time_plot_points_changed(self) -> None:
        """Notify the owning panel/tab that this panel's selected points changed."""
        debug_print("HeatmapController._notify_time_plot_points_changed called")
        if self._time_plot_points_changed_callback is None:
            debug_print("PlotOverTime notify skipped no callback")
            return
        snapshot = self.time_plot_points_snapshot()
        self._time_plot_points_changed_callback(snapshot)
        debug_print("PlotOverTime notified points changed")

    def _current_file_paths(self) -> list[str]:
        """Return file paths currently listed in the file combo."""
        debug_print("HeatmapController._current_file_paths called")
        combo = self.controls_widget.file_combo
        paths = [combo.itemData(index) for index in range(combo.count())]
        paths = [str(path) for path in paths if path]
        debug_print(f"PlotOverTime combo file count={len(paths)}")
        return paths

    def _start_time_plot(self) -> None:
        """Start background Plot Over Time calculation."""
        debug_print("HeatmapController._start_time_plot called")
        if not self.state.time_plot_points:
            debug_print("PlotOverTime calculate skipped no point")
            self.controls_widget.set_status_text("Add a point before calculating Plot Over Time")
            if self.time_plot_canvas is not None:
                self.time_plot_canvas.render_placeholder("Add a point to plot value over time")
            return
        scalar_def = self._get_scalar_def(self.state.scalar_key)
        if scalar_def is None:
            debug_print("PlotOverTime calculate skipped no scalar")
            self.controls_widget.set_status_text("Select a scalar before calculating Plot Over Time")
            return
        files = collect_same_series_files(self.state.file_path, self._current_file_paths())
        debug_print(f"PlotOverTime same-series file count={len(files)}")
        if not files:
            debug_print("PlotOverTime calculate skipped no files")
            self.controls_widget.set_status_text("No matching timestep files found")
            return
        self._cancel_time_plot_worker()
        self._time_plot_steps = []
        self._time_plot_values = []
        self._time_plot_errors = []
        self._time_plot_series_data = [
            {"label": str(point["label"]), "x": float(point["x"]), "y": float(point["y"]), "steps": [], "values": []}
            for point in self.state.time_plot_points
        ]
        self._time_plot_series = files
        self._time_plot_index = 0
        self._time_plot_success = 0
        self._time_plot_failed = 0
        self._time_plot_scalar_def = scalar_def
        self._time_plot_running = True
        self._time_plot_cancel_requested = False
        if self.time_plot_progress is not None:
            self.time_plot_progress.setValue(0)
            self.time_plot_progress.setFormat("Loading %p%")
        if self.time_plot_calculate_btn is not None:
            self.time_plot_calculate_btn.setEnabled(False)
        if self.time_plot_cancel_btn is not None:
            self.time_plot_cancel_btn.setEnabled(True)
        extra_scale, display_label = self._get_display_params(self.controls_widget.current_scalar_label())
        self._time_plot_display_scale = extra_scale
        self._time_plot_display_label = display_label
        self.controls_widget.set_status_text(f"Plot Over Time reading {len(files)} files for {len(self._time_plot_series_data)} points")
        debug_print("PlotOverTime timer calculation started")
        QTimer.singleShot(0, self._process_next_time_plot_file)

    def _process_next_time_plot_file(self) -> None:
        """Process one Plot Over Time file on the main Qt event loop."""
        debug_print("HeatmapController._process_next_time_plot_file called")
        if not self._time_plot_running:
            debug_print("PlotOverTime timer skipped not running")
            return
        if self._time_plot_cancel_requested:
            debug_print("PlotOverTime timer saw cancel request")
            self._handle_time_plot_cancelled()
            return
        total = len(self._time_plot_series)
        if self._time_plot_index >= total:
            self._finish_time_plot(
                self._time_plot_success,
                self._time_plot_failed,
                self._time_plot_display_label,
            )
            return
        item = self._time_plot_series[self._time_plot_index]
        current_number = self._time_plot_index + 1
        debug_print(f"PlotOverTime reading file {current_number}/{total}: {item.path}")
        try:
            reader = get_reader(item.path)
            scalar_def = self._time_plot_scalar_def or {}
            scale = (scalar_def.get("scale", 1.0) or 1.0) * self._time_plot_display_scale
            file_success = 0
            file_failed = 0
            for point in self._time_plot_series_data:
                debug_print(f"PlotOverTime sampling point={point['label']} x={point['x']} y={point['y']}")
                value = reader.sample_point_value(
                    axis=self.state.axis,
                    index=self.state.slice_index,
                    scalar_name=scalar_def["array"],
                    component=scalar_def.get("component"),
                    x_value=point["x"],
                    y_value=point["y"],
                )
                value = float(value) * scale
                debug_print(f"PlotOverTime value point={point['label']} value={value}")
                point["steps"].append(int(item.step))
                point["values"].append(value)
                file_success += 1
            self._time_plot_success += file_success
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            debug_print(f"PlotOverTime error file={item.path} message={message}")
            self._time_plot_errors.append(f"{Path(item.path).name}: {message}")
            self._time_plot_failed += max(1, len(self._time_plot_series_data))
        self._time_plot_index += 1
        percent = int(self._time_plot_index / max(1, total) * 100)
        debug_print(f"PlotOverTime progress={percent}")
        if self.time_plot_progress is not None:
            self.time_plot_progress.setValue(percent)
        QTimer.singleShot(0, self._process_next_time_plot_file)

    def _render_time_plot_values(self) -> None:
        """Render currently collected Plot Over Time values."""
        debug_print("HeatmapController._render_time_plot_values called")
        if self.time_plot_canvas is None:
            debug_print("PlotOverTime render skipped no canvas")
            return
        series, x_label, hover_x_label = self._converted_time_plot_series()
        self.time_plot_canvas.render_time_series(
            series,
            y_label=self._time_plot_display_label,
            x_label=x_label,
            hover_x_label=hover_x_label,
        )

    def _handle_time_plot_sample(self, sample, display_label: str) -> None:
        """Receive one sampled timestep value from the worker."""
        debug_print("HeatmapController._handle_time_plot_sample called")
        debug_print(f"PlotOverTime sample step={sample.step}")
        debug_print(f"PlotOverTime sample value={sample.value}")
        self._time_plot_steps.append(int(sample.step))
        self._time_plot_values.append(float(sample.value))
        if self.time_plot_canvas is not None:
            point_label = f"x={self.state.time_plot_x:.4f}, y={self.state.time_plot_y:.4f}"
            factor, x_label, hover_x_label = self._phase_history_time_axis()
            converted_steps = [float(step) * factor for step in self._time_plot_steps]
            debug_print(f"PlotOverTime sample converted steps count={len(converted_steps)}")
            self.time_plot_canvas.render_time_plot(
                converted_steps,
                self._time_plot_values,
                y_label=display_label,
                point_label=point_label,
                x_label=x_label,
                hover_x_label=hover_x_label,
            )

    def _handle_time_plot_error(self, index: int, path: str, message: str) -> None:
        """Record one failed timestep without stopping the whole plot."""
        debug_print("HeatmapController._handle_time_plot_error called")
        debug_print(f"PlotOverTime error index={index}")
        debug_print(f"PlotOverTime error path={path}")
        debug_print(f"PlotOverTime error message={message}")
        self._time_plot_errors.append(f"{Path(path).name}: {message}")

    def _finish_time_plot(self, success: int, failed: int, display_label: str) -> None:
        """Finish worker UI state and leave final graph visible."""
        debug_print("HeatmapController._finish_time_plot called")
        debug_print(f"PlotOverTime worker finished success={success} failed={failed}")
        self._time_plot_running = False
        self._time_plot_cancel_requested = False
        if self.time_plot_progress is not None:
            self.time_plot_progress.setValue(100)
            self.time_plot_progress.setFormat(f"Done: {success} ok, {failed} failed")
        if self.time_plot_calculate_btn is not None:
            self.time_plot_calculate_btn.setEnabled(True)
        if self.time_plot_cancel_btn is not None:
            self.time_plot_cancel_btn.setEnabled(False)
        if success == 0 and self.time_plot_canvas is not None:
            self.time_plot_canvas.render_placeholder("No finite point-history values")
        elif success > 0:
            self._render_time_plot_values()
        self.controls_widget.set_status_text(f"Plot Over Time finished: {success} ok, {failed} failed")
        debug_print("PlotOverTime timer calculation finished")

    def _handle_time_plot_cancelled(self) -> None:
        """Update UI after user cancellation."""
        debug_print("HeatmapController._handle_time_plot_cancelled called")
        self._time_plot_running = False
        self._time_plot_cancel_requested = False
        if self.time_plot_progress is not None:
            self.time_plot_progress.setFormat("Cancelled")
        if self.time_plot_calculate_btn is not None:
            self.time_plot_calculate_btn.setEnabled(True)
        if self.time_plot_cancel_btn is not None:
            self.time_plot_cancel_btn.setEnabled(False)
        self.controls_widget.set_status_text("Plot Over Time cancelled")
        debug_print("PlotOverTime timer calculation cancelled")

    def _cancel_time_plot_worker(self) -> None:
        """Request cancellation for the active Plot Over Time worker."""
        debug_print("HeatmapController._cancel_time_plot_worker called")
        if not self._time_plot_running:
            debug_print("PlotOverTime cancel skipped not running")
            return
        self._time_plot_cancel_requested = True
        if self.time_plot_progress is not None:
            self.time_plot_progress.setFormat("Cancelling")
        debug_print("PlotOverTime cancel requested")

    def _export_png(self) -> None:
        """Ask for a location and save the current heatmap row as a PNG file."""
        debug_print("HeatmapController._export_png called")
        default_name = self._default_export_filename(self.dataset_info.get("label", "panel"))
        debug_print(f"HeatmapController default export name={default_name}")
        parent = self.export_widget or self.heatmap_canvas
        debug_print(f"HeatmapController export dialog parent={parent.__class__.__name__}")
        selected_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Export PNG",
            default_name,
            "PNG (*.png);;All Files (*)",
        )
        debug_print(f"HeatmapController selected export path={selected_path}")
        output_path = self._normalise_png_export_path(selected_path)
        if output_path is None:
            debug_print("HeatmapController export cancelled")
            self.controls_widget.set_status_text("PNG export cancelled")
            return
        plot_type = self.controls_widget.current_plot_type()
        debug_print(f"HeatmapController export plot_type={plot_type}")
        if plot_type == "threshold":
            debug_print("HeatmapController exporting exact current threshold row")
            saved = self._save_current_export_widget_png(str(output_path))
        else:
            debug_print("HeatmapController exporting from heatmap data payload")
            saved = self.heatmap_canvas.save_high_resolution_png(str(output_path))
        debug_print(f"HeatmapController export saved={saved}")
        debug_print(f"HeatmapController export output path={output_path}")
        if saved:
            self.controls_widget.set_status_text(f"PNG saved: {output_path.name}")
        else:
            self.controls_widget.set_status_text("PNG export failed")
        debug_print("HeatmapController._export_png complete")

    def _save_current_export_widget_png(self, path: str) -> bool:
        """Save the visible export row so logo and heatmap are captured together."""
        debug_print("HeatmapController._save_current_export_widget_png called")
        widget = self.export_widget or self.heatmap_canvas
        debug_print(f"HeatmapController current-row export widget={widget.__class__.__name__}")
        debug_print(f"HeatmapController current-row export path={path}")
        pixmap = widget.grab()
        debug_print(f"HeatmapController current-row pixmap null={pixmap.isNull()}")
        saved = pixmap.save(path, "PNG")
        debug_print(f"HeatmapController current-row export saved={saved}")
        return bool(saved)

    @staticmethod
    def _default_export_filename(label: str) -> str:
        debug_print("HeatmapController._default_export_filename called")
        debug_print(f"HeatmapController export label={label}")
        safe_label = "".join(
            char if char.isalnum() or char in ("-", "_") else "_"
            for char in (label or "panel")
        ).strip("_")
        safe_label = safe_label or "panel"
        filename = f"{safe_label}_heatmap.png"
        debug_print(f"HeatmapController export filename={filename}")
        return filename

    @staticmethod
    def _normalise_png_export_path(path: str) -> Path | None:
        debug_print("HeatmapController._normalise_png_export_path called")
        debug_print(f"HeatmapController raw export path={path}")
        if not path:
            debug_print("HeatmapController normalised export path=None")
            return None
        output_path = Path(path)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".png")
            debug_print(f"HeatmapController appended png suffix={output_path}")
        debug_print(f"HeatmapController normalised export path={output_path}")
        return output_path

    def _handle_range_slider_signal(self, minimum: float, maximum: float) -> None:
        """Receive the range slider's min/max values emitted after the user drags the handles."""
        debug_print("HeatmapController._handle_range_slider_signal called")
        debug_print(f"Controller slider signal={minimum}..{maximum}")
