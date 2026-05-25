"""Shared Plotly typography and axis styling for app graphs."""

from __future__ import annotations

from typing import Any


class PlotStyle:
    """Central style object for Plotly-based charts."""

    FONT_FAMILY = "Arial"
    TEXT_COLOR = "#102a52"
    MUTED_COLOR = "#6a7e9f"
    GRID_COLOR = "rgba(128, 128, 128, 0.2)"

    BASE_FONT_SIZE          = 16
    EMPTY_FONT_SIZE         = 14

    PANEL_LEGEND_FONT_SIZE  = 20
    PANEL_AXIS_TITLE_SIZE   = 22
    PANEL_TICK_FONT_SIZE    = 18
    TRACE_LINE_WIDTH        = 3.5
    MAX_MARKER_POINTS       = 15
    MARKER_SIZE             = 12
    MARKER_SYMBOLS          = (
        "circle",
        "square",
        "diamond",
        "cross",
        "x",
        "triangle-up",
        "triangle-down",
        "star",
    )
    SERIES_COLORS           = (
        "#111111",
        "#d62728",
        "#2ca02c",
        "#1f77b4",
        "#9467bd",
        "#ff7f0e",
        "#17becf",
        "#8c564b",
    )

    GRAPH_LEGEND_FONT_SIZE  = 28
    GRAPH_AXIS_TITLE_SIZE   = 32
    GRAPH_TICK_FONT_SIZE    = 26
    GUIDE_LINE_WIDTH        = 6

    COLORBAR_TITLE_SIZE     = 28
    COLORBAR_TICK_FONT_SIZE = 24


    @classmethod
    def font(
        cls,
        *,
        size: int | None = None,
        color: str | None = None,
        family: str | None = None,
    ) -> dict[str, Any]:
        return {
            "color": color or cls.TEXT_COLOR,
            "size": size or cls.BASE_FONT_SIZE,
            "family": family or cls.FONT_FAMILY,
        }

    @classmethod
    def layout_font(cls) -> dict[str, Any]:
        return cls.font()

    @classmethod
    def panel_axis_title_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.PANEL_AXIS_TITLE_SIZE)

    @classmethod
    def panel_tick_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.PANEL_TICK_FONT_SIZE)

    @classmethod
    def graph_axis_title_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.GRAPH_AXIS_TITLE_SIZE)

    @classmethod
    def graph_tick_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.GRAPH_TICK_FONT_SIZE)

    @classmethod
    def colorbar_title_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.COLORBAR_TITLE_SIZE)

    @classmethod
    def colorbar_tick_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.COLORBAR_TICK_FONT_SIZE)

    @classmethod
    def axis_title_font(cls) -> dict[str, Any]:
        return cls.graph_axis_title_font()

    @classmethod
    def tick_font(cls) -> dict[str, Any]:
        return cls.graph_tick_font()

    @classmethod
    def legend_font(cls) -> dict[str, Any]:
        return cls.graph_legend_font()

    @classmethod
    def panel_legend_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.PANEL_LEGEND_FONT_SIZE)

    @classmethod
    def graph_legend_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.GRAPH_LEGEND_FONT_SIZE)

    @classmethod
    def empty_annotation_font(cls) -> dict[str, Any]:
        return cls.font(size=cls.EMPTY_FONT_SIZE, color=cls.MUTED_COLOR)

    @classmethod
    def _legend(cls, font: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        config = {"font": font}
        config.update(overrides)
        return config

    @classmethod
    def panel_legend(cls, **overrides: Any) -> dict[str, Any]:
        return cls._legend(cls.panel_legend_font(), **overrides)

    @classmethod
    def graph_legend(cls, **overrides: Any) -> dict[str, Any]:
        return cls._legend(cls.graph_legend_font(), **overrides)

    @classmethod
    def legend(cls, **overrides: Any) -> dict[str, Any]:
        return cls.graph_legend(**overrides)

    @classmethod
    def trace_line(cls, **overrides: Any) -> dict[str, Any]:
        config = {"width": cls.TRACE_LINE_WIDTH}
        config.update(overrides)
        return config

    @classmethod
    def series_color(cls, series_index: int) -> str:
        return cls.SERIES_COLORS[int(series_index) % len(cls.SERIES_COLORS)]

    @classmethod
    def marker_sample_indices(cls, point_count: int) -> list[int]:
        count = max(0, int(point_count))
        if count <= cls.MAX_MARKER_POINTS:
            return list(range(count))
        if cls.MAX_MARKER_POINTS <= 1:
            return [0]
        step = (count - 1) / (cls.MAX_MARKER_POINTS - 1)
        indices = [round(index * step) for index in range(cls.MAX_MARKER_POINTS)]
        indices[0] = 0
        indices[-1] = count - 1
        return indices

    @classmethod
    def marker_style(cls, series_index: int, **overrides: Any) -> dict[str, Any]:
        symbol = cls.MARKER_SYMBOLS[int(series_index) % len(cls.MARKER_SYMBOLS)]
        config = {
            "size": cls.MARKER_SIZE,
            "symbol": symbol,
            "maxdisplayed": cls.MAX_MARKER_POINTS,
            "line": {"color": "white", "width": 1.5},
        }
        config.update(overrides)
        return config

    @classmethod
    def _axis(
        cls,
        title: str,
        show_grid: bool,
        *,
        title_font: dict[str, Any],
        tick_font: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "title": {"text": title, "font": title_font},
            "tickfont": tick_font,
            "exponentformat": "e",
            "showexponent": "all",
            "minexponent": 4,
            "showgrid": show_grid,
            "gridcolor": cls.GRID_COLOR,
            "zeroline": False,
            "showline": True,
            "linecolor": "black",
            "linewidth": 2.5,
            "mirror": "allticks",
            "ticks": "inside",
            "ticklen": 10,
            "tickwidth": 2.5,
            "tickcolor": "black",
            "minor": {
                "ticks": "inside",
                "ticklen": 6,
                "tickwidth": 1.5,
                "tickcolor": "black",
                "showgrid": False,
            },
        }

    @classmethod
    def panel_axis(cls, title: str, show_grid: bool) -> dict[str, Any]:
        return cls._axis(
            title,
            show_grid,
            title_font=cls.panel_axis_title_font(),
            tick_font=cls.panel_tick_font(),
        )

    @classmethod
    def graph_axis(cls, title: str, show_grid: bool) -> dict[str, Any]:
        return cls._axis(
            title,
            show_grid,
            title_font=cls.graph_axis_title_font(),
            tick_font=cls.graph_tick_font(),
        )

    @classmethod
    def publication_axis(cls, title: str, show_grid: bool) -> dict[str, Any]:
        return cls.graph_axis(title, show_grid)
