"""Plotly-backed canvas for Custom Graph panels."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print
from config import units
from data.text_sources import GenericTextDataSource
from utils.webengine_downloads import install_save_dialog_download_handler
from viewer.plot_style import PlotStyle

_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_GRAPH_WIDTH = 800
_GRAPH_HEIGHT = 620
_GREEK_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "STIXTwoText-Italic.ttf"
# Greek letters (and µ) come from the bundled serif italic face; everything else falls through to the next family.
_GREEK_FONT_FACE = (
    "@font-face{font-family:'" + PlotStyle.GREEK_FONT_FAMILY + "';font-style:normal;font-weight:100 900;"
    f"src:url('{_GREEK_FONT_PATH.as_uri()}') format('truetype');unicode-range:U+0370-03FF,U+00B5;}}"
)


class GraphCanvas(QWidget):
    """Render a multi-file line chart for one graph panel."""

    def __init__(self) -> None:
        debug_print("GraphCanvas.__init__ start")
        super().__init__()
        self.setObjectName("customGraphCanvas")
        self._last_trace_count = 0
        self._graph_width = _GRAPH_WIDTH
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        install_save_dialog_download_handler(
            self._web_view,
            self,
            fallback_name="custom_graph.png",
        )
        debug_print(f"GraphCanvas.__init__ size width={_GRAPH_WIDTH} height={_GRAPH_HEIGHT}")
        self._web_view.setMinimumSize(_GRAPH_WIDTH, 0)
        debug_print(f"GraphCanvas.__init__ web view placeholder min_width={_GRAPH_WIDTH}")
        debug_print("GraphCanvas.__init__ web view placeholder min_height=0")
        self._web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        debug_print("GraphCanvas.__init__ web view size policy expanding")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)
        self._web_view.setHtml(self._empty_html(), self._base_url)
        debug_print("GraphCanvas.__init__ complete")

    def set_available_width(self, width: int) -> None:
        debug_print(f"GraphCanvas.set_available_width width={width}")
        self._graph_width = _GRAPH_WIDTH
        self.setMinimumWidth(_GRAPH_WIDTH)
        self._web_view.setMinimumWidth(_GRAPH_WIDTH)
        debug_print(f"GraphCanvas graph width={self._graph_width}")

    def render(self, state: dict[str, Any]) -> None:
        debug_print("GraphCanvas.render start")
        figure = self._build_figure(state)
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print(f"GraphCanvas.render complete traces={self._last_trace_count}")

    def download_png(self, filename: str = "custom_graph") -> None:
        debug_print(f"GraphCanvas.download_png filename={filename}")
        safe_name = "".join(
            char if char.isalnum() or char in ("-", "_") else "_"
            for char in filename
        ).strip("_") or "custom_graph"
        script = (
            "var gd = document.getElementById('graph');"
            "if (gd && window.Plotly) {"
            "Plotly.downloadImage(gd, {"
            f"format: 'png', filename: {safe_name!r}, "
            f"width: {self._graph_width}, height: {_GRAPH_HEIGHT}, scale: 2"
            "});"
            "}"
        )
        self._web_view.page().runJavaScript(script)

    def _build_figure(self, state: dict[str, Any]) -> go.Figure:
        debug_print("GraphCanvas._build_figure called")
        files = state.get("files", [])
        columns_by_file = state.get("columns_by_file", {})
        column_settings = state.get("column_settings", {})
        x_axis_column = state.get("x_axis_column")
        trace_mode = state.get("trace_mode", "lines")
        line_style = state.get("line_style", "solid")
        show_grid = bool(state.get("show_grid", True))
        show_legend = bool(state.get("show_legend", True))
        legend_position = state.get("legend_position", "top-left")
        right_margin = 220 if legend_position == "right-outside" else 82
        figure = go.Figure()
        self._last_trace_count = 0
        any_legend_visible = False

        if not files:
            debug_print("GraphCanvas._build_figure no files")
            return self._empty_figure("Add a text-data file to plot columns")

        first_file = files[0]
        x_source = GenericTextDataSource(first_file)
        if not x_source.load():
            debug_print(f"GraphCanvas._build_figure failed x file={first_file}")
            return self._empty_figure("Could not load X-axis file")

        available_x_columns = x_source.columns()
        if not available_x_columns:
            debug_print("GraphCanvas._build_figure no x columns")
            return self._empty_figure("No numeric columns available")

        if x_axis_column not in available_x_columns:
            debug_print(f"GraphCanvas._build_figure fallback x column from={x_axis_column}")
            x_axis_column = available_x_columns[0]
        raw_x = np.asarray(x_source.series(x_axis_column), dtype=float)
        x_columns = x_source.dataframe_dict()
        x_data = self.x_transform(state, tuple(x_columns)).apply(raw_x, x_columns)
        debug_print(f"GraphCanvas._build_figure x_axis_column={x_axis_column} points={len(x_data)}")
        debug_print(f"GraphCanvas._build_figure x_conversion={state.get('x_axis_conversion', 'as-is')}")
        debug_print(f"GraphCanvas._build_figure raw_x_sample={raw_x[:3].tolist()}")
        debug_print(f"GraphCanvas._build_figure converted_x_sample={x_data[:3].tolist()}")

        color_index = 0
        plotted_x_values: list[float] = []
        for file_path in files:
            debug_print(f"GraphCanvas._build_figure load y file={file_path}")
            source = GenericTextDataSource(file_path)
            if not source.load():
                debug_print(f"GraphCanvas._build_figure skip unloaded file={file_path}")
                continue
            selected_columns = columns_by_file.get(file_path, [])
            debug_print(f"GraphCanvas._build_figure selected_columns={selected_columns}")
            for column in selected_columns:
                if column == x_axis_column:
                    debug_print(f"GraphCanvas._build_figure skip x column={column}")
                    continue
                if column not in source.columns():
                    debug_print(f"GraphCanvas._build_figure skip missing column={column}")
                    continue
                y_data = source.series(column)
                if len(y_data) != len(x_data):
                    debug_print(f"GraphCanvas._build_figure skip length mismatch x={len(x_data)} y={len(y_data)}")
                    continue
                settings = column_settings.get(file_path, {}).get(column, {})
                yaxis_side = settings.get("yaxis", "y1")
                raw_legend = settings.get("legend", column)
                legend_visible = bool(str(raw_legend).strip())
                legend_label = str(raw_legend) if legend_visible else column
                any_legend_visible = any_legend_visible or legend_visible
                yaxis = "y2" if yaxis_side == "y2" else "y"
                raw_y = np.asarray(y_data, dtype=float)
                y_columns = source.dataframe_dict()
                converted_y = self.column_transform(settings, tuple(y_columns)).apply(raw_y, y_columns)
                debug_print(f"GraphCanvas._build_figure conversion column={column} conversion={settings.get('conversion', 'as-is')}")
                debug_print(f"GraphCanvas._build_figure raw_y_sample={raw_y[:3].tolist()}")
                debug_print(f"GraphCanvas._build_figure converted_y_sample={converted_y[:3].tolist()}")
                plotted_x_values.extend(float(value) for value in x_data if np.isfinite(value))
                color = settings.get("color") or PlotStyle.series_color(color_index)
                self._add_series_traces(
                    figure,
                    x_data=x_data,
                    y_data=converted_y,
                    trace_mode=trace_mode,
                    line_style=line_style,
                    legend_label=legend_label,
                    legend_visible=legend_visible,
                    yaxis=yaxis,
                    color=color,
                    series_index=color_index,
                )
                color_index += 1
                self._last_trace_count += 1
                debug_print(f"GraphCanvas._build_figure added trace={legend_label} yaxis={yaxis}")

        figure.update_layout(
            height=_GRAPH_HEIGHT,
            width=self._graph_width,
            margin=dict(l=82, r=right_margin, t=70, b=80),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            showlegend=show_legend and any_legend_visible,
            legend=self._legend_config(legend_position),
            xaxis=dict(
                title=dict(text=state.get("x_axis_title") or x_axis_column or "Time", font=PlotStyle.graph_axis_title_font()),
                showgrid=show_grid,
                showline=True,
                linecolor="#111111",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickfont=PlotStyle.graph_tick_font(),
            ),
            yaxis=dict(
                title=dict(text=state.get("yaxis1_title") or state.get("y_axis_title") or "Y1", font=PlotStyle.graph_axis_title_font()),
                showgrid=show_grid,
                showline=True,
                linecolor="#111111",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickfont=PlotStyle.graph_tick_font(),
            ),
            yaxis2=dict(
                title=dict(text=state.get("yaxis2_title") or "Y2", font=PlotStyle.graph_axis_title_font()),
                overlaying="y",
                side="right",
                showgrid=False,
                showline=True,
                linecolor="#111111",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickfont=PlotStyle.graph_tick_font(),
            ),
        )
        self._apply_publication_axis_styling(figure, state)
        if trace_mode == "lines":
            x_range = self._padded_axis_range(plotted_x_values)
            if x_range is not None:
                figure.layout.xaxis.range = x_range
                figure.layout.xaxis.autorange = False
        if self._last_trace_count == 0:
            debug_print("GraphCanvas._build_figure no traces after processing")
            figure.add_annotation(
                text="Select Y columns to display the graph",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=PlotStyle.empty_annotation_font(),
            )
        return figure

    def _padded_axis_range(self, values: list[float]) -> list[float] | None:
        finite_values = [float(value) for value in values if np.isfinite(value)]
        if not finite_values:
            return None
        minimum = min(finite_values)
        maximum = max(finite_values)
        span = maximum - minimum
        if span == 0:
            padding = abs(minimum) * 0.05 or 1.0
        else:
            padding = span * 0.05
        return [minimum - padding, maximum + padding]

    def _add_series_traces(
        self,
        figure: go.Figure,
        *,
        x_data: np.ndarray,
        y_data: np.ndarray,
        trace_mode: str,
        line_style: str,
        legend_label: str,
        legend_visible: bool,
        yaxis: str,
        color: str,
        series_index: int,
    ) -> None:
        debug_print(f"GraphCanvas._add_series_traces mode={trace_mode}")
        x_values = np.asarray(x_data).tolist()
        y_values = np.asarray(y_data).tolist()
        if trace_mode == "lines+markers":
            marker_indices = PlotStyle.marker_sample_indices(len(x_values))
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines",
                    name=legend_label,
                    showlegend=legend_visible,
                    yaxis=yaxis,
                    line=PlotStyle.trace_line(color=color, dash=line_style),
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=[x_values[index] for index in marker_indices],
                    y=[y_values[index] for index in marker_indices],
                    mode="markers",
                    name=legend_label,
                    yaxis=yaxis,
                    showlegend=False,
                    marker=PlotStyle.marker_style(series_index, color=color),
                )
            )
            return
        marker_indices = (
            PlotStyle.marker_sample_indices(len(x_values))
            if trace_mode == "markers"
            else list(range(len(x_values)))
        )
        figure.add_trace(
            go.Scatter(
                x=[x_values[index] for index in marker_indices],
                y=[y_values[index] for index in marker_indices],
                mode=trace_mode,
                name=legend_label,
                showlegend=legend_visible,
                yaxis=yaxis,
                line=PlotStyle.trace_line(color=color, dash=line_style),
                marker=PlotStyle.marker_style(series_index, color=color),
            )
        )

    def _apply_publication_axis_styling(self, figure: go.Figure, state: dict[str, Any]) -> go.Figure:
        debug_print("GraphCanvas._apply_publication_axis_styling start")
        show_grid = bool(state.get("show_grid", True))
        debug_print(f"GraphCanvas._apply_publication_axis_styling show_grid={show_grid}")
        x_title = state.get("x_axis_title") or self._axis_title_text(figure.layout.xaxis, "Time")
        debug_print(f"GraphCanvas._apply_publication_axis_styling x_title={x_title}")
        y1_title = state.get("yaxis1_title") or state.get("y_axis_title") or self._axis_title_text(figure.layout.yaxis, "Y1")
        debug_print(f"GraphCanvas._apply_publication_axis_styling y1_title={y1_title}")
        y2_title = state.get("yaxis2_title") or self._axis_title_text(figure.layout.yaxis2, "Y2")
        debug_print(f"GraphCanvas._apply_publication_axis_styling y2_title={y2_title}")
        figure.update_layout(
            xaxis=self._publication_axis_config(x_title, show_grid),
            yaxis=self._publication_axis_config(y1_title, show_grid),
            yaxis2=dict(
                **self._publication_axis_config(y2_title, show_grid),
                overlaying="y",
                side="right",
            ),
        )
        debug_print("GraphCanvas._apply_publication_axis_styling complete")
        return figure

    def _axis_title_text(self, axis: Any, fallback: str) -> str:
        debug_print(f"GraphCanvas._axis_title_text fallback={fallback}")
        title = getattr(axis, "title", None)
        debug_print(f"GraphCanvas._axis_title_text title={title}")
        text = getattr(title, "text", None)
        debug_print(f"GraphCanvas._axis_title_text text={text}")
        return text or fallback

    def _publication_axis_config(self, title: str, show_grid: bool) -> dict[str, Any]:
        debug_print(f"GraphCanvas._publication_axis_config title={title} show_grid={show_grid}")
        config = PlotStyle.graph_axis(title, show_grid)
        debug_print("GraphCanvas._publication_axis_config complete")
        return config

    @staticmethod
    def column_transform(settings: dict, column_names=()) -> units.Transform:
        """The conversion of one Y column: its target (or custom factor/offset) from its source unit."""
        return units.resolve_transform(
            settings.get("conversion", "as-is"),
            source_unit=settings.get("source_unit", ""),
            factor=settings.get("factor"),
            offset=settings.get("offset"),
            custom_unit=settings.get("custom_unit", ""),
            formula=settings.get("formula", ""),
            column_names=column_names,
        )

    @staticmethod
    def x_transform(state: dict, column_names=()) -> units.Transform:
        """The conversion of the X axis column."""
        return units.resolve_transform(
            state.get("x_axis_conversion", "as-is"),
            source_unit=state.get("x_axis_source_unit", ""),
            factor=state.get("x_axis_factor"),
            offset=state.get("x_axis_offset"),
            custom_unit=state.get("x_axis_custom_unit", ""),
            formula=state.get("x_axis_formula", ""),
            column_names=column_names,
        )

    def _apply_conversion(self, values: np.ndarray, conversion: str | None) -> np.ndarray:
        return units.resolve_transform(conversion).apply(values)

    def _apply_x_conversion(self, values: np.ndarray, conversion: str | None) -> np.ndarray:
        return units.resolve_transform(conversion).apply(values)

    def _conversion_multiplier(self, conversion: str) -> float:
        """Factor of a conversion when no source unit is known (legacy keys assume Pa / fraction / s)."""
        return units.resolve_transform(conversion).a

    def _x_conversion_multiplier(self, conversion: str) -> float:
        return units.resolve_transform(conversion).a

    def _normalize_conversion(self, conversion: str | None) -> str:
        return units.normalize_conversion(conversion)

    def _normalize_x_conversion(self, conversion: str | None) -> str:
        return units.normalize_conversion(conversion)

    def _legend_config(self, position: str) -> dict[str, Any]:
        debug_print(f"GraphCanvas._legend_config position={position}")
        configs = {
            "top-left": dict(x=0.02, y=0.98, xanchor="left", yanchor="top"),
            "middle-top": dict(x=0.5, y=0.98, xanchor="center", yanchor="top"),
            "top-right": dict(x=0.98, y=0.98, xanchor="right", yanchor="top"),
            "middle-left": dict(x=0.02, y=0.5, xanchor="left", yanchor="middle"),
            "middle-right": dict(x=0.98, y=0.5, xanchor="right", yanchor="middle"),
            "bottom-left": dict(x=0.02, y=0.02, xanchor="left", yanchor="bottom"),
            "middle-bottom": dict(x=0.5, y=0.02, xanchor="center", yanchor="bottom"),
            "bottom-right": dict(x=0.98, y=0.02, xanchor="right", yanchor="bottom"),
            "right-outside": dict(x=1.02, y=1.0, xanchor="left", yanchor="top"),
        }
        selected = configs.get(position, configs["top-left"])
        debug_print(f"GraphCanvas._legend_config selected={selected}")
        legend = PlotStyle.graph_legend(**selected)
        debug_print(f"GraphCanvas._legend_config resolved={legend}")
        return legend

    def _empty_figure(self, message: str) -> go.Figure:
        debug_print(f"GraphCanvas._empty_figure message={message}")
        figure = go.Figure()
        figure.add_annotation(
            text=message,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=PlotStyle.empty_annotation_font(),
        )
        figure.update_layout(
            width=self._graph_width,
            height=_GRAPH_HEIGHT,
            margin=dict(l=82, r=82, t=70, b=80),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
        )
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        debug_print(f"GraphCanvas._build_html size width={self._graph_width} height={_GRAPH_HEIGHT}")
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>{_GREEK_FONT_FACE}html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;display:flex;align-items:flex-start;justify-content:center;}}#graph{{width:{self._graph_width}px;height:{_GRAPH_HEIGHT}px;}}</style>
<script src="plotly.min.js"></script>
</head><body>
<div id="graph"></div>
<script>
var fig = {figure_json};
Plotly.newPlot('graph', fig.data, fig.layout, {{displayModeBar:true, responsive:true}});
</script>
</body></html>"""

    def _empty_html(self) -> str:
        return "<!DOCTYPE html><html><body style='margin:0;background:white;'></body></html>"
