"""Plotly-backed heatmap canvas."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print
from config.constants import DEFAULTS
from viewer.colorbar_ticks import format_colorbar_tick, format_colorbar_ticks
from viewer.colorscale import cmap_to_plotly_scale
from viewer.discrete_legend import add_discrete_legend_to_figure
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.plot_style import PlotStyle

_CANVAS_HEIGHT = 420
_CANVAS_WIDTH  = 360
_COLORBAR_WIDTH = 90
_COLORBAR_GAP = 0.012
_EXPORT_COLORBAR_GAP_VIEW_PX = 10.0
_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


class _AxesCompat:
    """Small compatibility shim for existing tests."""

    def get_aspect(self) -> float:
        return 1.0


class _NormCompat:
    """Compatibility shim for old matplotlib norm checks."""

    def __init__(self, vmin: float, vmax: float) -> None:
        self.vmin = vmin
        self.vmax = vmax


class _ImageCompat:
    """Compatibility shim for old matplotlib image checks."""

    def __init__(self, vmin: float, vmax: float) -> None:
        self.norm = _NormCompat(vmin, vmax)


class _PlotlyBridge(QObject):
    """WebChannel bridge used by Plotly events."""

    def __init__(self, canvas: "HeatmapCanvas") -> None:
        super().__init__()
        self._canvas = canvas

    @Slot(str, str)
    def sendEvent(self, event_type: str, payload_json: str) -> None:  # noqa: N802
        debug_print("PlotlyBridge.sendEvent called")
        debug_print(f"PlotlyBridge event_type={event_type}")
        self._canvas.handle_plotly_event(event_type, payload_json)


class _DebugWebEnginePage(QWebEnginePage):
    """Page subclass that forwards JS console and load diagnostics."""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802
        debug_print("DebugWebEnginePage.javaScriptConsoleMessage called")
        debug_print(f"Plotly console level={level}")
        debug_print(f"Plotly console line={line_number}")
        debug_print(f"Plotly console source={source_id}")
        debug_print(f"Plotly console message={message}")
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class HeatmapCanvas(QWidget):
    """Render interactive Plotly heatmaps inside the Qt panel."""

    heatmap_clicked = Signal(float, float)
    geometry_changed = Signal()
    status_changed = Signal(str)

    def __init__(self) -> None:
        debug_print("HeatmapCanvas.__init__ start")
        super().__init__()
        self._status_text = "Heatmap waiting for controller"
        self._hover_text = ""
        self._axes = _AxesCompat()
        self._image = None
        self._last_z_grid = None
        self._last_extent = None
        self._last_export_payload = None
        self._plot_width = _CANVAS_WIDTH
        self._colorbar_width = _COLORBAR_WIDTH
        self._colorbar_label = ""
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        self._web_view.setPage(_DebugWebEnginePage(self._web_view))
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._channel = QWebChannel(self._web_view.page())
        self._bridge = _PlotlyBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._web_view.page().setWebChannel(self._channel)
        self._web_view.loadStarted.connect(self._handle_load_started)
        self._web_view.loadFinished.connect(self._handle_load_finished)
        self._web_view.setContextMenuPolicy(self.contextMenuPolicy())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._web_view)
        self.set_canvas_width(_CANVAS_WIDTH)
        self.setFixedHeight(_CANVAS_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        debug_print("HeatmapCanvas.__init__ complete")

    def set_canvas_width(self, width: int) -> None:
        """Set the heatmap plotting width and keep room for Plotly's colorbar."""
        debug_print("HeatmapCanvas.set_canvas_width called")
        debug_print(f"HeatmapCanvas plot width={width}")
        self._plot_width = width
        widget_width = width + self._colorbar_width
        self._web_view.setFixedSize(widget_width, _CANVAS_HEIGHT)
        self.setFixedSize(widget_width, _CANVAS_HEIGHT)
        self.geometry_changed.emit()
        debug_print(f"HeatmapCanvas widget width={widget_width}")
        debug_print("HeatmapCanvas geometry_changed emitted")

    def _fmt_tick(self, v: float) -> str:
        """Format a colorbar tick value — scientific notation for large/small numbers."""
        debug_print("HeatmapCanvas._fmt_tick called")
        label = format_colorbar_tick(v)
        debug_print(f"HeatmapCanvas formatted tick={label}")
        return label

    def _compute_colorbar_width(self, vmin: float, vmax: float) -> int:
        """Estimate pixel width needed for the colorbar based on the widest tick label."""
        debug_print("HeatmapCanvas._compute_colorbar_width called")
        ticks = self._colorbar_ticks(vmin, vmax)
        tick_text = format_colorbar_ticks(ticks)
        debug_print(f"HeatmapCanvas width tick_text={tick_text}")
        n_chars = max(len(label) for label in tick_text)
        # Shared tick font is size 22; estimate roughly 11px per character.
        # bar thickness (18px) + gap (8px) + label text + right padding (14px)
        return max(_COLORBAR_WIDTH, 18 + 8 + n_chars * 11 + 14)

    @staticmethod
    def _colorbar_ticks(vmin: float, vmax: float) -> list[float]:
        debug_print("HeatmapCanvas._colorbar_ticks called")
        ticks = [
            vmin,
            vmin + (vmax - vmin) * 0.25,
            vmin + (vmax - vmin) * 0.5,
            vmin + (vmax - vmin) * 0.75,
            vmax,
        ]
        debug_print(f"HeatmapCanvas colorbar ticks={ticks}")
        return ticks

    def _update_colorbar_width(self, vmin: float, vmax: float) -> None:
        """Resize the canvas if the required colorbar width has changed."""
        needed = self._compute_colorbar_width(vmin, vmax)
        if needed != self._colorbar_width:
            self._colorbar_width = needed
            widget_width = self._plot_width + self._colorbar_width
            self._web_view.setFixedSize(widget_width, _CANVAS_HEIGHT)
            self.setFixedSize(widget_width, _CANVAS_HEIGHT)
            self.geometry_changed.emit()
            debug_print(f"HeatmapCanvas colorbar_width updated to {needed}")

    def canvas_width(self) -> int:
        debug_print("HeatmapCanvas.canvas_width called")
        return self.width()

    def canvas_height(self) -> int:
        debug_print("HeatmapCanvas.canvas_height called")
        return self.height()

    def render_heatmap(
        self,
        x_grid,
        y_grid,
        z_grid,
        *,
        cmap,
        status_message: str,
        vmin: float,
        vmax: float,
        line_overlay=None,
        overlay_grid=None,
        time_plot_points=None,
        title: str = "",
        colorbar_label: str = "",
        plot_type: str = "heatmap",
        colorbar_mode: str = "bar",
        discrete_colors=None,
        phase_fraction_overlays=None,
        vector_overlay=None,
    ) -> None:
        debug_print("HeatmapCanvas.render_heatmap called")
        debug_print(f"HeatmapCanvas colorbar_mode={colorbar_mode}")
        debug_print(f"HeatmapCanvas discrete_colors={discrete_colors}")
        self._update_colorbar_width(vmin, vmax)
        extent = (
            float(np.nanmin(x_grid)),
            float(np.nanmax(x_grid)),
            float(np.nanmin(y_grid)),
            float(np.nanmax(y_grid)),
        )
        self._last_extent = extent
        self._last_z_grid = np.asarray(z_grid)
        self._colorbar_label = colorbar_label
        self._status_text = status_message
        self._hover_text = ""
        self._image = _ImageCompat(vmin, vmax)
        self._last_export_payload = {
            "x_grid": np.asarray(x_grid),
            "y_grid": np.asarray(y_grid),
            "z_grid": np.asarray(z_grid),
            "cmap": cmap,
            "vmin": vmin,
            "vmax": vmax,
            "line_overlay": line_overlay,
            "overlay_grid": overlay_grid,
            "time_plot_points": time_plot_points or [],
            "colorbar_label": colorbar_label,
            "plot_type": plot_type,
            "colorbar_mode": colorbar_mode,
            "discrete_colors": list(discrete_colors or []),
            "phase_fraction_overlays": phase_fraction_overlays or [],
            "vector_overlay": vector_overlay,
        }
        self._emit_status_changed()
        debug_print(f"HeatmapCanvas extent={self._last_extent}")
        debug_print(f"HeatmapCanvas colorbar_label={colorbar_label}")
        debug_print(f"HeatmapCanvas vector overlay present={vector_overlay is not None}")
        figure = self._build_figure(
            x_grid=x_grid,
            y_grid=y_grid,
            z_grid=z_grid,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            line_overlay=line_overlay,
            overlay_grid=overlay_grid,
            time_plot_points=time_plot_points or [],
            title=title,
            colorbar_label=colorbar_label,
            plot_type=plot_type,
            colorbar_mode=colorbar_mode,
            discrete_colors=discrete_colors,
            phase_fraction_overlays=phase_fraction_overlays or [],
            vector_overlay=vector_overlay,
        )
        html = self._build_html(figure)
        debug_print(f"HeatmapCanvas html size={len(html)}")
        self._web_view.setHtml(html, self._base_url)
        debug_print("HeatmapCanvas Plotly HTML updated")

    def save_png(self, path: str) -> bool:
        """Export the current web view contents to PNG."""
        debug_print("HeatmapCanvas.save_png called")
        debug_print(f"HeatmapCanvas current-view export path={path}")
        pixmap = self._web_view.grab()
        debug_print(f"HeatmapCanvas current-view pixmap null={pixmap.isNull()}")
        saved = pixmap.save(path, "PNG")
        debug_print(f"HeatmapCanvas current-view export saved={saved}")
        debug_print(f"HeatmapCanvas saved {path}")
        return bool(saved)

    def save_high_resolution_png(
        self,
        path: str,
        *,
        payload: dict | None = None,
        logo_path: Path | None = None,
        logo_band_width: int = 0,
        dpi: int | None = None,
    ) -> bool:
        """Export the current heatmap data as a high-pixel PNG without resizing the widget."""
        debug_print("HeatmapCanvas.save_high_resolution_png called")
        source_payload = payload or self._last_export_payload
        debug_print(f"HeatmapCanvas high-resolution external payload={payload is not None}")
        if not source_payload:
            debug_print("HeatmapCanvas high-resolution export missing payload")
            return False
        try:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure
            from matplotlib.colors import ListedColormap
            from matplotlib import image as mpimg
        except ModuleNotFoundError as exc:
            debug_print(f"HeatmapCanvas high-resolution export unavailable missing={exc.name}")
            return False

        payload = self._export_payload_at_good_resolution(source_payload)
        z_grid = self._export_z_grid_for_payload(payload)
        x_grid = np.asarray(payload["x_grid"])
        y_grid = np.asarray(payload["y_grid"])
        rows, cols = z_grid.shape[:2]
        dpi = int(dpi or DEFAULTS.get("export_dpi", 300))
        debug_print(f"HeatmapCanvas export dpi={dpi}")
        layout = self._export_layout_metrics(rows, cols, logo_band_width)
        logo_band_pixels = layout["logo_band_pixels"]
        colorbar_pixels = layout["colorbar_panel_pixels"]
        width_pixels = layout["width_pixels"]
        height_pixels = layout["height_pixels"]
        debug_print(f"HeatmapCanvas export logo path={logo_path}")
        debug_print(f"HeatmapCanvas export logo band widget width={logo_band_width}")
        debug_print(f"HeatmapCanvas export logo band pixels={logo_band_pixels}")
        debug_print(f"HeatmapCanvas export colorbar panel pixels={colorbar_pixels}")
        debug_print(f"HeatmapCanvas export colorbar thickness pixels={layout['colorbar_thickness_pixels']}")
        debug_print(f"HeatmapCanvas export colorbar gap pixels={layout['colorbar_gap_pixels']}")
        debug_print(f"HeatmapCanvas export data pixels={cols}x{rows}")
        debug_print(f"HeatmapCanvas export image pixels={width_pixels}x{height_pixels}")

        fig = Figure(figsize=(width_pixels / dpi, height_pixels / dpi), dpi=dpi)
        fig.patch.set_facecolor("white")
        canvas = FigureCanvasAgg(fig)
        if logo_band_pixels:
            logo_x, logo_y, logo_width, logo_height = layout["logo_rect"]
            debug_print(f"HeatmapCanvas export logo rect={layout['logo_rect']}")
            logo_ax = fig.add_axes([
                logo_x / width_pixels,
                logo_y / height_pixels,
                logo_width / width_pixels,
                logo_height / height_pixels,
            ])
            logo_ax.set_facecolor("white")
            logo_ax.set_axis_off()
            debug_print("HeatmapCanvas export logo axes created")
            if logo_path and logo_path.exists():
                try:
                    logo = mpimg.imread(str(logo_path))
                    logo_ax.imshow(logo)
                    debug_print("HeatmapCanvas export logo loaded")
                    debug_print(f"HeatmapCanvas export logo shape={getattr(logo, 'shape', None)}")
                except Exception as exc:
                    debug_print(f"HeatmapCanvas export logo load failed={exc}")
            else:
                debug_print("HeatmapCanvas export logo file missing")
        ax = fig.add_axes([logo_band_pixels / width_pixels, 0.0, cols / width_pixels, 1.0])
        colorbar_x, colorbar_y, colorbar_width, colorbar_height = layout["colorbar_rect"]
        debug_print(f"HeatmapCanvas export colorbar rect={layout['colorbar_rect']}")
        cax = fig.add_axes([
            colorbar_x / width_pixels,
            colorbar_y / height_pixels,
            colorbar_width / width_pixels,
            colorbar_height / height_pixels,
        ])
        x_values, y_values = Heatmap2DOrientation.plot_axes(x_grid, y_grid, z_grid)
        image = ax.imshow(
            z_grid,
            origin="lower",
            extent=[float(np.nanmin(x_values)), float(np.nanmax(x_values)), float(np.nanmin(y_values)), float(np.nanmax(y_values))],
            cmap=payload["cmap"],
            vmin=payload["vmin"],
            vmax=payload["vmax"],
            aspect="equal",
            interpolation="bilinear",
        )
        overlay_grid = payload.get("overlay_grid")
        if overlay_grid is not None:
            debug_print("HeatmapCanvas export drawing interface overlay")
            overlay_z = np.asarray(overlay_grid["z"])
            overlay_x, overlay_y = Heatmap2DOrientation.plot_axes(
                overlay_grid["x"],
                overlay_grid["y"],
                overlay_z,
            )
            ax.contourf(
                overlay_x,
                overlay_y,
                overlay_z,
                levels=[1.5, 3.5],
                colors=["black"],
                alpha=0.82,
            )
        for overlay in payload.get("phase_fraction_overlays") or []:
            debug_print(f"HeatmapCanvas export drawing phase overlay={overlay.get('label')}")
            lo, hi = overlay["range"]
            phase_z = np.asarray(overlay["z"], dtype=float)
            visible = np.where((phase_z >= lo) & (phase_z <= hi), 1.0, np.nan)
            phase_x, phase_y = Heatmap2DOrientation.plot_axes(overlay["x"], overlay["y"], phase_z)
            ax.imshow(
                visible,
                origin="lower",
                extent=[float(np.nanmin(phase_x)), float(np.nanmax(phase_x)), float(np.nanmin(phase_y)), float(np.nanmax(phase_y))],
                cmap=ListedColormap([overlay["color"]]),
                vmin=0.0,
                vmax=1.0,
                aspect="equal",
                interpolation="nearest",
            )
        line_overlay = payload.get("line_overlay")
        if line_overlay:
            debug_print(f"HeatmapCanvas export drawing line overlay={line_overlay}")
            orientation, value = line_overlay
            if orientation == "horizontal":
                ax.axhline(value, color="#c50623", linewidth=PlotStyle.GUIDE_LINE_WIDTH, linestyle="--")
            else:
                ax.axvline(value, color="#c50623", linewidth=PlotStyle.GUIDE_LINE_WIDTH, linestyle="--")
        for point in payload.get("time_plot_points") or []:
            debug_print(f"HeatmapCanvas export drawing time point={point}")
            ax.scatter(
                [float(point["x"])],
                [float(point["y"])],
                c="#c50623",
                s=90,
                marker="x",
                linewidths=2.5,
            )
            ax.text(
                float(point["x"]),
                float(point["y"]),
                str(point["label"]),
                color="#06162d",
                fontsize=13,
                ha="center",
                va="bottom",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.92, pad=2),
            )
        ax.set_axis_off()
        colorbar = fig.colorbar(image, cax=cax)
        tick_font_size = self._export_font_points(PlotStyle.COLORBAR_TICK_FONT_SIZE, dpi, layout["pixel_scale"])
        title_font_size = self._export_font_points(PlotStyle.COLORBAR_TITLE_SIZE, dpi, layout["pixel_scale"])
        label_pad = self._export_font_points(12, dpi, layout["pixel_scale"])
        tick_pad = self._export_font_points(4, dpi, layout["pixel_scale"])
        debug_print(f"HeatmapCanvas export colorbar tick font pt={tick_font_size}")
        debug_print(f"HeatmapCanvas export colorbar title font pt={title_font_size}")
        debug_print(f"HeatmapCanvas export colorbar label pad pt={label_pad}")
        colorbar.ax.tick_params(labelsize=tick_font_size, pad=tick_pad)
        if payload.get("colorbar_label"):
            colorbar.set_label(payload["colorbar_label"], fontsize=title_font_size, labelpad=label_pad)
        canvas.draw()
        fig.savefig(path, dpi=dpi, facecolor="white")
        debug_print(f"HeatmapCanvas high-resolution export saved={path}")
        return True

    @staticmethod
    def _export_layout_metrics(rows: int, cols: int, logo_band_width: int) -> dict:
        """Return pixel-perfect PNG layout metrics scaled from the visible heatmap row."""
        debug_print("HeatmapCanvas._export_layout_metrics called")
        pixel_scale = max(float(rows) / float(_CANVAS_HEIGHT), 1.0)
        debug_print(f"HeatmapCanvas export layout pixel_scale={pixel_scale}")
        logo_band_pixels = 0
        logo_rect = (0, 0, 0, 0)
        if logo_band_width > 0:
            logo_band_pixels = max(1, int(round(float(logo_band_width) * pixel_scale)))
            debug_print(f"HeatmapCanvas export layout logo band={logo_band_pixels}")
            logo_width = max(1, int(round(52.0 * pixel_scale)))
            logo_width = min(logo_width, logo_band_pixels)
            logo_height = logo_width
            logo_x = max(0, int(round((logo_band_pixels - logo_width) / 2.0)))
            logo_y = max(0, int(round(12.0 * pixel_scale)))
            logo_rect = (logo_x, logo_y, logo_width, logo_height)
            debug_print(f"HeatmapCanvas export layout logo_rect={logo_rect}")
        colorbar_gap_pixels = max(1, int(round(_EXPORT_COLORBAR_GAP_VIEW_PX * pixel_scale)))
        colorbar_thickness_pixels = max(1, int(round(18.0 * pixel_scale)))
        colorbar_right_text_pixels = max(1, int(round(170.0 * pixel_scale)))
        colorbar_panel_pixels = max(
            int(round(float(_COLORBAR_WIDTH) * pixel_scale)),
            colorbar_gap_pixels + colorbar_thickness_pixels + colorbar_right_text_pixels,
        )
        width_pixels = max(1, logo_band_pixels + int(cols) + colorbar_panel_pixels)
        height_pixels = max(1, int(rows))
        colorbar_x = logo_band_pixels + int(cols) + colorbar_gap_pixels
        colorbar_y = int(round(float(rows) * 0.15))
        colorbar_height = max(1, int(round(float(rows) * 0.7)))
        colorbar_rect = (colorbar_x, colorbar_y, colorbar_thickness_pixels, colorbar_height)
        debug_print(f"HeatmapCanvas export layout colorbar_panel={colorbar_panel_pixels}")
        debug_print(f"HeatmapCanvas export layout colorbar_rect={colorbar_rect}")
        debug_print(f"HeatmapCanvas export layout image={width_pixels}x{height_pixels}")
        return {
            "pixel_scale": pixel_scale,
            "logo_band_pixels": logo_band_pixels,
            "logo_rect": logo_rect,
            "colorbar_gap_pixels": colorbar_gap_pixels,
            "colorbar_thickness_pixels": colorbar_thickness_pixels,
            "colorbar_panel_pixels": colorbar_panel_pixels,
            "colorbar_rect": colorbar_rect,
            "width_pixels": width_pixels,
            "height_pixels": height_pixels,
        }

    @staticmethod
    def _export_font_points(view_font_pixels: int, dpi: int, pixel_scale: float) -> float:
        """Convert Plotly pixel font sizes to Matplotlib points at export DPI."""
        debug_print("HeatmapCanvas._export_font_points called")
        font_pixels = float(view_font_pixels) * float(pixel_scale)
        font_points = font_pixels * 72.0 / float(dpi)
        debug_print(f"HeatmapCanvas export font pixels={font_pixels}")
        debug_print(f"HeatmapCanvas export font points={font_points}")
        return font_points

    def _export_z_grid_for_payload(self, payload: dict):
        """Return the display z-grid used by PNG export."""
        debug_print("HeatmapCanvas._export_z_grid_for_payload called")
        z_grid = np.asarray(payload["z_grid"], dtype=float)
        plot_type = payload.get("plot_type", "heatmap")
        debug_print(f"HeatmapCanvas export plot_type={plot_type}")
        if plot_type != "threshold":
            debug_print("HeatmapCanvas export threshold mask skipped")
            return z_grid
        vmin = float(payload["vmin"])
        vmax = float(payload["vmax"])
        debug_print(f"HeatmapCanvas export threshold range={vmin}..{vmax}")
        visible_mask = (z_grid >= vmin) & (z_grid <= vmax)
        visible_count = int(np.count_nonzero(visible_mask))
        debug_print(f"HeatmapCanvas export threshold visible count={visible_count}")
        masked = np.where(visible_mask, z_grid, np.nan)
        debug_print("HeatmapCanvas export threshold mask applied")
        return masked

    def _export_payload_at_good_resolution(self, payload: dict) -> dict:
        """Return a copy of payload resampled to the configured PNG export resolution."""
        debug_print("HeatmapCanvas._export_payload_at_good_resolution called")
        target = int(DEFAULTS.get("export_resolution", 1000))
        debug_print(f"HeatmapCanvas export target resolution={target}")
        z_grid = np.asarray(payload["z_grid"], dtype=float)
        x_grid = np.asarray(payload["x_grid"], dtype=float)
        y_grid = np.asarray(payload["y_grid"], dtype=float)
        rows, cols = z_grid.shape[:2]
        debug_print(f"HeatmapCanvas export source grid={cols}x{rows}")
        if max(rows, cols) >= target:
            debug_print("HeatmapCanvas export resample skipped")
            return payload
        scale = target / max(rows, cols)
        target_rows = max(1, int(round(rows * scale)))
        target_cols = max(1, int(round(cols * scale)))
        debug_print(f"HeatmapCanvas export resample target={target_cols}x{target_rows}")
        export_payload = dict(payload)
        export_payload["z_grid"] = self._resample_array(z_grid, target_rows, target_cols)
        export_payload["x_grid"] = self._resample_array(x_grid, target_rows, target_cols)
        export_payload["y_grid"] = self._resample_array(y_grid, target_rows, target_cols)
        overlay_grid = payload.get("overlay_grid")
        if overlay_grid is not None:
            debug_print("HeatmapCanvas export resampling overlay")
            export_payload["overlay_grid"] = {
                "x": self._resample_array(np.asarray(overlay_grid["x"], dtype=float), target_rows, target_cols),
                "y": self._resample_array(np.asarray(overlay_grid["y"], dtype=float), target_rows, target_cols),
                "z": self._resample_array(np.asarray(overlay_grid["z"], dtype=float), target_rows, target_cols),
            }
        debug_print("HeatmapCanvas export payload resampled")
        return export_payload

    def _resample_array(self, array, target_rows: int, target_cols: int):
        """Linearly resample a 2D array to target rows/columns."""
        debug_print("HeatmapCanvas._resample_array called")
        source = np.asarray(array, dtype=float)
        rows, cols = source.shape[:2]
        debug_print(f"HeatmapCanvas resample array from={cols}x{rows} to={target_cols}x{target_rows}")
        if rows == target_rows and cols == target_cols:
            debug_print("HeatmapCanvas resample array skipped")
            return source
        source_cols = np.arange(cols)
        source_rows = np.arange(rows)
        target_col_positions = np.linspace(0, cols - 1, target_cols)
        target_row_positions = np.linspace(0, rows - 1, target_rows)
        resampled_cols = np.empty((rows, target_cols), dtype=float)
        for row_index in range(rows):
            resampled_cols[row_index] = np.interp(
                target_col_positions,
                source_cols,
                source[row_index],
            )
        resampled = np.empty((target_rows, target_cols), dtype=float)
        for col_index in range(target_cols):
            resampled[:, col_index] = np.interp(
                target_row_positions,
                source_rows,
                resampled_cols[:, col_index],
            )
        debug_print("HeatmapCanvas resample array complete")
        return resampled

    def render_status(self, message: str) -> None:
        debug_print("HeatmapCanvas.render_status called")
        debug_print(f"HeatmapCanvas message={message}")
        self._status_text = message
        self._emit_status_changed()
        debug_print("HeatmapCanvas status_changed emitted")

    def status_text(self) -> str:
        debug_print("HeatmapCanvas.status_text called")
        return self._compose_status_text()

    def handle_plotly_event(self, event_type: str, payload_json: str) -> None:
        """Handle click and hover events coming from the embedded Plotly view."""
        debug_print("HeatmapCanvas.handle_plotly_event called")
        payload = json.loads(payload_json or "{}")
        debug_print(f"HeatmapCanvas payload keys={list(payload.keys())}")
        if event_type == "click":
            x_value = payload.get("x")
            y_value = payload.get("y")
            if x_value is None or y_value is None:
                debug_print("HeatmapCanvas click payload missing coordinates")
                return
            self.heatmap_clicked.emit(float(x_value), float(y_value))
            debug_print(f"HeatmapCanvas emitted click x={x_value} y={y_value}")
            return
        if event_type == "hover":
            hover_text = self._build_hover_text(
                payload.get("x"),
                payload.get("y"),
                payload.get("z"),
            )
            if hover_text == self._hover_text:
                debug_print("HeatmapCanvas hover unchanged")
                return
            self._hover_text = hover_text
            self._emit_status_changed()
            debug_print(f"HeatmapCanvas hover updated to {hover_text}")
            return
        if event_type == "unhover":
            if not self._hover_text:
                debug_print("HeatmapCanvas hover already empty")
                return
            self._hover_text = ""
            self._emit_status_changed()
            debug_print("HeatmapCanvas hover cleared")
            return
        debug_print(f"HeatmapCanvas ignored event_type={event_type}")

    def _build_figure(
        self,
        *,
        x_grid,
        y_grid,
        z_grid,
        cmap,
        vmin: float,
        vmax: float,
        line_overlay,
        overlay_grid,
        time_plot_points=None,
        title: str = "",
        colorbar_label: str = "",
        plot_type: str = "heatmap",
        colorbar_mode: str = "bar",
        discrete_colors=None,
        phase_fraction_overlays=None,
        vector_overlay=None,
    ) -> go.Figure:
        debug_print("HeatmapCanvas._build_figure called")
        debug_print(f"HeatmapCanvas build colorbar_mode={colorbar_mode}")
        debug_print(f"HeatmapCanvas build discrete_colors={discrete_colors}")
        rows, cols = np.asarray(z_grid).shape[:2]
        x_values, y_values = Heatmap2DOrientation.plot_axes(x_grid, y_grid, z_grid)
        colorscale = cmap_to_plotly_scale(cmap)
        colorbar_x = 1.0 + _COLORBAR_GAP
        ticks = self._colorbar_ticks(vmin, vmax)
        tick_text = format_colorbar_ticks(ticks)
        debug_print(f"HeatmapCanvas colorbar tick text={tick_text}")
        colorbar_cfg = dict(
            x             = colorbar_x,
            xanchor       = "left",
            y             = 0.35,
            yanchor       = "middle",
            len           = 0.7,
            lenmode       = "fraction",
            thickness     = 18,
            thicknessmode = "pixels",
            outlinewidth  = 0,
            title         = dict(text=colorbar_label, side="right", font=PlotStyle.colorbar_title_font()),
            tickfont      = PlotStyle.colorbar_tick_font(),
            tickmode      = "array",
            tickvals      = ticks,
            ticktext      = tick_text,
        )
        from viewer.plot_types import PLOT_TYPE_MAP
        figure = go.Figure()
        renderer = PLOT_TYPE_MAP.get(plot_type, PLOT_TYPE_MAP["heatmap"])
        hovertemplate = "x=%{x:.4f}<br>y=%{y:.4f}<br>value=%{z:.4f}<extra></extra>"
        debug_print(f"HeatmapCanvas live Plotly heatmap data pixels={cols}x{rows}")
        debug_print(f"HeatmapCanvas live Plotly fixed widget pixels={self.width()}x{_CANVAS_HEIGHT}")
        phase_fraction_overlays = phase_fraction_overlays or []
        debug_print(f"HeatmapCanvas phase fraction overlay count={len(phase_fraction_overlays)}")
        if phase_fraction_overlays:
            self._add_phase_fraction_traces(figure, phase_fraction_overlays)
        else:
            for trace in renderer.build_traces(
                x_values, y_values, z_grid, vmin, vmax, colorscale, colorbar_cfg, hovertemplate
            ):
                figure.add_trace(trace)
        if colorbar_mode == "boxes" and discrete_colors:
            debug_print("HeatmapCanvas applying discrete numbered colorbar")
            for trace in figure.data:
                if hasattr(trace, "showscale"):
                    trace.showscale = False
                    debug_print(f"HeatmapCanvas disabled trace scale type={trace.type}")
            add_discrete_legend_to_figure(figure, list(discrete_colors), colorbar_label)
            debug_print("HeatmapCanvas discrete numbered colorbar applied")
        else:
            debug_print("HeatmapCanvas using full colorbar")
        if overlay_grid is not None:
            debug_print("HeatmapCanvas adding smooth contour overlay")
            overlay_x, overlay_y = Heatmap2DOrientation.plot_axes(
                overlay_grid["x"],
                overlay_grid["y"],
                overlay_grid["z"],
            )
            figure.add_trace(
                go.Contour(
                    x=overlay_x,
                    y=overlay_y,
                    z=np.asarray(overlay_grid["z"]),
                    showscale=False,
                    contours=dict(
                        coloring="fill",
                        start=1.5,
                        end=3.5,
                        size=2.0,
                        showlines=False,
                    ),
                    colorscale=[
                        [0.0, "rgba(0, 0, 0, 0.0)"],
                        [0.499, "rgba(0, 0, 0, 0.0)"],
                        [0.5, "rgba(0, 0, 0, 0.82)"],
                        [1.0, "rgba(0, 0, 0, 0.82)"],
                    ],
                    line=dict(width=0, color="rgba(0, 0, 0, 0)"),
                    hoverinfo="skip",
                    opacity=1.0,
                )
            )
        if vector_overlay is not None:
            debug_print("HeatmapCanvas adding vector arrow overlay")
            arrow_traces = self._build_vector_arrow_traces(
                vector_overlay,
                arrow_length=vector_overlay.get("arrow_length"),
            )
            debug_print(f"HeatmapCanvas vector arrow trace count={len(arrow_traces)}")
            for trace in arrow_traces:
                figure.add_trace(trace)
        points = time_plot_points or []
        if points:
            debug_print("HeatmapCanvas adding time plot point markers")
            debug_print(f"HeatmapCanvas time plot marker count={len(points)}")
            for point in points:
                debug_print(f"HeatmapCanvas marker point={point}")
            debug_print("HeatmapCanvas using borderless label boxes without white underlay")
            for point in points:
                debug_print(f"HeatmapCanvas adding label box point={point}")
                figure.add_annotation(
                    x=float(point["x"]),
                    y=float(point["y"]),
                    text=f"<b>{point['label']}</b>",
                    showarrow=False,
                    xanchor="center",
                    yanchor="bottom",
                    yshift=10,
                    name="Plot Over Time Label Box",
                    font=dict(color="#06162d", size=13, family="Arial"),
                    bgcolor="rgba(255, 255, 255, 0.92)",
                    bordercolor="rgba(0, 0, 0, 0)",
                    borderwidth=0,
                    borderpad=2,
                    opacity=1.0,
                    captureevents=False,
                )
            figure.add_trace(
                go.Scatter(
                    x=[float(point["x"]) for point in points],
                    y=[float(point["y"]) for point in points],
                    text=[str(point["label"]) for point in points],
                    mode="markers+text",
                    name="Plot Over Time Points",
                    marker=dict(
                        color="#c50623",
                        size=11,
                        symbol="x",
                        line=dict(color="#ffffff", width=2),
                    ),
                    textposition="top center",
                    textfont=dict(color="#06162d", size=13),
                    hovertemplate="%{text}<br>x=%{x:.4f}<br>y=%{y:.4f}<extra></extra>",
                    showlegend=False,
                )
            )
        if line_overlay:
            debug_print("HeatmapCanvas adding line overlay")
            orientation, value = line_overlay
            if orientation == "horizontal":
                figure.add_hline(
                    y=value,
                    line_width=PlotStyle.GUIDE_LINE_WIDTH,
                    line_dash="dash",
                    line_color="#c50623",
                )
            else:
                figure.add_vline(
                    x=value,
                    line_width=PlotStyle.GUIDE_LINE_WIDTH,
                    line_dash="dash",
                    line_color="#c50623",
                )
        if phase_fraction_overlays:
            debug_print("HeatmapCanvas enabling phase fraction legend")
            figure.update_layout(
                showlegend=True,
                legend=dict(
                    x=1.02,
                    xanchor="left",
                    y=1.0,
                    yanchor="top",
                    bgcolor="rgba(255, 255, 255, 0.88)",
                    bordercolor="rgba(16, 42, 82, 0.18)",
                    borderwidth=1,
                    font=PlotStyle.layout_font(),
                ),
            )
        figure.update_layout(
            title=dict(text=title),
            width=self.width(),
            height=_CANVAS_HEIGHT,
            margin=dict(l=0, r=self._colorbar_width, t=60, b=15),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            dragmode="pan",
        )
        figure.update_xaxes(
            visible=False,
            range=[self._last_extent[0], self._last_extent[1]],
            constrain="domain",
            fixedrange=False,
            automargin=False,
        )
        figure.update_yaxes(
            visible=False,
            range=[self._last_extent[2], self._last_extent[3]],
            scaleanchor="x",
            scaleratio=1.0,
            constrain="domain",
            fixedrange=False,
            automargin=False,
        )
        debug_print("HeatmapCanvas figure ready")
        return figure

    @staticmethod
    def _build_vector_arrow_traces(vector_overlay: dict, *, arrow_length: float | None = None, color_bins: int = 8) -> list[go.Scatter]:
        """Build fixed-length, magnitude-colored arrow traces for a vector overlay."""
        debug_print("HeatmapCanvas._build_vector_arrow_traces called")
        x_values = np.asarray(vector_overlay["x"], dtype=float).ravel()
        y_values = np.asarray(vector_overlay["y"], dtype=float).ravel()
        u_values = np.asarray(vector_overlay["u"], dtype=float).ravel()
        v_values = np.asarray(vector_overlay["v"], dtype=float).ravel()
        magnitudes = np.asarray(vector_overlay["magnitude"], dtype=float).ravel()
        label = str(vector_overlay.get("label", "Vector"))
        finite = (
            np.isfinite(x_values)
            & np.isfinite(y_values)
            & np.isfinite(u_values)
            & np.isfinite(v_values)
            & np.isfinite(magnitudes)
        )
        x_values = x_values[finite]
        y_values = y_values[finite]
        u_values = u_values[finite]
        v_values = v_values[finite]
        magnitudes = magnitudes[finite]
        debug_print(f"HeatmapCanvas vector finite arrows={len(x_values)}")
        if len(x_values) == 0:
            debug_print("HeatmapCanvas vector arrows empty")
            return []
        direction_lengths = np.sqrt((u_values * u_values) + (v_values * v_values))
        nonzero = direction_lengths > 1e-12
        x_values = x_values[nonzero]
        y_values = y_values[nonzero]
        u_values = u_values[nonzero]
        v_values = v_values[nonzero]
        magnitudes = magnitudes[nonzero]
        direction_lengths = direction_lengths[nonzero]
        debug_print(f"HeatmapCanvas vector nonzero arrows={len(x_values)}")
        if len(x_values) == 0:
            debug_print("HeatmapCanvas vector arrows all zero")
            return []
        if arrow_length is None:
            x_span = float(np.nanmax(x_values) - np.nanmin(x_values))
            y_span = float(np.nanmax(y_values) - np.nanmin(y_values))
            arrow_length = max(x_span, y_span, 1.0) * 0.035
        arrow_length = float(arrow_length)
        debug_print(f"HeatmapCanvas fixed arrow length={arrow_length}")
        ux = u_values / direction_lengths
        vy = v_values / direction_lengths
        mag_min = float(np.nanmin(magnitudes))
        mag_max = float(np.nanmax(magnitudes))
        debug_print(f"HeatmapCanvas vector magnitude min={mag_min}")
        debug_print(f"HeatmapCanvas vector magnitude max={mag_max}")
        span = max(mag_max - mag_min, 1e-12)
        if mag_max > mag_min:
            magnitude_fraction = (magnitudes - mag_min) / span
            length_scale = 0.50 + (magnitude_fraction * 1.00)
        else:
            length_scale = np.ones_like(magnitudes)
        scaled_lengths = arrow_length * length_scale
        debug_print(f"HeatmapCanvas vector length scale min={float(np.nanmin(length_scale))}")
        debug_print(f"HeatmapCanvas vector length scale max={float(np.nanmax(length_scale))}")
        debug_print(f"HeatmapCanvas vector arrow length min={float(np.nanmin(scaled_lengths))}")
        debug_print(f"HeatmapCanvas vector arrow length max={float(np.nanmax(scaled_lengths))}")
        end_x = x_values + (ux * scaled_lengths)
        end_y = y_values + (vy * scaled_lengths)
        bin_count = max(1, int(color_bins))
        bins = np.clip(((magnitudes - mag_min) / span * bin_count).astype(int), 0, bin_count - 1)
        colors = HeatmapCanvas._vector_bin_colors(bin_count)
        traces: list[go.Scatter] = []
        for bin_index, color in enumerate(colors):
            mask = bins == bin_index
            if not np.any(mask):
                continue
            shaft_x: list[float | None] = []
            shaft_y: list[float | None] = []
            head_x: list[float | None] = []
            head_y: list[float | None] = []
            for start_x, start_y, stop_x, stop_y, dir_x, dir_y, current_length in zip(
                x_values[mask],
                y_values[mask],
                end_x[mask],
                end_y[mask],
                ux[mask],
                vy[mask],
                scaled_lengths[mask],
            ):
                shaft_x.extend([float(start_x), float(stop_x), None])
                shaft_y.extend([float(start_y), float(stop_y), None])
                head_length = current_length * 0.34
                head_width = current_length * 0.20
                normal_x = -dir_y
                normal_y = dir_x
                base_x = stop_x - (dir_x * head_length)
                base_y = stop_y - (dir_y * head_length)
                left_x = base_x + (normal_x * head_width)
                left_y = base_y + (normal_y * head_width)
                right_x = base_x - (normal_x * head_width)
                right_y = base_y - (normal_y * head_width)
                head_x.extend([float(left_x), float(stop_x), float(right_x), None])
                head_y.extend([float(left_y), float(stop_y), float(right_y), None])
            traces.append(
                go.Scatter(
                    x=shaft_x,
                    y=shaft_y,
                    mode="lines",
                    line=dict(color=color, width=1.6),
                    hoverinfo="skip",
                    showlegend=False,
                    name=f"{label} arrows",
                )
            )
            traces.append(
                go.Scatter(
                    x=head_x,
                    y=head_y,
                    mode="lines",
                    line=dict(color=color, width=1.4),
                    hoverinfo="skip",
                    showlegend=False,
                    name=f"{label} arrow heads",
                )
            )
        debug_print(f"HeatmapCanvas vector traces built={len(traces)}")
        return traces

    @staticmethod
    def _vector_bin_colors(color_bins: int) -> list[str]:
        debug_print("HeatmapCanvas._vector_bin_colors called")
        from plotly.colors import sample_colorscale

        if color_bins <= 1:
            samples = [0.5]
        else:
            samples = np.linspace(0.12, 0.95, color_bins)
        colors = sample_colorscale("Viridis", [float(sample) for sample in samples])
        debug_print(f"HeatmapCanvas vector color bins={len(colors)}")
        return colors

    def _add_phase_fraction_traces(self, figure: go.Figure, overlays: list[dict]) -> None:
        """Add one thresholded, solid-color heatmap trace per selected phase fraction."""
        debug_print("HeatmapCanvas._add_phase_fraction_traces called")
        for overlay in overlays:
            label = str(overlay["label"])
            lo, hi = overlay["range"]
            color = overlay["color"]
            x_values, y_values = Heatmap2DOrientation.plot_axes(
                overlay["x"],
                overlay["y"],
                overlay["z"],
            )
            z_values = np.asarray(overlay["z"], dtype=float)
            visible_mask = (z_values >= lo) & (z_values <= hi)
            visible_count = int(np.count_nonzero(visible_mask))
            debug_print(f"HeatmapCanvas phase trace label={label}")
            debug_print(f"HeatmapCanvas phase trace range={lo}..{hi}")
            debug_print(f"HeatmapCanvas phase trace color={color}")
            debug_print(f"HeatmapCanvas phase trace visible count={visible_count}")
            masked = np.where(visible_mask, z_values, np.nan)
            figure.add_trace(
                go.Heatmap(
                    x=x_values,
                    y=y_values,
                    z=masked,
                    zmin=lo,
                    zmax=hi if hi > lo else lo + 1e-12,
                    colorscale=[[0.0, color], [1.0, color]],
                    showscale=False,
                    showlegend=True,
                    name=label,
                    legendgroup=label,
                    hovertemplate=(
                        f"{label}<br>"
                        "x=%{x:.4f}<br>"
                        "y=%{y:.4f}<br>"
                        "value=%{z:.4f}<extra></extra>"
                    ),
                )
            )
        debug_print("HeatmapCanvas phase fraction traces added")

    def _build_html(self, figure: go.Figure) -> str:
        debug_print("HeatmapCanvas._build_html called")
        figure_json = figure.to_json()
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <style>
        html, body, #heatmapDiv {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: white;
        }}
        .modebar {{
            right: 0 !important;
        }}
        .nsewdrag, .ewdrag, .nsdrag, .drag {{
            cursor: default !important;
        }}
    </style>
    <script src="plotly.min.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
    <div id="heatmapDiv"></div>
    <script>
        const figure = {figure_json};
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            const bridge = channel.objects.bridge;
            const div = document.getElementById("heatmapDiv");
            const config = {{
                displaylogo: false,
                responsive: false,
                scrollZoom: true,
                doubleClick: "reset+autosize"
            }};
            Plotly.newPlot(div, figure.data, figure.layout, config).then(function(gd) {{
                gd.on("plotly_click", function(eventData) {{
                    if (!eventData.points || !eventData.points.length) {{
                        return;
                    }}
                    const point = eventData.points[0];
                    bridge.sendEvent("click", JSON.stringify({{
                        x: point.x,
                        y: point.y,
                        z: point.z
                    }}));
                }});
                gd.on("plotly_hover", function(eventData) {{
                    if (!eventData.points || !eventData.points.length) {{
                        return;
                    }}
                    const point = eventData.points[0];
                    bridge.sendEvent("hover", JSON.stringify({{
                        x: point.x,
                        y: point.y,
                        z: point.z
                    }}));
                }});
                gd.on("plotly_unhover", function() {{
                    bridge.sendEvent("unhover", "{{}}");
                }});
            }});
        }});
    </script>
