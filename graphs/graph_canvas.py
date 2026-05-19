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
from data.text_sources import GenericTextDataSource

_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_GRAPH_WIDTH = 800
_GRAPH_HEIGHT = 620


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
        colors = ["#111111", "#d62728", "#2ca02c", "#1f77b4", "#9467bd", "#ff7f0e"]
        figure = go.Figure()
        self._last_trace_count = 0

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
        x_conversion = state.get("x_axis_conversion", "as-is")
        x_multiplier = self._x_conversion_multiplier(x_conversion)
        x_data = raw_x * x_multiplier
        debug_print(f"GraphCanvas._build_figure x_axis_column={x_axis_column} points={len(x_data)}")
        debug_print(f"GraphCanvas._build_figure x_conversion={x_conversion} multiplier={x_multiplier}")
        debug_print(f"GraphCanvas._build_figure raw_x_sample={raw_x[:3].tolist()}")
        debug_print(f"GraphCanvas._build_figure converted_x_sample={x_data[:3].tolist()}")

        color_index = 0
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
                legend_label = settings.get("legend", column) or column
                conversion = settings.get("conversion", "as-is")
                multiplier = self._conversion_multiplier(conversion)
                yaxis = "y2" if yaxis_side == "y2" else "y"
                raw_y = np.asarray(y_data, dtype=float)
                converted_y = raw_y * multiplier
                debug_print(
                    f"GraphCanvas._build_figure conversion column={column} conversion={conversion} multiplier={multiplier}"
                )
                debug_print(f"GraphCanvas._build_figure raw_y_sample={raw_y[:3].tolist()}")
                debug_print(f"GraphCanvas._build_figure converted_y_sample={converted_y[:3].tolist()}")
                figure.add_trace(
                    go.Scatter(
                        x=x_data.tolist(),
                        y=converted_y.tolist(),
                        mode=trace_mode,
                        name=legend_label,
                        yaxis=yaxis,
                        line=dict(color=colors[color_index % len(colors)], dash=line_style, width=2),
                        marker=dict(size=6),
                    )
                )
                color_index += 1
                self._last_trace_count += 1
                debug_print(f"GraphCanvas._build_figure added trace={legend_label} yaxis={yaxis}")

        figure.update_layout(
            height=_GRAPH_HEIGHT,
            width=self._graph_width,
            margin=dict(l=82, r=82, t=26, b=70),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#102a52", size=16),
            showlegend=show_legend,
            legend=self._legend_config(state.get("legend_position", "top-left")),
            xaxis=dict(
                title=dict(text=state.get("x_axis_title") or x_axis_column or "Time", font=dict(color="#102a52", size=20)),
                showgrid=show_grid,
                showline=True,
                linecolor="#111111",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickfont=dict(color="#102a52", size=16),
            ),
            yaxis=dict(
                title=dict(text=state.get("yaxis1_title") or state.get("y_axis_title") or "Y1", font=dict(color="#102a52", size=20)),
                showgrid=show_grid,
                showline=True,
                linecolor="#111111",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickfont=dict(color="#102a52", size=16),
            ),
            yaxis2=dict(
                title=dict(text=state.get("yaxis2_title") or "Y2", font=dict(color="#102a52", size=20)),
                overlaying="y",
                side="right",
                showgrid=False,
                showline=True,
                linecolor="#111111",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickfont=dict(color="#102a52", size=16),
            ),
        )
        self._apply_publication_axis_styling(figure, state)
        if self._last_trace_count == 0:
            debug_print("GraphCanvas._build_figure no traces after processing")
            figure.add_annotation(text="Select Y columns to display the graph", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        return figure

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
        config = dict(
            title=dict(text=title, font=dict(size=24, family="Arial")),
            tickfont=dict(size=22, family="Arial"),
            showgrid=show_grid,
            gridcolor="rgba(128, 128, 128, 0.2)",
            mirror="allticks",
            ticks="inside",
            ticklen=10,
            tickwidth=2.5,
            tickcolor="black",
            minor=dict(
                ticks="inside",
                ticklen=6,
                tickwidth=1.5,
                tickcolor="black",
                showgrid=False,
            ),
            linecolor="black",
            linewidth=2.5,
            showline=True,
        )
        debug_print("GraphCanvas._publication_axis_config complete")
        return config

    def _conversion_multiplier(self, conversion: str) -> float:
        debug_print(f"GraphCanvas._conversion_multiplier conversion={conversion}")
        normalized = self._normalize_conversion(conversion)
        debug_print(f"GraphCanvas._conversion_multiplier normalized={normalized}")
        multipliers = {
            "as-is": 1.0,
            "percent": 100.0,
            "mpa": 1e-6,
            "gpa": 1e-9,
        }
        multiplier = multipliers.get(normalized, 1.0)
        debug_print(f"GraphCanvas._conversion_multiplier multiplier={multiplier}")
        return multiplier

    def _x_conversion_multiplier(self, conversion: str) -> float:
        debug_print(f"GraphCanvas._x_conversion_multiplier conversion={conversion}")
        normalized = self._normalize_x_conversion(conversion)
        debug_print(f"GraphCanvas._x_conversion_multiplier normalized={normalized}")
        multipliers = {
            "as-is": 1.0,
            "sec-to-min": 1.0 / 60.0,
            "sec-to-hour": 1.0 / 3600.0,
        }
        multiplier = multipliers.get(normalized, 1.0)
        debug_print(f"GraphCanvas._x_conversion_multiplier multiplier={multiplier}")
        return multiplier

    def _normalize_x_conversion(self, conversion: str | None) -> str:
        debug_print(f"GraphCanvas._normalize_x_conversion conversion={conversion}")
        value = str(conversion or "as-is").strip().lower()
        debug_print(f"GraphCanvas._normalize_x_conversion value={value}")
        aliases = {
            "": "as-is",
            "as is": "as-is",
            "as-is": "as-is",
            "raw": "as-is",
            "sec": "as-is",
            "s": "as-is",
            "seconds": "as-is",
            "sec -> min": "sec-to-min",
            "sec-to-min": "sec-to-min",
            "seconds to minutes": "sec-to-min",
            "min": "sec-to-min",
            "minutes": "sec-to-min",
            "sec -> hour": "sec-to-hour",
            "sec-to-hour": "sec-to-hour",
            "seconds to hours": "sec-to-hour",
            "hour": "sec-to-hour",
            "hours": "sec-to-hour",
        }
        normalized = aliases.get(value, "as-is")
        debug_print(f"GraphCanvas._normalize_x_conversion normalized={normalized}")
        return normalized

    def _normalize_conversion(self, conversion: str | None) -> str:
        debug_print(f"GraphCanvas._normalize_conversion conversion={conversion}")
        value = str(conversion or "as-is").strip().lower()
        debug_print(f"GraphCanvas._normalize_conversion value={value}")
        aliases = {
            "": "as-is",
            "as is": "as-is",
            "as-is": "as-is",
            "raw": "as-is",
            "%": "percent",
            "percent": "percent",
            "percentage": "percent",
            "mpa": "mpa",
            "gpa": "gpa",
        }
        normalized = aliases.get(value, "as-is")
        debug_print(f"GraphCanvas._normalize_conversion normalized={normalized}")
        return normalized

    def _legend_config(self, position: str) -> dict[str, Any]:
        debug_print(f"GraphCanvas._legend_config position={position}")
        configs = {
            "top-left": dict(x=0.02, y=0.98, xanchor="left", yanchor="top"),
            "top-right": dict(x=0.98, y=0.98, xanchor="right", yanchor="top"),
            "bottom-left": dict(x=0.02, y=0.02, xanchor="left", yanchor="bottom"),
            "bottom-right": dict(x=0.98, y=0.02, xanchor="right", yanchor="bottom"),
        }
        return configs.get(position, configs["top-left"])

    def _empty_figure(self, message: str) -> go.Figure:
        debug_print(f"GraphCanvas._empty_figure message={message}")
        figure = go.Figure()
        figure.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        figure.update_layout(
            width=self._graph_width,
            height=_GRAPH_HEIGHT,
            margin=dict(l=82, r=82, t=26, b=70),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#102a52", size=16),
        )
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        debug_print(f"GraphCanvas._build_html size width={self._graph_width} height={_GRAPH_HEIGHT}")
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;display:flex;align-items:flex-start;justify-content:center;}}#graph{{width:{self._graph_width}px;height:{_GRAPH_HEIGHT}px;}}</style>
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
