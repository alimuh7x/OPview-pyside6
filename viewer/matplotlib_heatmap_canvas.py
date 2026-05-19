"""Matplotlib imshow drop-in replacement for HeatmapCanvas (Plotly)."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

_CANVAS_HEIGHT  = 420
_COLORBAR_WIDTH = 90
_DPI            = 100


class MatplotlibHeatmapCanvas(QWidget):
    """Matplotlib imshow canvas with the same public interface as HeatmapCanvas."""

    heatmap_clicked  = Signal(float, float)
    geometry_changed = Signal()
    status_changed   = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plot_width     = 360
        self._colorbar_width = _COLORBAR_WIDTH
        self._dpi            = _DPI

        total_w = self._plot_width + self._colorbar_width
        self._fig = Figure(
            figsize=(total_w / _DPI, _CANVAS_HEIGHT / _DPI),
            dpi=_DPI,
            facecolor="white",
        )
        self._ax_im: object = None
        self._ax_cb: object = None

        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

        self.setFixedSize(total_w, _CANVAS_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Hover/click state
        self._last_x: np.ndarray | None = None
        self._last_y: np.ndarray | None = None
        self._last_z: np.ndarray | None = None
        self._base_status  = ""
        self._hover_text   = ""

        self._canvas.mpl_connect("button_press_event",  self._on_click)
        self._canvas.mpl_connect("motion_notify_event", self._on_hover)
        self._canvas.mpl_connect("axes_leave_event",    self._on_leave)

        # Cached render state — reuse imshow instead of full rebuild
        self._im:          object = None
        self._cbar_obj:    object = None
        self._hline_obj:   object = None
        self._vline_obj:   object = None
        self._last_cmap    = None
        self._last_vmin    = None
        self._last_vmax    = None
        self._last_extent  = None

    # ------------------------------------------------------------------
    # Size / geometry
    # ------------------------------------------------------------------

    def canvas_height(self) -> int:
        return _CANVAS_HEIGHT

    def canvas_width(self) -> int:
        return self.width()

    def set_canvas_width(self, width: int) -> None:
        total = max(100, width) + self._colorbar_width
        self.setFixedWidth(total)
        self._fig.set_size_inches(total / self._dpi, _CANVAS_HEIGHT / self._dpi)
        self.geometry_changed.emit()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def render_status(self, message: str) -> None:
        self._base_status = message
        self.status_changed.emit(self._build_status())

    def status_text(self) -> str:
        return self._build_status()

    def _build_status(self) -> str:
        parts = [p for p in (self._base_status, self._hover_text) if p]
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Main render
    # ------------------------------------------------------------------

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
        title: str = "",
        colorbar_label: str = "",
        plot_type: str = "heatmap",
    ) -> None:
        self._last_x = x_grid
        self._last_y = y_grid
        self._last_z = z_grid
        self._base_status = status_message

        x_min = float(np.nanmin(x_grid))
        x_max = float(np.nanmax(x_grid))
        y_min = float(np.nanmin(y_grid))
        y_max = float(np.nanmax(y_grid))
        extent = [x_min, x_max, y_min, y_max]

        needs_rebuild = (
            self._im is None
            or cmap is not self._last_cmap
            or extent != self._last_extent
        )

        if needs_rebuild:
            self._fig.clear()
            total_w = self.width() or (self._plot_width + self._colorbar_width)
            cb_frac = (self._colorbar_width - 10) / total_w
            plot_w  = 1.0 - cb_frac - 0.04 - 0.03
            self._ax_im = self._fig.add_axes([0.01, 0.04, plot_w, 0.88])
            self._ax_cb = self._fig.add_axes([0.01 + plot_w + 0.03, 0.08, cb_frac, 0.80])
            self._im = self._ax_im.imshow(
                z_grid, origin="lower", aspect="auto",
                cmap=cmap, vmin=vmin, vmax=vmax,
                extent=extent, interpolation="nearest",
            )
            self._ax_im.set_axis_off()
            self._cbar_obj = self._fig.colorbar(self._im, cax=self._ax_cb)
            self._cbar_obj.ax.tick_params(labelsize=8)
            self._last_cmap   = cmap
            self._last_extent = extent
            self._hline_obj   = None
            self._vline_obj   = None
        else:
            # Fast path: just swap data
            self._im.set_data(z_grid)

        # Color range
        if vmin != self._last_vmin or vmax != self._last_vmax:
            self._im.set_clim(vmin, vmax)
            ticks = np.linspace(vmin, vmax, 5)
            self._cbar_obj.set_ticks(ticks)
            if colorbar_label:
                self._cbar_obj.set_label(colorbar_label, fontsize=9)
            self._last_vmin = vmin
            self._last_vmax = vmax

        # Title
        if title:
            self._ax_im.set_title(title, fontsize=10, pad=4, color="#333333")

        # Line overlay — update in-place
        if line_overlay is not None:
            orientation, value = line_overlay
            if orientation == "horizontal":
                if self._hline_obj is None:
                    self._hline_obj, = self._ax_im.plot(
                        [], [], color="#c50623", linewidth=2, linestyle="--"
                    )
                    self._hline_obj = self._ax_im.axhline(
                        value, color="#c50623", linewidth=2, linestyle="--"
                    )
                else:
                    self._hline_obj.set_ydata([value, value])
            else:
                if self._vline_obj is None:
                    self._vline_obj = self._ax_im.axvline(
                        value, color="#c50623", linewidth=2, linestyle="--"
                    )
                else:
                    self._vline_obj.set_xdata([value, value])

        # Interfaces overlay (only on rebuild to avoid accumulation)
        if needs_rebuild and overlay_grid is not None:
            try:
                self._ax_im.contour(
                    overlay_grid["x"], overlay_grid["y"], overlay_grid["z"],
                    levels=[1.5, 3.5], colors="black", linewidths=1.0,
                )
            except Exception:
                pass

        self._canvas.draw_idle()
        self.status_changed.emit(self._build_status())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def save_png(self, path: str) -> None:
        self._fig.savefig(path, dpi=150, bbox_inches="tight")

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def _on_click(self, event) -> None:
        if event.inaxes is self._ax_im and event.xdata is not None:
            self.heatmap_clicked.emit(float(event.xdata), float(event.ydata))

    def _on_hover(self, event) -> None:
        if (
            event.inaxes is self._ax_im
            and event.xdata is not None
            and self._last_z is not None
        ):
            z_val = self._nearest_z(event.xdata, event.ydata)
            self._hover_text = (
                f"x={event.xdata:.4g}  y={event.ydata:.4g}  z={z_val:.4g}"
            )
        else:
            self._hover_text = ""
        self.status_changed.emit(self._build_status())

    def _on_leave(self, event) -> None:
        self._hover_text = ""
        self.status_changed.emit(self._build_status())

    def _nearest_z(self, x: float, y: float) -> float:
        try:
            xi = int(np.argmin(np.abs(self._last_x[0, :] - x)))
            yi = int(np.argmin(np.abs(self._last_y[:, 0] - y)))
            return float(self._last_z[yi, xi])
        except Exception:
            return float("nan")
