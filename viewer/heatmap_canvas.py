"""Plotly-backed heatmap canvas."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.debug import debug_print
from viewer.colorscale import cmap_to_plotly_scale
from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.plot_style import PlotStyle

_CANVAS_HEIGHT = 420
_CANVAS_WIDTH  = 360
_COLORBAR_WIDTH = 90
_COLORBAR_GAP = 0.03
_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


class _AxesCompat:
    """Small compatibility shim for existing tests."""

    def get_aspect(self) -> float:
        return 1.0


class _NormCompat:
    """Compatibility shim for old matplotlib norm checks."""

    def __init__(self, vmin: float, vmax: float) -> None:
        self.vmin = vmin
        self.vmax = vmax


class _ImageCompat:
    """Compatibility shim for old matplotlib image checks."""

    def __init__(self, vmin: float, vmax: float) -> None:
        self.norm = _NormCompat(vmin, vmax)


class _PlotlyBridge(QObject):
    """WebChannel bridge used by Plotly events."""

    def __init__(self, canvas: "HeatmapCanvas") -> None:
        super().__init__()
        self._canvas = canvas

    @Slot(str, str)
    def sendEvent(self, event_type: str, payload_json: str) -> None:  # noqa: N802
        debug_print("PlotlyBridge.sendEvent called")
        debug_print(f"PlotlyBridge event_type={event_type}")
        self._canvas.handle_plotly_event(event_type, payload_json)


class _DebugWebEnginePage(QWebEnginePage):
    """Page subclass that forwards JS console and load diagnostics."""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802
        debug_print("DebugWebEnginePage.javaScriptConsoleMessage called")
        debug_print(f"Plotly console level={level}")
        debug_print(f"Plotly console line={line_number}")
        debug_print(f"Plotly console source={source_id}")
        debug_print(f"Plotly console message={message}")
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class HeatmapCanvas(QWidget):
    """Render interactive Plotly heatmaps inside the Qt panel."""

    heatmap_clicked = Signal(float, float)
    geometry_changed = Signal()
    status_changed = Signal(str)

    def __init__(self) -> None:
        debug_print("HeatmapCanvas.__init__ start")
        super().__init__()
        self._status_text = "Heatmap waiting for controller"
        self._hover_text = ""
        self._axes = _AxesCompat()
        self._image = None
        self._last_z_grid = None
        self._last_extent = None
        self._plot_width = _CANVAS_WIDTH
        self._colorbar_width = _COLORBAR_WIDTH
        self._colorbar_label = ""
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._web_view = QWebEngineView(self)
        self._web_view.setPage(_DebugWebEnginePage(self._web_view))
        self._web_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._channel = QWebChannel(self._web_view.page())
        self._bridge = _PlotlyBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._web_view.page().setWebChannel(self._channel)
        self._web_view.loadStarted.connect(self._handle_load_started)
        self._web_view.loadFinished.connect(self._handle_load_finished)
        self._web_view.setContextMenuPolicy(self.contextMenuPolicy())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._web_view)
        self.set_canvas_width(_CANVAS_WIDTH)
        self.setFixedHeight(_CANVAS_HEIGHT)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        debug_print("HeatmapCanvas.__init__ complete")

    def set_canvas_width(self, width: int) -> None:
        """Set the heatmap plotting width and keep room for Plotly's colorbar."""
        debug_print("HeatmapCanvas.set_canvas_width called")
        debug_print(f"HeatmapCanvas plot width={width}")
        self._plot_width = width
        widget_width = width + self._colorbar_width
        self._web_view.setFixedSize(widget_width, _CANVAS_HEIGHT)
        self.setFixedSize(widget_width, _CANVAS_HEIGHT)
        self.geometry_changed.emit()
        debug_print(f"HeatmapCanvas widget width={widget_width}")
        debug_print("HeatmapCanvas geometry_changed emitted")

    def _fmt_tick(self, v: float) -> str:
        """Format a colorbar tick value — scientific notation for large/small numbers."""
        import math
        if v == 0:
            return "0"
        try:
            mag = math.floor(math.log10(abs(v)))
        except ValueError:
            return "0"
        if -3 <= mag <= 4:
            decimals = max(0, 3 - int(mag))
            return f"{v:.{decimals}f}"
        return f"{v:.2e}"

    def _compute_colorbar_width(self, vmin: float, vmax: float) -> int:
        """Estimate pixel width needed for the colorbar based on the widest tick label."""
        import math

        def _fmt(v: float) -> str:
            if v == 0:
                return "0"
            try:
                mag = math.floor(math.log10(abs(v)))
            except ValueError:
                return "0"
            if -3 <= mag <= 4:
                decimals = max(0, 3 - int(mag))
                return f"{v:.{decimals}f}"
            return f"{v:.2e}"

        n_chars = max(len(_fmt(vmin)), len(_fmt(vmax)), len(_fmt(0)))
        # Shared tick font is size 22; estimate roughly 11px per character.
        # bar thickness (18px) + gap (8px) + label text + right padding (14px)
        return max(_COLORBAR_WIDTH, 18 + 8 + n_chars * 11 + 14)

    def _update_colorbar_width(self, vmin: float, vmax: float) -> None:
        """Resize the canvas if the required colorbar width has changed."""
        needed = self._compute_colorbar_width(vmin, vmax)
        if needed != self._colorbar_width:
            self._colorbar_width = needed
            widget_width = self._plot_width + self._colorbar_width
            self._web_view.setFixedSize(widget_width, _CANVAS_HEIGHT)
            self.setFixedSize(widget_width, _CANVAS_HEIGHT)
            self.geometry_changed.emit()
            debug_print(f"HeatmapCanvas colorbar_width updated to {needed}")

    def canvas_width(self) -> int:
        debug_print("HeatmapCanvas.canvas_width called")
        return self.width()

    def canvas_height(self) -> int:
        debug_print("HeatmapCanvas.canvas_height called")
        return self.height()

    def render_heatmap(
        self,
        x_grid,
        y_grid,
        z_grid,
        *,
        cmap,
        status_message: str,
        vmin: float,
        vmax: float,
        line_overlay=None,
        overlay_grid=None,
        title: str = "",
        colorbar_label: str = "",
        plot_type: str = "heatmap",
    ) -> None:
        debug_print("HeatmapCanvas.render_heatmap called")
        self._update_colorbar_width(vmin, vmax)
        extent = (
            float(np.nanmin(x_grid)),
            float(np.nanmax(x_grid)),
            float(np.nanmin(y_grid)),
            float(np.nanmax(y_grid)),
        )
        self._last_extent = extent
        self._last_z_grid = np.asarray(z_grid)
        self._colorbar_label = colorbar_label
        self._status_text = status_message
        self._hover_text = ""
        self._image = _ImageCompat(vmin, vmax)
        self._emit_status_changed()
        debug_print(f"HeatmapCanvas extent={self._last_extent}")
        debug_print(f"HeatmapCanvas colorbar_label={colorbar_label}")
        figure = self._build_figure(
            x_grid=x_grid,
            y_grid=y_grid,
            z_grid=z_grid,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            line_overlay=line_overlay,
            overlay_grid=overlay_grid,
            title=title,
            colorbar_label=colorbar_label,
            plot_type=plot_type,
        )
        html = self._build_html(figure)
        debug_print(f"HeatmapCanvas html size={len(html)}")
        self._web_view.setHtml(html, self._base_url)
        debug_print("HeatmapCanvas Plotly HTML updated")

    def save_png(self, path: str) -> None:
        """Export the current web view contents to PNG."""
        debug_print("HeatmapCanvas.save_png called")
        pixmap = self._web_view.grab()
        pixmap.save(path, "PNG")
        debug_print(f"HeatmapCanvas saved {path}")

    def render_status(self, message: str) -> None:
        debug_print("HeatmapCanvas.render_status called")
        debug_print(f"HeatmapCanvas message={message}")
        self._status_text = message
        self._emit_status_changed()
        debug_print("HeatmapCanvas status_changed emitted")

    def status_text(self) -> str:
        debug_print("HeatmapCanvas.status_text called")
        return self._compose_status_text()

    def handle_plotly_event(self, event_type: str, payload_json: str) -> None:
        """Handle click and hover events coming from the embedded Plotly view."""
        debug_print("HeatmapCanvas.handle_plotly_event called")
        payload = json.loads(payload_json or "{}")
        debug_print(f"HeatmapCanvas payload keys={list(payload.keys())}")
        if event_type == "click":
            x_value = payload.get("x")
            y_value = payload.get("y")
            if x_value is None or y_value is None:
                debug_print("HeatmapCanvas click payload missing coordinates")
                return
            self.heatmap_clicked.emit(float(x_value), float(y_value))
            debug_print(f"HeatmapCanvas emitted click x={x_value} y={y_value}")
            return
        if event_type == "hover":
            hover_text = self._build_hover_text(
                payload.get("x"),
                payload.get("y"),
                payload.get("z"),
            )
            if hover_text == self._hover_text:
                debug_print("HeatmapCanvas hover unchanged")
                return
            self._hover_text = hover_text
            self._emit_status_changed()
            debug_print(f"HeatmapCanvas hover updated to {hover_text}")
            return
        if event_type == "unhover":
            if not self._hover_text:
                debug_print("HeatmapCanvas hover already empty")
                return
            self._hover_text = ""
            self._emit_status_changed()
            debug_print("HeatmapCanvas hover cleared")
            return
        debug_print(f"HeatmapCanvas ignored event_type={event_type}")

    def _build_figure(
        self,
        *,
        x_grid,
        y_grid,
        z_grid,
        cmap,
        vmin: float,
        vmax: float,
        line_overlay,
        overlay_grid,
        title: str,
        colorbar_label: str,
        plot_type: str = "heatmap",
    ) -> go.Figure:
        debug_print("HeatmapCanvas._build_figure called")
        rows, cols = np.asarray(z_grid).shape[:2]
        x_values, y_values = Heatmap2DOrientation.plot_axes(x_grid, y_grid, z_grid)
        colorscale = cmap_to_plotly_scale(cmap)
        colorbar_x = 1.0 + _COLORBAR_GAP
        colorbar_cfg = dict(
            x             = colorbar_x,
            xanchor       = "left",
            y             = 0.35,
            yanchor       = "middle",
            len           = 0.7,
            lenmode       = "fraction",
            thickness     = 18,
            thicknessmode = "pixels",
            outlinewidth  = 0,
            title         = dict(text=colorbar_label, side="right", font=PlotStyle.colorbar_title_font()),
            tickfont      = PlotStyle.colorbar_tick_font(),
            tickmode      = "array",
            tickvals      = [
                vmin,
                vmin + (vmax - vmin) * 0.25,
                vmin + (vmax - vmin) * 0.5,
                vmin + (vmax - vmin) * 0.75,
                vmax,
            ],
            ticktext      = [
                self._fmt_tick(vmin),
                self._fmt_tick(vmin + (vmax - vmin) * 0.25),
                self._fmt_tick(vmin + (vmax - vmin) * 0.5),
                self._fmt_tick(vmin + (vmax - vmin) * 0.75),
                self._fmt_tick(vmax),
            ],
        )
        from viewer.plot_types import PLOT_TYPE_MAP
        figure = go.Figure()
        renderer = PLOT_TYPE_MAP.get(plot_type, PLOT_TYPE_MAP["heatmap"])
        hovertemplate = "x=%{x:.4f}<br>y=%{y:.4f}<br>value=%{z:.4f}<extra></extra>"
        for trace in renderer.build_traces(
            x_values, y_values, z_grid, vmin, vmax, colorscale, colorbar_cfg, hovertemplate
        ):
            figure.add_trace(trace)
        if overlay_grid is not None:
            debug_print("HeatmapCanvas adding smooth contour overlay")
            overlay_x, overlay_y = Heatmap2DOrientation.plot_axes(
                overlay_grid["x"],
                overlay_grid["y"],
                overlay_grid["z"],
            )
            figure.add_trace(
                go.Contour(
                    x=overlay_x,
                    y=overlay_y,
                    z=np.asarray(overlay_grid["z"]),
                    showscale=False,
                    contours=dict(
                        coloring="fill",
                        start=1.5,
                        end=3.5,
                        size=2.0,
                        showlines=False,
                    ),
                    colorscale=[
                        [0.0, "rgba(0, 0, 0, 0.0)"],
                        [0.499, "rgba(0, 0, 0, 0.0)"],
                        [0.5, "rgba(0, 0, 0, 0.82)"],
                        [1.0, "rgba(0, 0, 0, 0.82)"],
                    ],
                    line=dict(width=0, color="rgba(0, 0, 0, 0)"),
                    hoverinfo="skip",
                    opacity=1.0,
                )
            )
        if line_overlay:
            debug_print("HeatmapCanvas adding line overlay")
            orientation, value = line_overlay
            if orientation == "horizontal":
                figure.add_hline(
                    y=value,
                    line_width=PlotStyle.GUIDE_LINE_WIDTH,
                    line_dash="dash",
                    line_color="#c50623",
                )
            else:
                figure.add_vline(
                    x=value,
                    line_width=PlotStyle.GUIDE_LINE_WIDTH,
                    line_dash="dash",
                    line_color="#c50623",
                )
        figure.update_layout(
            title=dict(text=title),
            width=self.width(),
            height=_CANVAS_HEIGHT,
            margin=dict(l=0, r=self._colorbar_width, t=60, b=15),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=PlotStyle.layout_font(),
            dragmode="pan",
        )
        figure.update_xaxes(
            visible=False,
            range=[self._last_extent[0], self._last_extent[1]],
            constrain="domain",
            fixedrange=False,
            automargin=False,
        )
        figure.update_yaxes(
            visible=False,
            range=[self._last_extent[2], self._last_extent[3]],
            scaleanchor="x",
            scaleratio=1.0,
            constrain="domain",
            fixedrange=False,
            automargin=False,
        )
        debug_print("HeatmapCanvas figure ready")
        return figure

    def _build_html(self, figure: go.Figure) -> str:
        debug_print("HeatmapCanvas._build_html called")
        figure_json = figure.to_json()
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <style>
        html, body, #heatmapDiv {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: white;
        }}
        .modebar {{
            right: 0 !important;
        }}
        .nsewdrag, .ewdrag, .nsdrag, .drag {{
            cursor: default !important;
        }}
    </style>
    <script src="plotly.min.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
    <div id="heatmapDiv"></div>
    <script>
        const figure = {figure_json};
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            const bridge = channel.objects.bridge;
            const div = document.getElementById("heatmapDiv");
            const config = {{
                displaylogo: false,
                responsive: false,
                scrollZoom: true,
                doubleClick: "reset+autosize"
            }};
            Plotly.newPlot(div, figure.data, figure.layout, config).then(function(gd) {{
                gd.on("plotly_click", function(eventData) {{
                    if (!eventData.points || !eventData.points.length) {{
                        return;
                    }}
                    const point = eventData.points[0];
                    bridge.sendEvent("click", JSON.stringify({{
                        x: point.x,
                        y: point.y,
                        z: point.z
                    }}));
                }});
                gd.on("plotly_hover", function(eventData) {{
                    if (!eventData.points || !eventData.points.length) {{
                        return;
                    }}
                    const point = eventData.points[0];
                    bridge.sendEvent("hover", JSON.stringify({{
                        x: point.x,
                        y: point.y,
                        z: point.z
                    }}));
                }});
                gd.on("plotly_unhover", function() {{
                    bridge.sendEvent("unhover", "{{}}");
                }});
            }});
        }});
    </script>
