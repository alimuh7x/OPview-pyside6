"""One heatmap column in the Multi View comparison row."""

from pathlib import Path

import numpy as np
import plotly
import plotly.graph_objects as go
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from viewer.colorscale import cmap_to_plotly_scale
from viewer.heatmap_canvas import _CANVAS_HEIGHT, _CANVAS_WIDTH

_ASSETS     = Path(__file__).resolve().parent.parent / "assets"
_PLOTLY_JS  = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_CELL_W     = _CANVAS_WIDTH


class MultiViewHeader(QWidget):
    """Filename label + close button above a heatmap cell."""

    close_requested = Signal(str)

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self.file_path = file_path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(4)

        label = QLabel(Path(file_path).name)
        label.setObjectName("mutedInfo")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setToolTip(file_path)

        btn = QPushButton()
        btn.setObjectName("panelTabCloseButton")
        btn.setFlat(True)
        btn.setFixedSize(12, 12)
        btn.setIcon(QIcon(str(_ASSETS / "remove.png")))
        btn.setIconSize(btn.size())
        btn.clicked.connect(lambda: self.close_requested.emit(self.file_path))

        layout.addWidget(label)
        layout.addWidget(btn)
        self.setFixedWidth(_CELL_W)


class MultiViewCell(QWidget):
    """A single heatmap (no colorbar) in the Multi View row."""

    remove_requested = Signal(str)

    def __init__(self, file_path: str, parent=None) -> None:
        super().__init__(parent)
        self.file_path = file_path
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS.parent.resolve()) + "/")

        self._web = QWebEngineView(self)
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
               cmap, overlay_grid=None) -> None:
        colorscale = cmap_to_plotly_scale(cmap)
        rows, cols  = np.asarray(z_grid).shape[:2]
        x_vals = np.linspace(float(np.nanmin(x_grid)), float(np.nanmax(x_grid)), cols)
        y_vals = np.linspace(float(np.nanmin(y_grid)), float(np.nanmax(y_grid)), rows)

        figure = go.Figure()
        figure.add_trace(go.Heatmap(
            x=x_vals, y=y_vals,
            z=np.asarray(z_grid),
            zmin=vmin, zmax=vmax,
            colorscale=colorscale,
            showscale=False,
            hovertemplate="x=%{x:.4f}<br>y=%{y:.4f}<br>value=%{z:.4f}<extra></extra>",
        ))
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
<script src="plotly.min.js"></script></head>
<body><div id="d"></div>
<script>
var fig={fig_json};
Plotly.newPlot('d',fig.data,fig.layout,{{displayModeBar:false,responsive:false,scrollZoom:true}});
</script></body></html>"""
        self._web.setHtml(html, self._base_url)

    def grab_pixmap(self):
        return self._web.grab()
