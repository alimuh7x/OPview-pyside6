"""Plotly-backed phase-fraction history canvas."""

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

_W = 680
_H = 400
_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


class PhaseFractionHistoryCanvas(QWidget):
    """Render total phase-fraction percentages over timestep."""

    def __init__(self) -> None:
        debug_print("PhaseFractionHistoryCanvas.__init__ start")
        super().__init__()
        self._canvas_width = _W
        self._last_payload = {
            "series": [],
            "current_step": None,
            "x_label": "Timestep",
            "y_label": "Phase fraction (%)",
        }
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        install_save_dialog_download_handler(
            self._web_view,
            self,
            fallback_name="phase_fraction_history.png",
        )
        self._web_view.setFixedSize(_W, _H)
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        debug_print("PhaseFractionHistoryCanvas canvas height=400")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)
        self.setFixedSize(_W, _H)
        self.render_placeholder("No phase-fraction history")
        debug_print("PhaseFractionHistoryCanvas.__init__ complete")

    def set_available_width(self, width: int) -> None:
        debug_print(f"PhaseFractionHistoryCanvas.set_available_width width={width}")
        self._canvas_width = max(240, min(_W, int(width)))
        self._web_view.setFixedSize(self._canvas_width, _H)
        self.setFixedSize(self._canvas_width, _H)
        debug_print(f"PhaseFractionHistoryCanvas canvas width={self._canvas_width}")

    def render_placeholder(self, message: str) -> None:
        debug_print("PhaseFractionHistoryCanvas.render_placeholder called")
        debug_print(f"PhaseFractionHistoryCanvas placeholder message={message}")
        self._last_payload = {
            "series": [],
            "current_step": None,
            "x_label": "Timestep",
            "y_label": "Phase fraction (%)",
        }
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
            margin=dict(l=74, r=20, t=28, b=58),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            xaxis=PlotStyle.panel_axis("Timestep", True),
            yaxis=PlotStyle.panel_axis("Phase fraction (%)", True),
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("PhaseFractionHistoryCanvas placeholder rendered")

    def render_phase_fraction_history(
        self,
        series: list[dict],
        *,
        current_step: float | None,
        x_label: str = "Timestep",
        hover_x_label: str = "timestep",
    ) -> None:
        debug_print("PhaseFractionHistoryCanvas.render_phase_fraction_history called")
        debug_print(f"PhaseFractionHistoryCanvas series count={len(series)}")
        debug_print(f"PhaseFractionHistoryCanvas current_step={current_step}")
        debug_print(f"PhaseFractionHistoryCanvas x_label={x_label}")
        self._last_payload = {
            "series": [
                {
                    "label": item.get("label", ""),
                    "steps": list(item.get("steps", [])),
                    "values": list(item.get("values", [])),
                    "color": item.get("color"),
                }
                for item in series
            ],
            "current_step": current_step,
            "x_label": x_label,
            "y_label": "Phase fraction (%)",
        }
        figure = self._build_figure(
            series,
            current_step=current_step,
            x_label=x_label,
            hover_x_label=hover_x_label,
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("PhaseFractionHistoryCanvas graph rendered")

    def _build_figure(
        self,
        series: list[dict],
        *,
        current_step: float | None,
        x_label: str = "Timestep",
        hover_x_label: str = "timestep",
    ) -> go.Figure:
        debug_print("PhaseFractionHistoryCanvas._build_figure called")
        debug_print(f"PhaseFractionHistoryCanvas figure x_label={x_label}")
        figure = go.Figure()
        added = 0
        for index, item in enumerate(series):
            steps_arr = np.asarray(item.get("steps", []), dtype=float)
            values_arr = np.asarray(item.get("values", []), dtype=float)
            debug_print(f"PhaseFractionHistoryCanvas building trace index={index}")
            debug_print(f"PhaseFractionHistoryCanvas trace label={item.get('label')}")
            debug_print(f"PhaseFractionHistoryCanvas raw count={values_arr.size}")
            if steps_arr.size != values_arr.size:
                debug_print("PhaseFractionHistoryCanvas skipped mismatched trace")
                continue
            finite = np.isfinite(values_arr)
            debug_print(f"PhaseFractionHistoryCanvas finite count={int(np.count_nonzero(finite))}")
            if not np.any(finite):
                continue
            color = item.get("color") or None
            figure.add_trace(
                go.Scatter(
                    x=steps_arr[finite].tolist(),
                    y=values_arr[finite].tolist(),
                    mode="lines+markers",
                    name=item.get("label", f"Phase {index}"),
                    line=PlotStyle.trace_line(color=color),
                    marker=dict(size=5, color=color),
                    hovertemplate=f"{hover_x_label}=%{{x:.6g}}<br>phase=%{{y:.3f}}%<extra></extra>",
                    showlegend=True,
                )
            )
            added += 1
        if current_step is not None:
            debug_print("PhaseFractionHistoryCanvas adding current-step marker")
            figure.add_vline(
                x=float(current_step),
                line_width=2,
                line_dash="dash",
                line_color="#1f2937",
            )
        if added == 0:
            debug_print("PhaseFractionHistoryCanvas no finite values")
            figure.add_annotation(
                text="No finite phase-fraction values",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=PlotStyle.empty_annotation_font(),
            )
        debug_print("PhaseFractionHistoryCanvas legend columns target=3")
        debug_print("PhaseFractionHistoryCanvas legend anchor=right")
        debug_print("PhaseFractionHistoryCanvas legend entrywidth=0.33 fraction")
        debug_print("PhaseFractionHistoryCanvas legend y=1.02")
        debug_print("PhaseFractionHistoryCanvas top margin=108")
        figure.update_layout(
            width=self._canvas_width,
            height=_H,
            margin=dict(l=74, r=20, t=108, b=58),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            legend=PlotStyle.panel_legend(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                entrywidthmode="fraction",
                entrywidth=0.33,
            ),
            xaxis=PlotStyle.panel_axis(x_label, True),
            yaxis=PlotStyle.panel_axis("Phase fraction (%)", True),
        )
        figure.update_yaxes(range=[0, 100])
        debug_print("PhaseFractionHistoryCanvas._build_figure complete")
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        debug_print("PhaseFractionHistoryCanvas._build_html called")
        debug_print("PhaseFractionHistoryCanvas modebar top offset=0px")
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"/>
<style>
html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;}}
.modebar{{top: 0px !important;}}
</style>
<script src=\"plotly.min.js\"></script>
</head><body>
<div id=\"div\"></div>
<script>
var fig = {figure_json};
Plotly.newPlot('div', fig.data, fig.layout, {{displayModeBar:true, responsive:false}});
</script>
</body></html>"""