</body>
</html>
"""

    def _handle_load_started(self) -> None:
        debug_print("HeatmapCanvas._handle_load_started called")

    def _handle_load_finished(self, ok: bool) -> None:
        debug_print("HeatmapCanvas._handle_load_finished called")
        debug_print(f"HeatmapCanvas load ok={ok}")

    def _build_hover_text(self, x_value, y_value, z_value) -> str:
        debug_print("HeatmapCanvas._build_hover_text called")
        if x_value is None or y_value is None:
            debug_print("HeatmapCanvas hover missing coordinates")
            return ""
        if z_value is None:
            lookup_value = self._lookup_value(float(x_value), float(y_value))
            if lookup_value is None:
                return f"hover x={float(x_value):.4f} | y={float(y_value):.4f}"
            z_value = lookup_value
        hover_text = f"hover x={float(x_value):.4f} | y={float(y_value):.4f} | value={float(z_value):.4f}"
        debug_print(f"HeatmapCanvas hover_text={hover_text}")
        return hover_text

    def _lookup_value(self, x_value: float, y_value: float):
        debug_print("HeatmapCanvas._lookup_value called")
        if self._last_z_grid is None or self._last_extent is None:
            debug_print("HeatmapCanvas no grid for lookup")
            return None
        x_min, x_max, y_min, y_max = self._last_extent
        if x_max == x_min or y_max == y_min:
            debug_print("HeatmapCanvas degenerate extent")
            return None
        rows, cols = self._last_z_grid.shape[:2]
        x_ratio = (x_value - x_min) / (x_max - x_min)
        y_ratio = (y_value - y_min) / (y_max - y_min)
        x_index = int(np.clip(round(x_ratio * (cols - 1)), 0, cols - 1))
        y_index = int(np.clip(round(y_ratio * (rows - 1)), 0, rows - 1))
        value = float(self._last_z_grid[y_index, x_index])
        debug_print(f"HeatmapCanvas lookup row={y_index} col={x_index}")
        debug_print(f"HeatmapCanvas lookup value={value}")
        return value

    def _compose_status_text(self) -> str:
        debug_print("HeatmapCanvas._compose_status_text called")
        if self._hover_text:
            combined = f"{self._status_text} | {self._hover_text}"
            debug_print(f"HeatmapCanvas combined status={combined}")
            return combined
        debug_print(f"HeatmapCanvas base status only={self._status_text}")
        return self._status_text

    def _emit_status_changed(self) -> None:
        debug_print("HeatmapCanvas._emit_status_changed called")
        combined = self._compose_status_text()
        self.status_changed.emit(combined)
        debug_print("HeatmapCanvas emitted combined status")
