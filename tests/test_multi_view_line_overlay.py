import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from multi_view.multi_view_panel import MultiViewPanel
from viewer.heatmap_orientation import Heatmap2DOrientation

_VTK_FILE = Path("Project1/VTK/PhaseField_00000000.vts").resolve()


class MultiViewLineOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel_with_recorded_overlays(self):
        fp = str(_VTK_FILE)
        info = {
            "label": "demo",
            "available_projects": [
                {
                    "files": [fp],
                    "dataset_config": {"scalars": [{"label": "PhaseFields", "array": "PhaseFields"}]},
                }
            ],
        }
        panel = MultiViewPanel(info)
        panel._add_column(fp)
        cell = panel._columns[fp][1]
        overlays: list = []
        original_render = cell.render

        def recording_render(*args, **kwargs):
            overlays.append(kwargs.get("line_overlay"))
            return original_render(*args, **kwargs)

        cell.render = recording_render
        return panel, overlays

    def test_line_appears_when_line_scan_is_enabled_without_a_click(self):
        panel, overlays = self._panel_with_recorded_overlays()

        panel.line_mode_check.setChecked(True)

        self.assertIsNotNone(overlays[-1])
        self.assertEqual(overlays[-1][0], "horizontal")

    def test_line_appears_when_show_line_is_toggled_on_without_a_click(self):
        panel, overlays = self._panel_with_recorded_overlays()
        panel.line_mode_check.setChecked(True)
        panel.show_line_check.setChecked(False)
        self.assertIsNone(overlays[-1])

        panel.show_line_check.setChecked(True)

        self.assertIsNotNone(overlays[-1])

    def test_vertical_line_appears_without_a_click(self):
        panel, overlays = self._panel_with_recorded_overlays()
        panel.line_mode_check.setChecked(True)

        panel._set_line_scan_direction("vertical")
        panel.show_line_check.setChecked(False)
        panel.show_line_check.setChecked(True)

        self.assertIsNotNone(overlays[-1])
        self.assertEqual(overlays[-1][0], "vertical")

    def test_default_line_sits_where_the_line_graph_samples(self):
        panel, overlays = self._panel_with_recorded_overlays()
        panel.line_mode_check.setChecked(True)
        x_grid, y_grid, z_grid = panel._grid_cache[str(_VTK_FILE)]

        sampled_row = z_grid.shape[0] // 2
        _, plot_y = Heatmap2DOrientation.plot_axes(x_grid, y_grid, z_grid)
        self.assertAlmostEqual(overlays[-1][1], float(plot_y[sampled_row]))

    def test_clicked_position_still_wins_over_default(self):
        panel, overlays = self._panel_with_recorded_overlays()
        panel.line_mode_check.setChecked(True)

        panel._handle_cell_click(str(_VTK_FILE), 1.0, 2.5)

        self.assertEqual(overlays[-1], ("horizontal", 2.5))

    def test_line_hidden_when_line_scan_off(self):
        panel, overlays = self._panel_with_recorded_overlays()
        panel.line_mode_check.setChecked(True)

        panel.line_mode_check.setChecked(False)

        self.assertIsNone(overlays[-1])


if __name__ == "__main__":
    unittest.main()
