"""QTimer-based playback controller for stepping through VTK file frames."""

from PySide6.QtCore import QObject, QTimer, Signal


class PlaybackController(QObject):
    """Manages play/pause/stop state and fires frame_changed at the requested FPS."""

    frame_changed = Signal(int)   # 0-based frame index
    state_changed = Signal(str)   # "playing" | "paused" | "stopped"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._frame_count: int = 0
        self._current_frame: int = 0
        self._fps: int = 2
        self._loop: bool = True
        self._state: str = "stopped"

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._state == "playing"

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def current_frame(self) -> int:
        return self._current_frame

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_frame_count(self, n: int) -> None:
        was_playing = self.is_playing
        if was_playing:
            self._timer.stop()
        self._frame_count = max(0, n)
        self._current_frame = min(self._current_frame, max(0, n - 1))
        if was_playing and self._frame_count > 1:
            self._timer.start(1000 // self._fps)

    def set_fps(self, fps: int) -> None:
        self._fps = max(1, fps)
        if self.is_playing:
            self._timer.setInterval(1000 // self._fps)

    def set_loop(self, loop: bool) -> None:
        self._loop = loop

    # ------------------------------------------------------------------
    # Playback commands
    # ------------------------------------------------------------------

    def play(self) -> None:
        if self._frame_count < 2:
            return
        self._state = "playing"
        self._timer.start(1000 // self._fps)
        self.state_changed.emit("playing")

    def pause(self) -> None:
        self._timer.stop()
        self._state = "paused"
        self.state_changed.emit("paused")

    def stop(self) -> None:
        self._timer.stop()
        self._state = "stopped"
        self.state_changed.emit("stopped")
        self.set_frame(0)

    def step(self, delta: int) -> None:
        self.set_frame(self._current_frame + delta)

    def set_frame(self, index: int) -> None:
        if self._frame_count == 0:
            return
        clamped = max(0, min(index, self._frame_count - 1))
        self._current_frame = clamped
        self.frame_changed.emit(clamped)

    def set_frame_last(self) -> None:
        self.set_frame(self._frame_count - 1)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _advance(self) -> None:
        next_frame = self._current_frame + 1
        if next_frame >= self._frame_count:
            if self._loop:
                next_frame = 0
            else:
                self.stop()
                return
        self._current_frame = next_frame
        self.frame_changed.emit(next_frame)
