"""Fast animation player using Matplotlib imshow."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.resources import ASSETS_DIR
from viewer.colorscale import palette_to_cmap

_TRANSPORT_ICON_SIZE = QSize(28, 28)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class _FrameFetcher(QObject):
    frame_ready = Signal(int, object)
    frame_error = Signal(int, str)
    finished    = Signal()
    progress    = Signal(int)

    def __init__(self, file_paths, scalar_def, axis, slice_index, resolution, interfaces_overlay=False):
        super().__init__()
        self._file_paths  = file_paths
        self._scalar_def  = scalar_def
        self._axis        = axis
        self._slice_index = slice_index
        self._resolution  = resolution
        self._interfaces_overlay = interfaces_overlay
        self._abort       = False

    def abort(self):
        self._abort = True

    def run(self):
        import pyvista as pv
        total     = len(self._file_paths)
        if total == 0:
            self.progress.emit(100)
            self.finished.emit()
            return

        scale     = self._scalar_def.get("scale", 1.0) or 1.0
        array_key = self._scalar_def["array"]
        component = self._scalar_def.get("component")
        for i, path in enumerate(self._file_paths):
            if self._abort:
                break
            try:
                z = self._fast_load(pv.read(path), array_key, component, scale)
                overlay = self._load_overlay(path, pv) if self._interfaces_overlay else None
                self.frame_ready.emit(i, (z, overlay))
            except Exception as exc:
                message = str(exc) or exc.__class__.__name__
                self.frame_error.emit(i, message)
            self.progress.emit(int((i + 1) / total * 100))
        self.finished.emit()

    def _load_overlay(self, file_path, pv):
        phase_file = self._phase_overlay_file(file_path)
        if phase_file is None:
            return None
        try:
            overlay = self._fast_load(pv.read(str(phase_file)), "Interfaces", None, 1.0)
        except Exception:
            return None
        return np.asarray(overlay)

    @staticmethod
    def _phase_overlay_file(file_path):
        if not file_path:
            return None
        path = Path(file_path)
        if path.name.startswith("PhaseField_"):
            return path
        suffix = path.name.split("_")[-1]
        candidate = path.with_name(f"PhaseField_{suffix}")
        return candidate if candidate.exists() else None

    def _fast_load(self, mesh, array_key, component, scale):
        raw = mesh[array_key]
        if raw.ndim == 2:
            raw = raw[:, component] if component is not None else np.linalg.norm(raw, axis=1)
        dims = getattr(mesh, "dimensions", None)
        if dims is not None:
            active = [d for d in dims if d > 1]
            if len(active) == 2:
                return (raw.reshape(active[1], active[0]) * scale).astype(np.float32)
        from utils.vtk_reader import VTKReader
        reader = VTKReader.__new__(VTKReader)
        reader.mesh = mesh
        reader.scalar_name = array_key
        reader.dimensions  = dims or (1, 1, 1)
        reader.is_3d       = False
        reader._interpolation_cache = {}
        _, _, z_grid, _ = reader.get_interpolated_slice(
            axis=self._axis, index=self._slice_index,
            scalar_name=array_key, component=component,
            resolution=self._resolution,
        )
        return (z_grid * scale).astype(np.float32)


# ---------------------------------------------------------------------------
# Backend A: Matplotlib imshow (CPU Agg)
# ---------------------------------------------------------------------------

class _MatplotlibCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fig    = Figure(figsize=(5, 5), tight_layout=True)
        self._ax     = self._fig.add_subplot(111)
        self._ax.set_axis_off()
        self._im     = None
        self._cbar   = None
        self._overlay = None
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

    def show_frame(self, z, cmap, vmin, vmax, *, title="", colorbar_label="", overlay=None):
        if self._im is None:
            self._im   = self._ax.imshow(z, origin="lower", aspect="equal",
                                          cmap=cmap, vmin=vmin, vmax=vmax,
                                          interpolation="bilinear")
            self._cbar = self._fig.colorbar(self._im, ax=self._ax,
                                             fraction=0.046, pad=0.04,
                                             shrink=0.78)
            self._cbar.ax.tick_params(labelsize=11)
        else:
            self._im.set_data(z)
        self._clear_overlay()
        if overlay is not None:
            overlay_values = np.asarray(overlay, dtype=float)
            self._overlay = self._ax.contourf(
                overlay_values,
                levels=[1.5, 3.5],
                colors=["#000000"],
                alpha=0.82,
                origin="lower",
                antialiased=True,
                zorder=3,
            )
        if title:
            self._ax.set_title(title, fontsize=9, pad=4)
        if self._cbar is not None:
            self._cbar.set_label(colorbar_label or "", fontsize=14)
        self._canvas.draw_idle()

    def _clear_overlay(self):
        if self._overlay is None:
            return
        try:
            self._overlay.remove()
        except AttributeError:
            for collection in getattr(self._overlay, "collections", []):
                collection.remove()
        self._overlay = None

    def reset(self):
        self._ax.clear()
        self._ax.set_axis_off()
        self._im = self._cbar = self._overlay = None
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class AnimationPlayer(QDialog):
    """Popup window that plays VTK timesteps fast."""

    def __init__(self, file_paths, scalar_def, axis, slice_index,
                 palette, vmin, vmax, resolution=320, colorbar_label="",
                 interfaces_overlay=False, parent=None):
        super().__init__(parent)
        self.setObjectName("animationPlayer")
        self.setWindowTitle("Animation Player")
        self.resize(580, 650)
        self.setModal(False)

        self._file_paths  = file_paths
        self._scalar_def  = scalar_def
        self._axis        = axis
        self._slice_index = slice_index
        self._vmin        = vmin
        self._vmax        = vmax
        self._resolution  = resolution
        self._colorbar_label = colorbar_label
        self._interfaces_overlay = interfaces_overlay
        self._cmap        = palette_to_cmap(palette)

        self._frames: list[np.ndarray | None] = [None] * len(file_paths)
        self._overlays: list[np.ndarray | None] = [None] * len(file_paths)
        self._frame_errors: dict[int, str] = {}
        self._current       = 0
        self._playing       = False
        self._fps           = 10
        self._load_finished = False
        self._exporting      = False
        self._closed        = False
        self._fetcher       = None
        self._thread        = None

        self._build_ui()
        self._start_fetch()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _apply_dialog_styles(self):
        self.setStyleSheet("""
