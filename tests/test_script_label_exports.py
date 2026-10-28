"""Script formatting must survive the real image-rendering boundaries."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
from matplotlib.colorbar import Colorbar
import numpy as np
from PySide6.QtWidgets import QApplication

from config.constants import DEFAULTS
from multi_property.export_renderer import save_multi_property_png
from multi_view.colorbar_canvas import _build_colorbar_figure
from utils.label_formatting import format_plotly_figure, label_to_html, label_to_matplotlib
from viewer.animation_player import _MatplotlibCanvas
from viewer.heatmap_canvas import HeatmapCanvas


class ScriptLabelExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def payload(self):
        x, y = np.meshgrid(np.arange(3.0), np.arange(3.0))
        return {
            "x_grid": x, "y_grid": y, "z_grid": np.linspace(0.0, 1.0, 9).reshape(3, 3),
            "cmap": matplotlib.colormaps["viridis"], "vmin": 0.0, "vmax": 1.0,
            "colorbar_label": "σ_xx^p [MPa]",
            "label": "σ_xx^p [MPa]",
        }

    def test_single_view_png_renders_script_colorbar_label(self):
        payload = self.payload()
        canvas = HeatmapCanvas.__new__(HeatmapCanvas)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(DEFAULTS, {"export_resolution": 128}), patch.object(
            Colorbar, "set_label", autospec=True, side_effect=Colorbar.set_label
        ) as labels:
            path = Path(tmp) / "single.png"
            self.assertTrue(canvas.save_high_resolution_png(str(path), payload=payload, dpi=100))
            self.assertGreater(path.stat().st_size, 100)
            self.assertEqual(labels.call_args.args[1], label_to_matplotlib(payload["label"]))

    def test_multi_property_png_renders_script_colorbar_label(self):
        payload = self.payload()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            Colorbar, "set_label", autospec=True, side_effect=Colorbar.set_label
        ) as labels:
            path = Path(tmp) / "properties.png"
            self.assertTrue(save_multi_property_png(str(path), rows=[[payload]], logo_path=None, dpi=100))
            self.assertGreater(path.stat().st_size, 100)
            self.assertEqual(labels.call_args.args[1], label_to_matplotlib(payload["label"]))

    def test_animation_canvas_renders_script_labels(self):
        payload = self.payload()
        canvas = _MatplotlibCanvas()
        try:
            canvas.show_frame(payload["z_grid"], "viridis", 0.0, 1.0, colorbar_label=payload["label"])
            canvas._canvas.draw()
            self.assertEqual(canvas._cbar.ax.get_ylabel(), label_to_matplotlib(payload["label"]))
        finally:
            canvas.deleteLater()

    def test_plotly_colorbar_keeps_script_markup(self):
        label = self.payload()["label"]
        figure = _build_colorbar_figure([[0.0, "black"], [1.0, "white"]], 0.0, 1.0, label)
        format_plotly_figure(figure)
        self.assertEqual(figure.data[0].colorbar.title.text, label_to_html(label))
