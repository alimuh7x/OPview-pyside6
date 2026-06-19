"""Controller for panel UI state and rendering updates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
from matplotlib.colors import Normalize
from PySide6.QtWidgets import QFileDialog

from app.debug import debug_print
from config.constants import DEFAULTS
from utils.vtk_utils import get_reader
from viewer.colorscale import make_dynamic_colormap, palette_to_cmap
from viewer.heatmap_canvas import _CANVAS_HEIGHT
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.state import ViewerState, initial_state


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
        self.export_widget = export_widget
        self.dataset_info = dataset_info
        self._file_loaded_callback = None
        self.reader = None
        self.scalar_defs: list[dict] = []
        self._last_grids = None
        self._last_display_grids = None
        self._last_scaled_grid = None
        self._histogram_cache: dict | None = None
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
        self.show_line_check.toggled.connect(self.refresh_view)
        self.direction_combo.currentIndexChanged.connect(self.refresh_view)
        self.controls_widget.scalar_combo.currentIndexChanged.connect(self.refresh_view)
        self.histogram_bins_slider.valueChanged.connect(self.refresh_view)
        self.interfaces_check.toggled.connect(self.refresh_view)
        self.export_button.clicked.connect(self._export_png)
        self.heatmap_canvas.heatmap_clicked.connect(self._handle_heatmap_click)
        self.colorbar_label_edit.editingFinished.connect(self.refresh_view)
        self.unit_scale_combo.currentIndexChanged.connect(self.refresh_view)
        debug_print("HeatmapController connected all signals")

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
            if project_info:
                self.dataset_info["vtk_folder"] = project_info.get("vtk_folder", "")
                self.dataset_info["project_name"] = project_info.get("project_name", "")
                self.controls_widget.set_file_options(project_info.get("files", []))
            return  # file_combo change fires a second refresh that loads the file
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
        debug_print(f"Controller read scalar_key={scalar_key}")
        debug_print(f"Controller read scalar_label={scalar_label}")
        debug_print(f"Controller read axis={axis}")
        debug_print(f"Controller read slice_index={slice_index}")
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
        self.state.click_mode                 = "linescan" if self.line_mode_check.isChecked() else "range"
        if previous_state.rotation_degrees != self.state.rotation_degrees:
            self.state.line_scan_x = None
            self.state.line_scan_y = None
            self.state.click_count = 0
            self.state.first_click = None

        x_grid, y_grid, z_grid, stats = self.reader.get_interpolated_slice(
            axis=axis,
            index=slice_index,
            scalar_name=scalar_def["array"],
            component=scalar_def.get("component"),
            resolution=DEFAULTS["interpolation_resolution"],
        )
        z_grid = z_grid * self.state.scale
        self._last_grids = (x_grid, y_grid, z_grid, stats)
        self._last_scaled_grid = z_grid

        stats_scaled = {key: stats[key] * self.state.scale for key in stats}
        trigger = self.controls_widget.last_trigger()
        if (
            previous_state.scalar_key != self.state.scalar_key
            or previous_state.file_path != self.state.file_path
            or previous_state.axis != self.state.axis
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

        message = (
            f"Dataset={self.state.dataset_label} | "
            f"scalar={scalar_label or 'not-selected'} | "
            f"axis={axis} | "
            f"slice={slice_index} | "
            f"min={self.state.range_min:.4g} | "
            f"max={self.state.range_max:.4g}"
        )
        self.state.status_message = message
        debug_print(f"Controller updated state={self.state}")
        self.controls_widget.set_status_text(message)
        extra_scale, display_label = self._get_display_params(scalar_label)
        self._render_heatmap(x_grid, y_grid, z_grid, extra_scale, display_label)
        self._render_line_scan(x_grid, y_grid, z_grid, extra_scale, display_label)
        self._render_histogram(extra_scale, display_label)
        debug_print("Controller requested all canvas updates")

    def _load_reader(self, file_path: str) -> None:
        """Open a VTK file, detect slice axis, build scalar definitions, and sync all UI controls."""
        debug_print("HeatmapController._load_reader called")
        self._histogram_cache = None
        self.reader      = get_reader(file_path)
        axis             = self._detect_axis()
        self.scalar_defs = self._build_scalar_defs()
        first_scalar     = self.scalar_defs[0] if self.scalar_defs else {"value": "", "label": ""}
        fallback_state   = self._build_state(self.reader, file_path, first_scalar["value"], axis)
        self.state       = fallback_state
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

        self.controls_widget.set_slider_bounds(self.state.range_min, self.state.range_max)
        self.controls_widget.set_range_values(self.state.range_min, self.state.range_max)
        self.controls_widget.set_status_text(f"Loaded {Path(file_path).name}")
        if self._file_loaded_callback:
            self._file_loaded_callback(file_path)
        debug_print("HeatmapController reader and controls updated")

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
        x_grid, y_grid, z_grid, stats = reader.get_interpolated_slice(
            axis=axis,
            index=slice_index,
            scalar_name=descriptor["array"],
            component=descriptor.get("component"),
            resolution=DEFAULTS["interpolation_resolution"],
        )
        scale = descriptor.get("scale", 1.0) or 1.0
        stats_scaled = {key: stats[key] * scale for key in stats}
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
            colorbar_label=colorbar_label,
            plot_type=self.controls_widget.current_plot_type(),
        )

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
        _, _, z_next, _ = next_reader.get_interpolated_slice(
            axis        = self.state.axis,
            index       = self.state.slice_index,
            scalar_name = scalar_def["array"],
            component   = scalar_def.get("component"),
            resolution  = DEFAULTS["interpolation_resolution"],
        )
        z_next    = z_next * self.state.scale
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
        cache_key = (scalar_key, self.state.axis, self.state.slice_index, self.state.file_path)
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
                resolution=DEFAULTS["interpolation_resolution"],
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
            clicked_value = Heatmap2DOrientation.nearest_value(x_grid, y_grid, z_grid, x_value, y_value)
        except ValueError:
            self.controls_widget.set_status_text("Click ignored: no valid value")
            return
        debug_print(f"Heatmap click nearest value={clicked_value}")
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
        else:
            if self.state.line_scan_direction == "horizontal":
                self.state.line_scan_y = y_value
            else:
                self.state.line_scan_x = x_value
            self.refresh_view()

    def _on_line_mode_toggled(self, checked: bool) -> None:
        """Line Scan toggled — turn off Range Selection, refresh immediately."""
        self.controls_widget.click_mode_range_check.blockSignals(True)
        self.controls_widget.click_mode_range_check.setChecked(not checked)
        self.controls_widget.click_mode_range_check.blockSignals(False)
        self.refresh_view()

    def _on_range_mode_toggled(self, checked: bool) -> None:
        """Range Selection toggled — turn off Line Scan, refresh immediately."""
        self.line_mode_check.blockSignals(True)
        self.line_mode_check.setChecked(not checked)
        self.line_mode_check.blockSignals(False)
        self.refresh_view()

    def _sync_line_mode(self) -> None:
        """Keep the range-mode checkbox inverse-synced with the line-scan-mode checkbox."""
        debug_print("HeatmapController._sync_line_mode called")
        self.controls_widget.click_mode_range_check.blockSignals(True)
        self.controls_widget.click_mode_range_check.setChecked(not self.line_mode_check.isChecked())
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
                resolution=DEFAULTS["interpolation_resolution"],
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
        target = self.export_widget or self.heatmap_canvas
        debug_print(f"HeatmapController export target={target.__class__.__name__}")
        debug_print(f"HeatmapController export target size={target.size()}")
        pixmap = target.grab()
        debug_print(f"HeatmapController export pixmap size={pixmap.size()}")
        saved = pixmap.save(str(output_path), "PNG")
        debug_print(f"HeatmapController export saved={saved}")
        debug_print(f"HeatmapController export output path={output_path}")
        if saved:
            self.controls_widget.set_status_text(f"PNG saved: {output_path.name}")
        else:
            self.controls_widget.set_status_text("PNG export failed")
        debug_print("HeatmapController._export_png complete")

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
