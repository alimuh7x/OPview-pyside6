"""Palette helpers for matplotlib and Plotly heatmaps."""

from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.colors import to_hex

from app.debug import debug_print
from config.constants import PALETTES

DISCRETE_CUSTOM_PALETTE = "discrete-custom"
_DISCRETE_COLORS = [
    "#0066ff",
    "#ff1f1f",
    "#00c853",
    "#ffd600",
    "#aa00ff",
    "#00e5ff",
    "#ff6d00",
    "#f50057",
    "#64dd17",
    "#304ffe",
]


def discrete_palette_colors(count: int) -> list[str]:
    """Return bright default colors for a discrete custom palette."""
    debug_print("colorscale.discrete_palette_colors called")
    safe_count = max(2, min(10, int(count)))
    debug_print(f"colorscale discrete color count={safe_count}")
    colors = list(_DISCRETE_COLORS[:safe_count])
    debug_print(f"colorscale discrete colors={colors}")
    return colors


def make_discrete_colormap(colors: list[str]) -> ListedColormap:
    """Create a hard-banded colormap and matching Plotly scale."""
    debug_print("colorscale.make_discrete_colormap called")
    safe_colors = list(colors) if len(colors) >= 2 else discrete_palette_colors(2)
    debug_print(f"colorscale discrete input colors={safe_colors}")
    step = 1.0 / len(safe_colors)
    debug_print(f"colorscale discrete step={step}")
    plotly_scale: list[list[float | str]] = []
    for index, color in enumerate(safe_colors):
        start = index * step
        end = 1.0 if index == len(safe_colors) - 1 else (index + 1) * step
        debug_print(f"colorscale discrete band index={index} start={start} end={end} color={color}")
        plotly_scale.append([start, color])
        plotly_scale.append([end, color])
    cmap = ListedColormap(safe_colors, name="discrete-custom")
    setattr(cmap, "_opview_plotly_scale", plotly_scale)
    debug_print(f"colorscale discrete plotly stops={len(plotly_scale)}")
    return cmap


def palette_to_cmap(palette_name: str) -> LinearSegmentedColormap:
    """Convert a named palette into a matplotlib colormap."""
    debug_print("colorscale.palette_to_cmap called")
    debug_print(f"colorscale palette name={palette_name}")
    if palette_name == DISCRETE_CUSTOM_PALETTE:
        debug_print("colorscale using default discrete custom palette")
        return make_discrete_colormap(discrete_palette_colors(2))
    colors = PALETTES.get(palette_name, PALETTES["aqua-fire"])
    debug_print(f"colorscale palette colors={colors}")
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
    debug_print("colorscale.cmap_to_plotly_scale called")
    explicit_scale = getattr(colormap, "_opview_plotly_scale", None)
    if explicit_scale is not None:
        debug_print(f"colorscale returning explicit stops={len(explicit_scale)}")
        return explicit_scale
    if steps < 2:
        steps = 2
    positions = [index / (steps - 1) for index in range(steps)]
    scale = [[position, to_hex(colormap(position))] for position in positions]
    debug_print(f"colorscale sampled stops={len(scale)}")
    return scale
