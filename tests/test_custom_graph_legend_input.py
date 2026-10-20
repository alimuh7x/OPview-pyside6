import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from graphs.graph_canvas import GraphCanvas
from graphs.tab_widget import CustomGraphTab


def _state(path: Path, legends: dict[str, str]) -> dict:
    columns = list(legends)
    return {
        "files": [str(path)],
        "columns_by_file": {str(path): columns},
        "column_settings": {
            str(path): {
                column: {"legend": legend, "yaxis": "y1", "conversion": "as-is"}
                for column, legend in legends.items()
            }
        },
        "x_axis_column": "Time",
        "x_axis_conversion": "as-is",
        "trace_mode": "lines",
        "line_style": "solid",
        "show_grid": True,
        "show_legend": True,
    }


def _legend_visible(figure) -> bool:
    """True when the browser would draw at least one legend entry."""
    if figure.layout.showlegend is False:
        return False
    return any(trace.showlegend is not False for trace in figure.data)


class CustomGraphLegendInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "curves.txt"
        self.path.write_text("Time A B\n0 1 10\n1 2 20\n", encoding="utf-8")
        self.canvas = GraphCanvas()

    def test_canvas_shows_legend_for_valid_legend_input(self):
        figure = self.canvas._build_figure(_state(self.path, {"A": "Alpha"}))

        self.assertEqual(figure.data[0].name, "Alpha")
        self.assertTrue(_legend_visible(figure))

    def test_html_declares_greek_italic_font_face_for_bundled_file(self):
        html = self.canvas._build_html(self.canvas._build_figure(_state(self.path, {"A": "σ"})))

        self.assertIn("<style>@font-face{font-family:'OPViewGreek'", html)
        self.assertNotIn("{{", html.split("</style>")[0])
        self.assertIn("font-family:'OPViewGreek'", html)
        self.assertIn("unicode-range:U+0370-03FF", html)
        self.assertIn("STIXTwoText-Italic.ttf", html)

    def test_canvas_hides_legend_when_legend_input_is_empty(self):
        figure = self.canvas._build_figure(_state(self.path, {"A": ""}))

        self.assertFalse(_legend_visible(figure))

    def test_canvas_hides_legend_when_legend_input_is_whitespace(self):
        figure = self.canvas._build_figure(_state(self.path, {"A": "   "}))

        self.assertFalse(_legend_visible(figure))

    def test_canvas_hides_only_the_series_whose_legend_input_is_empty(self):
        figure = self.canvas._build_figure(_state(self.path, {"A": "Alpha", "B": ""}))

        by_name = {trace.name: trace for trace in figure.data}
        self.assertIsNot(by_name["Alpha"].showlegend, False)
        self.assertFalse(
            any(trace.showlegend is not False for trace in figure.data if trace.name != "Alpha")
        )
        self.assertTrue(_legend_visible(figure))

    def test_canvas_hides_marker_series_legend_when_input_is_empty(self):
        state = _state(self.path, {"A": ""})
        state["trace_mode"] = "lines+markers"

        figure = self.canvas._build_figure(state)

        self.assertFalse(_legend_visible(figure))

    def test_panel_clearing_legend_field_removes_legend_from_figure(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()
        panel.add_files([str(self.path)])
        resolved = str(self.path.resolve())
        panel._column_checkboxes[(resolved, "A")].setChecked(True)
        self.assertTrue(_legend_visible(panel.canvas._build_figure(panel.state())))

        legend = panel._legend_edits[(resolved, "A")]
        legend.setText("")
        legend.editingFinished.emit()

        self.assertFalse(_legend_visible(panel.canvas._build_figure(panel.state())))

    def test_panel_retyping_legend_field_restores_legend(self):
        tab = CustomGraphTab()
        panel = tab.add_graph_panel()
        panel.add_files([str(self.path)])
        resolved = str(self.path.resolve())
        panel._column_checkboxes[(resolved, "A")].setChecked(True)
        legend = panel._legend_edits[(resolved, "A")]
        legend.setText("")
        legend.editingFinished.emit()

        legend.setText("Alpha")
        legend.editingFinished.emit()

        figure = panel.canvas._build_figure(panel.state())
        self.assertEqual(figure.data[0].name, "Alpha")
        self.assertTrue(_legend_visible(figure))


if __name__ == "__main__":
    unittest.main()
