import unittest

from multi_view.colorbar_canvas import _build_discrete_legend_html


class MultiViewDiscreteColorbarTests(unittest.TestCase):
    def test_discrete_legend_html_uses_color_boxes_and_integer_labels(self):
        html = _build_discrete_legend_html(
            ["#0066ff", "#ff1f1f", "#00c853"],
            "Phase",
        )

        self.assertIn("Phase", html)
        self.assertIn("background:#0066ff", html)
        self.assertIn("background:#ff1f1f", html)
        self.assertIn("background:#00c853", html)
        self.assertIn("<span class=\"label\">1</span>", html)
        self.assertIn("<span class=\"label\">2</span>", html)
        self.assertIn("<span class=\"label\">3</span>", html)
        self.assertIn("writing-mode:vertical-rl", html)
        self.assertIn("text-orientation:mixed", html)
        self.assertIn("<div class=\"rows\">", html)
        self.assertIn(".legend{display:grid;grid-template-columns:auto auto;gap:8px 28px", html)
        self.assertIn(".title{", html)
        self.assertIn(".title{font-size:22px;font-weight:700;writing-mode:vertical-rl;text-orientation:mixed;transform:rotate(180deg);white-space:nowrap;grid-column:2", html)
        self.assertIn(".rows{grid-column:1", html)
        self.assertNotIn("Plotly.newPlot", html)


if __name__ == "__main__":
    unittest.main()
