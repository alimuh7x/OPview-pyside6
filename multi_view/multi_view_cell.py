"""One heatmap column in the Multi View comparison row."""

import json
from pathlib import Path
from html import escape

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from viewer.colorscale import cmap_to_plotly_scale
from viewer.heatmap_canvas import HeatmapCanvas, _CANVAS_HEIGHT, _CANVAS_WIDTH
from viewer.heatmap_orientation import Heatmap2DOrientation
from app.debug import debug_print
from utils.time_series import compact_timestep_label

_ASSETS     = Path(__file__).resolve().parent.parent / "assets"
_PLOTLY_JS  = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_CELL_W     = _CANVAS_WIDTH


class _MultiViewPlotlyBridge(QObject):
    """WebChannel bridge that forwards Plotly click events from a Multi View cell."""

    def __init__(self, cell: "MultiViewCell") -> None:
        super().__init__()
        self._cell = cell

    @Slot(str, str)
    def sendEvent(self, event_type: str, payload_json: str) -> None:  # noqa: N802
        debug_print("MultiViewPlotlyBridge.sendEvent called")
        debug_print(f"MultiViewPlotlyBridge event_type={event_type}")
        self._cell.handle_plotly_event(event_type, payload_json)


class _MultiViewDebugPage(QWebEnginePage):
    """Forward JavaScript console messages to the existing debug stream."""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802
        debug_print("MultiViewDebugPage.javaScriptConsoleMessage called")
        debug_print(f"MultiView plotly console level={level}")
        debug_print(f"MultiView plotly console line={line_number}")
        debug_print(f"MultiView plotly console source={source_id}")
        debug_print(f"MultiView plotly console message={message}")
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class MultiViewHeader(QWidget):
    """Filename label (editable) + close button above a heatmap cell."""

    close_requested = Signal(str)
    legend_name_changed = Signal(str, str)  # (file_path, new_name)

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self.file_path = file_path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        debug_print("MultiViewHeader layout margins set to 6,4,6,4")
        debug_print("MultiViewHeader layout spacing set to 6")

        legend_lbl = QLabel("Legend:")
        legend_lbl.setObjectName("mutedInfo")

        self._name_edit = QLineEdit(compact_timestep_label(file_path))
        self._name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._name_edit.setFixedHeight(30)
        name_font = QFont(self._name_edit.font())
        name_font.setPointSize(13)
        name_font.setWeight(QFont.Weight.DemiBold)
        self._name_edit.setFont(name_font)
        self._name_edit.setToolTip(f"Edit legend label — file: {file_path}")
        self._name_edit.setStyleSheet(
            "QLineEdit {"
            "  background: #f0f4fa;"
            "  color: #0d2b55;"
            "  font-size: 13px;"
            "  font-weight: 600;"
            "  border: 1px solid #c2d0e8;"
            "  border-radius: 4px;"
            "  padding: 4px 7px;"
            "}"
            "QLineEdit:focus {"
            "  border: 1.5px solid #1e4a8a;"
            "  background: #ffffff;"
            "}"
        )
        debug_print("MultiViewHeader legend edit fixed height=30")
        debug_print("MultiViewHeader legend edit font-size=13")
        self._name_edit.editingFinished.connect(self._on_name_edited)

        btn = QPushButton()
        btn.setObjectName("panelTabCloseButton")
        btn.setFlat(True)
        btn.setFixedSize(18, 18)
        btn.setIcon(QIcon(str(_ASSETS / "remove.png")))
        btn.setIconSize(btn.size())
        debug_print("MultiViewHeader close button fixed size=18")
        btn.clicked.connect(lambda: self.close_requested.emit(self.file_path))

        layout.addWidget(legend_lbl)
        layout.addWidget(self._name_edit)
        layout.addWidget(btn)
        self.setFixedWidth(_CELL_W)

    def legend_name(self) -> str:
        return self._name_edit.text().strip() or compact_timestep_label(self.file_path)

    def set_cell_width(self, width: int) -> None:
        self.setFixedWidth(width)

    def _on_name_edited(self) -> None:
        self.legend_name_changed.emit(self.file_path, self.legend_name())


