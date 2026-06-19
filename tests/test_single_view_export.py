import unittest
from pathlib import Path

from viewer.heatmap_controller import HeatmapController


class SingleViewExportTests(unittest.TestCase):
    def test_default_export_filename_is_safe_png(self):
        self.assertEqual(
            HeatmapController._default_export_filename("Elastic Strains"),
            "Elastic_Strains_heatmap.png",
        )

    def test_normalise_png_export_path_adds_png_suffix(self):
        output_path = HeatmapController._normalise_png_export_path("my_heatmap")

        self.assertEqual(output_path, Path("my_heatmap.png"))

    def test_normalise_png_export_path_returns_none_on_cancel(self):
        self.assertIsNone(HeatmapController._normalise_png_export_path(""))


if __name__ == "__main__":
    unittest.main()
