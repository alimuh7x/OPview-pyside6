import unittest

from viewer.plot_style import PlotStyle


class PlotStyleTests(unittest.TestCase):
    def test_panel_axis_uses_compact_single_and_multiview_fonts(self):
        axis = PlotStyle.panel_axis("X Position", show_grid=True)

        self.assertEqual(axis["title"]["text"], "X Position")
        self.assertEqual(axis["title"]["font"], PlotStyle.panel_axis_title_font())
        self.assertEqual(axis["tickfont"], PlotStyle.panel_tick_font())
        self.assertEqual(axis["title"]["font"]["family"], "Arial")
        self.assertEqual(axis["title"]["font"]["color"], "#102a52")
        self.assertEqual(axis["title"]["font"]["size"], PlotStyle.PANEL_AXIS_TITLE_SIZE)
        self.assertEqual(axis["tickfont"]["size"], PlotStyle.PANEL_TICK_FONT_SIZE)
        self.assertTrue(axis["showgrid"])

    def test_graph_axis_uses_larger_custom_graph_fonts(self):
        axis = PlotStyle.graph_axis("Stress", show_grid=True)

        self.assertEqual(axis["title"]["font"], PlotStyle.graph_axis_title_font())
        self.assertEqual(axis["tickfont"], PlotStyle.graph_tick_font())
        self.assertEqual(axis["title"]["font"]["size"], 32)
        self.assertEqual(axis["tickfont"]["size"], 26)
        self.assertTrue(axis["showgrid"])

    def test_panel_legend_uses_compact_font_with_position_overrides(self):
        legend = PlotStyle.panel_legend(x=1.0, y=1.02, xanchor="right")

        self.assertEqual(legend["font"], PlotStyle.panel_legend_font())
        self.assertEqual(legend["x"], 1.0)
        self.assertEqual(legend["y"], 1.02)
        self.assertEqual(legend["xanchor"], "right")

    def test_graph_legend_uses_larger_custom_graph_font(self):
        legend = PlotStyle.graph_legend(x=0.02, y=0.98)

        self.assertEqual(legend["font"], PlotStyle.graph_legend_font())
        self.assertEqual(legend["font"]["size"], PlotStyle.GRAPH_LEGEND_FONT_SIZE)
        self.assertEqual(legend["x"], 0.02)
        self.assertEqual(legend["y"], 0.98)

    def test_trace_line_uses_global_width(self):
        line = PlotStyle.trace_line(color="#c50623")

        self.assertEqual(line["color"], "#c50623")
        self.assertEqual(line["width"], 3.5)

    def test_series_color_uses_shared_palette_and_cycles(self):
        self.assertEqual(PlotStyle.series_color(0), "#111111")
        self.assertEqual(PlotStyle.series_color(1), "#d62728")
        self.assertEqual(PlotStyle.series_color(len(PlotStyle.SERIES_COLORS)), "#111111")

    def test_marker_sample_indices_keep_at_most_15_points_including_ends(self):
        indices = PlotStyle.marker_sample_indices(40)

        self.assertEqual(len(indices), 15)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 39)

    def test_marker_sample_indices_keep_all_points_when_under_limit(self):
        self.assertEqual(PlotStyle.marker_sample_indices(5), [0, 1, 2, 3, 4])

    def test_marker_style_is_smaller_and_varies_by_trace(self):
        first = PlotStyle.marker_style(0, color="#111111")
        second = PlotStyle.marker_style(1, color="#d62728")

        self.assertEqual(first["size"], 12)
        self.assertEqual(second["size"], 12)
        self.assertEqual(first["color"], "#111111")
        self.assertEqual(second["color"], "#d62728")
        self.assertNotEqual(first["symbol"], second["symbol"])
        self.assertEqual(first["maxdisplayed"], PlotStyle.MAX_MARKER_POINTS)
        self.assertEqual(first["line"]["width"], 1.5)


if __name__ == "__main__":
    unittest.main()
