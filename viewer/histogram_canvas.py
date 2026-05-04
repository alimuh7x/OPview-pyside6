"""Matplotlib canvas for histogram plots."""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.debug import debug_print


class HistogramCanvas(QWidget):
    """Render histogram data similar to OPView."""

    def __init__(self) -> None:
        debug_print("HistogramCanvas.__init__ start")
        super().__init__()
        self._figure = Figure(figsize=(5.2, 3.0))
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._axes = self._figure.add_subplot(111)
        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)
        debug_print("HistogramCanvas.__init__ complete")

    def render_histogram(self, values, *, label: str, bins: int) -> None:
        debug_print("HistogramCanvas.render_histogram called")
        self._figure.clear()
        self._axes = self._figure.add_subplot(111)
        data = np.asarray(values).flatten()
        data = data[~np.isnan(data)]
        if data.size == 0:
            debug_print("HistogramCanvas no finite data, rendering empty histogram")
            self._axes.text(0.5, 0.5, "No finite data", ha="center", va="center", transform=self._axes.transAxes)
        else:
            data_min = float(np.min(data))
            data_max = float(np.max(data))
            data_range = data_max - data_min
            tolerance = max(1e-12, abs(data_max) * 1e-12)
            debug_print(f"HistogramCanvas data_min={data_min}")
            debug_print(f"HistogramCanvas data_max={data_max}")
            debug_print(f"HistogramCanvas data_range={data_range}")
            if data_range <= tolerance:
                debug_print("HistogramCanvas near-constant data detected, using fallback range")
                pad = max(1.0, abs(data_max) * 1e-9)
                self._axes.hist(
                    data,
                    bins=1,
                    range=(data_min - pad, data_max + pad),
                    color="#183568",
                    alpha=0.9,
                    rwidth=0.4,
                )
            else:
                safe_bins = max(1, int(bins))
                self._axes.hist(data, bins=safe_bins, color="#183568", alpha=0.9, rwidth=0.95)
        self._axes.set_title(f"Distribution of {label}", fontsize=10)
        self._axes.set_xlabel(label)
        self._axes.set_ylabel("Frequency")
        self._axes.grid(True, axis="y", color="#d8deea", linewidth=0.6)
        self._figure.tight_layout()
        self._canvas.draw()
        debug_print("HistogramCanvas draw complete")