QDialog#animationPlayer {
    background: #1e1e1e;
    color: #f3f6fb;
}
QDialog#animationPlayer QLabel {
    color: #f3f6fb;
    background: transparent;
}
QDialog#animationPlayer QLabel#mutedInfo {
    color: #d7e2f2;
}
QDialog#animationPlayer QComboBox {
    min-height: 28px;
    background: #2d2d30;
    color: #f3f6fb;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    padding: 2px 24px 2px 8px;
}
QDialog#animationPlayer QComboBox:hover,
QDialog#animationPlayer QComboBox:focus {
    border-color: #5a7fb0;
}
QDialog#animationPlayer QComboBox:disabled {
    background: #252526;
    color: #8f9bab;
    border-color: #333333;
}
QDialog#animationPlayer QComboBox::drop-down {
    border: none;
    width: 24px;
    background: transparent;
}
QDialog#animationPlayer QComboBox QAbstractItemView {
    background: #252526;
    color: #ffffff;
    border: 1px solid #3e3e42;
    selection-background-color: #3c3c3c;
    selection-color: #ffffff;
}
QDialog#animationPlayer QPushButton {
    background: #2d2d30;
    color: #f3f6fb;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    font-size: 17px;
    font-weight: 700;
    padding: 0px;
}
QDialog#animationPlayer QPushButton:hover {
    background: #38383d;
    border-color: #5a7fb0;
}
QDialog#animationPlayer QPushButton:pressed,
QDialog#animationPlayer QPushButton:checked {
    background: #0d2b55;
    border-color: #245a9c;
}
QDialog#animationPlayer QPushButton:disabled {
    background: #252526;
    color: #6f7a88;
    border-color: #333333;
}
QDialog#animationPlayer QSlider::groove:horizontal {
    height: 6px;
    background: #4a4d52;
    border-radius: 3px;
}
QDialog#animationPlayer QSlider::sub-page:horizontal {
    background: #4f8dcc;
    border-radius: 3px;
}
QDialog#animationPlayer QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: #ffffff;
    border: 2px solid #4f8dcc;
}
QDialog#animationPlayer QSlider:disabled::groove:horizontal {
    background: #333333;
}
QDialog#animationPlayer QSlider:disabled::handle:horizontal {
    background: #5a5a5a;
    border-color: #6f6f6f;
}
QDialog#animationPlayer QProgressBar {
    background: #333333;
    color: #ffffff;
    border: 1px solid #454545;
    border-radius: 3px;
    text-align: center;
}
QDialog#animationPlayer QProgressBar::chunk {
    background: #4f8dcc;
    border-radius: 3px;
}
""")

    def _build_ui(self):
        self._apply_dialog_styles()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setFormat("Loading %p% …")
        self._progress_bar.setFixedHeight(18)
        root.addWidget(self._progress_bar)

        self._status_label = QLabel("Preparing animation frames...")
        self._status_label.setObjectName("mutedInfo")
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._mpl_canvas = _MatplotlibCanvas()
        root.addWidget(self._mpl_canvas, 1)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)

        def _btn(icon_name, w=38):
            b = QPushButton()
            b.setFixedSize(w, 34)
            b.setIcon(QIcon(str(ASSETS_DIR / icon_name)))
            b.setIconSize(_TRANSPORT_ICON_SIZE)
            return b

        self._first_btn = _btn("rewind.png")
        self._prev_btn  = _btn("previous.png")
        self._stop_btn  = _btn("stop-button.png")
        self._play_btn  = _btn("play.png", 42)
        self._next_btn  = _btn("fast-forward.png", 42)
        self._last_btn  = _btn("next.png")
        for b in (self._first_btn, self._prev_btn, self._stop_btn,
                  self._play_btn, self._next_btn, self._last_btn):
            ctrl.addWidget(b)
        ctrl.addSpacing(8)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, max(0, len(self._file_paths) - 1))
        ctrl.addWidget(self._slider, 1)
        ctrl.addSpacing(8)

        self._frame_label = QLabel("– / –")
        self._frame_label.setMinimumWidth(64)
        ctrl.addWidget(self._frame_label)
        ctrl.addSpacing(4)

        self._fps_combo = QComboBox()
        for lbl, fps in [("1 fps", 1), ("2 fps", 2), ("5 fps", 5), ("10 fps", 10), ("15 fps", 15),
                          ("20 fps", 20), ("30 fps", 30)]:
            self._fps_combo.addItem(lbl, fps)
        self._fps_combo.setCurrentIndex(3)
        ctrl.addWidget(self._fps_combo)

        self._export_btn = QPushButton(QIcon(str(ASSETS_DIR / "download.png")), "MP4")
        self._export_btn.setFixedHeight(34)
        self._export_btn.setIconSize(QSize(18, 18))
        self._export_btn.setToolTip("Export loaded animation as MP4")
        ctrl.addWidget(self._export_btn)

        root.addLayout(ctrl)

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

        # Connections
        self._first_btn.clicked.connect(lambda: self._jump(0))
        self._prev_btn.clicked.connect(lambda: self._jump(self._current - 1))
        self._stop_btn.clicked.connect(self._stop)
        self._play_btn.clicked.connect(self._toggle_play)
        self._next_btn.clicked.connect(lambda: self._jump(self._current + 1))
        self._last_btn.clicked.connect(lambda: self._jump(len(self._file_paths) - 1))
        self._slider.valueChanged.connect(self._jump)
        self._fps_combo.currentIndexChanged.connect(self._on_fps_changed)
        self._export_btn.clicked.connect(self._export_mp4)

        self._set_transport_enabled(False)
        self._export_btn.setEnabled(False)

    def _active_canvas(self):
        return self._mpl_canvas

    def _set_play_icon(self, icon_name):
        self._play_btn.setIcon(QIcon(str(ASSETS_DIR / icon_name)))
        self._play_btn.setIconSize(_TRANSPORT_ICON_SIZE)

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _start_fetch(self):
        if not self._file_paths:
            self._load_finished = True
            self._progress_bar.hide()
            self._frame_label.setText("0 / 0")
            self._set_transport_enabled(False)
            self._set_status("No frames available.")
            return

        self._fetcher = _FrameFetcher(
            self._file_paths, self._scalar_def,
            self._axis, self._slice_index, self._resolution,
            interfaces_overlay=self._interfaces_overlay,
        )
        self._thread = QThread(self)
        self._fetcher.moveToThread(self._thread)
        self._thread.started.connect(self._fetcher.run)
        self._fetcher.frame_ready.connect(self._on_frame_ready)
        self._fetcher.frame_error.connect(self._on_frame_error)
        self._fetcher.progress.connect(self._progress_bar.setValue)
        self._fetcher.finished.connect(self._on_fetch_done)
        self._fetcher.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_frame_ready(self, index, payload):
        if self._closed or not (0 <= index < len(self._frames)):
            return
        if isinstance(payload, tuple) and len(payload) == 2:
            z, overlay = payload
        else:
            z, overlay = payload, None
        self._frames[index] = z
        self._overlays[index] = overlay
        self._frame_errors.pop(index, None)
        self._update_loading_status(index)
        if z is not None and not self._has_valid_frame_before(index):
            self._set_transport_enabled(True)
            self._show(index)

    def _on_frame_error(self, index, message):
        if self._closed or not (0 <= index < len(self._frames)):
            return
        self._frames[index] = None
        self._frame_errors[index] = message
        self._update_loading_status(index)

    def _on_fetch_done(self):
        if self._closed:
            return
        self._load_finished = True
        self._progress_bar.hide()
        valid_index = self._first_valid_index(self._frames)
        if valid_index is None:
            self._pause()
            self._set_transport_enabled(False)
            self._export_btn.setEnabled(False)
            self._frame_label.setText(f"0 / {len(self._file_paths)}")
            self._set_status(self._summary_status("No valid frames."))
            return

        self._set_transport_enabled(True)
        self._export_btn.setEnabled(True)
        if self._frames[self._current] is None:
            self._show(valid_index)
        else:
            self._show(self._current)
        self._start_play()

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _set_transport_enabled(self, enabled):
        for w in (self._first_btn, self._prev_btn, self._stop_btn,
                  self._play_btn, self._next_btn, self._last_btn,
                  self._slider):
            w.setEnabled(enabled)
        if hasattr(self, "_export_btn"):
            self._export_btn.setEnabled(enabled and self._load_finished and self._first_valid_index(self._frames) is not None)

    def _toggle_play(self):
        self._pause() if self._playing else self._start_play()

    def _start_play(self):
        if self._first_valid_index(self._frames) is None:
            self._pause()
            self._set_transport_enabled(False)
            self._set_status(self._summary_status("No valid frames."))
            return
        self._playing = True
        self._set_play_icon("pause.png")
        self._timer.start(1000 // self._fps)

    def _pause(self):
        self._playing = False
        self._timer.stop()
        self._set_play_icon("play.png")

    def _stop(self):
        self._pause()
        self._jump(0)

    def _advance(self):
        nxt = self._next_valid_index(self._frames, self._current + 1)
        if nxt is None:
            self._pause()
            self._set_transport_enabled(False)
            self._set_status(self._summary_status("No valid frames."))
            return
        self._show(nxt)

    def _jump(self, index):
        if not self._file_paths:
            self._pause()
            self._frame_label.setText("0 / 0")
            self._set_status("No frames available.")
            return
        index = max(0, min(index, len(self._file_paths) - 1))
        direction = 1 if index >= self._current else -1
        valid_index = self._nearest_valid_index(self._frames, index, direction)
        if valid_index is None:
            self._pause()
            self._set_status(self._summary_status("No valid frames."))
            return
        self._show(valid_index)

    def _show(self, index):
        if not (0 <= index < len(self._frames)):
            return
        z = self._frames[index]
        if z is None:
            self._set_status(self._summary_status("Frame is not available."))
            return
        self._current = index
        n = len(self._file_paths)
        self._frame_label.setText(f"{index + 1} / {n}")
        self._slider.blockSignals(True)
        self._slider.setValue(index)
        self._slider.blockSignals(False)
        from pathlib import Path
        self._active_canvas().show_frame(
            z, self._cmap, self._vmin, self._vmax,
            title=Path(self._file_paths[index]).name,
            colorbar_label=self._colorbar_label,
            overlay=self._overlays[index],
        )
        self._set_status(self._summary_status(Path(self._file_paths[index]).name))

    def _on_fps_changed(self, idx):
        self._fps = self._fps_combo.itemData(idx) or 10
        if self._playing:
            self._timer.setInterval(1000 // self._fps)

    def _export_mp4(self):
        valid_indices = self._valid_frame_indices(self._frames)
        if not self._load_finished:
            self._set_status("Wait for all frames to load before exporting MP4.")
            return
        if not valid_indices:
            self._set_status("No valid frames available for MP4 export.")
            return
        encoder_error = self._mp4_encoder_error()
        if encoder_error:
            if self._offer_ffmpeg_install():
                return
            self._set_status(encoder_error)
            QMessageBox.warning(
                self,
                "MP4 Export Unavailable",
                encoder_error,
            )
            return

        default_name = self._default_export_name()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Animation",
            default_name,
            "MP4 Video (*.mp4)",
        )
        if not path:
            return
        if not path.lower().endswith(".mp4"):
            path = f"{path}.mp4"

        was_playing = self._playing
        self._pause()
        self._exporting = True
        self._export_btn.setEnabled(False)
        self._set_status(f"Exporting MP4 at {self._fps} fps...")
        try:
            self._write_mp4(Path(path), valid_indices)
        except FileNotFoundError:
            message = self._mp4_encoder_missing_message()
            self._set_status(message)
            QMessageBox.warning(self, "MP4 Export Unavailable", message)
        except Exception as exc:
            self._set_status(f"MP4 export failed: {exc}")
            QMessageBox.warning(
                self,
                "MP4 Export Failed",
                f"Could not export MP4.\n\n{exc}",
            )
        else:
            self._set_status(f"MP4 exported: {Path(path).name}")
            QMessageBox.information(
                self,
                "MP4 Export Complete",
                f"MP4 exported successfully.\n\n{path}",
            )
        finally:
            self._exporting = False
            self._export_btn.setEnabled(True)
            if was_playing:
                self._start_play()

    def _mp4_encoder_error(self):
        try:
            from matplotlib.animation import FFMpegWriter
        except Exception as exc:
            return f"MP4 export is unavailable because Matplotlib could not load FFmpeg support: {exc}"
        if not FFMpegWriter.isAvailable():
            return self._mp4_encoder_missing_message()
        return ""

    def _offer_ffmpeg_install(self):
        if not self._is_windows_winget_available():
            return False
        response = QMessageBox.question(
            self,
            "Install FFmpeg?",
            (
                "MP4 export requires FFmpeg, but it was not found.\n\n"
                "Do you want OPView to start the Windows FFmpeg installer using winget?\n\n"
                "After installation finishes, restart OPView before exporting MP4."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if response != QMessageBox.StandardButton.Yes:
            return False
        try:
            subprocess.Popen(
                [
                    "winget",
                    "install",
                    "--id",
                    "Gyan.FFmpeg",
                    "-e",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )
        except Exception as exc:
            self._set_status(f"Could not start FFmpeg installer: {exc}")
            QMessageBox.warning(
                self,
                "FFmpeg Install Failed",
                f"Could not start the FFmpeg installer.\n\n{exc}",
            )
            return True
        self._set_status("FFmpeg installer started. Restart OPView after installation finishes.")
        QMessageBox.information(
            self,
            "FFmpeg Installer Started",
            "The FFmpeg installer has started in a separate window.\n\nRestart OPView after installation finishes, then export MP4 again.",
        )
        return True

    @staticmethod
    def _is_windows_winget_available():
        return shutil.which("winget") is not None

    @staticmethod
    def _mp4_encoder_missing_message():
        return (
            "MP4 export requires FFmpeg, but ffmpeg.exe was not found. "
            "Install FFmpeg with winget or add ffmpeg.exe to PATH, then restart OPView and export again."
        )

    def _write_mp4(self, path: Path, frame_indices):
        from matplotlib.animation import FFMpegWriter

        writer = FFMpegWriter(fps=self._fps)
        fig = Figure(figsize=(6, 6), tight_layout=True)
        canvas = FigureCanvasQTAgg(fig)
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        first_index = frame_indices[0]
        image = ax.imshow(
            self._frames[first_index],
            origin="lower",
            aspect="equal",
            cmap=self._cmap,
            vmin=self._vmin,
            vmax=self._vmax,
            interpolation="bilinear",
        )
        cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, shrink=0.78)
        cbar.ax.tick_params(labelsize=11)
        cbar.set_label(self._colorbar_label or "", fontsize=14)
        overlay_artist = None

        with writer.saving(fig, str(path), dpi=150):
            for index in frame_indices:
                image.set_data(self._frames[index])
                ax.set_title(Path(self._file_paths[index]).name, fontsize=9, pad=4)
                overlay_artist = self._draw_export_overlay(ax, overlay_artist, self._overlays[index])
                canvas.draw()
                writer.grab_frame()

    def _draw_export_overlay(self, ax, overlay_artist, overlay):
        self._remove_overlay_artist(overlay_artist)
        if overlay is None:
            return None
        return ax.contourf(
            np.asarray(overlay, dtype=float),
            levels=[1.5, 3.5],
            colors=["#000000"],
            alpha=0.82,
            origin="lower",
            antialiased=True,
            zorder=3,
        )

    @staticmethod
    def _remove_overlay_artist(overlay_artist):
        if overlay_artist is None:
            return
        try:
            overlay_artist.remove()
        except AttributeError:
            for collection in getattr(overlay_artist, "collections", []):
                collection.remove()

    def _default_export_name(self):
        stem = Path(self._file_paths[self._current]).stem if self._file_paths else "animation"
        return str(Path.cwd() / f"{stem}_animation.mp4")

    @staticmethod
    def _first_valid_index(frames):
        return next((i for i, frame in enumerate(frames) if frame is not None), None)

    @staticmethod
    def _valid_frame_indices(frames):
        return [i for i, frame in enumerate(frames) if frame is not None]

    @staticmethod
    def _next_valid_index(frames, start, direction=1):
        if not frames:
            return None
        step = 1 if direction >= 0 else -1
        n = len(frames)
        for offset in range(n):
            index = (start + (offset * step)) % n
            if frames[index] is not None:
                return index
        return None

    @classmethod
    def _nearest_valid_index(cls, frames, target, direction=1):
        if not frames:
            return None
        n = len(frames)
        target = max(0, min(target, n - 1))
        step = 1 if direction >= 0 else -1
        for offset in range(n):
            index = target + (offset * step)
            if 0 <= index < n and frames[index] is not None:
                return index
        return cls._next_valid_index(frames, target, -step)

    def _has_valid_frame_before(self, index):
        return any(frame is not None for frame in self._frames[:index])

    def _update_loading_status(self, index):
        total = len(self._file_paths)
        loaded = sum(frame is not None for frame in self._frames)
        failed = len(self._frame_errors)
        pending = max(0, total - loaded - failed)
        self._set_status(
            f"Loading frame {index + 1}/{total} - "
            f"{loaded} loaded, {failed} failed, {pending} pending."
        )

    def _summary_status(self, prefix=""):
        total = len(self._file_paths)
        loaded = sum(frame is not None for frame in self._frames)
        failed = len(self._frame_errors)
        pending = max(0, total - loaded - failed)
        parts = []
        if prefix:
            parts.append(prefix)
        parts.append(f"{loaded}/{total} loaded")
        if failed:
            parts.append(f"{failed} failed")
        if pending:
            parts.append(f"{pending} pending")
        return " - ".join(parts) + "."

    def _set_status(self, message):
        if not self._closed:
            self._status_label.setText(message)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _disconnect_fetcher_signals(self):
        if self._fetcher is None:
            return
        for signal, slot in (
            (self._fetcher.frame_ready, self._on_frame_ready),
            (self._fetcher.frame_error, self._on_frame_error),
            (self._fetcher.progress, self._progress_bar.setValue),
            (self._fetcher.finished, self._on_fetch_done),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def closeEvent(self, event):
        self._closed = True
        self._timer.stop()
        if self._fetcher is not None:
            self._fetcher.abort()
            self._disconnect_fetcher_signals()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            stopped = self._thread.wait(2000)
            if not stopped:
                self._status_label.setText("Animation loader is still shutting down.")
        super().closeEvent(event)
