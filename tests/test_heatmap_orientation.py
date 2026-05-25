import unittest

import numpy as np

from viewer.heatmap_orientation import Heatmap2DOrientation


class Heatmap2DOrientationTests(unittest.TestCase):
    def test_detects_collapsed_axis_with_threshold_five(self):
        self.assertEqual(Heatmap2DOrientation.detect_axis((100, 4, 80)), "y")
        self.assertEqual(Heatmap2DOrientation.detect_axis((3, 100, 80)), "x")
        self.assertEqual(Heatmap2DOrientation.detect_axis((100, 80, 5)), "z")

    def test_detect_axis_uses_z_y_x_precedence(self):
        self.assertEqual(Heatmap2DOrientation.detect_axis((3, 4, 5)), "z")
        self.assertEqual(Heatmap2DOrientation.detect_axis((3, 4, 6)), "y")

    def test_rotates_non_square_grid_and_overlay_clockwise(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        orientation = Heatmap2DOrientation(rotation_degrees=90)

        oriented = orientation.apply_grid(x_grid, y_grid, z_grid)
        overlay = orientation.apply_overlay({"x": x_grid, "y": y_grid, "z": z_grid})

        self.assertEqual(oriented.z.shape, (3, 2))
        np.testing.assert_array_equal(oriented.z, np.array([[4.0, 1.0], [5.0, 2.0], [6.0, 3.0]]))
        np.testing.assert_array_equal(overlay["z"], oriented.z)

    def test_nearest_value_uses_oriented_grid(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        oriented = Heatmap2DOrientation(rotation_degrees=90).apply_grid(x_grid, y_grid, z_grid)

        value = Heatmap2DOrientation.nearest_value(
            oriented.x,
            oriented.y,
            oriented.z,
            float(oriented.x[0, 0]),
            float(oriented.y[0, 0]),
        )

        self.assertEqual(value, 4.0)

    def test_line_scan_uses_oriented_grid(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        oriented = Heatmap2DOrientation(rotation_degrees=90).apply_grid(x_grid, y_grid, z_grid)

        x_data, z_data, title, x_label = Heatmap2DOrientation.extract_line_scan(
            oriented.x,
            oriented.y,
            oriented.z,
            "horizontal",
            float(oriented.y[1, 0]),
        )

        np.testing.assert_array_equal(z_data, np.array([5.0, 2.0]))
        self.assertIn("Horizontal Scan", title)
        self.assertEqual(x_label, "X Position")

    def test_line_scan_180_uses_display_axis_not_rotated_coordinate_column(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        oriented = Heatmap2DOrientation(rotation_degrees=180).apply_grid(x_grid, y_grid, z_grid)

        _, z_data, _, _ = Heatmap2DOrientation.extract_line_scan(
            oriented.x,
            oriented.y,
            oriented.z,
            "horizontal",
            0.0,
        )

        np.testing.assert_array_equal(z_data, np.array([6.0, 5.0, 4.0]))

    def test_vertical_line_scan_180_uses_display_axis_not_rotated_coordinate_row(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        oriented = Heatmap2DOrientation(rotation_degrees=180).apply_grid(x_grid, y_grid, z_grid)

        _, z_data, _, _ = Heatmap2DOrientation.extract_line_scan(
            oriented.x,
            oriented.y,
            oriented.z,
            "vertical",
            0.0,
        )

        np.testing.assert_array_equal(z_data, np.array([6.0, 3.0]))

    def test_plot_width_uses_coordinate_extent_not_grid_shape(self):
        x_grid = np.array([[0.0, 8.0], [0.0, 8.0]])
        y_grid = np.array([[0.0, 0.0], [2.0, 2.0]])

        width = Heatmap2DOrientation().plot_width_for_height(x_grid, y_grid, 100, maximum=1000)

        self.assertEqual(width, 400)

    def test_plot_axes_are_monotonic_after_rotation(self):
        x_grid = np.array([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0]])
        y_grid = np.array([[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]])
        z_grid = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        oriented = Heatmap2DOrientation(rotation_degrees=90).apply_grid(x_grid, y_grid, z_grid)

        x_values, y_values = Heatmap2DOrientation.plot_axes(oriented.x, oriented.y, oriented.z)

        np.testing.assert_array_equal(x_values, np.array([0.0, 10.0]))
        np.testing.assert_array_equal(y_values, np.array([0.0, 1.0, 2.0]))


if __name__ == "__main__":
    unittest.main()
