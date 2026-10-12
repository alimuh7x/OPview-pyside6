import unittest

import numpy as np

from viewer.heatmap_orientation import Heatmap2DOrientation
from viewer.phase_fraction_history_canvas import PhaseFractionHistoryCanvas


def _raw_grid(rows=4, cols=6):
    x, y = np.meshgrid(np.arange(cols, dtype=float), np.arange(rows, dtype=float) * 10.0)
    return x, y


class RotatedPointMappingTests(unittest.TestCase):
    """Picks arrive in PLOT-AXIS values (always ascending), not rotated coordinate arrays."""

    def test_rotated_view_axes_differ_from_rotated_coordinate_arrays(self):
        # The reason the old nearest-in-array pick landed on the mirrored point.
        x_raw, y_raw = _raw_grid()
        for degrees in (90, 180, 270):
            shown = Heatmap2DOrientation(degrees).apply_grid(x_raw, y_raw, np.zeros_like(x_raw))
            x_axis, _ = Heatmap2DOrientation.plot_axes(shown.x, shown.y, shown.x)
            self.assertLess(x_axis[0], x_axis[-1])
        flipped = Heatmap2DOrientation(180).apply_grid(x_raw, y_raw, np.zeros_like(x_raw))
        self.assertGreater(flipped.x[0, 0], flipped.x[0, -1])  # array runs descending, axis does not

    def test_picked_pixel_maps_to_the_source_cell_with_the_same_value(self):
        x_raw, y_raw = _raw_grid()
        z_raw = x_raw * 100.0 + y_raw  # unique value per source cell
        for degrees in (0, 90, 180, 270):
            orientation = Heatmap2DOrientation(degrees)
            shown = orientation.apply_grid(x_raw, y_raw, z_raw)
            x_axis, y_axis = Heatmap2DOrientation.plot_axes(shown.x, shown.y, shown.z)
            for row in range(shown.z.shape[0]):
                for col in range(shown.z.shape[1]):
                    data_x, data_y = orientation.display_to_data_point(x_raw, y_raw, x_axis[col], y_axis[row])
                    # the source cell under the cursor holds exactly the value the view shows there
                    self.assertEqual(data_x * 100.0 + data_y, shown.z[row, col], f"rot {degrees} px {(row, col)}")
                    back = orientation.data_to_display_point(x_raw, y_raw, data_x, data_y)
                    self.assertEqual(back, (float(x_axis[col]), float(y_axis[row])))


class SteadyYRangeTests(unittest.TestCase):
    def test_nanoscale_noise_is_not_magnified(self):
        series = [{"values": [0.30, 0.30 + 1e-9, 0.30 - 1e-9]}]

        lo, hi = PhaseFractionHistoryCanvas._steady_y_range(series)

        self.assertGreaterEqual(hi - lo, 3e-4)  # >= 0.1% of the value, vs 2e-9 of real noise
        self.assertLess(lo, 0.30)
        self.assertGreater(hi, 0.30)

    def test_real_changes_still_autoscale(self):
        series = [{"values": [0.1, 0.2, 0.3]}]

        self.assertIsNone(PhaseFractionHistoryCanvas._steady_y_range(series))

    def test_empty_or_non_finite_series_is_left_alone(self):
        self.assertIsNone(PhaseFractionHistoryCanvas._steady_y_range([{"values": [float("nan")]}]))
        self.assertIsNone(PhaseFractionHistoryCanvas._steady_y_range([]))


if __name__ == "__main__":
    unittest.main()


class PlotOverTimeMatchesHoverTests(unittest.TestCase):
    """Plot Over Time must read the same (resampled) grid the heatmap hover reads."""

    def test_displayed_sampling_equals_hover_value_but_raw_nearest_node_does_not(self):
        from utils.vtk_utils import get_reader

        reader = get_reader("Project1/VTK/CauchyStresses_00004500.vts")
        axis = Heatmap2DOrientation.detect_axis(reader.dimensions)
        x, y, z, _ = reader.get_interpolated_slice(
            axis=axis, index=0, scalar_name="CauchyStresses", component=0, resolution=160
        )
        z = np.asarray(z)
        rng = np.random.default_rng(3)
        raw_differs = 0
        for _ in range(40):
            i, j = rng.integers(0, z.shape[0]), rng.integers(0, z.shape[1])
            kwargs = dict(axis=axis, index=0, scalar_name="CauchyStresses", component=0,
                          x_value=float(x[i, j]), y_value=float(y[i, j]))
            self.assertEqual(reader.sample_displayed_value(resolution=160, **kwargs), float(z[i, j]))
            if not np.isclose(reader.sample_point_value(**kwargs), z[i, j], rtol=1e-3):
                raw_differs += 1
        self.assertGreater(raw_differs, 0)  # documents why the old nearest-node sampling disagreed


