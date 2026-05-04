"""Matplotlib canvas for line scan plots."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.debug import debug_print


class LineScanCanvas(QWidget):
    """Render line scan data similar to OPView."""

    def __init__(self) -> None:
        debug_print("LineScanCanvas.__init__ start")
        super().__init__()
        self._figure = Figure(figsize=(5.2, 3.0))
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._axes = self._figure.add_subplot(111)
        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)
        debug_print("LineScanCanvas.__init__ complete")

    def render_line(self, x_data, z_data, *, title: str, x_label: str, y_label: str) -> None:
        debug_print("LineScanCanvas.render_line called")
        self._figure.clear()
        self._axes = self._figure.add_subplot(111)
        self._axes.plot(x_data, z_data, color="#c50623", linewidth=2)
        self._axes.set_title(title, fontsize=10)
        self._axes.set_xlabel(x_label)
        self._axes.set_ylabel(y_label)
        self._axes.grid(True, color="#d8deea", linewidth=0.6)
        self._figure.tight_layout()
        self._canvas.draw()
        debug_print("LineScanCanvas draw complete")
