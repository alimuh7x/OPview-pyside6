"""One heatmap column in the Multi View comparison row."""

import json
from pathlib import Path
from html import escape

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QIcon
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
from viewer.heatmap_canvas import _CANVAS_HEIGHT, _CANVAS_WIDTH
from app.debug import debug_print

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
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)

        legend_lbl = QLabel("Legend:")
        legend_lbl.setObjectName("mutedInfo")

        self._name_edit = QLineEdit(Path(file_path).name)
        self._name_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._name_edit.setFixedHeight(22)
        self._name_edit.setToolTip(f"Edit legend label — file: {file_path}")
        self._name_edit.setStyleSheet(
            "QLineEdit {"
            "  background: #f0f4fa;"
            "  color: #0d2b55;"
            "  font-size: 11px;"
            "  font-weight: 500;"
            "  border: 1px solid #c2d0e8;"
            "  border-radius: 3px;"
            "  padding: 1px 5px;"
            "}"
            "QLineEdit:focus {"
            "  border: 1.5px solid #1e4a8a;"
            "  background: #ffffff;"
            "}"
        )
        self._name_edit.editingFinished.connect(self._on_name_edited)

        btn = QPushButton()
        btn.setObjectName("panelTabCloseButton")
        btn.setFlat(True)
        btn.setFixedSize(12, 12)
        btn.setIcon(QIcon(str(_ASSETS / "remove.png")))
        btn.setIconSize(btn.size())
        btn.clicked.connect(lambda: self.close_requested.emit(self.file_path))

        layout.addWidget(legend_lbl)
        layout.addWidget(self._name_edit)
        layout.addWidget(btn)
        self.setFixedWidth(_CELL_W)

    def legend_name(self) -> str:
        return self._name_edit.text().strip() or Path(self.file_path).name

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

    def render(self, x_grid, y_grid, z_grid, *, vmin: float, vmax: float,
               cmap, overlay_grid=None, line_overlay=None) -> None:
        debug_print(f"MultiViewCell.render start file={self.file_path}")
        colorscale = cmap_to_plotly_scale(cmap)
        debug_print(f"MultiViewCell colorscale stops={len(colorscale)}")
        rows, cols  = np.asarray(z_grid).shape[:2]
        debug_print(f"MultiViewCell grid shape rows={rows} cols={cols}")
        x_vals = np.linspace(float(np.nanmin(x_grid)), float(np.nanmax(x_grid)), cols)
        y_vals = np.linspace(float(np.nanmin(y_grid)), float(np.nanmax(y_grid)), rows)
        debug_print(f"MultiViewCell x range={x_vals[0]}..{x_vals[-1]}")
        debug_print(f"MultiViewCell y range={y_vals[0]}..{y_vals[-1]}")

        figure = go.Figure()
        debug_print("MultiViewCell adding heatmap trace")
        figure.add_trace(go.Heatmap(
            x=x_vals, y=y_vals,
            z=np.asarray(z_grid),
            zmin=vmin, zmax=vmax,
            colorscale=colorscale,
            showscale=False,
            hovertemplate="x=%{x:.4f}<br>y=%{y:.4f}<br>value=%{z:.4f}<extra></extra>",
        ))
        if overlay_grid is not None:
            debug_print("MultiViewCell overlay_grid received")
            overlay_x = np.asarray(overlay_grid["x"])[0]
            overlay_y = np.asarray(overlay_grid["y"])[:, 0]
            overlay_z = np.asarray(overlay_grid["z"])
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
        figure.update_layout(
            width=_CELL_W, height=_CANVAS_HEIGHT,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="white", plot_bgcolor="white",
        )
        figure.update_xaxes(visible=False, constrain="domain", automargin=False)
        figure.update_yaxes(
            visible=False, scaleanchor="x", scaleratio=1.0,
            constrain="domain", automargin=False,
        )

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
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
html,body{{margin:0;padding:0;background:#f7f9fc;color:#102a52;font-family:sans-serif;}}
.box{{height:{_CANVAS_HEIGHT}px;display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;box-sizing:border-box;}}
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