class MultiViewCell(QWidget):
    """A single heatmap (no colorbar) in the Multi View row."""

    remove_requested = Signal(str)
    heatmap_clicked = Signal(str, float, float)

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self.file_path = file_path
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS.parent.resolve()) + "/")

        self._web = QWebEngineView(self)
        self._web.setPage(_MultiViewDebugPage(self._web))
        self._channel = QWebChannel(self._web.page())
        self._bridge = _MultiViewPlotlyBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._web.page().setWebChannel(self._channel)
        self._web.setFixedSize(_CELL_W, _CANVAS_HEIGHT)
        self._web.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._web)
        self.setFixedSize(_CELL_W, _CANVAS_HEIGHT)

        self._web.setHtml(
            "<!DOCTYPE html><html><body style='margin:0;background:white;'></body></html>",
            self._base_url,
        )

    def set_cell_size(self, width: int, height: int | None = None) -> None:
        debug_print("MultiViewCell.set_cell_size called")
        safe_width = max(1, int(width))
        safe_height = _CANVAS_HEIGHT if height is None else max(1, int(height))
        debug_print(f"MultiViewCell requested width={width}")
        debug_print(f"MultiViewCell requested height={height}")
        debug_print(f"MultiViewCell safe width={safe_width}")
        debug_print(f"MultiViewCell safe height={safe_height}")
        self._web.setFixedSize(safe_width, safe_height)
        self.setFixedSize(safe_width, safe_height)
        debug_print("MultiViewCell size applied")

    def set_cell_width(self, width: int) -> None:
        debug_print("MultiViewCell.set_cell_width called")
        self.set_cell_size(width, _CANVAS_HEIGHT)

    def render(self, x_grid, y_grid, z_grid, *, vmin: float, vmax: float,
               cmap, plot_type: str = "heatmap", overlay_grid=None, line_overlay=None, vector_overlay=None,
               fill_canvas: bool = False) -> None:
        debug_print(f"MultiViewCell.render start file={self.file_path}")
        debug_print(f"MultiViewCell fill_canvas={fill_canvas}")
        debug_print(f"MultiViewCell selected plot_type={plot_type}")
        rows, cols  = np.asarray(z_grid).shape[:2]
        debug_print(f"MultiViewCell grid shape rows={rows} cols={cols}")
        x_vals, y_vals = Heatmap2DOrientation.plot_axes(x_grid, y_grid, z_grid)
        debug_print(f"MultiViewCell x range={x_vals[0]}..{x_vals[-1]}")
        debug_print(f"MultiViewCell y range={y_vals[0]}..{y_vals[-1]}")

        figure = go.Figure()
        debug_print("MultiViewCell building selected plot traces")
        plot_traces = self._build_plot_traces(
            x_grid,
            y_grid,
            z_grid,
            vmin=vmin,
            vmax=vmax,
            cmap=cmap,
            plot_type=plot_type,
        )
        debug_print(f"MultiViewCell plot trace count={len(plot_traces)}")
        for trace in plot_traces:
            debug_print(f"MultiViewCell adding plot trace type={getattr(trace, 'type', 'unknown')}")
            figure.add_trace(trace)
        if overlay_grid is not None:
            debug_print("MultiViewCell overlay_grid received")
            overlay_z = np.asarray(overlay_grid["z"])
            overlay_x, overlay_y = Heatmap2DOrientation.plot_axes(
                overlay_grid["x"],
                overlay_grid["y"],
                overlay_z,
            )
            overlay_mask = self._build_overlay_mask(overlay_z)
            debug_print(f"MultiViewCell overlay contour x count={len(overlay_x)}")
            debug_print(f"MultiViewCell overlay contour y count={len(overlay_y)}")
            debug_print(f"MultiViewCell overlay pixels={int(np.count_nonzero(~np.isnan(overlay_mask)))}")
            figure.add_trace(go.Contour(
                x=overlay_x,
                y=overlay_y,
                z=overlay_z,
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
                    [0.5, "rgba(0, 0, 0, 1.0)"],
                    [1.0, "rgba(0, 0, 0, 1.0)"],
                ],
                line=dict(width=0, color="rgba(0, 0, 0, 0)"),
                hoverinfo="skip",
                opacity=1.0,
            ))
        else:
            debug_print("MultiViewCell no overlay_grid")
        if vector_overlay is not None:
            debug_print("MultiViewCell adding vector overlay")
            arrow_traces = self._build_vector_traces(vector_overlay)
            debug_print(f"MultiViewCell vector trace count={len(arrow_traces)}")
            for trace in arrow_traces:
                figure.add_trace(trace)
        else:
            debug_print("MultiViewCell no vector overlay")
        if line_overlay:
            debug_print("MultiViewCell adding line overlay")
            orientation, value = line_overlay
            debug_print(f"MultiViewCell line orientation={orientation}")
            debug_print(f"MultiViewCell line value={value}")
            if orientation == "horizontal":
                figure.add_hline(y=value, line_width=2, line_dash="dash", line_color="#c50623")
            else:
                figure.add_vline(x=value, line_width=2, line_dash="dash", line_color="#c50623")
        else:
            debug_print("MultiViewCell no line overlay")
        debug_print("MultiViewCell updating layout")
        canvas_width = max(1, self.width())
        canvas_height = max(1, self.height())
        debug_print(f"MultiViewCell canvas width={canvas_width}")
        debug_print(f"MultiViewCell canvas height={canvas_height}")
        figure.update_layout(
            width=canvas_width, height=canvas_height,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="white", plot_bgcolor="white",
        )
        self._configure_axes(figure, fill_canvas=fill_canvas)

        fig_json = figure.to_json()
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
	<style>
	html,body{{margin:0;padding:0;overflow:hidden;background:white;}}
	.nsewdrag,.ewdrag,.nsdrag,.drag{{cursor:default!important;}}
	</style>
	<script src="plotly.min.js"></script>
	<script src="qrc:///qtwebchannel/qwebchannel.js"></script></head>
	<body><div id="d"></div>
	<script>
	var fig={fig_json};
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            var bridge = channel.objects.bridge;
            Plotly.newPlot('d',fig.data,fig.layout,{{displayModeBar:false,responsive:false,scrollZoom:true}}).then(function(gd) {{
                gd.on("plotly_click", function(eventData) {{
                    if (!eventData.points || !eventData.points.length) {{
                        return;
                    }}
                    var point = eventData.points[0];
                    bridge.sendEvent("click", JSON.stringify({{
                        x: point.x,
                        y: point.y,
                        z: point.z
                    }}));
                }});
            }});
        }});
        </script></body></html>"""
        self._web.setHtml(html, self._base_url)
        debug_print("MultiViewCell.render complete")

    @staticmethod
    def _build_plot_traces(x_grid, y_grid, z_grid, *, vmin: float, vmax: float, cmap, plot_type: str):
        debug_print("MultiViewCell._build_plot_traces called")
        debug_print(f"MultiViewCell plot_type requested={plot_type}")
        colorscale = cmap_to_plotly_scale(cmap)
        debug_print(f"MultiViewCell colorscale stops={len(colorscale)}")
        x_vals, y_vals = Heatmap2DOrientation.plot_axes(x_grid, y_grid, z_grid)
        debug_print(f"MultiViewCell trace x count={len(x_vals)}")
        debug_print(f"MultiViewCell trace y count={len(y_vals)}")
        from viewer.plot_types import PLOT_TYPE_MAP
        renderer = PLOT_TYPE_MAP.get(plot_type, PLOT_TYPE_MAP["heatmap"])
        debug_print(f"MultiViewCell renderer key={renderer.key}")
        hovertemplate = "x=%{x:.4f}<br>y=%{y:.4f}<br>value=%{z:.4f}<extra></extra>"
        traces = renderer.build_traces(
            x_vals,
            y_vals,
            z_grid,
            vmin,
            vmax,
            colorscale,
            {},
            hovertemplate,
        )
        for trace in traces:
            if hasattr(trace, "showscale"):
                trace.showscale = False
                debug_print(f"MultiViewCell disabled trace colorbar type={getattr(trace, 'type', 'unknown')}")
        debug_print(f"MultiViewCell built trace count={len(traces)}")
        return traces

    @staticmethod
    def _configure_axes(figure: go.Figure, *, fill_canvas: bool = False) -> None:
        debug_print("MultiViewCell._configure_axes called")
        debug_print(f"MultiViewCell configure fill_canvas={fill_canvas}")
        if fill_canvas:
            figure.update_xaxes(
                visible=False,
                automargin=False,
                constrain="domain",
                domain=[0, 1],
            )
            figure.update_yaxes(
                visible=False,
                automargin=False,
                constrain="domain",
                domain=[0, 1],
            )
            debug_print("MultiViewCell axes configured edge-to-edge")
            return
        figure.update_xaxes(visible=False, constrain="domain", automargin=False)
        figure.update_yaxes(
            visible=False,
            scaleanchor="x",
            scaleratio=1.0,
            constrain="domain",
            automargin=False,
        )
        debug_print("MultiViewCell axes configured aspect-preserving")

    @staticmethod
    def _build_vector_traces(vector_overlay: dict) -> list[go.Scatter]:
        debug_print("MultiViewCell._build_vector_traces called")
        debug_print(f"MultiViewCell vector label={vector_overlay.get('label')}")
        debug_print(f"MultiViewCell vector arrow_length={vector_overlay.get('arrow_length')}")
        traces = HeatmapCanvas._build_vector_arrow_traces(
            vector_overlay,
            arrow_length=vector_overlay.get("arrow_length"),
        )
        debug_print(f"MultiViewCell vector traces built={len(traces)}")
        return traces

    def handle_plotly_event(self, event_type: str, payload_json: str) -> None:
        debug_print("MultiViewCell.handle_plotly_event called")
        debug_print(f"MultiViewCell event_type={event_type}")
        payload = json.loads(payload_json or "{}")
        debug_print(f"MultiViewCell payload keys={list(payload.keys())}")
        if event_type != "click":
            debug_print("MultiViewCell ignoring non-click event")
            return
        x_value = payload.get("x")
        y_value = payload.get("y")
        if x_value is None or y_value is None:
            debug_print("MultiViewCell click payload missing coordinates")
            return
        self.heatmap_clicked.emit(self.file_path, float(x_value), float(y_value))
        debug_print(f"MultiViewCell emitted click x={x_value} y={y_value}")

    def render_status(self, message: str) -> None:
        debug_print(f"MultiViewCell.render_status file={self.file_path}")
        debug_print(f"MultiViewCell status message={message}")
        safe_message = escape(message).replace("&lt;br&gt;", "<br>")
        canvas_height = max(1, self.height())
        debug_print(f"MultiViewCell status canvas height={canvas_height}")
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
html,body{{margin:0;padding:0;background:#f7f9fc;color:#102a52;font-family:sans-serif;}}
.box{{height:{canvas_height}px;display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;box-sizing:border-box;}}
.msg{{max-width:360px;font-size:15px;line-height:1.35;color:#526987;}}
</style></head><body><div class="box"><div class="msg">{safe_message}</div></div></body></html>"""
        self._web.setHtml(html, self._base_url)
        debug_print("MultiViewCell.render_status complete")

    def grab_pixmap(self):
        debug_print(f"MultiViewCell.grab_pixmap file={self.file_path}")
        return self._web.grab()

    @staticmethod
    def _build_overlay_mask(z_grid):
        debug_print("MultiViewCell._build_overlay_mask called")
        z_arr = np.asarray(z_grid, dtype=float)
        debug_print(f"MultiViewCell overlay input shape={z_arr.shape}")
        mask = np.where((z_arr >= 1.5) & (z_arr <= 3.5), 1.0, np.nan)
        debug_print(f"MultiViewCell overlay mask count={int(np.count_nonzero(~np.isnan(mask)))}")
        return mask
