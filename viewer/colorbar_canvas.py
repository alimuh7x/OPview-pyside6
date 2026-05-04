"""Standalone colorbar widget — mirrors Dash heatmap-colorbar-card."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print
from viewer.heatmap_canvas import _CANVAS_HEIGHT

_WIDTH = 90
_HEIGHT = _CANVAS_HEIGHT


class ColorbarCanvas(QWidget):
    """Narrow fixed-size widget that renders only the colorbar."""

    def __init__(self) -> None:
        debug_print("ColorbarCanvas.__init__ start")
        super().__init__()
        self.setFixedWidth(_WIDTH)
        self.setFixedHeight(_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._figure = Figure(figsize=(_WIDTH / 100, _HEIGHT / 100))
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setFixedSize(_WIDTH, _HEIGHT)
        self._canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        debug_print("ColorbarCanvas.__init__ complete")

    def render(self, cmap, vmin: float, vmax: float, label: str) -> None:
        debug_print("ColorbarCanvas.render called")
        self._figure.clear()
        ax = self._figure.add_axes([0.24, 0.03, 0.34, 0.94])
        sm = ScalarMappable(cmap=cmap, norm=Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cb = self._figure.colorbar(sm, cax=ax)
        cb.set_label(label, fontsize=10)
        cb.ax.tick_params(labelsize=10)
        self._canvas.draw()
        debug_print("ColorbarCanvas.render complete")

    def clear(self) -> None:
        self._figure.clear()
        self._canvas.draw()
