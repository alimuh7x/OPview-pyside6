import unittest

from matplotlib.mathtext import MathTextParser

from utils.label_formatting import label_to_html, label_to_matplotlib


class LabelFormattingTests(unittest.TestCase):
    def test_preview_preserves_scripts_but_escapes_other_markup(self):
        self.assertEqual(
            label_to_html("σ<sub>xx</sub><sup>p</sup> < 2 & <b>bold</b>"),
            "σ<sub>xx</sub><sup>p</sup> &lt; 2 &amp; &lt;b&gt;bold&lt;/b&gt;",
        )

    def test_plain_matplotlib_labels_remain_unchanged(self):
        self.assertEqual(label_to_matplotlib("Stress σ [MPa]"), "Stress σ [MPa]")

    def test_plain_matplotlib_labels_decode_stored_entities(self):
        self.assertEqual(label_to_matplotlib("A&amp;B"), "A&B")
        self.assertEqual(label_to_matplotlib("x&lt;2"), "x<2")

    def test_matplotlib_scripts_render_without_html_tags(self):
        for label in ("σ<sub>xx</sub> [MPa]", "ε<sup>p</sup>", "σ<sub>xx</sub><sup>2</sup>",
                      "σ<sub>a_b &amp; x&lt;2</sub>", "σ<sub>xx</sub><sub>yy</sub>",
                      "σ<sub><sup>x</sup>y</sub>", "σ<sub>x<sup>p</sup>x</sub>",
                      "σ<sup># &amp; _ ^ ~ $ % {x} \\y</sup>"):
            with self.subTest(label=label):
                converted = label_to_matplotlib(label)
                self.assertNotIn("<sub>", converted)
                self.assertNotIn("<sup>", converted)
                self.assertNotIn("</sub>", converted)
                self.assertNotIn("</sup>", converted)
                self.assertIn("$", converted)
                MathTextParser("path").parse(converted)