class PlotOverTimePointEntryTests(unittest.TestCase):
    """Real UI rotation + a click at an axis position must pick the pixel under the cursor."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        import glob
        from pathlib import Path

        from viewer.panel_widget import PanelWidget

        files = sorted(str(Path(f).resolve()) for f in glob.glob("Project1/VTK/CauchyStresses_*.vts"))
        cfg = {"label": "Cauchy", "scale": 1.0,
               "scalars": [{"label": "s_xx", "array": "CauchyStresses", "component": 0}]}
        panel = PanelWidget(dataset_info={"id": "c", "label": "Cauchy", "files": files,
                                          "dataset_config": cfg, "tab_id": "single_view"})
        panel.controls_widget.file_combo.setCurrentIndex(3)  # a timestep with non-zero stress
        self.app.processEvents()
        return panel

    def _rotation_buttons(self, panel):
        controls = panel.controls_widget
        return controls.rotation_button_row.findChildren(type(controls.reset_button))

    def test_click_marker_and_plot_over_time_value_match_the_hovered_pixel_at_every_rotation(self):
        panel = self._panel()
        controller = panel.controller
        rng = np.random.default_rng(5)
        seen_rotations = set()
        for button in self._rotation_buttons(panel):
            button.click()  # real UI rotation (setting state directly is overwritten on refresh)
            self.app.processEvents()
            seen_rotations.add(controller.state.rotation_degrees)
            x_disp, y_disp, z_disp = controller._last_display_grids
            x_axis, y_axis = Heatmap2DOrientation.plot_axes(x_disp, y_disp, z_disp)
            for _ in range(8):
                row, col = int(rng.integers(5, 150)), int(rng.integers(5, 150))
                hovered = float(z_disp[row, col])  # what Plotly shows at (x_axis[col], y_axis[row])
                controller.state.time_plot_points = []
                controller.state.time_plot_pick_mode = True
                controller._handle_heatmap_click(float(x_axis[col]), float(y_axis[row]))
                controller.state.time_plot_pick_mode = False
                point = controller.state.time_plot_points[-1]
                scalar = controller._get_scalar_def(controller.state.scalar_key)
                sampled = controller.reader.sample_displayed_value(
                    axis=controller.state.axis, index=controller.state.slice_index,
                    scalar_name=scalar["array"], component=scalar.get("component"),
                    x_value=point["x"], y_value=point["y"], resolution=controller._selected_resolution(),
                )
                marker = controller._time_plot_marker_points()[-1]
                label = f"rotation {controller.state.rotation_degrees}"
                self.assertAlmostEqual(sampled, hovered, delta=abs(hovered) * 1e-9, msg=label)
                self.assertAlmostEqual(marker["x"], float(x_axis[col]), msg=label)
                self.assertAlmostEqual(marker["y"], float(y_axis[row]), msg=label)
        self.assertEqual(seen_rotations, {0, 90, 180, 270})

    def test_existing_points_follow_the_data_when_the_view_is_rotated(self):
        panel = self._panel()
        controller = panel.controller
        buttons = self._rotation_buttons(panel)
        buttons[0].click()
        self.app.processEvents()
        x_disp, y_disp, z_disp = controller._last_display_grids
        x_axis, y_axis = Heatmap2DOrientation.plot_axes(x_disp, y_disp, z_disp)
        row, col = 40, 110
        picked = float(z_disp[row, col])
        controller.state.time_plot_points = []
        controller.state.time_plot_pick_mode = True
        controller._handle_heatmap_click(float(x_axis[col]), float(y_axis[row]))
        controller.state.time_plot_pick_mode = False

        for button in buttons:
            button.click()
            self.app.processEvents()
            x_disp, y_disp, z_disp = controller._last_display_grids
            x_axis, y_axis = Heatmap2DOrientation.plot_axes(x_disp, y_disp, z_disp)
            marker = controller._time_plot_marker_points()[-1]
            under_marker = z_disp[
                int(np.argmin(np.abs(y_axis - marker["y"]))), int(np.argmin(np.abs(x_axis - marker["x"])))
            ]
            self.assertEqual(float(under_marker), picked, f"rotation {controller.state.rotation_degrees}")
            self.assertIn(f"x={marker['x']:.4f}", panel.time_plot_selected_label.text())
