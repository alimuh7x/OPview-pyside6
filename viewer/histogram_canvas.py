"""Plotly-backed histogram canvas."""

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


class HistogramCanvas(QWidget):
    """Render histogram data using Plotly."""

    def __init__(self) -> None:
        debug_print("HistogramCanvas.__init__ start")
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
        debug_print("HistogramCanvas.__init__ complete")

    def render_histogram(self, values, *, label: str, bins: int) -> None:
        debug_print("HistogramCanvas.render_histogram called")
        data = np.asarray(values).flatten()
        data = data[~np.isnan(data)]

        figure = go.Figure()

        if data.size == 0:
            figure.add_annotation(
                text="No finite data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="#6a7e9f"),
            )
        else:
            data_min = float(np.min(data))
            data_max = float(np.max(data))
            data_range = data_max - data_min
            tolerance = max(1e-12, abs(data_max) * 1e-12)

            if data_range <= tolerance:
                # Near-constant data — pad symmetrically relative to value magnitude
                pad = max(abs(data_max) * 0.1, 1e-10)
                bin_start = data_min - pad
                bin_end   = data_max + pad
                bin_size  = (bin_end - bin_start)
            else:
                safe_bins = max(1, int(bins))
                bin_size  = data_range / safe_bins
                bin_start = data_min
                bin_end   = data_max + bin_size  # ensure last bin included

            figure.add_trace(go.Histogram(
                x=data.tolist(),
                xbins=dict(start=bin_start, end=bin_end, size=bin_size),
                marker_color="#183568",
                opacity=0.9,
                hovertemplate="value=%{x:.4g}<br>count=%{y}<extra></extra>",
            ))

        figure.update_layout(
            width=_W,
            height=_H,
            margin=dict(l=54, r=16, t=16, b=44),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                title=dict(text=label, font=dict(size=15, color="#000000")),
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
                title=dict(text="Frequency", font=dict(size=15, color="#000000")),
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
            bargap=0.05,
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("HistogramCanvas render complete")

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
