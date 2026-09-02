"""Plotly-backed histogram canvas."""

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


class HistogramCanvas(QWidget):
    """Render histogram data using Plotly."""

    def __init__(self) -> None:
        debug_print("HistogramCanvas.__init__ start")
        super().__init__()
        self._canvas_width = _W
        self._canvas_height = _H
        debug_print(f"HistogramCanvas default height={self._canvas_height}")
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        install_save_dialog_download_handler(
            self._web_view,
            self,
            fallback_name="histogram.png",
        )
        self._web_view.setFixedSize(_W, self._canvas_height)
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)
        self.setFixedSize(_W, self._canvas_height)
        self._web_view.setHtml(self._empty_html(), self._base_url)
        debug_print("HistogramCanvas.__init__ complete")

    def set_available_width(self, width: int) -> None:
        debug_print(f"HistogramCanvas.set_available_width width={width}")
        self._canvas_width = max(240, min(_W, int(width)))
        self._web_view.setFixedSize(self._canvas_width, self._canvas_height)
        self.setFixedSize(self._canvas_width, self._canvas_height)
        debug_print(f"HistogramCanvas canvas width={self._canvas_width}")
        debug_print(f"HistogramCanvas canvas height={self._canvas_height}")

    def set_canvas_height(self, height: int) -> None:
        debug_print(f"HistogramCanvas.set_canvas_height height={height}")
        self._canvas_height = max(240, int(height))
        self._web_view.setFixedSize(self._canvas_width, self._canvas_height)
        self.setFixedSize(self._canvas_width, self._canvas_height)
        debug_print(f"HistogramCanvas applied height={self._canvas_height}")
        debug_print(f"HistogramCanvas current size={self.width()}x{self.height()}")

    def render_histogram(self, values, *, label: str, bins: int) -> None:
        debug_print("HistogramCanvas.render_histogram called")
        debug_print("HistogramCanvas delegating single trace to render_histograms")
        self.render_histograms(
            [{"name": "", "values": values}],
            label=label,
            bins=bins,
        )
        debug_print("HistogramCanvas.render_histogram complete")

    def render_histograms(self, series, *, label: str, bins: int, show_grid: bool = True) -> None:
        debug_print("HistogramCanvas.render_histograms called")
        debug_print(f"HistogramCanvas series count={len(series)}")
        figure = self._figure_for_histograms(
            series,
            label=label,
            bins=bins,
            show_grid=show_grid,
        )
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        debug_print("HistogramCanvas.render_histograms complete")

    def _figure_for_histograms(self, series, *, label: str, bins: int, show_grid: bool = True) -> go.Figure:
        debug_print("HistogramCanvas._figure_for_histograms called")
        debug_print(f"HistogramCanvas figure series count={len(series)}")
        figure = go.Figure()
        colors = ["#183568", "#c50623", "#0f9ca6", "#f0a202", "#7b2cbf", "#2d6a4f"]
        all_values = []
        prepared = []
        for index, item in enumerate(series):
            debug_print(f"HistogramCanvas preparing series index={index}")
            name = item.get("name", "")
            debug_print(f"HistogramCanvas preparing series name={name}")
            data = np.asarray(item.get("values", [])).flatten()
            data = data[~np.isnan(data)]
            prepared.append((name, data))
            if data.size:
                all_values.append(data)
            debug_print(f"HistogramCanvas finite count={data.size}")

        if not all_values:
            debug_print("HistogramCanvas no finite data")
            figure.add_annotation(
                text="No finite data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=PlotStyle.empty_annotation_font(),
            )
        else:
            combined = np.concatenate(all_values)
            data_min = float(np.min(combined))
            data_max = float(np.max(combined))
            data_range = data_max - data_min
            tolerance = max(1e-12, abs(data_max) * 1e-12)
            debug_print(f"HistogramCanvas combined min={data_min}")
            debug_print(f"HistogramCanvas combined max={data_max}")

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

            for index, (name, data) in enumerate(prepared):
                if data.size == 0:
                    debug_print(f"HistogramCanvas skipping empty series index={index}")
                    continue
                debug_print(f"HistogramCanvas adding histogram index={index}")
                figure.add_trace(go.Histogram(
                    x=data.tolist(),
                    name=name,
                    xbins=dict(start=bin_start, end=bin_end, size=bin_size),
                    marker_color=colors[index % len(colors)],
                    opacity=0.62 if len(prepared) > 1 else 0.9,
                    hovertemplate="value=%{x:.4g}<br>count=%{y}<br>%{fullData.name}<extra></extra>",
                    showlegend=bool(name),
                ))

        legend_config = PlotStyle.panel_legend(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
        )
        debug_print(f"HistogramCanvas legend entrywidthmode={legend_config.get('entrywidthmode')}")
        debug_print(f"HistogramCanvas legend entrywidth={legend_config.get('entrywidth')}")
        debug_print("HistogramCanvas legend columns target=3")
        debug_print("HistogramCanvas top margin=76 for modebar")
        figure.update_layout(
            width=self._canvas_width,
            height=self._canvas_height,
            margin=dict(l=80, r=20, t=76, b=70),
            paper_bgcolor="white",
            plot_bgcolor="white",
            barmode="overlay",
            font=PlotStyle.layout_font(),
            legend=legend_config,
            xaxis=PlotStyle.panel_axis(label, show_grid),
            yaxis=PlotStyle.panel_axis("Frequency", show_grid),
            bargap=0.05,
        )
        debug_print("HistogramCanvas._figure_for_histograms complete")
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        debug_print("HistogramCanvas._build_html called")
        debug_print("HistogramCanvas modebar top offset=0px")
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;}}
.modebar{{top: 0px !important;}}
</style>
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
