"""Plotly-backed line scan canvas."""

from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print

_W = 600
_H = 300
_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


class LineScanCanvas(QWidget):
    """Render line scan data using Plotly."""

    def __init__(self) -> None:
        debug_print("LineScanCanvas.__init__ start")
        super().__init__()
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

    def render_line(self, x_data, z_data, *, title: str, x_label: str, y_label: str) -> None:
        debug_print("LineScanCanvas.render_line called")
        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=np.asarray(x_data).tolist(),
            y=np.asarray(z_data).tolist(),
            mode="lines",
            line=dict(color="#c50623", width=2),
            hovertemplate=f"{x_label}=%{{x:.4f}}<br>{y_label}=%{{y:.4f}}<extra></extra>",
        ))
        figure.update_layout(
            width=_W,
            height=_H,
            margin=dict(l=54, r=16, t=16, b=44),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                title=dict(text=x_label, font=dict(size=15, color="#000000")),
                tickfont=dict(size=14, color="#000000"),
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor="#000000",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickcolor="#000000",
                minor=dict(ticks="inside", ticklen=4, showgrid=False),
            ),
            yaxis=dict(
                title=dict(text=y_label, font=dict(size=15, color="#000000")),
                tickfont=dict(size=14, color="#000000"),
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor="#000000",
                linewidth=2,
                mirror=True,
                ticks="inside",
                ticklen=8,
                tickcolor="#000000",
                minor=dict(ticks="inside", ticklen=4, showgrid=False),
            ),
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("LineScanCanvas render complete")

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
Plotly.newPlot('div', fig.data, fig.layout, {{displayModeBar:false, responsive:false}});
</script>
</body></html>"""

    def _empty_html(self) -> str:
        return "<!DOCTYPE html><html><body style='margin:0;background:white;'></body></html>"
