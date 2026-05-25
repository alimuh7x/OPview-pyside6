import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import numpy as np
    from PySide6.QtWidgets import QApplication
    from viewer.animation_player import AnimationPlayer
except ModuleNotFoundError as exc:
    QApplication = None
    AnimationPlayer = None
    np = None
    MISSING_DEPENDENCY = exc.name
else:
    MISSING_DEPENDENCY = None


@unittest.skipIf(MISSING_DEPENDENCY is not None, f"missing dependency: {MISSING_DEPENDENCY}")
class AnimationPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is not None:
            cls._app = QApplication.instance() or QApplication([])

    def test_next_valid_index_skips_missing_frames(self):
        frames = [None, object(), None, object()]

        self.assertEqual(AnimationPlayer._next_valid_index(frames, 0), 1)
        self.assertEqual(AnimationPlayer._next_valid_index(frames, 2), 3)
        self.assertEqual(AnimationPlayer._next_valid_index(frames, 4), 1)

    def test_next_valid_index_returns_none_when_no_frame_is_valid(self):
        self.assertIsNone(AnimationPlayer._next_valid_index([None, None], 0))
        self.assertIsNone(AnimationPlayer._next_valid_index([], 0))

    def test_nearest_valid_index_falls_back_to_available_frame(self):
        frames = [object(), None, None, object()]

        self.assertEqual(AnimationPlayer._nearest_valid_index(frames, 1, 1), 3)
        self.assertEqual(AnimationPlayer._nearest_valid_index(frames, 2, -1), 0)

    def test_empty_file_list_does_not_start_loading_or_playback(self):
        player = AnimationPlayer([], {"array": "unused"}, "z", 0, "Aqua Fire", 0.0, 1.0)
        try:
            self.assertEqual(player.objectName(), "animationPlayer")
            self.assertIn("QDialog#animationPlayer QLabel", player.styleSheet())
            self.assertFalse(player._playing)
            self.assertIsNone(player._thread)
            self.assertEqual(player._frame_label.text(), "0 / 0")
            self.assertIn("No frames available", player._status_label.text())
            self.assertFalse(player._play_btn.isEnabled())
            self.assertTrue(player._fps_combo.isEnabled())
            self.assertFalse(hasattr(player, "_renderer_combo"))
        finally:
            player.close()

    def test_controls_enable_after_first_valid_frame(self):
        player = AnimationPlayer([], {"array": "unused"}, "z", 0, "Aqua Fire", 0.0, 1.0)
        try:
            player._file_paths = ["first.vts"]
            frame = np.zeros((2, 2), dtype=np.float32)
            player._frames = [None]
            player._on_frame_ready(0, frame)

            self.assertTrue(player._play_btn.isEnabled())
            self.assertEqual(player._frame_label.text(), "1 / 1")
        finally:
            player.close()


if __name__ == "__main__":
    unittest.main()
