"""Standalone Plotly colorbar widget for Multi View."""

from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.debug import debug_print
from viewer.colorscale import cmap_to_plotly_scale

_PLOTLY_JS = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_W = 140
_H = 420


class ColorbarCanvas(QWidget):
    """Renders only a Plotly colorbar — no heatmap data visible."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        debug_print("MultiView ColorbarCanvas.__init__ start")
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS.parent.resolve()) + "/")
        debug_print(f"MultiView ColorbarCanvas base_url={self._base_url.toString()}")
        self._web = QWebEngineView(self)
        debug_print("MultiView ColorbarCanvas web view created")
        self._web.setFixedSize(_W, _H)
        self._web.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web)
        self.setFixedSize(_W, _H)
        self._web.setHtml(
            "<!DOCTYPE html><html><body style='margin:0;background:white;'></body></html>",
            self._base_url,
        )
        debug_print("MultiView ColorbarCanvas.__init__ complete")

    def update_colorbar(
        self,
        cmap,
        vmin: float,
        vmax: float,
        label: str = "",
    ) -> None:
        debug_print("MultiView ColorbarCanvas.update_colorbar called")
        debug_print(f"MultiView ColorbarCanvas vmin={vmin}")
        debug_print(f"MultiView ColorbarCanvas vmax={vmax}")
        debug_print(f"MultiView ColorbarCanvas label={label}")
        colorscale = cmap_to_plotly_scale(cmap)
        debug_print(f"MultiView ColorbarCanvas colorscale stops={len(colorscale)}")

        def fmt(v: float) -> str:
            import math
            if v == 0:
                return "0"
            try:
                mag = math.floor(math.log10(abs(v)))
            except ValueError:
                return "0"
            if -3 <= mag <= 4:
                return f"{v:.{max(0, 3 - int(mag))}f}"
            return f"{v:.2e}"

        tick_vals = [
            vmin,
            vmin + (vmax - vmin) * 0.25,
            vmin + (vmax - vmin) * 0.5,
            vmin + (vmax - vmin) * 0.75,
            vmax,
        ]

        figure = go.Figure()
        debug_print("MultiView ColorbarCanvas adding invisible scale trace")
        figure.add_trace(go.Heatmap(
            z=[[vmin, vmax]],
            colorscale=colorscale,
            zmin=vmin,
            zmax=vmax,
            showscale=True,
            opacity=0.0,
            colorbar=dict(
                x=0.04,
                xanchor="left",
                y=0.5,
                yanchor="middle",
                len=0.82,
                lenmode="fraction",
                thickness=24,
                thicknessmode="pixels",
                outlinewidth=0,
                title=dict(text=label, side="right", font=dict(size=18)),
                tickfont=dict(size=15),
                tickmode="array",
                tickvals=tick_vals,
                ticktext=[fmt(v) for v in tick_vals],
            ),
        ))
        figure.update_layout(
            width=_W,
            height=_H,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
        )
        figure.update_xaxes(visible=False)
        figure.update_yaxes(visible=False)
        debug_print("MultiView ColorbarCanvas layout ready")

        fig_json = figure.to_json()
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>html,body{{margin:0;padding:0;overflow:hidden;background:white;}}</style>
<script src="plotly.min.js"></script></head>
<body><div id="d"></div>
	<script>Plotly.newPlot('d',{fig_json}.data,{fig_json}.layout,{{displayModeBar:false,responsive:false}});</script>
	</body></html>"""
        self._web.setHtml(html, self._base_url)
        debug_print("MultiView ColorbarCanvas.update_colorbar complete")
