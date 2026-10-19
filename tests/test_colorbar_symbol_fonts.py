"""Colorbar symbols use the same bundled Greek face as Custom Graph."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import plotly.graph_objects as go
from PySide6.QtWidgets import QApplication

from graphs.graph_canvas import GraphCanvas
from multi_property.colorbar_canvas import MultiPropertyColorbarCanvas, _build_colorbar_figure as property_figure
from multi_view.colorbar_canvas import ColorbarCanvas, _build_colorbar_figure as multi_figure
from viewer.colorscale import palette_to_cmap
from viewer.discrete_legend import add_discrete_legend_to_figure, build_discrete_legend_html
from viewer.heatmap_canvas import HeatmapCanvas, _COLORBAR_TITLE_FONT_SIZE
from viewer.plot_style import PlotStyle


class ColorbarSymbolFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def assert_greek_family(self, font):
        self.assertEqual(font.family, PlotStyle.graph_axis_title_font()["family"])

    def assert_greek_face(self, html):
        self.assertIn("@font-face{font-family:'OPViewGreek'", html)
        self.assertIn("STIXTwoText-Italic.ttf", html)
        self.assertIn("unicode-range:U+0370-03FF,U+00B5", html)

    def test_single_view_colorbar_title_uses_greek_font_and_original_size(self):
        canvas = HeatmapCanvas()
        self.addCleanup(canvas.deleteLater)
        canvas._last_extent = (0, 1, 0, 1)
        figure = canvas._build_figure(
            x_grid=np.array([0, 1]), y_grid=np.array([0, 1]), z_grid=np.array([[0, 1], [1, 0]]),
            cmap=palette_to_cmap("viridis"), vmin=0, vmax=1, line_overlay=None, overlay_grid=None,
            colorbar_label="Stress σ [MPa]",
        )
        self.assert_greek_family(figure.data[0].colorbar.title.font)
        self.assertEqual(figure.data[0].colorbar.title.font.size, _COLORBAR_TITLE_FONT_SIZE)
        self.assert_greek_face(canvas._build_html(figure))

    def test_multi_view_colorbar_title_uses_greek_font(self):
        figure = multi_figure([[0, "black"], [1, "white"]], 0, 1, "σ [MPa]")
        self.assert_greek_family(figure.data[0].colorbar.title.font)
        self.assertEqual(figure.data[0].colorbar.title.font.size, PlotStyle.COLORBAR_TITLE_SIZE)

    def test_multi_property_colorbar_title_uses_greek_font_and_original_weight(self):
        figure = property_figure([[0, "black"], [1, "white"]], 0, 1, "ε")
        self.assert_greek_family(figure.data[0].colorbar.title.font)
        self.assertEqual(figure.data[0].colorbar.title.font.size, 22)
        self.assertEqual(figure.data[0].colorbar.title.font.weight, 700)

    def test_standalone_colorbar_pages_load_greek_font(self):
        for canvas_type in (ColorbarCanvas, MultiPropertyColorbarCanvas):
            with self.subTest(canvas=canvas_type.__name__):
                web = Mock()
                canvas = SimpleNamespace(_web=web, _base_url=None, width=lambda: 360)
                canvas_type.update_colorbar(canvas, palette_to_cmap("viridis"), 0, 1, "σ")
                self.assert_greek_face(web.setHtml.call_args.args[0])

    def test_discrete_colorbar_title_uses_greek_font(self):
        figure = go.Figure()
        add_discrete_legend_to_figure(figure, ["red", "blue"], "ϕ")
        title = next(item for item in figure.layout.annotations if item.name == "Discrete Colorbar Title")
        self.assert_greek_family(title.font)
        html = build_discrete_legend_html(["red", "blue"], "ϕ")
        self.assert_greek_face(html)
        self.assertIn("font-family:OPViewGreek, Arial", html)

    def test_custom_graph_keeps_same_greek_font_setup(self):
        canvas = SimpleNamespace(_graph_width=800)
        self.assert_greek_face(GraphCanvas._build_html(canvas, go.Figure()))


if __name__ == "__main__":
    unittest.main()
