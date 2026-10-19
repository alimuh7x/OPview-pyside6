"""Greek typography in the analysis graphs shared by all three data views."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from viewer.histogram_canvas import HistogramCanvas
from viewer.line_scan_canvas import LineScanCanvas
from viewer.phase_fraction_history_canvas import PhaseFractionHistoryCanvas
from viewer.plot_style import PlotStyle
from viewer.time_plot_canvas import TimePlotCanvas


class PanelGraphSymbolFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.addCleanup(lambda: QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete))

    def assert_graph_fonts(self, canvas, figure):
        family = PlotStyle.graph_axis_title_font()["family"]
        for axis in (figure.layout.xaxis, figure.layout.yaxis):
            self.assertEqual(axis.title.font.family, family)
            self.assertEqual(axis.title.font.size, PlotStyle.PANEL_AXIS_TITLE_SIZE)
            self.assertEqual(axis.tickfont.family, family)
            self.assertEqual(axis.tickfont.size, PlotStyle.PANEL_TICK_FONT_SIZE)
        self.assertEqual(figure.layout.legend.font.family, family)
        self.assertEqual(figure.layout.legend.font.size, PlotStyle.PANEL_LEGEND_FONT_SIZE)
        html = canvas._build_html(figure)
        self.assertIn("@font-face{font-family:'OPViewGreek'", html)
        self.assertIn("STIXTwoText-Italic.ttf", html)
        self.assertIn("unicode-range:U+0370-03FF,U+00B5", html)

    def test_line_scan_axis_labels_and_legends_use_greek_face(self):
        canvas = LineScanCanvas()
        self.addCleanup(canvas.deleteLater)
        figure = canvas._figure_for_lines(
            [{"name": "σ", "x": [0, 1], "y": [1, 2]}],
            title="", x_label="μm", y_label="σ [MPa]",
        )
        self.assert_graph_fonts(canvas, figure)

    def test_histogram_axis_labels_and_legends_use_greek_face(self):
        canvas = HistogramCanvas()
        self.addCleanup(canvas.deleteLater)
        figure = canvas._figure_for_histograms(
            [{"name": "ε", "values": [1, 2, 3]}], label="ε", bins=10,
        )
        self.assert_graph_fonts(canvas, figure)

    def test_time_history_axis_labels_and_legends_use_greek_face(self):
        canvas = TimePlotCanvas()
        self.addCleanup(canvas.deleteLater)
        figure = canvas._build_time_plot_figure(
            [{"label": "σ", "steps": [0, 1], "values": [1, 2]}], y_label="σ [MPa]",
        )
        self.assert_graph_fonts(canvas, figure)

    def test_phase_history_axis_labels_and_legends_use_greek_face(self):
        canvas = PhaseFractionHistoryCanvas()
        self.addCleanup(canvas.deleteLater)
        figure = canvas._build_figure(
            [{"label": "ϕ", "steps": [0, 1], "values": [0.2, 0.3]}], current_step=None,
        )
        self.assert_graph_fonts(canvas, figure)


if __name__ == "__main__":
    unittest.main()