</body>
</html>
"""

    def _handle_load_started(self) -> None:
        debug_print("HeatmapCanvas._handle_load_started called")

    def _handle_load_finished(self, ok: bool) -> None:
        debug_print("HeatmapCanvas._handle_load_finished called")
        debug_print(f"HeatmapCanvas load ok={ok}")

    def _build_hover_text(self, x_value, y_value, z_value) -> str:
        debug_print("HeatmapCanvas._build_hover_text called")
        if x_value is None or y_value is None:
            debug_print("HeatmapCanvas hover missing coordinates")
            return ""
        if z_value is None:
            lookup_value = self._lookup_value(float(x_value), float(y_value))
            if lookup_value is None:
                return f"hover x={float(x_value):.4f} | y={float(y_value):.4f}"
            z_value = lookup_value
        formatted_value = self._fmt_tick(float(z_value))
        debug_print(f"HeatmapCanvas hover raw value={float(z_value)}")
        debug_print(f"HeatmapCanvas hover formatted value={formatted_value}")
        hover_text = f"hover x={float(x_value):.4f} | y={float(y_value):.4f} | value={formatted_value}"
        debug_print(f"HeatmapCanvas hover_text={hover_text}")
        return hover_text

    def _lookup_value(self, x_value: float, y_value: float):
        debug_print("HeatmapCanvas._lookup_value called")
        if self._last_z_grid is None or self._last_extent is None:
            debug_print("HeatmapCanvas no grid for lookup")
            return None
        x_min, x_max, y_min, y_max = self._last_extent
        if x_max == x_min or y_max == y_min:
            debug_print("HeatmapCanvas degenerate extent")
            return None
        rows, cols = self._last_z_grid.shape[:2]
        x_ratio = (x_value - x_min) / (x_max - x_min)
        y_ratio = (y_value - y_min) / (y_max - y_min)
        x_index = int(np.clip(round(x_ratio * (cols - 1)), 0, cols - 1))
        y_index = int(np.clip(round(y_ratio * (rows - 1)), 0, rows - 1))
        value = float(self._last_z_grid[y_index, x_index])
        debug_print(f"HeatmapCanvas lookup row={y_index} col={x_index}")
        debug_print(f"HeatmapCanvas lookup value={value}")
        return value

    def _compose_status_text(self) -> str:
        debug_print("HeatmapCanvas._compose_status_text called")
        if self._hover_text:
            combined = f"{self._status_text} | {self._hover_text}"
            debug_print(f"HeatmapCanvas combined status={combined}")
            return combined
        debug_print(f"HeatmapCanvas base status only={self._status_text}")
        return self._status_text

    def _emit_status_changed(self) -> None:
        debug_print("HeatmapCanvas._emit_status_changed called")
        combined = self._compose_status_text()
        self.status_changed.emit(combined)
        debug_print("HeatmapCanvas emitted combined status")
