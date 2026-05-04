"""Palette helpers for matplotlib and Plotly heatmaps."""

from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import to_hex

from config.constants import PALETTES


def palette_to_cmap(palette_name: str) -> LinearSegmentedColormap:
    """Convert a named palette into a matplotlib colormap."""
    colors = PALETTES.get(palette_name, PALETTES["aqua-fire"])
    return LinearSegmentedColormap.from_list(palette_name, colors)


def make_dynamic_colormap(min_val: float, max_val: float, blue_cut: float, red_cut: float, palette_name: str) -> LinearSegmentedColormap:
    """Approximate OPView's dynamic colorscale using matplotlib."""
    colors = PALETTES.get(palette_name, PALETTES["aqua-fire"])
    if max_val == min_val:
        return LinearSegmentedColormap.from_list(f"{palette_name}-flat", [(0.0, colors[2]), (1.0, colors[2])])

    def normalize(value: float) -> float:
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    prepend_black = blue_cut > min_val
    append_green = red_cut < max_val
    if prepend_black and append_green:
        p_blue = normalize(blue_cut)
        p_red = normalize(red_cut)
        points = [
            (0.0, colors[0]),
            ((0.0 + p_blue) / 2, colors[2]),
            (p_blue, colors[1]),
            ((p_blue + p_red) / 2, colors[2]),
            (p_red, colors[3]),
            ((p_red + 1.0) / 2, colors[2]),
            (1.0, colors[4]),
        ]
    elif prepend_black:
        p_blue = normalize(blue_cut)
        p_red = normalize(red_cut)
        points = [
            (0.0, colors[0]),
            ((0.0 + p_blue) / 2, colors[2]),
            (p_blue, colors[1]),
            ((p_blue + p_red) / 2, colors[2]),
            (p_red, colors[3]),
        ]
    elif append_green:
        p_blue = normalize(blue_cut)
        p_red = normalize(red_cut)
        points = [
            (0.0, colors[1]),
            ((p_blue + p_red) / 2, colors[2]),
            (p_red, colors[3]),
            ((p_red + 1.0) / 2, colors[2]),
            (1.0, colors[4]),
        ]
    else:
        points = [
            (0.0, colors[1]),
            (0.5, colors[2]),
            (1.0, colors[3]),
        ]
    return LinearSegmentedColormap.from_list(f"{palette_name}-dynamic", points)


def cmap_to_plotly_scale(colormap: LinearSegmentedColormap, steps: int = 17) -> list[list[float | str]]:
    """Convert a matplotlib colormap into a Plotly colorscale."""
    if steps < 2:
        steps = 2
    positions = [index / (steps - 1) for index in range(steps)]
    return [[position, to_hex(colormap(position))] for position in positions]
