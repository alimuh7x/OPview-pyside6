import unittest

from config.constants import PALETTES
from viewer.colorscale import (
    cmap_to_plotly_scale,
    discrete_palette_colors,
    make_discrete_colormap,
)


class ColorscalePaletteTests(unittest.TestCase):
    def test_min_max_palette_is_replaced_by_discrete_custom(self):
        self.assertNotIn("min-max", PALETTES)
        self.assertIn("discrete-custom", PALETTES)

    def test_discrete_custom_palette_builds_hard_color_bands(self):
        colors = discrete_palette_colors(2)
        cmap = make_discrete_colormap(colors)
        colorscale = cmap_to_plotly_scale(cmap)

        self.assertEqual(colors, ["#0066ff", "#ff1f1f"])
        self.assertEqual(
            colorscale,
            [
                [0.0, "#0066ff"],
                [0.5, "#0066ff"],
                [0.5, "#ff1f1f"],
                [1.0, "#ff1f1f"],
            ],
        )

    def test_discrete_custom_palette_expands_to_requested_band_count(self):
        colors = discrete_palette_colors(4)
        cmap = make_discrete_colormap(colors)
        colorscale = cmap_to_plotly_scale(cmap)

        self.assertEqual(len(colors), 4)
        self.assertEqual(colorscale[0], [0.0, colors[0]])
        self.assertEqual(colorscale[-1], [1.0, colors[-1]])
        self.assertEqual(colorscale[1], [0.25, colors[0]])
        self.assertEqual(colorscale[2], [0.25, colors[1]])


if __name__ == "__main__":
    unittest.main()
