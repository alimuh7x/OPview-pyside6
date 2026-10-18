import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from multi_property.export_renderer import save_multi_property_png
from viewer.heatmap_canvas import HeatmapCanvas
from viewer.plot_style import PlotStyle


def _widest_red_run(path: str) -> int:
    """Width in pixels of the red guide line, taken as the longest horizontal red run."""
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(int)
    red = (rgb[..., 0] > 150) & (rgb[..., 1] < 90) & (rgb[..., 2] < 110)
    widest = 0
    for row in red:
        run = 0
        for is_red in row:
            run = run + 1 if is_red else 0
            widest = max(widest, run)
    return widest


def _grids():
    x, y = np.meshgrid(np.arange(60, dtype=float), np.arange(40, dtype=float))
    z = np.random.default_rng(0).random((40, 60))
    return x, y, z


class ExportGuideLineWidthTests(unittest.TestCase):
    """The line-scan guide is sized in pixels on screen; export must not scale it with dpi."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _single_view_width(self, tmp: str, dpi: int) -> int:
        x, y, z = _grids()
        payload = {
            "x_grid": x, "y_grid": y, "z_grid": z, "cmap": matplotlib.colormaps["gray"],
            "vmin": 0.0, "vmax": 1.0, "colorbar_label": "v", "plot_type": "heatmap",
            "line_overlay": ("vertical", 30.0), "overlay_grid": None, "time_plot_points": [],
        }
        path = f"{tmp}/single_{dpi}.png"
        self.assertTrue(HeatmapCanvas().save_high_resolution_png(path, payload=payload, dpi=dpi))
        return _widest_red_run(path)

    def _multi_property_width(self, tmp: str, dpi: int) -> int:
        x, y, z = _grids()
        payload = {
            "x_grid": x, "y_grid": y, "z_grid": z, "cmap": matplotlib.colormaps["gray"],
            "vmin": 0.0, "vmax": 1.0, "label": "v", "plot_type": "heatmap",
            "overlay_grid": None, "line_overlay": ("vertical", 30.0),
        }
        path = f"{tmp}/multi_{dpi}.png"
        self.assertTrue(save_multi_property_png(path, rows=[[payload]], logo_path=None, dpi=dpi))
        return _widest_red_run(path)

    def test_single_view_export_line_width_does_not_scale_with_dpi(self):
        with tempfile.TemporaryDirectory() as tmp:
            low, high = self._single_view_width(tmp, 100), self._single_view_width(tmp, 300)

        self.assertGreater(low, 0)
        self.assertLessEqual(abs(high - low), 2)

    def test_multi_property_export_line_width_does_not_scale_with_dpi(self):
        with tempfile.TemporaryDirectory() as tmp:
            low, high = self._multi_property_width(tmp, 100), self._multi_property_width(tmp, 300)

        self.assertGreater(low, 0)
        self.assertLessEqual(abs(high - low), 2)

    def test_multi_property_export_line_is_guide_width_in_sheet_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            width = self._multi_property_width(tmp, 300)

        self.assertLessEqual(abs(width - PlotStyle.GUIDE_LINE_WIDTH), 2)


if __name__ == "__main__":
    unittest.main()
