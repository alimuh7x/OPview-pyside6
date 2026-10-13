import unittest

import numpy as np
from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QWidget

from viewer.heatmap_canvas import HeatmapCanvas, _COLORBAR_GAP
from viewer.heatmap_controller import HeatmapController
from viewer.panel_widget import _HEATMAP_LOGO_BAND_W, _HEATMAP_LOGO_GAP


class SingleViewExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

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

    def test_export_content_rect_crops_empty_row_margins(self):
        row = QWidget()
        row.resize(640, 420)
        logo = QWidget(row)
        logo.setGeometry(29, 0, 58, 420)
        heatmap = QWidget(row)
        heatmap.setGeometry(95, 0, 510, 420)

        rect = HeatmapController._export_content_rect(row)

        self.assertEqual(rect, QRect(29, 0, 576, 420))

    def test_export_scale_and_dpi_are_high_resolution(self):
        self.assertGreaterEqual(HeatmapController._export_device_scale(), 2)
        self.assertGreaterEqual(HeatmapController._export_dpi(), 300)

    def test_high_resolution_export_layout_keeps_logo_and_colorbar_inside_image(self):
        layout = HeatmapCanvas._export_layout_metrics(rows=1000, cols=1000, logo_band_width=_HEATMAP_LOGO_BAND_W)
        logo_x, logo_y, logo_width, logo_height = layout["logo_rect"]
        cbar_x, cbar_y, cbar_width, cbar_height = layout["colorbar_rect"]

        self.assertGreaterEqual(layout["logo_band_pixels"], logo_width)
        self.assertGreaterEqual(logo_y, 0)  # flush with the bottom, like the on-screen logo
        self.assertLess(logo_height, layout["height_pixels"])
        self.assertGreater(cbar_width, 28)
        self.assertEqual(cbar_height, round(1000 * 0.82 - 2 * 10 * 1000 / 420))
        self.assertLess(cbar_x + cbar_width, layout["width_pixels"])
        self.assertGreater(layout["width_pixels"] - (cbar_x + cbar_width), 300)

    def test_single_view_live_colorbar_and_logo_spacing_stays_compact(self):
        self.assertLessEqual(_COLORBAR_GAP, 0.015)
        # Single View logo band and gap match the Multi View row (58 px band, 8 px spacing).
        self.assertEqual(_HEATMAP_LOGO_GAP, 8)
        self.assertEqual(_HEATMAP_LOGO_BAND_W, 58)

    def test_high_resolution_export_layout_mirrors_on_screen_row(self):
        # 840 data rows = 2x the 420 px canvas, so every on-screen pixel measure doubles.
        layout = HeatmapCanvas._export_layout_metrics(
            rows=840, cols=900, logo_band_width=_HEATMAP_LOGO_BAND_W, logo_gap_width=_HEATMAP_LOGO_GAP
        )

        self.assertEqual(layout["logo_band_pixels"], 116)
        self.assertEqual(layout["logo_gap_pixels"], 16)
        self.assertEqual(layout["heatmap_x"], 132)
        logo_x, logo_y, logo_width, _ = layout["logo_rect"]
        self.assertEqual((logo_x, logo_y, logo_width), (8, 0, 100))
        cbar_x, cbar_y, cbar_width, cbar_height = layout["colorbar_rect"]
        self.assertEqual(cbar_x, 132 + 900 + round(10 * 2 + 0.012 * 900))  # Plotly xpad + x=1.012
        self.assertEqual((cbar_width, cbar_height), (36, round(840 * 0.82 - 2 * 10 * 2)))  # len 0.82 minus ypad
        self.assertEqual(cbar_y, round(840 * 0.5 - cbar_height / 2))

    def test_toolbar_strip_sits_outside_the_420px_plot_area(self):
        from viewer.heatmap_canvas import _CANVAS_HEIGHT, _WIDGET_HEIGHT

        self.assertEqual(HeatmapCanvas.modebar_strip_height(), 40)
        self.assertEqual(_WIDGET_HEIGHT - HeatmapCanvas.modebar_strip_height(), _CANVAS_HEIGHT)

    def test_interface_overlay_is_opaque_so_outline_never_stacks_on_fill(self):
        from viewer.plot_style import PlotStyle

        self.assertEqual(PlotStyle.INTERFACE_OVERLAY_ALPHA, 1.0)

    def test_export_image_width_follows_domain_aspect_not_grid_shape(self):
        # A 2:1 domain sampled on a square grid must still export a 2:1 image area (no letterboxing).
        x = np.linspace(0.0, 2.0, 50)
        y = np.linspace(0.0, 1.0, 50)

        self.assertEqual(HeatmapCanvas._export_image_width(840, x, y), 1680)
        self.assertEqual(HeatmapCanvas._export_image_width(840, y, y), 840)

    def test_high_resolution_export_keeps_colorbar_close_to_heatmap(self):
        layout = HeatmapCanvas._export_layout_metrics(rows=1000, cols=1000, logo_band_width=_HEATMAP_LOGO_BAND_W)

        self.assertLessEqual(layout["colorbar_gap_pixels"], 40)  # 10 px xpad + 0.012 of the image, scaled

    def test_export_font_conversion_matches_view_pixels_at_png_dpi(self):
        points = HeatmapCanvas._export_font_points(view_font_pixels=24, dpi=300, pixel_scale=1000 / 420)

        self.assertAlmostEqual(points, 13.714, places=2)


if __name__ == "__main__":
    unittest.main()
