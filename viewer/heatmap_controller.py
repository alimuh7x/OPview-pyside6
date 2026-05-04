"""Controller for panel UI state and rendering updates."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
from matplotlib.colors import Normalize

from app.debug import debug_print
from config.constants import DEFAULTS
from utils.vtk_utils import get_reader
from viewer.colorscale import make_dynamic_colormap, palette_to_cmap
from viewer.heatmap_canvas import _CANVAS_HEIGHT
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
        line_scan_info_label,
        line_mode_check,
        show_line_check,
        direction_combo,
        histogram_field_combo,
        histogram_bins_slider,
        interfaces_check,
        export_button,
        map_title_label,
        dataset_info: dict,
    ) -> None:
        debug_print("HeatmapController.__init__ start")
        self.controls_widget = controls_widget
        self.heatmap_canvas = heatmap_canvas
        self.line_scan_canvas = line_scan_canvas
        self.histogram_canvas = histogram_canvas
        self.line_scan_info_label = line_scan_info_label
        self.line_mode_check = line_mode_check
        self.show_line_check = show_line_check
        self.direction_combo = direction_combo
        self.histogram_field_combo = histogram_field_combo
        self.histogram_bins_slider = histogram_bins_slider
        self.interfaces_check = interfaces_check
        self.export_button = export_button
        self.map_title_label = map_title_label
        self.dataset_info = dataset_info
        self.reader = None
        self.scalar_defs: list[dict] = []
        self._last_grids = None
        self._last_scaled_grid = None
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

    def connect_signals(self) -> None:
        debug_print("HeatmapController.connect_signals called")
        self.controls_widget.refresh_requested.connect(self.refresh_view)
        self.controls_widget.range_slider_changed.connect(self._handle_range_slider_signal)
        self.line_mode_check.toggled.connect(self._sync_line_mode)
        self.show_line_check.toggled.connect(self.refresh_view)
        self.direction_combo.currentIndexChanged.connect(self.refresh_view)
        self.histogram_field_combo.currentIndexChanged.connect(self.refresh_view)
        self.histogram_bins_slider.valueChanged.connect(self.refresh_view)
        self.interfaces_check.toggled.connect(self.refresh_view)
        self.export_button.clicked.connect(self._export_png)
        self.heatmap_canvas.heatmap_clicked.connect(self._handle_heatmap_click)
        debug_print("HeatmapController connected all signals")

    def _initialize_controls(self) -> None:
        debug_print("HeatmapController._initialize_controls called")
        files = self.dataset_info.get("files", [])
        self.controls_widget.set_file_options(files)
        if files:
            self._load_reader(files[0])
        else:
            self.controls_widget.set_status_text("No VTK files available")
        self._sync_line_mode()

    def refresh_view(self) -> None:
        debug_print("HeatmapController.refresh_view called")
        file_path = self.controls_widget.current_file_path()
        debug_print(f"Controller file_path={file_path}")
        if not file_path:
            self.controls_widget.set_status_text("Select a VTK file first")
            self.heatmap_canvas.render_status("No file selected")
            return
        if self.reader is None or self.state.file_path != file_path:
            self._load_reader(file_path)

        scalar_key = self.controls_widget.current_scalar_key()
        scalar_label = self.controls_widget.current_scalar_label()
        axis = self.controls_widget.current_axis()
        slice_index = self.controls_widget.current_slice_index()
        palette = self.controls_widget.current_palette()
        debug_print(f"Controller read scalar_key={scalar_key}")
        debug_print(f"Controller read scalar_label={scalar_label}")
        debug_print(f"Controller read axis={axis}")
        debug_print(f"Controller read slice_index={slice_index}")
        scalar_def = self._get_scalar_def(scalar_key)
        if scalar_def is None:
            self.controls_widget.set_status_text("No scalar selected")
            self.heatmap_canvas.render_status("No scalar selected")
            return

        previous_state = replace(self.state)
        self.state.scalar_key = scalar_key
        self.state.scalar_label = scalar_label
        self.state.axis = axis
        self.state.slice_index = slice_index
        self.state.file_path = file_path
        self.state.palette = palette
        self.state.scale = scalar_def.get("scale", 1.0) or 1.0
        self.state.units = scalar_def.get("units")
        self.state.colorscale_mode = "dynamic" if self.controls_widget.full_scale_enabled() else "normal"
        self.state.line_overlay_visible = self.show_line_check.isChecked()
        self.state.line_scan_direction = self.direction_combo.currentData() or "horizontal"
        self.state.interfaces_overlay_visible = self.interfaces_check.isChecked()
        self.state.click_mode = "linescan" if self.line_mode_check.isChecked() else "range"

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
        if self.map_title_label is not None:
            self.map_title_label.setText(f"Auto Dataset: {scalar_label}")
        self._render_heatmap(x_grid, y_grid, z_grid, scalar_label)
        self._render_line_scan(x_grid, y_grid, z_grid)
        self._render_histogram()
        debug_print("Controller requested all canvas updates")

    def _load_reader(self, file_path: str) -> None:
        debug_print("HeatmapController._load_reader called")
        self.reader = get_reader(file_path)
        axis = self._detect_axis()
        self.scalar_defs = self._build_scalar_defs()
        first_scalar = self.scalar_defs[0] if self.scalar_defs else {"value": "", "label": ""}
        fallback_state = self._build_state(self.reader, file_path, first_scalar["value"], axis)
        self.state = fallback_state
        self.controls_widget.set_project_text(self._project_display_text())
        self.controls_widget.set_axis(axis)
        max_slice_index = self.reader.get_max_slice_index(axis)
        self.controls_widget.set_slice_range(0, max_slice_index)
        self.controls_widget.set_slice_controls_visible(max_slice_index > 0)
        self.controls_widget.set_scalar_options(self.scalar_defs)
        self.histogram_field_combo.blockSignals(True)
        self.histogram_field_combo.clear()
        for scalar_def in self.scalar_defs:
            self.histogram_field_combo.addItem(scalar_def["label"], scalar_def["value"])
        self.histogram_field_combo.blockSignals(False)
        self.controls_widget.set_slider_bounds(self.state.range_min, self.state.range_max)
        self.controls_widget.set_range_values(self.state.range_min, self.state.range_max)
        self.controls_widget.set_status_text(f"Loaded {Path(file_path).name}")
        self.interfaces_check.setChecked(False)
        debug_print("HeatmapController reader and controls updated")

    def _project_display_text(self) -> str:
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
        debug_print("HeatmapController._get_scalar_def called")
        for scalar_def in self.scalar_defs:
            if scalar_def["value"] == scalar_key:
                return scalar_def
        return self.scalar_defs[0] if self.scalar_defs else None

    def _detect_axis(self) -> str:
        debug_print("HeatmapController._detect_axis called")
        assert self.reader is not None
        dx, dy, dz = self.reader.dimensions
        if dz <= 1:
            return "z"
        if dy <= 1:
            return "y"
        if dx <= 1:
            return "x"
        return "y"

    def _build_state(self, reader, file_path: str, scalar_key: str, axis: str) -> ViewerState:
        debug_print("HeatmapController._build_state called")
        descriptor = self._get_scalar_def(scalar_key) or self.scalar_defs[0]
        slice_index = 0 if not reader.is_3d else reader.get_max_slice_index(axis) // 2
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
        debug_print("HeatmapController._reset_range_from_stats called")
        self.state.range_min = stats_scaled["min"]
        self.state.range_max = stats_scaled["max"]
        self.state.threshold = (stats_scaled["min"] + stats_scaled["max"]) / 2
        self.state.click_count = 0
        self.state.first_click = None
        self.controls_widget.set_slider_bounds(self.state.range_min, self.state.range_max)
        self.controls_widget.set_range_values(self.state.range_min, self.state.range_max)

    def _slice_dimensions(self, axis: str) -> tuple[int, int]:
        """Return (nx, ny) of the slice plane — mirrors Dash _slice_dimensions."""
        if self.reader is None or not self.reader.dimensions:
            return 1, 1
        dx, dy, dz = self.reader.dimensions
        axis = (axis or "y").lower()
        if axis == "x":
            return max(dy, 1), max(dz, 1)
        if axis == "y":
            return max(dx, 1), max(dz, 1)
        return max(dx, 1), max(dy, 1)

    def _render_heatmap(self, x_grid, y_grid, z_grid, scalar_label: str) -> None:
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

        overlay_grid = self._build_overlay_grid()
        line_overlay = None
        if self.state.line_overlay_visible:
            if self.state.line_scan_direction == "horizontal" and self.state.line_scan_y is not None:
                line_overlay = ("horizontal", self.state.line_scan_y)
            elif self.state.line_scan_direction == "vertical" and self.state.line_scan_x is not None:
                line_overlay = ("vertical", self.state.line_scan_x)

        nx, ny = self._slice_dimensions(self.state.axis)
        fig_width = max(100, min(1200, int(_CANVAS_HEIGHT * nx / ny)))
        self.heatmap_canvas.set_canvas_width(fig_width)

        colorbar_label = scalar_label + (f" ({self.state.units})" if self.state.units else "")
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
        )

    def _render_line_scan(self, x_grid, y_grid, z_grid) -> None:
        debug_print("HeatmapController._render_line_scan called")
        if self.state.line_scan_direction == "horizontal":
            if self.state.line_scan_y is not None:
                y_values = y_grid[:, 0]
                y_idx = int(np.argmin(np.abs(y_values - self.state.line_scan_y)))
                x_data = x_grid[y_idx, :]
                z_data = z_grid[y_idx, :]
                title = f"Horizontal Scan at Y={self.state.line_scan_y:.2f}"
            else:
                y_idx = z_grid.shape[0] // 2
                x_data = x_grid[y_idx, :]
                z_data = z_grid[y_idx, :]
                title = "Horizontal Scan (click heatmap to set position)"
            x_label = "X Position"
        else:
            if self.state.line_scan_x is not None:
                x_values = x_grid[0, :]
                x_idx = int(np.argmin(np.abs(x_values - self.state.line_scan_x)))
                x_data = y_grid[:, x_idx]
                z_data = z_grid[:, x_idx]
                title = f"Vertical Scan at X={self.state.line_scan_x:.2f}"
            else:
                x_idx = z_grid.shape[1] // 2
                x_data = y_grid[:, x_idx]
                z_data = z_grid[:, x_idx]
                title = "Vertical Scan (click heatmap to set position)"
            x_label = "Y Position"
        self.line_scan_canvas.render_line(
            x_data,
            z_data,
            title=title,
            x_label=x_label,
            y_label=self.state.scalar_label + (f" ({self.state.units})" if self.state.units else ""),
        )
        if self.state.click_mode == "linescan":
            self.line_scan_info_label.setText("Click heatmap to set line scan position")
        else:
            self.line_scan_info_label.setText("Switch to 'Line Scan' mode to set position by clicking")

    def _render_histogram(self) -> None:
        debug_print("HeatmapController._render_histogram called")
        if not self._last_grids:
            return
        scalar_key = self.histogram_field_combo.currentData() or self.state.scalar_key
        scalar_def = self._get_scalar_def(scalar_key)
        if scalar_def is None:
            return
        x_grid, y_grid, z_grid, _ = self.reader.get_interpolated_slice(
            axis=self.state.axis,
            index=self.state.slice_index,
            scalar_name=scalar_def["array"],
            component=scalar_def.get("component"),
            resolution=DEFAULTS["interpolation_resolution"],
        )
        scale = scalar_def.get("scale", 1.0) or 1.0
        z_grid = z_grid * scale
        self.histogram_canvas.render_histogram(
            z_grid,
            label=scalar_def["label"],
            bins=int(self.histogram_bins_slider.value()),
        )

    def _handle_heatmap_click(self, x_value: float, y_value: float) -> None:
        debug_print("HeatmapController._handle_heatmap_click called")
        if not self._last_grids:
            return
        x_grid, y_grid, z_grid, _ = self._last_grids
        distance = (x_grid - x_value) ** 2 + (y_grid - y_value) ** 2
        idx = np.unravel_index(np.nanargmin(distance), distance.shape)
        clicked_value = float(z_grid[idx])
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

    def _sync_line_mode(self) -> None:
        debug_print("HeatmapController._sync_line_mode called")
        self.controls_widget.click_mode_range_check.blockSignals(True)
        self.controls_widget.click_mode_range_check.setChecked(not self.line_mode_check.isChecked())
        self.controls_widget.click_mode_range_check.blockSignals(False)

    def _build_overlay_grid(self):
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

    def _phase_overlay_file(self, file_path: str):
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
        debug_print("HeatmapController._export_png called")
        output_path = Path.cwd() / f"{self.dataset_info.get('label', 'panel').replace(' ', '_')}_heatmap.png"
        self.heatmap_canvas.save_png(str(output_path))
        self.controls_widget.set_status_text(f"PNG saved: {output_path.name}")

    def _handle_range_slider_signal(self, minimum: float, maximum: float) -> None:
        debug_print("HeatmapController._handle_range_slider_signal called")
        debug_print(f"Controller slider signal={minimum}..{maximum}")
