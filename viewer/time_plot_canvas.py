"""Plotly-backed Plot Over Time canvas."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print
from utils.webengine_downloads import install_save_dialog_download_handler
from viewer.plot_style import PlotStyle

_W = 600
_H = 300
_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


class TimePlotCanvas(QWidget):
    """Render one local point value over timestep using Plotly."""

    def __init__(self) -> None:
        debug_print("TimePlotCanvas.__init__ start")
        super().__init__()
        self._canvas_width = _W
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        install_save_dialog_download_handler(
            self._web_view,
            self,
            fallback_name="plot_over_time.png",
        )
        self._web_view.setFixedSize(_W, _H)
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)
        self.setFixedSize(_W, _H)
        self.render_placeholder("Add a point to plot value over time")
        debug_print("TimePlotCanvas.__init__ complete")

    def set_available_width(self, width: int) -> None:
        debug_print(f"TimePlotCanvas.set_available_width width={width}")
        self._canvas_width = max(240, min(_W, int(width)))
        self._web_view.setFixedSize(self._canvas_width, _H)
        self.setFixedSize(self._canvas_width, _H)
        debug_print(f"TimePlotCanvas canvas width={self._canvas_width}")

    def render_placeholder(self, message: str) -> None:
        debug_print("TimePlotCanvas.render_placeholder called")
        debug_print(f"TimePlotCanvas placeholder message={message}")
        figure = go.Figure()
        figure.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=PlotStyle.empty_annotation_font(),
        )
        figure.update_layout(
            width=self._canvas_width,
            height=_H,
            margin=dict(l=80, r=20, t=30, b=70),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            xaxis=PlotStyle.panel_axis("Time Step", True),
            yaxis=PlotStyle.panel_axis("Value", True),
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("TimePlotCanvas placeholder rendered")

    def render_time_plot(self, steps, values, *, y_label: str, point_label: str) -> None:
        debug_print("TimePlotCanvas.render_time_plot called")
        self.render_time_series(
            [{"label": point_label, "steps": steps, "values": values}],
            y_label=y_label,
        )
        debug_print("TimePlotCanvas.render_time_plot complete")

    def render_time_series(self, series, *, y_label: str) -> None:
        """Render multiple point-history series."""
        debug_print("TimePlotCanvas.render_time_series called")
        debug_print(f"TimePlotCanvas series count={len(series)}")
        figure = self._build_time_plot_figure(series, y_label=y_label)
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("TimePlotCanvas.render_time_series complete")

    def _build_time_plot_figure(self, series, *, y_label: str) -> go.Figure:
        """Build a Plotly figure for one or more point-history series."""
        debug_print("TimePlotCanvas._build_time_plot_figure called")
        figure = go.Figure()
        colors = ["#c50623", "#183568", "#0f9ca6", "#f0a202", "#7b2cbf", "#2d6a4f"]
        added = 0
        for index, item in enumerate(series):
            steps_arr = np.asarray(item.get("steps", []), dtype=float)
            values_arr = np.asarray(item.get("values", []), dtype=float)
            if steps_arr.size != values_arr.size:
                debug_print(f"TimePlotCanvas skipped mismatched series index={index}")
                continue
            finite = ~np.isnan(values_arr)
            debug_print(f"TimePlotCanvas series index={index}")
            debug_print(f"TimePlotCanvas raw points={values_arr.size}")
            debug_print(f"TimePlotCanvas finite points={int(np.count_nonzero(finite))}")
            if not np.any(finite):
                continue
            figure.add_trace(
                go.Scatter(
                    x=steps_arr[finite].tolist(),
                    y=values_arr[finite].tolist(),
                    mode="lines+markers",
                    name=item.get("label", f"P{index + 1}"),
                    line=PlotStyle.trace_line(color=colors[index % len(colors)]),
                    marker=dict(size=6, color=colors[index % len(colors)]),
                    hovertemplate="step=%{x:.0f}<br>value=%{y:.6g}<extra></extra>",
                    showlegend=True,
                )
            )
            added += 1
        if added == 0:
            debug_print("TimePlotCanvas no finite values")
            figure.add_annotation(
                text="No finite point-history values",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=PlotStyle.empty_annotation_font(),
            )
        figure.update_layout(
            width=self._canvas_width,
            height=_H,
            margin=dict(l=80, r=20, t=30, b=70),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            legend=PlotStyle.panel_legend(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
            ),
            xaxis=PlotStyle.panel_axis("Time Step", True),
            yaxis=PlotStyle.panel_axis(y_label or "Value", True),
        )
        debug_print("TimePlotCanvas._build_time_plot_figure complete")
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"/>
<style>html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;}}</style>
<script src=\"plotly.min.js\"></script>
</head><body>
<div id=\"div\"></div>
<script>
var fig = {figure_json};
Plotly.newPlot('div', fig.data, fig.layout, {{displayModeBar:true, responsive:false}});
</script>
</body></html>"""
