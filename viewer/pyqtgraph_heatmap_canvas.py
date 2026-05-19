"""PyQtGraph GPU-accelerated heatmap canvas — same interface as MatplotlibHeatmapCanvas."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

pg.setConfigOptions(antialias=False, imageAxisOrder="row-major")

_CANVAS_HEIGHT  = 420
_COLORBAR_WIDTH = 80
_DPI            = 100


def _mpl_cmap_to_pg(cmap, n: int = 256) -> pg.ColorMap:
    """Convert a matplotlib colormap to a pyqtgraph ColorMap."""
    pos    = np.linspace(0.0, 1.0, n)
    colors = (cmap(pos) * 255).astype(np.uint8)
    return pg.ColorMap(pos=pos, color=colors)


class PyQtGraphHeatmapCanvas(QWidget):
    """OpenGL-accelerated heatmap using pyqtgraph ImageItem."""

    heatmap_clicked  = Signal(float, float)
    geometry_changed = Signal()
    status_changed   = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plot_width     = 360
        self._colorbar_width = _COLORBAR_WIDTH

        total_w = self._plot_width + self._colorbar_width
        self.setFixedSize(total_w, _CANVAS_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Graphics layout: [plot | colorbar]
        self._gw   = pg.GraphicsLayoutWidget()
        self._gw.setBackground("w")
        self._plot = self._gw.addPlot(row=0, col=0)
        self._plot.hideAxis("left")
        self._plot.hideAxis("bottom")
        self._plot.setMenuEnabled(False)
        self._plot.setAspectLocked(False)

        self._img = pg.ImageItem()
        self._plot.addItem(self._img)

        # Colorbar (narrow column)
        self._cbar = pg.ColorBarItem(
            interactive=False,
            colorMap=pg.colormap.get("viridis"),
            width=15,
            label="",
        )
        self._cbar.setImageItem(self._img, insert_in=self._plot)
        self._gw.addItem(self._cbar, row=0, col=1)
        self._gw.ci.layout.setColumnFixedWidth(1, _COLORBAR_WIDTH)

        # Overlay items (created once, shown/hidden per frame)
        self._hline = pg.InfiniteLine(
            angle=0,
            pen=pg.mkPen("#c50623", width=2, style=Qt.PenStyle.DashLine),
        )
        self._vline = pg.InfiniteLine(
            angle=90,
            pen=pg.mkPen("#c50623", width=2, style=Qt.PenStyle.DashLine),
        )
        self._plot.addItem(self._hline)
        self._plot.addItem(self._vline)
        self._hline.hide()
        self._vline.hide()

        # Contour item (interfaces overlay) — rebuilt each render
        self._iso: pg.IsocurveItem | None = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._gw)

        # State
        self._last_z:      np.ndarray | None = None
        self._x_min        = 0.0
        self._x_max        = 1.0
        self._y_min        = 0.0
        self._y_max        = 1.0
        self._base_status  = ""
        self._hover_text   = ""

        # Mouse events
        self._plot.scene().sigMouseClicked.connect(self._on_click)
        self._hover_proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved,
            rateLimit=30,
            slot=self._on_hover,
        )

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
        self._last_z = z_grid
        self._x_min  = float(np.nanmin(x_grid))
        self._x_max  = float(np.nanmax(x_grid))
        self._y_min  = float(np.nanmin(y_grid))
        self._y_max  = float(np.nanmax(y_grid))
        self._base_status = status_message

        # Colormap → pyqtgraph
        pg_cmap = _mpl_cmap_to_pg(cmap)
        self._img.setColorMap(pg_cmap)

        # Image data + extent
        self._img.setImage(z_grid, levels=(vmin, vmax), autoLevels=False)
        self._img.setRect(
            self._x_min,
            self._y_min,
            self._x_max - self._x_min,
            self._y_max - self._y_min,
        )

        # Colorbar range
        self._cbar.setLevels((vmin, vmax))
        self._cbar.setColorMap(pg_cmap)

        # Title
        self._plot.setTitle(title, size="10pt", color="#333333")

        # Line overlay
        if line_overlay is not None:
            orientation, value = line_overlay
            if orientation == "horizontal":
                self._hline.setPos(value)
                self._hline.show()
                self._vline.hide()
            else:
                self._vline.setPos(value)
                self._vline.show()
                self._hline.hide()
        else:
            self._hline.hide()
            self._vline.hide()

        # Interfaces overlay (isocurve)
        if self._iso is not None:
            self._plot.removeItem(self._iso)
            self._iso = None
        if overlay_grid is not None:
            try:
                self._iso = pg.IsocurveItem(
                    data=overlay_grid["z"],
                    level=2.5,
                    pen=pg.mkPen("k", width=1),
                )
                self._iso.setParentItem(self._img)
                self._plot.addItem(self._iso)
            except Exception:
                pass

        self.status_changed.emit(self._build_status())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def save_png(self, path: str) -> None:
        exporter = pg.exporters.ImageExporter(self._plot)
        exporter.export(path)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def _on_click(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.scenePos()
        if self._plot.sceneBoundingRect().contains(pos):
            mouse_point = self._plot.vb.mapSceneToView(pos)
            self.heatmap_clicked.emit(float(mouse_point.x()), float(mouse_point.y()))

    def _on_hover(self, args) -> None:
        pos = args[0]
        if self._plot.sceneBoundingRect().contains(pos) and self._last_z is not None:
            mp = self._plot.vb.mapSceneToView(pos)
            x, y = float(mp.x()), float(mp.y())
            z_val = self._nearest_z(x, y)
            self._hover_text = f"x={x:.4g}  y={y:.4g}  z={z_val:.4g}"
        else:
            self._hover_text = ""
        self.status_changed.emit(self._build_status())

    def _nearest_z(self, x: float, y: float) -> float:
        try:
            ny, nx = self._last_z.shape
            xi = int(np.clip(
                (x - self._x_min) / (self._x_max - self._x_min) * (nx - 1), 0, nx - 1
            ))
            yi = int(np.clip(
                (y - self._y_min) / (self._y_max - self._y_min) * (ny - 1), 0, ny - 1
            ))
            return float(self._last_z[yi, xi])
        except Exception:
            return float("nan")
