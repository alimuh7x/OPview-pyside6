"""Fast animation player — two render backends: Matplotlib and Qt Pixmap."""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from viewer.colorscale import palette_to_cmap


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class _FrameFetcher(QObject):
    frame_ready = Signal(int, object)
    finished    = Signal()
    progress    = Signal(int)

    def __init__(self, file_paths, scalar_def, axis, slice_index, resolution):
        super().__init__()
        self._file_paths  = file_paths
        self._scalar_def  = scalar_def
        self._axis        = axis
        self._slice_index = slice_index
        self._resolution  = resolution
        self._abort       = False

    def abort(self):
        self._abort = True

    def run(self):
        import pyvista as pv
        total     = len(self._file_paths)
        scale     = self._scalar_def.get("scale", 1.0) or 1.0
        array_key = self._scalar_def["array"]
        component = self._scalar_def.get("component")
        for i, path in enumerate(self._file_paths):
            if self._abort:
                break
            try:
                z = self._fast_load(pv.read(path), array_key, component, scale)
                self.frame_ready.emit(i, z)
            except Exception:
                self.frame_ready.emit(i, None)
            self.progress.emit(int((i + 1) / total * 100))
        self.finished.emit()

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
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

    def show_frame(self, z, cmap, vmin, vmax, *, title=""):
        if self._im is None:
            self._im   = self._ax.imshow(z, origin="lower", aspect="auto",
                                          cmap=cmap, vmin=vmin, vmax=vmax,
                                          interpolation="nearest")
            self._cbar = self._fig.colorbar(self._im, ax=self._ax,
                                             fraction=0.046, pad=0.04)
            self._canvas.draw()
        else:
            self._im.set_data(z)
            self._canvas.draw_idle()
        if title:
            self._ax.set_title(title, fontsize=9, pad=4)

    def reset(self):
        self._ax.clear()
        self._ax.set_axis_off()
        self._im = self._cbar = None
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# Backend B: Qt Pixmap (numpy → QImage → QLabel, near-zero overhead)
# ---------------------------------------------------------------------------

