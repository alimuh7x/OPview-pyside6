"""Reveal-line animation dialog for Custom Graph panels."""

from __future__ import annotations

import copy
import math
import shutil
import subprocess
from pathlib import Path

import plotly
import plotly.graph_objects as go
from PySide6.QtCore import QEventLoop, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from app.debug import debug_print
from app.readable_dialogs import readable_information, readable_warning
from app.resources import ASSETS_DIR
from graphs.graph_canvas import GraphCanvas

_PLOTLY_JS_PATH = Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"
_GRAPH_WIDTH = 800
_GRAPH_HEIGHT = 620
_TRANSPORT_ICON_SIZE = QSize(28, 28)
_DEFAULT_FPS = 30
_REVEAL_DURATION_SECONDS = 3.0
_MAX_REVEAL_FRAMES = int(_DEFAULT_FPS * _REVEAL_DURATION_SECONDS)
_MAX_ANIMATION_TRACE_POINTS = 1000


class _GraphAnimationDebugPage(QWebEnginePage):
    """Forward animation-preview JavaScript diagnostics to the app debug log."""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):  # noqa: N802
        debug_print("GraphAnimationDebugPage.javaScriptConsoleMessage called")
        debug_print(f"GraphAnimation console level={level}")
        debug_print(f"GraphAnimation console line={line_number}")
        debug_print(f"GraphAnimation console source={source_id}")
        debug_print(f"GraphAnimation console message={message}")
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class GraphAnimationPlayer(QDialog):
    """Preview and export a Custom Graph reveal animation without mutating the graph."""

    def __init__(self, state: dict, panel_number: int = 1, parent=None) -> None:
        debug_print("GraphAnimationPlayer.__init__ start")
        super().__init__(parent)
        self.setObjectName("graphAnimationPlayer")
        self.setWindowTitle("Custom Graph Animation")
        self.resize(940, 760)
        self.setMinimumSize(940, 760)
        self.setModal(False)
        self._state = copy.deepcopy(state)
        self._panel_number = int(panel_number)
        self._base_url = QUrl.fromLocalFile(str(_PLOTLY_JS_PATH.parent.resolve()) + "/")
        self._figure = go.Figure()
        self._frame_count = 0
        self._current = 0
        self._playing = False
        self._fps = _DEFAULT_FPS
        self._initial_preview_rendered = False
        self._preview_html_loaded = False
        self._animation_prepared = False
        self._build_ui()
        debug_print(f"GraphAnimationPlayer panel_number={self._panel_number}")
        debug_print(f"GraphAnimationPlayer frame_count={self._frame_count}")
        debug_print("GraphAnimationPlayer.__init__ complete")

    @staticmethod
    def build_reveal_figure(state: dict) -> go.Figure:
        """Build a Plotly figure whose frames reveal every trace from left to right."""
        debug_print("GraphAnimationPlayer.build_reveal_figure called")
        state_copy = copy.deepcopy(state)
        canvas = GraphCanvas.__new__(GraphCanvas)
        canvas._graph_width = _GRAPH_WIDTH
        canvas._last_trace_count = 0
        figure = canvas._build_figure(state_copy)
        traces = [
            GraphAnimationPlayer._downsample_trace(trace, _MAX_ANIMATION_TRACE_POINTS)
            for trace in figure.data
            if hasattr(trace, "x") and hasattr(trace, "y")
        ]
        debug_print(f"GraphAnimationPlayer source trace count={len(traces)}")
        if not traces:
            debug_print("GraphAnimationPlayer no traces for reveal figure")
            return figure
        point_count = max(len(GraphAnimationPlayer._trace_values(trace, "x")) for trace in traces)
        debug_print(f"GraphAnimationPlayer reveal point count={point_count}")
        reveal_progress = GraphAnimationPlayer._reveal_progress_values(point_count)
        debug_print(f"GraphAnimationPlayer reveal frame count={len(reveal_progress)}")
        if not reveal_progress:
            debug_print("GraphAnimationPlayer no reveal progress")
            return figure
        axis_ranges = GraphAnimationPlayer._final_axis_ranges(traces)
        frames = []
        for frame_index, progress in enumerate(reveal_progress):
            debug_print(f"GraphAnimationPlayer building frame={frame_index}")
            debug_print(f"GraphAnimationPlayer building progress={progress}")
            frames.append(
                go.Frame(
                    name=str(frame_index),
                    data=[
                        GraphAnimationPlayer._trace_prefix(
                            trace,
                            GraphAnimationPlayer._visible_progress(trace, progress),
                            axis_ranges,
                        )
                        for trace in traces
                    ],
                )
            )
        animated_figure = go.Figure(
            data=[
                GraphAnimationPlayer._trace_prefix(
                    trace,
                    GraphAnimationPlayer._visible_progress(trace, reveal_progress[0]),
                    axis_ranges,
                )
                for trace in traces
            ],
            layout=figure.layout,
            frames=frames,
        )
        debug_print("GraphAnimationPlayer animated figure created")
        GraphAnimationPlayer._lock_final_axis_ranges(animated_figure, axis_ranges)
        animated_figure.update_layout(updatemenus=[], sliders=[])
        debug_print("GraphAnimationPlayer duplicate plotly controls removed")
        debug_print("GraphAnimationPlayer.build_reveal_figure complete")
        return animated_figure

    @staticmethod
    def _downsample_trace(trace, max_points: int):
        x_values = GraphAnimationPlayer._trace_values(trace, "x")
        y_values = GraphAnimationPlayer._trace_values(trace, "y")
        point_count = min(len(x_values), len(y_values))
        limit = max(2, int(max_points))
        if point_count <= limit:
            return trace
        indices = GraphAnimationPlayer._sample_indices(point_count, limit)
        trace_json = trace.to_plotly_json()
        next_trace = go.Scatter(**trace_json)
        next_trace.x = [x_values[index] for index in indices]
        next_trace.y = [y_values[index] for index in indices]
        return next_trace

    @staticmethod
    def _sample_indices(point_count: int, max_points: int) -> list[int]:
        total = max(0, int(point_count))
        limit = max(2, min(total, int(max_points)))
        if total <= limit:
            return list(range(total))
        last_index = total - 1
        return [round(index * last_index / (limit - 1)) for index in range(limit)]

    @staticmethod
    def _reveal_progress_values(point_count: int) -> list[float]:
        debug_print("GraphAnimationPlayer._reveal_progress_values called")
        total = max(0, int(point_count))
        debug_print(f"GraphAnimationPlayer reveal total points={total}")
        if total <= 0:
            return []
        if total <= _MAX_REVEAL_FRAMES:
            denominator = max(1, total - 1)
            progress = [float(index) / float(denominator) for index in range(total)]
            debug_print(f"GraphAnimationPlayer reveal uncapped frames={len(progress)}")
            return progress
        progress = []
        for index in range(_MAX_REVEAL_FRAMES):
            progress.append(float(index) / float(_MAX_REVEAL_FRAMES - 1))
        progress[-1] = 1.0
        debug_print(f"GraphAnimationPlayer reveal capped frames={len(progress)}")
        debug_print(f"GraphAnimationPlayer reveal first progress={progress[0]}")
        debug_print(f"GraphAnimationPlayer reveal last progress={progress[-1]}")
        return progress

    @staticmethod
    def _final_axis_ranges(traces: list) -> dict[str, list[float] | None]:
        debug_print("GraphAnimationPlayer._final_axis_ranges called")
        x_values = []
        y1_values = []
        y2_values = []
        for trace in traces:
            debug_print(f"GraphAnimationPlayer range trace={getattr(trace, 'name', '')}")
            x_values.extend(GraphAnimationPlayer._trace_values(trace, "x"))
            target = y2_values if getattr(trace, "yaxis", None) == "y2" else y1_values
            target.extend(GraphAnimationPlayer._trace_values(trace, "y"))
        pad_x = bool(traces) and all(str(getattr(trace, "mode", "") or "") == "lines" for trace in traces)
        ranges = {
            "xaxis": GraphAnimationPlayer._range_from_values(x_values, pad=pad_x),
            "yaxis": GraphAnimationPlayer._range_from_values(y1_values),
            "yaxis2": GraphAnimationPlayer._range_from_values(y2_values),
        }
        debug_print(f"GraphAnimationPlayer ranges={ranges}")
        return ranges

    @staticmethod
    def _lock_final_axis_ranges(figure: go.Figure, axis_ranges: dict[str, list[float] | None]) -> None:
        debug_print("GraphAnimationPlayer._lock_final_axis_ranges called")
        x_range = axis_ranges.get("xaxis")
        y1_range = axis_ranges.get("yaxis")
        y2_range = axis_ranges.get("yaxis2")
        debug_print(f"GraphAnimationPlayer x_range={x_range}")
        debug_print(f"GraphAnimationPlayer y1_range={y1_range}")
        debug_print(f"GraphAnimationPlayer y2_range={y2_range}")
        if x_range is not None:
            figure.layout.xaxis.range = x_range
            figure.layout.xaxis.autorange = False
        if y1_range is not None:
            figure.layout.yaxis.range = y1_range
            figure.layout.yaxis.autorange = False
        if y2_range is not None:
            figure.layout.yaxis2.range = y2_range
            figure.layout.yaxis2.autorange = False
        debug_print("GraphAnimationPlayer._lock_final_axis_ranges complete")

    @staticmethod
    def _range_from_values(values: list, *, pad: bool = False) -> list[float] | None:
        debug_print("GraphAnimationPlayer._range_from_values called")
        numeric_values = [float(value) for value in values if value is not None]
        debug_print(f"GraphAnimationPlayer range value count={len(numeric_values)}")
        if not numeric_values:
            return None
        minimum = min(numeric_values)
        maximum = max(numeric_values)
        if minimum == maximum:
            padding = abs(minimum) * 0.05 or 1.0
            minimum -= padding
            maximum += padding
        elif pad:
            padding = (maximum - minimum) * 0.05
            minimum -= padding
            maximum += padding
        result = [minimum, maximum]
        debug_print(f"GraphAnimationPlayer range result={result}")
        return result

    @staticmethod
    def _trace_prefix(trace, progress: float, axis_ranges: dict[str, list[float] | None] | None = None):
        """Return one trace copy truncated at a visual progress value."""
        debug_print("GraphAnimationPlayer._trace_prefix called")
        trace_json = trace.to_plotly_json()
        x_values = GraphAnimationPlayer._trace_values(trace, "x")
        y_values = GraphAnimationPlayer._trace_values(trace, "y")
        axis_ranges = axis_ranges or GraphAnimationPlayer._final_axis_ranges([trace])
        next_x, next_y = GraphAnimationPlayer._visual_prefix(
            x_values,
            y_values,
            progress,
            axis_ranges.get("xaxis"),
            axis_ranges.get("yaxis2") if getattr(trace, "yaxis", None) == "y2" else axis_ranges.get("yaxis"),
            str(getattr(trace, "mode", "lines") or "lines"),
        )
        next_trace = go.Scatter(**trace_json)
        next_trace.x = next_x
        next_trace.y = next_y
        GraphAnimationPlayer._apply_reveal_trace_mode(next_trace, str(getattr(trace, "mode", "lines") or "lines"), progress)
        debug_print(f"GraphAnimationPlayer trace prefix progress={progress}")
        debug_print(f"GraphAnimationPlayer trace prefix x_count={len(next_trace.x)}")
        return next_trace

    @staticmethod
    def _apply_reveal_trace_mode(trace, mode: str, progress: float) -> None:
        debug_print("GraphAnimationPlayer._apply_reveal_trace_mode called")
        normalized = str(mode or "lines")
        debug_print(f"GraphAnimationPlayer reveal source mode={normalized}")
        debug_print(f"GraphAnimationPlayer reveal progress={progress}")
        if normalized == "lines+markers" and float(progress) < 1.0:
            trace.mode = "lines"
            debug_print("GraphAnimationPlayer line markers hidden for reveal frame")
            return
        trace.mode = normalized
        debug_print(f"GraphAnimationPlayer reveal mode applied={trace.mode}")

    @staticmethod
    def _visual_prefix(
        x_values: list,
        y_values: list,
        progress: float,
        x_range: list[float] | None,
        y_range: list[float] | None,
        mode: str,
    ) -> tuple[list, list]:
        debug_print("GraphAnimationPlayer._visual_prefix called")
        point_count = min(len(x_values), len(y_values))
        debug_print(f"GraphAnimationPlayer visual point_count={point_count}")
        if point_count <= 0:
            return [], []
        bounded_progress = max(0.0, min(1.0, float(progress)))
        debug_print(f"GraphAnimationPlayer visual progress={bounded_progress}")
        if bounded_progress >= 1.0:
            return list(x_values[:point_count]), list(y_values[:point_count])
        if "markers" in mode and "lines" not in mode:
            marker_count = min(point_count, max(1, int(math.floor(bounded_progress * (point_count - 1))) + 1))
            debug_print(f"GraphAnimationPlayer visual marker_count={marker_count}")
            return list(x_values[:marker_count]), list(y_values[:marker_count])
        if bounded_progress <= 0.0 and point_count > 1:
            debug_print("GraphAnimationPlayer visual first line segment")
            return list(x_values[:2]), list(y_values[:2])
        distances = GraphAnimationPlayer._normalized_segment_lengths(x_values, y_values, x_range, y_range)
        total_distance = sum(distances)
        debug_print(f"GraphAnimationPlayer visual total_distance={total_distance}")
        if total_distance <= 0:
            point_position = 1.0 + bounded_progress * float(point_count - 1)
            return GraphAnimationPlayer._index_prefix(x_values, y_values, point_position)
        target_distance = total_distance * bounded_progress
        walked = 0.0
        for segment_index, segment_length in enumerate(distances):
            next_walked = walked + segment_length
            if target_distance <= next_walked or segment_index == len(distances) - 1:
                fraction = 0.0 if segment_length <= 0 else (target_distance - walked) / segment_length
                fraction = max(0.0, min(1.0, fraction))
                prefix_x = list(x_values[: segment_index + 1])
                prefix_y = list(y_values[: segment_index + 1])
                next_x = GraphAnimationPlayer._interpolate_value(x_values[segment_index], x_values[segment_index + 1], fraction)
                next_y = GraphAnimationPlayer._interpolate_value(y_values[segment_index], y_values[segment_index + 1], fraction)
                if fraction > 0.0 or len(prefix_x) < 2:
                    prefix_x.append(next_x)
                    prefix_y.append(next_y)
                debug_print(f"GraphAnimationPlayer visual fraction={fraction}")
                debug_print(f"GraphAnimationPlayer visual next_x={next_x}")
                debug_print(f"GraphAnimationPlayer visual next_y={next_y}")
                return prefix_x, prefix_y
            walked = next_walked
        return list(x_values), list(y_values)

    @staticmethod
    def _index_prefix(x_values: list, y_values: list, position: float) -> tuple[list, list]:
        debug_print("GraphAnimationPlayer._index_prefix called")
        point_count = min(len(x_values), len(y_values))
        endpoint = max(0.0, min(float(position) - 1.0, float(point_count - 1)))
        base_index = int(math.floor(endpoint))
        fraction = endpoint - base_index
        prefix_x = list(x_values[: base_index + 1])
        prefix_y = list(y_values[: base_index + 1])
        if fraction > 0.0 and base_index + 1 < point_count:
            next_x = GraphAnimationPlayer._interpolate_value(x_values[base_index], x_values[base_index + 1], fraction)
            next_y = GraphAnimationPlayer._interpolate_value(y_values[base_index], y_values[base_index + 1], fraction)
            prefix_x.append(next_x)
            prefix_y.append(next_y)
            debug_print(f"GraphAnimationPlayer index next_x={next_x}")
            debug_print(f"GraphAnimationPlayer index next_y={next_y}")
        return prefix_x, prefix_y

    @staticmethod
    def _normalized_segment_lengths(
        x_values: list,
        y_values: list,
        x_range: list[float] | None,
        y_range: list[float] | None,
    ) -> list[float]:
        debug_print("GraphAnimationPlayer._normalized_segment_lengths called")
        point_count = min(len(x_values), len(y_values))
        if point_count < 2:
            return []
        x_span = GraphAnimationPlayer._range_span(x_range)
        y_span = GraphAnimationPlayer._range_span(y_range)
        debug_print(f"GraphAnimationPlayer normalized x_span={x_span}")
        debug_print(f"GraphAnimationPlayer normalized y_span={y_span}")
        lengths = []
        for index in range(point_count - 1):
            dx = (float(x_values[index + 1]) - float(x_values[index])) / x_span
            dy = (float(y_values[index + 1]) - float(y_values[index])) / y_span
            length = math.hypot(dx, dy)
            lengths.append(length)
        debug_print(f"GraphAnimationPlayer normalized segment count={len(lengths)}")
        return lengths

    @staticmethod
    def _range_span(axis_range: list[float] | None) -> float:
        debug_print("GraphAnimationPlayer._range_span called")
        if not axis_range or len(axis_range) != 2:
            return 1.0
        span = abs(float(axis_range[1]) - float(axis_range[0]))
        resolved = span if span > 0 else 1.0
        debug_print(f"GraphAnimationPlayer range span={resolved}")
        return resolved

    @staticmethod
    def _interpolate_value(start, end, fraction: float):
        debug_print("GraphAnimationPlayer._interpolate_value called")
        try:
            value = float(start) + (float(end) - float(start)) * float(fraction)
        except (TypeError, ValueError):
            value = end if fraction >= 0.5 else start
        debug_print(f"GraphAnimationPlayer interpolated value={value}")
        return value

    @staticmethod
    def _visible_progress(trace, requested_progress: float) -> float:
        debug_print(f"GraphAnimationPlayer._visible_progress requested_progress={requested_progress}")
        progress = max(0.0, min(1.0, float(requested_progress)))
        debug_print(f"GraphAnimationPlayer visible progress={progress}")
        return progress

    @staticmethod
    def _trace_values(trace, key: str) -> list:
        debug_print(f"GraphAnimationPlayer._trace_values key={key}")
        values = trace.to_plotly_json().get(key)
        if values is None:
            return []
        return list(values)

    @staticmethod
    def preview_figure_for_frame(figure: go.Figure, index: int) -> go.Figure:
        """Return a standalone figure showing one reveal frame."""
        debug_print("GraphAnimationPlayer.preview_figure_for_frame called")
        if not figure.frames:
            debug_print("GraphAnimationPlayer preview without frames")
            return go.Figure(data=figure.data, layout=figure.layout)
        frame_index = max(0, min(int(index), len(figure.frames) - 1))
        debug_print(f"GraphAnimationPlayer preview frame_index={frame_index}")
        return go.Figure(
            data=list(figure.frames[frame_index].data),
            layout=figure.layout,
            frames=figure.frames,
        )

    def _build_ui(self) -> None:
        debug_print("GraphAnimationPlayer._build_ui called")
        self._apply_dialog_styles()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        self._status_label = QLabel("Reveal animation preview")
        self._status_label.setObjectName("mutedInfo")
        root.addWidget(self._status_label)
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self._web_view = QWebEngineView(self)
        self._web_view.setPage(_GraphAnimationDebugPage(self._web_view))
        self._web_view.loadStarted.connect(self._handle_load_started)
        self._web_view.loadFinished.connect(self._handle_load_finished)
        self._web_view.setMinimumSize(_GRAPH_WIDTH, _GRAPH_HEIGHT)
        self._web_view.setHtml(self._empty_html(), self._base_url)
        root.addWidget(self._web_view, 1)
        controls = QHBoxLayout()
        controls.setSpacing(4)
        self._first_btn = self._button("rewind.png")
        self._prev_btn = self._button("previous.png")
        self._play_btn = self._button("play.png", 42)
        self._next_btn = self._button("fast-forward.png", 42)
        self._last_btn = self._button("next.png")
        for button in (self._first_btn, self._prev_btn, self._play_btn, self._next_btn, self._last_btn):
            controls.addWidget(button)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, max(0, self._frame_count - 1))
        controls.addWidget(self._slider, 1)
        self._frame_label = QLabel("0 / 0")
        self._frame_label.setMinimumWidth(64)
        controls.addWidget(self._frame_label)
        self._fps_combo = QComboBox()
        for label, fps in [("1 fps", 1), ("2 fps", 2), ("5 fps", 5), ("10 fps", 10), ("15 fps", 15), ("20 fps", 20), ("30 fps", 30)]:
            self._fps_combo.addItem(label, fps)
        self._fps_combo.setCurrentIndex(self._fps_combo.findData(_DEFAULT_FPS))
        controls.addWidget(self._fps_combo)
        self._export_btn = QPushButton(QIcon(str(ASSETS_DIR / "download.png")), "MP4")
        self._export_btn.setFixedHeight(34)
        self._export_btn.setIconSize(QSize(18, 18))
        self._export_btn.setToolTip("Export reveal animation as MP4")
        controls.addWidget(self._export_btn)
        root.addLayout(controls)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.hide()
        root.addWidget(self._progress_bar)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._first_btn.clicked.connect(lambda: self._jump(0))
        self._prev_btn.clicked.connect(lambda: self._jump(self._current - 1))
        self._play_btn.clicked.connect(self._toggle_play)
        self._next_btn.clicked.connect(lambda: self._jump(self._current + 1))
        self._last_btn.clicked.connect(lambda: self._jump(self._frame_count - 1))
        self._slider.valueChanged.connect(self._jump)
        self._fps_combo.currentIndexChanged.connect(self._on_fps_changed)
        self._export_btn.clicked.connect(self._export_mp4)
        self._set_transport_enabled(self._frame_count > 0)
        debug_print("GraphAnimationPlayer._build_ui complete")

    def showEvent(self, event) -> None:  # noqa: N802
        debug_print("GraphAnimationPlayer.showEvent called")
        if event is not None:
            super().showEvent(event)
        if self._initial_preview_rendered:
            debug_print("GraphAnimationPlayer initial preview already rendered")
            return
        self._initial_preview_rendered = True
        debug_print("GraphAnimationPlayer scheduling animation preparation")
        self._status_label.setText("Preparing animation preview...")
        QTimer.singleShot(0, self._prepare_animation_preview)

    def _prepare_animation_preview(self) -> None:
        debug_print("GraphAnimationPlayer._prepare_animation_preview called")
        if self._animation_prepared:
            debug_print("GraphAnimationPlayer animation already prepared")
            return
        self._animation_prepared = True
        self._figure = self.build_reveal_figure(self._state)
        self._frame_count = len(self._figure.frames)
        self._current = 0
        self._preview_html_loaded = False
        self._slider.setRange(0, max(0, self._frame_count - 1))
        self._set_transport_enabled(self._frame_count > 0)
        debug_print(f"GraphAnimationPlayer prepared frame_count={self._frame_count}")
        self._show_frame(self._current)

    def _handle_load_started(self) -> None:
        debug_print("GraphAnimationPlayer web load started")

    def _handle_load_finished(self, ok: bool) -> None:
        debug_print(f"GraphAnimationPlayer web load finished ok={ok}")

    def _button(self, icon_name: str, width: int = 38) -> QPushButton:
        debug_print(f"GraphAnimationPlayer._button icon={icon_name}")
        button = QPushButton()
        button.setFixedSize(width, 34)
        button.setIcon(QIcon(str(ASSETS_DIR / icon_name)))
        button.setIconSize(_TRANSPORT_ICON_SIZE)
        return button

    def _apply_dialog_styles(self) -> None:
        debug_print("GraphAnimationPlayer._apply_dialog_styles called")
        self.setStyleSheet("""
QDialog#graphAnimationPlayer {
    background: #ffffff;
    color: #102a52;
}
QDialog#graphAnimationPlayer QLabel {
    color: #102a52;
    background: transparent;
}
QDialog#graphAnimationPlayer QLabel#mutedInfo {
    color: #506176;
}
QDialog#graphAnimationPlayer QPushButton {
    background: #ffffff;
    color: #102a52;
    border: 1px solid #d2dbea;
    border-radius: 6px;
    font-size: 17px;
    font-weight: 700;
    padding: 0px;
}
QDialog#graphAnimationPlayer QPushButton:hover {
    background: #eef4ff;
    border-color: #5a7fb0;
}
QDialog#graphAnimationPlayer QPushButton:disabled {
    background: #f2f4f8;
    color: #8f9bab;
    border-color: #d2dbea;
}
QDialog#graphAnimationPlayer QComboBox {
    min-height: 28px;
    background: #ffffff;
    color: #102a52;
    border: 1px solid #d2dbea;
    border-radius: 6px;
    padding: 2px 24px 2px 8px;
}
QDialog#graphAnimationPlayer QProgressBar {
    background: #eef2f7;
    color: #102a52;
    border: 1px solid #d2dbea;
    border-radius: 3px;
    text-align: center;
}
QDialog#graphAnimationPlayer QProgressBar::chunk {
    background: #4f8dcc;
    border-radius: 3px;
}
""")

    def _build_html(self, figure: go.Figure) -> str:
        debug_print("GraphAnimationPlayer._build_html called")
        figure_json = figure.to_json()
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:white;display:flex;align-items:flex-start;justify-content:center;}}#graph{{width:{_GRAPH_WIDTH}px;height:{_GRAPH_HEIGHT}px;}}</style>
<script src="plotly.min.js"></script>
</head><body>
<div id="graph"></div>
<script>
var fig = {figure_json};
try {{
    Plotly.newPlot('graph', fig.data, fig.layout, {{displayModeBar:false, responsive:true}});
    window.OPVIEW_SHOW_FRAME = function(frameIndex) {{
        console.log('OPView animation show frame ' + frameIndex);
        if (!fig.frames || !fig.frames[frameIndex]) {{
            console.log('OPView animation missing frame ' + frameIndex);
            return;
        }}
        Plotly.react('graph', fig.frames[frameIndex].data, fig.layout, {{displayModeBar:false, responsive:true}});
    }};
}} catch (err) {{
    document.body.innerHTML = '<pre style="white-space:pre-wrap;color:#b00020;padding:16px;font:14px monospace;">Plotly animation preview error: ' + err + '</pre>';
}}
</script>
</body></html>"""

    def _empty_html(self) -> str:
        debug_print("GraphAnimationPlayer._empty_html called")
        return (
            "<!DOCTYPE html><html><body "
            "style='margin:0;background:white;width:100%;height:100%;"
            "display:flex;align-items:center;justify-content:center;"
            "font:14px sans-serif;color:#506176;'>"
            "Preparing animation preview..."
            "</body></html>"
        )

    def _show_frame(self, index: int) -> None:
        debug_print("GraphAnimationPlayer._show_frame called")
        if self._frame_count <= 0:
            debug_print("GraphAnimationPlayer show skipped no frames")
            self._frame_label.setText("0 / 0")
            self._status_label.setText("No graph data available for animation.")
            self._web_view.setHtml(self._build_html(self._figure), self._base_url)
            return
        self._current = max(0, min(int(index), self._frame_count - 1))
        debug_print(f"GraphAnimationPlayer current frame={self._current}")
        self._render_preview_frame(self._current)
        self._slider.blockSignals(True)
        self._slider.setValue(self._current)
        self._slider.blockSignals(False)
        self._frame_label.setText(f"{self._current + 1} / {self._frame_count}")
        self._status_label.setText(f"Reveal frame {self._current + 1} of {self._frame_count}")

    def _render_preview_frame(self, index: int) -> None:
        debug_print("GraphAnimationPlayer._render_preview_frame called")
        if not self._preview_html_loaded:
            debug_print("GraphAnimationPlayer loading preview html")
            preview = self.preview_figure_for_frame(self._figure, index)
            self._web_view.setHtml(self._build_html(preview), self._base_url)
            self._preview_html_loaded = True
            return
        script = f"window.OPVIEW_SHOW_FRAME && window.OPVIEW_SHOW_FRAME({int(index)});"
        debug_print(f"GraphAnimationPlayer running preview js={script}")
        self._web_view.page().runJavaScript(script)

    def _set_transport_enabled(self, enabled: bool) -> None:
        debug_print(f"GraphAnimationPlayer._set_transport_enabled enabled={enabled}")
        for widget in (self._first_btn, self._prev_btn, self._play_btn, self._next_btn, self._last_btn, self._slider, self._export_btn):
            widget.setEnabled(bool(enabled))

    def _toggle_play(self) -> None:
        debug_print("GraphAnimationPlayer._toggle_play called")
        self._pause() if self._playing else self._start_play()

    def _start_play(self) -> None:
        debug_print("GraphAnimationPlayer._start_play called")
        if self._frame_count <= 0:
            debug_print("GraphAnimationPlayer play skipped no frames")
            return
        if self._current >= self._frame_count - 1:
            debug_print("GraphAnimationPlayer restarting from final frame")
            self._show_frame(0)
        self._playing = True
        self._play_btn.setIcon(QIcon(str(ASSETS_DIR / "pause.png")))
        self._timer.start(max(1, int(1000 / self._fps)))
        debug_print(f"GraphAnimationPlayer timer started fps={self._fps}")

    def _pause(self) -> None:
        debug_print("GraphAnimationPlayer._pause called")
        self._playing = False
        self._timer.stop()
        self._play_btn.setIcon(QIcon(str(ASSETS_DIR / "play.png")))

    def _stop(self) -> None:
        debug_print("GraphAnimationPlayer._stop called")
        self._pause()
        self._jump(0)

    def _advance(self) -> None:
        debug_print("GraphAnimationPlayer._advance called")
        if self._current >= self._frame_count - 1:
            debug_print("GraphAnimationPlayer reached final frame")
            self._pause()
            return
        self._show_frame(self._current + 1)

    def _jump(self, index: int) -> None:
        debug_print(f"GraphAnimationPlayer._jump index={index}")
        self._show_frame(index)

    def _on_fps_changed(self, index: int) -> None:
        debug_print(f"GraphAnimationPlayer._on_fps_changed index={index}")
        self._fps = int(self._fps_combo.itemData(index) or 10)
        debug_print(f"GraphAnimationPlayer fps={self._fps}")
        if self._playing:
            self._timer.setInterval(max(1, int(1000 / self._fps)))

    def _export_mp4(self) -> None:
        debug_print("GraphAnimationPlayer._export_mp4 called")
        if not self._animation_prepared:
            debug_print("GraphAnimationPlayer export preparing animation first")
            self._prepare_animation_preview()
        if self._frame_count <= 0:
            self._status_label.setText("No graph data available for MP4 export.")
            debug_print("GraphAnimationPlayer export skipped no frames")
            return
        encoder_error = self._mp4_encoder_error()
        if encoder_error:
            self._status_label.setText(encoder_error)
            readable_warning(self, "MP4 Export Unavailable", encoder_error)
            debug_print(f"GraphAnimationPlayer export encoder_error={encoder_error}")
            return
        default_name = f"custom_graph_{self._panel_number}_animation.mp4"
        path, _ = QFileDialog.getSaveFileName(self, "Export Graph Animation", default_name, "MP4 Video (*.mp4)")
        debug_print(f"GraphAnimationPlayer export selected path={path}")
        if not path:
            debug_print("GraphAnimationPlayer export cancelled")
            return
        if not path.lower().endswith(".mp4"):
            path = f"{path}.mp4"
        was_playing = self._playing
        self._pause()
        self._progress_bar.show()
        self._progress_bar.setValue(0)
        self._export_btn.setEnabled(False)
        self._status_label.setText(f"Exporting MP4 at {self._fps} fps...")
        try:
            self._write_mp4(Path(path))
        except Exception as exc:
            self._status_label.setText(f"MP4 export failed: {exc}")
            readable_warning(self, "MP4 Export Failed", f"Could not export MP4.\n\n{exc}")
            debug_print(f"GraphAnimationPlayer export failed={exc}")
        else:
            self._status_label.setText(f"MP4 exported: {Path(path).name}")
            readable_information(self, "MP4 Export Complete", f"MP4 exported successfully.\n\n{path}")
            debug_print(f"GraphAnimationPlayer export complete path={path}")
        finally:
            self._export_btn.setEnabled(True)
            self._progress_bar.hide()
            if was_playing:
                self._start_play()

    def _mp4_encoder_error(self) -> str:
        debug_print("GraphAnimationPlayer._mp4_encoder_error called")
        if shutil.which("ffmpeg") is None:
            return (
                "MP4 export requires FFmpeg, but ffmpeg.exe was not found. "
                "Install FFmpeg with winget or add ffmpeg.exe to PATH, then restart OPView and export again."
            )
        return ""

    def _write_mp4(self, path: Path) -> None:
        debug_print("GraphAnimationPlayer._write_mp4 called")
        self._write_mp4_from_web_view(path)

    def _write_mp4_from_web_view(self, path: Path) -> None:
        debug_print("GraphAnimationPlayer._write_mp4_from_web_view called")
        if not self._animation_prepared:
            debug_print("GraphAnimationPlayer web export preparing animation")
            self._prepare_animation_preview()
        if not self._preview_html_loaded:
            debug_print("GraphAnimationPlayer web export loading first preview")
            self._show_frame(0)
            self._wait_for_web_view(250)
        first_image = self._capture_web_view_image()
        width = first_image.width()
        height = first_image.height()
        debug_print(f"GraphAnimationPlayer web export width={width}")
        debug_print(f"GraphAnimationPlayer web export height={height}")
        process = subprocess.Popen(
            self._ffmpeg_rawvideo_command(path, width, height),
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            for frame_index in range(self._frame_count):
                debug_print(f"GraphAnimationPlayer web export frame={frame_index}")
                self._render_preview_frame(frame_index)
                self._wait_for_web_view(40)
                image = self._capture_web_view_image()
                process.stdin.write(self._qimage_rgba_bytes(image))
                percent = int((frame_index + 1) / max(1, self._frame_count) * 100)
                self._progress_bar.setValue(percent)
                debug_print(f"GraphAnimationPlayer web export progress={percent}")
        finally:
            if process.stdin:
                process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait()
        debug_print(f"GraphAnimationPlayer ffmpeg return_code={return_code}")
        if return_code != 0:
            raise RuntimeError(stderr.strip() or "FFmpeg failed while writing the MP4.")

    def _capture_web_view_image(self) -> QImage:
        debug_print("GraphAnimationPlayer._capture_web_view_image called")
        pixmap = self._web_view.grab()
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        debug_print(f"GraphAnimationPlayer captured image width={image.width()}")
        debug_print(f"GraphAnimationPlayer captured image height={image.height()}")
        return image

    @staticmethod
    def _qimage_rgba_bytes(image: QImage) -> bytes:
        debug_print("GraphAnimationPlayer._qimage_rgba_bytes called")
        converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
        byte_count = converted.sizeInBytes()
        debug_print(f"GraphAnimationPlayer image byte_count={byte_count}")
        return bytes(converted.constBits()[:byte_count])

    def _wait_for_web_view(self, milliseconds: int) -> None:
        debug_print(f"GraphAnimationPlayer._wait_for_web_view ms={milliseconds}")
        loop = QEventLoop(self)
        QTimer.singleShot(max(1, int(milliseconds)), loop.quit)
        loop.exec()

    def _ffmpeg_rawvideo_command(self, path: Path, width: int, height: int) -> list[str]:
        debug_print("GraphAnimationPlayer._ffmpeg_rawvideo_command called")
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s:v",
            f"{int(width)}x{int(height)}",
            "-r",
            str(int(self._fps)),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            str(path),
        ]
        debug_print(f"GraphAnimationPlayer ffmpeg command={command}")
        return command
