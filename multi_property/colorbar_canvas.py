"""Compact horizontal colorbar widget for Multi Property View."""

from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.debug import debug_print
from viewer.colorbar_ticks import format_colorbar_tick, format_colorbar_ticks
from viewer.colorscale import cmap_to_plotly_scale
from viewer.plot_style import PlotStyle

_PLOTLY_JS = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_W = 360
_H = 78
_BAR_THICKNESS = 14
_TITLE_FONT = {"family": PlotStyle.FONT_FAMILY, "size": 22, "color": PlotStyle.TEXT_COLOR, "weight": 700}
_TICK_FONT = {"family": PlotStyle.FONT_FAMILY, "size": 20, "color": PlotStyle.TEXT_COLOR}


def _format_tick(value: float) -> str:
    debug_print("MultiPropertyColorbar._format_tick called")
    debug_print(f"MultiPropertyColorbar tick value={value}")
    formatted = format_colorbar_tick(value)
    debug_print(f"MultiPropertyColorbar tick formatted={formatted}")
    return formatted


def _build_colorbar_figure(
    colorscale,
    vmin: float,
    vmax: float,
    label: str,
    width: int = _W,
    *,
    placement: str = "top",
) -> go.Figure:
    debug_print("MultiPropertyColorbar._build_colorbar_figure called")
    debug_print(f"MultiPropertyColorbar width={width}")
    debug_print(f"MultiPropertyColorbar height={_H}")
    debug_print(f"MultiPropertyColorbar thickness={_BAR_THICKNESS}")
    debug_print(f"MultiPropertyColorbar vmin={vmin}")
    debug_print(f"MultiPropertyColorbar vmax={vmax}")
    debug_print(f"MultiPropertyColorbar label={label}")
    debug_print(f"MultiPropertyColorbar placement={placement}")
    debug_print(f"MultiPropertyColorbar title font size={_TITLE_FONT['size']}")
    debug_print(f"MultiPropertyColorbar title font weight={_TITLE_FONT['weight']}")
    debug_print(f"MultiPropertyColorbar tick font size={_TICK_FONT['size']}")
    bottom_placement = placement == "bottom"
    title_side = "bottom" if bottom_placement else "top"
    tick_position = "outside top" if bottom_placement else "outside bottom"
    top_margin = 16 if bottom_placement else 22
    bottom_margin = 22 if bottom_placement else 16
    debug_print(f"MultiPropertyColorbar title_side={title_side}")
    debug_print(f"MultiPropertyColorbar tick_position={tick_position}")
    debug_print(f"MultiPropertyColorbar top_margin={top_margin}")
    debug_print(f"MultiPropertyColorbar bottom_margin={bottom_margin}")
    ticks = [
        vmin,
        vmin + (vmax - vmin) * 0.5,
        vmax,
    ]
    debug_print(f"MultiPropertyColorbar tick count={len(ticks)}")
    tick_text = format_colorbar_ticks(ticks)
    debug_print(f"MultiPropertyColorbar tick text={tick_text}")
    figure = go.Figure()
    figure.add_trace(go.Heatmap(
        z=[[vmin, vmax]],
        colorscale=colorscale,
        zmin=vmin,
        zmax=vmax,
        showscale=True,
        opacity=0.0,
        colorbar=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=0.5,
            yanchor="middle",
            len=0.88,
            lenmode="fraction",
            thickness=_BAR_THICKNESS,
            thicknessmode="pixels",
            outlinewidth=0,
            title=dict(text=label, side=title_side, font=_TITLE_FONT),
            tickfont=_TICK_FONT,
            ticklabelposition=tick_position,
            tickmode="array",
            tickvals=ticks,
            ticktext=tick_text,
        ),
    ))
    figure.update_layout(
        width=width,
        height=_H,
        margin=dict(l=36, r=36, t=top_margin, b=bottom_margin),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    debug_print("MultiPropertyColorbar figure built")
    return figure


class MultiPropertyColorbarCanvas(QWidget):
    """Horizontal colorbar used above or below one property heatmap."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        debug_print("MultiPropertyColorbarCanvas.__init__ start")
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS.parent.resolve()) + "/")
        self._web = QWebEngineView(self)
        self._web.setFixedSize(_W, _H)
        self._web.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web)
        self.setFixedSize(_W, _H)
        self._web.setHtml("<!DOCTYPE html><html><body style='margin:0;background:white;'></body></html>", self._base_url)
        debug_print(f"MultiPropertyColorbarCanvas fixed height={_H}")
        debug_print("MultiPropertyColorbarCanvas.__init__ complete")

    def set_canvas_width(self, width: int) -> None:
        debug_print("MultiPropertyColorbarCanvas.set_canvas_width called")
        debug_print(f"MultiPropertyColorbarCanvas width={width}")
        self._web.setFixedSize(width, _H)
        self.setFixedSize(width, _H)
        debug_print(f"MultiPropertyColorbarCanvas height={_H}")

    def update_colorbar(self, cmap, vmin: float, vmax: float, label: str = "", *, placement: str = "top") -> None:
        debug_print("MultiPropertyColorbarCanvas.update_colorbar called")
        debug_print(f"MultiPropertyColorbarCanvas vmin={vmin}")
        debug_print(f"MultiPropertyColorbarCanvas vmax={vmax}")
        debug_print(f"MultiPropertyColorbarCanvas label={label}")
        debug_print(f"MultiPropertyColorbarCanvas placement={placement}")
        colorscale = cmap_to_plotly_scale(cmap)
        figure = _build_colorbar_figure(colorscale, vmin, vmax, label, self.width() or _W, placement=placement)
        fig_json = figure.to_json()
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>html,body,#d{{margin:0;padding:0;overflow:hidden;background:white;width:100%;height:100%;}}</style>
<script src="plotly.min.js"></script></head>
<body><div id="d"></div>
<script>var fig={fig_json}; Plotly.newPlot('d', fig.data, fig.layout, {{displayModeBar:false,responsive:false}});</script>
</body></html>"""
        self._web.setHtml(html, self._base_url)
        debug_print("MultiPropertyColorbarCanvas.update_colorbar complete")