class _PixmapCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._img_label  = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._img_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._img_label.setScaledContents(False)

        # Colorbar: thin matplotlib figure (rendered once per cmap/range)
        self._cbar_fig    = Figure(figsize=(0.5, 4), tight_layout=True)
        self._cbar_ax     = self._cbar_fig.add_subplot(111)
        self._cbar_canvas = FigureCanvasQTAgg(self._cbar_fig)
        self._cbar_canvas.setFixedWidth(70)
        self._cbar_canvas.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._cbar_drawn  = False

        self._title_label = QLabel()
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-size: 9px;")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(self._img_label, 1)
        row.addWidget(self._cbar_canvas)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self._title_label)
        lay.addLayout(row, 1)

        self._cmap = None
        self._vmin = self._vmax = 0.0

    def show_frame(self, z, cmap, vmin, vmax, *, title=""):
        # Draw colorbar once (or if cmap/range changed)
        if not self._cbar_drawn or cmap is not self._cmap or vmin != self._vmin or vmax != self._vmax:
            self._cmap = cmap
            self._vmin = vmin
            self._vmax = vmax
            self._draw_colorbar(cmap, vmin, vmax)
            self._cbar_drawn = True

        # Normalize → apply colormap → RGBA uint8
        span = vmax - vmin if vmax != vmin else 1.0
        norm = np.clip((z.astype(np.float32) - vmin) / span, 0.0, 1.0)
        rgba = (cmap(norm) * 255).astype(np.uint8)

        h, w = rgba.shape[:2]
        img  = QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        pix  = QPixmap.fromImage(img).scaled(
            self._img_label.width() or w,
            self._img_label.height() or h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._img_label.setPixmap(pix)

        if title:
            self._title_label.setText(title)

    def _draw_colorbar(self, cmap, vmin, vmax):
        import matplotlib as mpl
        self._cbar_ax.clear()
        norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
        cb   = self._cbar_fig.colorbar(
            mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
            cax=self._cbar_ax,
        )
        cb.ax.tick_params(labelsize=7)
        self._cbar_canvas.draw()

    def reset(self):
        self._img_label.clear()
        self._cbar_drawn = False


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class AnimationPlayer(QDialog):
    """Popup window that plays VTK timesteps fast."""

    _BACKENDS = ["Qt Pixmap (fastest)", "Matplotlib imshow"]

    def __init__(self, file_paths, scalar_def, axis, slice_index,
                 palette, vmin, vmax, resolution=160, parent=None):
        super().__init__(parent)
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
        self._cmap        = palette_to_cmap(palette)

        self._frames: list[np.ndarray | None] = [None] * len(file_paths)
        self._current  = 0
        self._playing  = False
        self._fps      = 10

        self._build_ui()
        self._start_fetch()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Top bar: renderer selector
        top = QHBoxLayout()
        top.addWidget(QLabel("Renderer:"))
        self._renderer_combo = QComboBox()
        for name in self._BACKENDS:
            self._renderer_combo.addItem(name)
        self._renderer_combo.setCurrentIndex(0)
        top.addWidget(self._renderer_combo)
        top.addStretch(1)
        root.addLayout(top)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setFormat("Loading %p% …")
        self._progress_bar.setFixedHeight(18)
        root.addWidget(self._progress_bar)

        # Stacked canvas: index 0 = Qt Pixmap, index 1 = Matplotlib
        self._pixmap_canvas = _PixmapCanvas()
        self._mpl_canvas    = _MatplotlibCanvas()
        self._stack = QStackedWidget()
        self._stack.addWidget(self._pixmap_canvas)   # index 0
        self._stack.addWidget(self._mpl_canvas)      # index 1
        self._stack.setCurrentIndex(0)
        root.addWidget(self._stack, 1)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)

        def _btn(t, w=28):
            b = QPushButton(t)
            b.setFixedSize(w, 28)
            return b

        self._first_btn = _btn("⏮")
        self._prev_btn  = _btn("◀")
        self._stop_btn  = _btn("⏹")
        self._play_btn  = _btn("▶", 34)
        self._next_btn  = _btn("▶▶")
        self._last_btn  = _btn("⏭")
        for b in (self._first_btn, self._prev_btn, self._stop_btn,
                  self._play_btn, self._next_btn, self._last_btn):
            ctrl.addWidget(b)
        ctrl.addSpacing(8)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, max(0, len(self._file_paths) - 1))
        ctrl.addWidget(self._slider, 1)
        ctrl.addSpacing(8)

        self._frame_label = QLabel("– / –")
        self._frame_label.setMinimumWidth(52)
        ctrl.addWidget(self._frame_label)
        ctrl.addSpacing(4)

        self._fps_combo = QComboBox()
        for lbl, fps in [("5 fps", 5), ("10 fps", 10), ("15 fps", 15),
                          ("20 fps", 20), ("30 fps", 30)]:
            self._fps_combo.addItem(lbl, fps)
        self._fps_combo.setCurrentIndex(1)
        ctrl.addWidget(self._fps_combo)

        root.addLayout(ctrl)

        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

        # Connections
        self._renderer_combo.currentIndexChanged.connect(self._on_renderer_changed)
        self._first_btn.clicked.connect(lambda: self._jump(0))
        self._prev_btn.clicked.connect(lambda: self._jump(self._current - 1))
        self._stop_btn.clicked.connect(self._stop)
        self._play_btn.clicked.connect(self._toggle_play)
        self._next_btn.clicked.connect(lambda: self._jump(self._current + 1))
        self._last_btn.clicked.connect(lambda: self._jump(len(self._file_paths) - 1))
        self._slider.sliderMoved.connect(self._jump)
        self._fps_combo.currentIndexChanged.connect(self._on_fps_changed)

        self._set_controls_enabled(False)

    def _active_canvas(self):
        return self._stack.currentWidget()

    def _on_renderer_changed(self, idx):
        self._stack.setCurrentIndex(idx)
        # Re-show current frame in the newly selected backend
        z = self._frames[self._current]
        if z is not None:
            from pathlib import Path
            self._active_canvas().show_frame(
                z, self._cmap, self._vmin, self._vmax,
                title=Path(self._file_paths[self._current]).name,
            )

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _start_fetch(self):
        self._fetcher = _FrameFetcher(
            self._file_paths, self._scalar_def,
            self._axis, self._slice_index, self._resolution,
        )
        self._thread = QThread(self)
        self._fetcher.moveToThread(self._thread)
        self._thread.started.connect(self._fetcher.run)
        self._fetcher.frame_ready.connect(self._on_frame_ready)
        self._fetcher.progress.connect(self._progress_bar.setValue)
        self._fetcher.finished.connect(self._on_fetch_done)
        self._fetcher.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_frame_ready(self, index, z):
        self._frames[index] = z
        if index == 0 and z is not None:
            self._show(0)

    def _on_fetch_done(self):
        self._progress_bar.hide()
        self._set_controls_enabled(True)
        self._frame_label.setText(f"1 / {len(self._file_paths)}")
        self._start_play()

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _set_controls_enabled(self, enabled):
        for w in (self._first_btn, self._prev_btn, self._stop_btn,
                  self._play_btn, self._next_btn, self._last_btn,
                  self._slider, self._fps_combo):
            w.setEnabled(enabled)

    def _toggle_play(self):
        self._pause() if self._playing else self._start_play()

    def _start_play(self):
        self._playing = True
        self._play_btn.setText("⏸")
        self._timer.start(1000 // self._fps)

    def _pause(self):
        self._playing = False
        self._timer.stop()
        self._play_btn.setText("▶")

    def _stop(self):
        self._pause()
        self._jump(0)

    def _advance(self):
        nxt = (self._current + 1) % len(self._file_paths)
        self._show(nxt)

    def _jump(self, index):
        index = max(0, min(index, len(self._file_paths) - 1))
        self._show(index)

    def _show(self, index):
        z = self._frames[index]
        if z is None:
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
        )

    def _on_fps_changed(self, idx):
        self._fps = self._fps_combo.itemData(idx) or 10
        if self._playing:
            self._timer.setInterval(1000 // self._fps)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self._timer.stop()
        if hasattr(self, "_fetcher"):
            self._fetcher.abort()
        if hasattr(self, "_thread") and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
