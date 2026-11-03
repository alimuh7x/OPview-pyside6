import unittest

import plotly.graph_objects as go
from matplotlib.mathtext import MathTextParser

from utils.label_formatting import format_plotly_figure, label_to_html, label_to_matplotlib, label_to_plotly
from utils.label_editing import edit_label_text
from utils.label_notation import label_to_notation


class LabelNotationTests(unittest.TestCase):
    def test_preview_uses_underscore_and_caret(self):
        self.assertEqual(label_to_html("σ_xx^p [MPa]"), "σ<sub>xx</sub><sup>p</sup> [MPa]")
        self.assertEqual(label_to_html("ε^{p + 1}"), "ε<sup>p + 1</sup>")

    def test_legacy_labels_become_readable_notation(self):
        self.assertEqual(label_to_notation("σ<sub>xx</sub><sup>p</sup> [MPa]"), "σ_xx^p [MPa]")

    def test_nested_groups_and_literal_markers_render(self):
        for label in ("σ_{x^p}", r"raw\_name σ_xx", "σ_{x y}", "m^-2"):
            with self.subTest(label=label):
                converted = label_to_matplotlib(label)
                self.assertNotIn("<sub>", converted)
                MathTextParser("path").parse(converted)

    def test_plotly_renders_scientific_angle_brackets(self):
        self.assertEqual(label_to_plotly("<σ_xx>"), "&lt;σ<sub>xx</sub>&gt;")

    def test_script_backspace_and_normal_keep_readable_notation(self):
        self.assertEqual(edit_label_text("σ_xx", 4, 0, action="backspace")[0], "σ_x")
        self.assertEqual(edit_label_text("σ_x", 3, 0, action="backspace")[0], "σ")
        self.assertEqual(edit_label_text("σ_xy", 2, 1, action="normal")[0], "σx_y")

    def test_chart_rendering_formats_titles_legends_annotations_and_colorbar(self):
        figure = go.Figure(go.Heatmap(z=[[0, 1]], name="ε^p", colorbar={"title": "σ_xx"}))
        figure.update_layout(xaxis_title="ε_xx", annotations=[dict(x=0, y=0, text="<b>σ_xx</b>")])
        format_plotly_figure(figure)
        self.assertEqual(figure.data[0].name, "ε<sup>p</sup>")
        self.assertEqual(figure.data[0].colorbar.title.text, "σ<sub>xx</sub>")
        self.assertEqual(figure.layout.xaxis.title.text, "ε<sub>xx</sub>")
        self.assertEqual(figure.layout.annotations[0].text, "<b>σ<sub>xx</sub></b>")
        once = figure.to_json()
        format_plotly_figure(figure)
        self.assertEqual(figure.to_json(), once)
