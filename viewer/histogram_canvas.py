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


def _hist_debug(message: str) -> None:
    text = f"HIST-FREQ {message}"
    print(text)
    debug_print(text)


class HistogramCanvas(QWidget):
    """Render histogram data using Plotly."""

    def __init__(self, *, max_width: int = _W, show_legend: bool = True) -> None:
        debug_print("HistogramCanvas.__init__ start")
        super().__init__()
        self._max_width = max(240, int(max_width))
        debug_print(f"HistogramCanvas max width={self._max_width}")
        self._show_legend = bool(show_legend)
        debug_print(f"HistogramCanvas show legend={self._show_legend}")
        self._canvas_width = self._max_width
        self._canvas_height = _H
        debug_print(f"HistogramCanvas default height={self._canvas_height}")
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        install_save_dialog_download_handler(
            self._web_view,
            self,
            fallback_name="histogram.png",
        )
        self._web_view.setFixedSize(self._canvas_width, self._canvas_height)
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web_view)
        self.setFixedSize(self._canvas_width, self._canvas_height)
        self._web_view.setHtml(self._empty_html(), self._base_url)
        debug_print("HistogramCanvas.__init__ complete")

    def set_available_width(self, width: int) -> None:
        debug_print(f"HistogramCanvas.set_available_width width={width}")
        self._canvas_width = max(240, min(self._max_width, int(width)))
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
        _hist_debug(f"render_histograms input_count={len(series)} label={label} bins={bins} show_grid={show_grid}")
        _hist_debug(f"render_histograms input_names={[item.get('name', '') for item in series]}")
        figure = self._figure_for_histograms(
            series,
            label=label,
            bins=bins,
            show_grid=show_grid,
        )
        _hist_debug(f"render_histograms figure_trace_count={len(figure.data)}")
        _hist_debug(f"render_histograms figure_trace_names={[trace.name for trace in figure.data]}")
        self._web_view.setHtml(self._build_html(figure), self._base_url)
        _hist_debug("render_histograms html_set")
        debug_print("HistogramCanvas.render_histograms complete")

    def _figure_for_histograms(self, series, *, label: str, bins: int, show_grid: bool = True) -> go.Figure:
        debug_print("HistogramCanvas._figure_for_histograms called")
        debug_print(f"HistogramCanvas figure series count={len(series)}")
        _hist_debug(f"figure_start series_count={len(series)}")
        figure = go.Figure()
        colors = ["#183568", "#c50623", "#0f9ca6", "#f0a202", "#7b2cbf", "#2d6a4f"]
        all_values = []
        prepared = []
        for index, item in enumerate(series):
            debug_print(f"HistogramCanvas preparing series index={index}")
            _hist_debug(f"prepare index={index}")
            name = item.get("name", "")
            debug_print(f"HistogramCanvas preparing series name={name}")
            _hist_debug(f"prepare name={name}")
            data = np.asarray(item.get("values", [])).flatten()
            raw_count = data.size
            debug_print(f"HistogramCanvas raw count={raw_count}")
            _hist_debug(f"prepare raw_count={raw_count}")
            finite_mask = np.isfinite(data)
            debug_print(f"HistogramCanvas finite mask count={int(np.count_nonzero(finite_mask))}")
            data = data[finite_mask]
            prepared.append((name, data))
            if data.size:
                all_values.append(data)
            debug_print(f"HistogramCanvas finite count={data.size}")
            _hist_debug(f"prepare finite_count={data.size}")

        if not all_values:
            debug_print("HistogramCanvas no finite data")
            _hist_debug("figure no_finite_data")
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
            _hist_debug(f"combined min={data_min}")
            _hist_debug(f"combined max={data_max}")

            if data_range <= tolerance:
                # Near-constant data — pad symmetrically relative to value magnitude
                pad = max(abs(data_max) * 0.1, 1e-10)
                bin_start = data_min - pad
                bin_end   = data_max + pad
                safe_bins = 1
                bin_size  = (bin_end - bin_start)
            else:
                safe_bins = max(1, int(bins))
                bin_size  = data_range / safe_bins
                bin_start = data_min
                bin_end   = data_max + bin_size  # ensure last bin included
            _hist_debug(f"bins start={bin_start}")
            _hist_debug(f"bins end={bin_end}")
            _hist_debug(f"bins size={bin_size}")
            bin_edges = np.linspace(bin_start, bin_end, safe_bins + 1)
            _hist_debug(f"bins edge_count={len(bin_edges)}")
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
            _hist_debug(f"bins center_count={len(bin_centers)}")

            for index, (name, data) in enumerate(prepared):
                if data.size == 0:
                    debug_print(f"HistogramCanvas skipping empty series index={index}")
                    _hist_debug(f"trace skipped_empty index={index} name={name}")
                    continue
                debug_print(f"HistogramCanvas adding histogram index={index}")
                counts, _edges = np.histogram(data, bins=bin_edges)
                _hist_debug(f"trace add index={index} name={name} raw_count={data.size}")
                _hist_debug(f"trace binned_count={len(counts)} total_frequency={int(np.sum(counts))}")
                figure.add_trace(go.Bar(
                    x=bin_centers.tolist(),
                    y=counts.tolist(),
                    name=name,
                    marker_color=colors[index % len(colors)],
                    opacity=0.62 if len(prepared) > 1 else 0.9,
                    hovertemplate="value=%{x:.4g}<br>count=%{y}<br>%{fullData.name}<extra></extra>",
                    showlegend=bool(name) and self._show_legend,
                    width=bin_size * 0.92,
                ))

        series_count = len([data for _name, data in prepared if data.size])
        debug_print(f"HistogramCanvas visible series count={series_count}")
        _hist_debug(f"visible_series_count={series_count}")
        legend_orientation = "v"
        debug_print(f"HistogramCanvas legend orientation={legend_orientation}")
        _hist_debug(f"legend orientation={legend_orientation}")
        legend_x = 1.04
        debug_print(f"HistogramCanvas legend x={legend_x}")
        _hist_debug(f"legend x={legend_x}")
        legend_y = 1.0
        debug_print(f"HistogramCanvas legend y={legend_y}")
        _hist_debug(f"legend y={legend_y}")
        legend_yanchor = "top"
        debug_print(f"HistogramCanvas legend yanchor={legend_yanchor}")
        legend_xanchor = "left"
        debug_print(f"HistogramCanvas legend xanchor={legend_xanchor}")
        _hist_debug(f"legend xanchor={legend_xanchor}")
        top_margin = 76
        debug_print(f"HistogramCanvas dynamic top margin={top_margin}")
        _hist_debug(f"layout top_margin={top_margin}")
        bottom_margin = 70
        debug_print(f"HistogramCanvas dynamic bottom margin={bottom_margin}")
        _hist_debug(f"layout bottom_margin={bottom_margin}")
        right_margin = (210 if series_count > 3 else 180) if self._show_legend else 20
        debug_print(f"HistogramCanvas dynamic right margin={right_margin}")
        _hist_debug(f"layout right_margin={right_margin}")
        legend_config = None
        if self._show_legend:
            legend_config = PlotStyle.panel_legend(
                orientation=legend_orientation,
                yanchor=legend_yanchor,
                y=legend_y,
                xanchor=legend_xanchor,
                x=legend_x,
            )
            legend_config.pop("entrywidthmode", None)
            legend_config.pop("entrywidth", None)
            debug_print(f"HistogramCanvas legend entrywidthmode={legend_config.get('entrywidthmode')}")
            debug_print(f"HistogramCanvas legend entrywidth={legend_config.get('entrywidth')}")
            debug_print("HistogramCanvas legend placed outside right side")
        else:
            debug_print("HistogramCanvas legend hidden for single view")
            _hist_debug("legend hidden")
        debug_print(f"HistogramCanvas top margin={top_margin} for modebar")
        _hist_debug(f"layout legend_y={legend_y} legend_x={legend_x}")
        _hist_debug(f"layout top_margin={top_margin} bottom_margin={bottom_margin}")
        figure.update_layout(
            width=self._canvas_width,
            height=self._canvas_height,
            margin=dict(l=80, r=right_margin, t=top_margin, b=bottom_margin),
            paper_bgcolor="white",
            plot_bgcolor="white",
            barmode="overlay",
            font=PlotStyle.layout_font(),
            showlegend=self._show_legend,
            xaxis=PlotStyle.panel_axis(label, show_grid),
            yaxis=PlotStyle.panel_axis("Frequency", show_grid),
            bargap=0.05,
        )
        if legend_config is not None:
            figure.update_layout(legend=legend_config)
        debug_print("HistogramCanvas._figure_for_histograms complete")
        _hist_debug(f"figure_complete trace_count={len(figure.data)}")
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        debug_print("HistogramCanvas._build_html called")
        debug_print("HistogramCanvas modebar top offset=0px")
        figure_json = figure.to_json()
        _hist_debug(f"build_html trace_count={len(figure.data)} json_length={len(figure_json)}")
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
