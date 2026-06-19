import unittest
from pathlib import Path

from utils.webengine_downloads import _normalise_png_save_path, _suggested_png_name


class WebEngineDownloadTests(unittest.TestCase):
    def test_suggested_png_name_uses_plotly_suggestion(self):
        self.assertEqual(_suggested_png_name("newplot.png", "fallback.png"), "newplot.png")

    def test_suggested_png_name_adds_png_suffix(self):
        self.assertEqual(_suggested_png_name("newplot", "fallback.png"), "newplot.png")

    def test_suggested_png_name_uses_fallback(self):
        self.assertEqual(_suggested_png_name("", "line_scan.png"), "line_scan.png")

    def test_normalise_png_save_path_adds_suffix_from_suggestion(self):
        result = _normalise_png_save_path("/tmp/my_export", "newplot.png")

        self.assertEqual(Path(result).name, "my_export.png")

    def test_normalise_png_save_path_keeps_cancel_empty(self):
        self.assertEqual(_normalise_png_save_path("", "newplot.png"), "")


if __name__ == "__main__":
    unittest.main()
