import unittest

import numpy as np

from multi_property import export_renderer as er


class MultiPropertyExportLayoutTests(unittest.TestCase):
    def test_font_sizes_convert_pixels_to_points_at_export_dpi(self):
        self.assertAlmostEqual(er._px_to_pt(300, 300), 72.0)
        self.assertAlmostEqual(er._px_to_pt(40, 300), 9.6)

    def test_top_row_title_fits_inside_the_colorbar_zone(self):
        bar_top = er._BAR_OFFSET_TOP_ROW_PX + er._BAR_THICKNESS_PX
        self.assertLessEqual(bar_top + er._LABEL_PAD_PX + er._TITLE_FONT_PX, er._COLORBAR_HEIGHT_PX)
        # tick labels sit between the bar and the heatmap
        self.assertGreaterEqual(er._BAR_OFFSET_TOP_ROW_PX - er._TICK_PAD_PX - er._TICK_FONT_PX, 0)

    def test_bottom_row_title_stays_above_the_sheet_edge(self):
        bar_bottom = er._BAR_OFFSET_BOTTOM_ROW_PX  # colorbar offset from the sheet bottom (px)
        self.assertGreaterEqual(bar_bottom - er._LABEL_PAD_PX - er._TITLE_FONT_PX, 0)
        # tick labels sit between the bar and the heatmap
        bar_top = bar_bottom + er._BAR_THICKNESS_PX
        self.assertLessEqual(bar_top + er._TICK_PAD_PX + er._TICK_FONT_PX, er._COLORBAR_HEIGHT_PX)

    def test_end_tick_labels_stay_inside_their_cell(self):
        # A "-1.23e-10" style label is about 9 characters at ~0.62 em; it is centred on the bar end.
        half_label = 9 * 0.62 * er._TICK_FONT_PX / 2.0
        bar_start = er._HEATMAP_TARGET_PX * (1.0 - er._COLORBAR_SPAN) / 2.0
        self.assertGreaterEqual(bar_start - half_label, 0)

    @staticmethod
    def _payload(x_span: float, y_span: float, n: int = 160) -> dict:
        # The sampled grid is always n x n, whatever the domain's aspect ratio.
        x, y = np.meshgrid(np.linspace(0.0, x_span, n), np.linspace(0.0, y_span, n))
        return {"x_grid": x, "y_grid": y, "z_grid": np.zeros((n, n))}

    def test_heatmap_size_follows_domain_aspect_not_square_grid_shape(self):
        self.assertEqual(er._heatmap_size_px(self._payload(99, 99)), (1000, 1000))
        self.assertEqual(er._heatmap_size_px(self._payload(200, 100)), (1000, 500))
        self.assertEqual(er._heatmap_size_px(self._payload(60, 100)), (600, 1000))

    def test_tall_domain_cell_keeps_minimum_width_and_heatmap_is_centred_inside_it(self):
        layout = er._row_layout([self._payload(60, 100)])
        cell = layout["cells"][0]

        self.assertEqual(cell["heatmap_width"], 600)
        self.assertEqual(cell["width"], er._MIN_CELL_WIDTH_PX)
        self.assertEqual(cell["heatmap_height"], 1000)


if __name__ == "__main__":
    unittest.main()
