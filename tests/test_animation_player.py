import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import numpy as np
    from PySide6.QtWidgets import QApplication
    from viewer.animation_player import AnimationPlayer, _FrameFetcher, _MatplotlibCanvas
except ModuleNotFoundError as exc:
    QApplication = None
    AnimationPlayer = None
    _FrameFetcher = None
    _MatplotlibCanvas = None
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
            self.assertEqual(player._logo_label.objectName(), "animationLogo")
            self.assertFalse(player._logo_label.pixmap().isNull())
            self.assertEqual(player._canvas_row_widget.objectName(), "animationCanvasRow")
            self.assertEqual(player._logo_label.width(), 76)
            self.assertLessEqual(player._logo_label.pixmap().width(), player._logo_label.width())
            self.assertIn("background: #ffffff", player.styleSheet())
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

    def test_player_keeps_phase_fraction_animation_specs(self):
        specs = [
            {
                "label": "Austenite",
                "array": "PhaseFraction_0",
                "component": None,
                "scale": 1.0,
                "range": (0.2, 1.0),
                "color": "#f0a202",
            }
        ]

        player = AnimationPlayer(
            [],
            {"array": "PhaseFraction_0"},
            "z",
            0,
            "Aqua Fire",
            0.2,
            1.0,
            plot_type="threshold",
            phase_fraction_specs=specs,
        )
        try:
            self.assertEqual(player._plot_type, "threshold")
            self.assertEqual(player._phase_fraction_specs, specs)
        finally:
            player.close()

    def test_player_applies_rotation_to_loaded_frames_and_overlays(self):
        player = AnimationPlayer(
            [],
            {"array": "PhaseFraction_0"},
            "z",
            0,
            "Aqua Fire",
            0.0,
            1.0,
            rotation_degrees=90,
            plot_type="threshold",
        )
        try:
            player._file_paths = ["first.vts"]
            player._frames = [None]
            player._overlays = [None]
            player._phase_fraction_overlays = [[]]
            z = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
            overlay = np.array([[10, 20, 30], [40, 50, 60]], dtype=np.float32)
            phase_overlay = {
                "label": "Austenite",
                "z": np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32),
                "range": (0.2, 1.0),
                "color": "#f0a202",
            }

            player._on_frame_ready(
                0,
                {
                    "z": z,
                    "overlay": overlay,
                    "phase_fraction_overlays": [phase_overlay],
                },
            )

            np.testing.assert_array_equal(player._frames[0], np.rot90(z, k=-1))
            np.testing.assert_array_equal(player._overlays[0], np.rot90(overlay, k=-1))
            np.testing.assert_array_equal(
                player._phase_fraction_overlays[0][0]["z"],
                np.rot90(phase_overlay["z"], k=-1),
            )
        finally:
            player.close()

    def test_animation_overlay_file_prefers_phasefield_over_distorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            source = vtk_dir / "ElasticStrains_00005000.vts"
            phase = vtk_dir / "PhaseField_00005000.vts"
            distorted = vtk_dir / "PhaseFieldDistorted_00005000.vts"
            source.write_text("", encoding="utf-8")
            phase.write_text("", encoding="utf-8")
            distorted.write_text("", encoding="utf-8")

            self.assertEqual(_FrameFetcher._phase_overlay_file(str(source)), phase)

    def test_animation_overlay_file_falls_back_to_distorted_phasefield(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            source = vtk_dir / "ElasticStrains_00005000.vts"
            distorted = vtk_dir / "PhaseFieldDistorted_00005000.vts"
            source.write_text("", encoding="utf-8")
            distorted.write_text("", encoding="utf-8")

            self.assertEqual(_FrameFetcher._phase_overlay_file(str(source)), distorted)

    def test_animation_overlay_file_prefers_phasefield_when_source_is_distorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            vtk_dir = Path(tmp)
            phase = vtk_dir / "PhaseField_00005000.vts"
            distorted = vtk_dir / "PhaseFieldDistorted_00005000.vts"
            phase.write_text("", encoding="utf-8")
            distorted.write_text("", encoding="utf-8")

            self.assertEqual(_FrameFetcher._phase_overlay_file(str(distorted)), phase)

    def test_matplotlib_canvas_draws_phase_fraction_overlays_with_legend(self):
        canvas = _MatplotlibCanvas()
        try:
            z = np.zeros((2, 2), dtype=np.float32)
            overlays = [
                {
                    "label": "Austenite",
                    "z": np.array([[0.0, 0.7], [0.8, 0.1]], dtype=np.float32),
                    "range": (0.5, 1.0),
                    "color": "#f0a202",
                }
            ]

            canvas.show_frame(
                z,
                "viridis",
                0.0,
                1.0,
                phase_fraction_overlays=overlays,
                plot_type="threshold",
            )

            self.assertIsNone(canvas._cbar)
            self.assertEqual(len(canvas._phase_overlays), 1)
            self.assertIsNotNone(canvas._ax.get_legend())
            self.assertGreater(canvas._ax.get_legend().get_bbox_to_anchor()._bbox.x0, 1.0)
        finally:
            canvas.deleteLater()

    def test_matplotlib_canvas_masks_scalar_threshold_frames(self):
        canvas = _MatplotlibCanvas()
        try:
            z = np.array([[0.1, 0.6], [0.8, 1.2]], dtype=np.float32)

            canvas.show_frame(z, "viridis", 0.5, 1.0, plot_type="threshold")

            rendered = np.asarray(canvas._im.get_array(), dtype=float)
            self.assertTrue(np.isnan(rendered[0, 0]))
            self.assertFalse(np.isnan(rendered[0, 1]))
            self.assertFalse(np.isnan(rendered[1, 0]))
            self.assertTrue(np.isnan(rendered[1, 1]))
        finally:
            canvas.deleteLater()

    def test_export_figure_adds_logo_axes(self):
        player = AnimationPlayer([], {"array": "unused"}, "z", 0, "Aqua Fire", 0.0, 1.0)
        try:
            fig = player._build_export_figure()

            self.assertIsNotNone(player._export_logo_ax)
            self.assertIn(player._export_logo_ax, fig.axes)
            self.assertFalse(player._export_logo_ax.axison)
        finally:
            player.close()


if __name__ == "__main__":
    unittest.main()
