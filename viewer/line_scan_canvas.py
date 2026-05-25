"""Plotly-backed line scan canvas."""

from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print
from viewer.plot_style import PlotStyle

_W = 600
_H = 300
_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


class LineScanCanvas(QWidget):
    """Render line scan data using Plotly."""

    def __init__(self) -> None:
        debug_print("LineScanCanvas.__init__ start")
        super().__init__()
        self._canvas_width = _W
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        self._web_view.setFixedSize(_W, _H)
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)
        self.setFixedSize(_W, _H)
        self._web_view.setHtml(self._empty_html(), self._base_url)
        debug_print("LineScanCanvas.__init__ complete")

    def set_available_width(self, width: int) -> None:
        debug_print(f"LineScanCanvas.set_available_width width={width}")
        self._canvas_width = max(240, min(_W, int(width)))
        self._web_view.setFixedSize(self._canvas_width, _H)
        self.setFixedSize(self._canvas_width, _H)
        debug_print(f"LineScanCanvas canvas width={self._canvas_width}")

    def render_line(self, x_data, z_data, *, title: str, x_label: str, y_label: str) -> None:
        debug_print("LineScanCanvas.render_line called")
        debug_print("LineScanCanvas delegating single trace to render_lines")
        self.render_lines(
            [{"name": "", "x": x_data, "y": z_data}],
            title=title,
            x_label=x_label,
            y_label=y_label,
        )
        debug_print("LineScanCanvas.render_line complete")

    def render_lines(self, series, *, title: str, x_label: str, y_label: str, show_grid: bool = True) -> None:
        debug_print("LineScanCanvas.render_lines called")
        debug_print(f"LineScanCanvas series count={len(series)}")
        figure = go.Figure()
        colors = ["#c50623", "#183568", "#0f9ca6", "#f0a202", "#7b2cbf", "#2d6a4f"]
        if not series:
            debug_print("LineScanCanvas no series, adding annotation")
            figure.add_annotation(
                text="No line scan data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=PlotStyle.empty_annotation_font(),
            )
        for index, item in enumerate(series):
            name = item.get("name", "")
            debug_print(f"LineScanCanvas adding series index={index}")
            debug_print(f"LineScanCanvas adding series name={name}")
            figure.add_trace(go.Scatter(
                x=np.asarray(item.get("x", [])).tolist(),
                y=np.asarray(item.get("y", [])).tolist(),
                mode="lines",
                name=name,
                line=PlotStyle.trace_line(color=colors[index % len(colors)]),
                hovertemplate=(
                    f"{x_label}=%{{x:.4f}}<br>"
                    f"{y_label}=%{{y:.4f}}<br>"
                    "%{fullData.name}<extra></extra>"
                ),
                showlegend=bool(name),
            ))
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
            xaxis=PlotStyle.panel_axis(x_label, show_grid),
            yaxis=PlotStyle.panel_axis(y_label, show_grid),
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("LineScanCanvas.render_lines complete")

    def _build_html(self, figure: go.Figure) -> str:
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;}}</style>
<script src="plotly.min.js"></script>
</head><body>
<div id="div"></div>
<script>
var fig = {figure_json};
Plotly.newPlot('div', fig.data, fig.layout, {{displayModeBar:true, responsive:false}});
</script>
</body></html>"""

    def _empty_html(self) -> str:
        return "<!DOCTYPE html><html><body style='margin:0;background:white;'></body></html>"
