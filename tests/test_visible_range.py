import unittest

import numpy as np

from viewer import visible_range as vr


def _grid(n=11):
    axis = np.arange(n, dtype=float)
    x, y = np.meshgrid(axis, axis)
    return axis, axis, x + 100.0 * y  # z[row, col] = col + 100 * row


class NormalizeWindowTests(unittest.TestCase):
    def test_orders_bounds(self):
        self.assertEqual(vr.normalize_window(5, 1, 9, 3), (1.0, 5.0, 3.0, 9.0))

    def test_rejects_missing_or_non_finite_bounds(self):
        self.assertIsNone(vr.normalize_window(None, 1, 2, 3))
        self.assertIsNone(vr.normalize_window(0, float("nan"), 2, 3))
        self.assertIsNone(vr.normalize_window(0, float("inf"), 2, 3))

    def test_windows_equal_handles_none_and_tolerance(self):
        self.assertTrue(vr.windows_equal(None, None))
        self.assertFalse(vr.windows_equal(None, (0, 1, 0, 1)))
        self.assertTrue(vr.windows_equal((0, 1, 0, 1), (0, 1 + 1e-12, 0, 1)))
        self.assertFalse(vr.windows_equal((0, 1, 0, 1), (0, 1.1, 0, 1)))


class VisibleMinMaxTests(unittest.TestCase):
    def test_zoom_selects_only_the_visible_cells(self):
        x, y, z = _grid()

        lo, hi = vr.visible_min_max(x, y, z, (2.0, 4.0, 3.0, 5.0))

        self.assertEqual(lo, 2 + 100 * 3)  # lower-left visible cell
        self.assertEqual(hi, 4 + 100 * 5)  # upper-right visible cell

    def test_pan_moves_the_range_with_the_window(self):
        x, y, z = _grid()

        before = vr.visible_min_max(x, y, z, (1.0, 3.0, 1.0, 3.0))
        after = vr.visible_min_max(x, y, z, (5.0, 7.0, 1.0, 3.0))

        self.assertEqual(after[0] - before[0], 4)
        self.assertEqual(after[1] - before[1], 4)

    def test_full_domain_window_gives_the_global_range(self):
        x, y, z = _grid()

        self.assertEqual(vr.visible_min_max(x, y, z, (-1.0, 11.0, -1.0, 11.0)), (float(z.min()), float(z.max())))

    def test_partially_visible_cells_count(self):
        x, y, z = _grid()

        lo, hi = vr.visible_min_max(x, y, z, (2.4, 2.6, 2.4, 2.6))  # inside the cell centred on (2.5)

        self.assertEqual((lo, hi), (2 + 100 * 2, 3 + 100 * 3))  # cells 2 and 3 both overlap 2.5

    def test_window_smaller_than_a_cell_still_selects_one_cell(self):
        x, y, z = _grid()

        lo, hi = vr.visible_min_max(x, y, z, (4.01, 4.02, 6.01, 6.02))

        self.assertEqual((lo, hi), (4 + 100 * 6, 4 + 100 * 6))

    def test_window_outside_the_domain_falls_back_to_the_nearest_cell(self):
        x, y, z = _grid()

        lo, hi = vr.visible_min_max(x, y, z, (50.0, 60.0, 50.0, 60.0))

        self.assertEqual((lo, hi), (10 + 100 * 10, 10 + 100 * 10))

    def test_nan_and_inf_cells_are_ignored(self):
        x, y, z = _grid()
        z[3, 2] = np.nan
        z[5, 4] = np.inf

        lo, hi = vr.visible_min_max(x, y, z, (2.0, 4.0, 3.0, 5.0))

        self.assertEqual((lo, hi), (3 + 100 * 3, 3 + 100 * 5))  # (3,row3) is the lowest finite, (3,row5) the highest

    def test_all_nan_window_returns_none(self):
        x, y, z = _grid()
        z[:, :] = np.nan

        self.assertIsNone(vr.visible_min_max(x, y, z, (2.0, 4.0, 3.0, 5.0)))

    def test_non_uniform_spacing_uses_midpoint_cell_edges(self):
        x = np.array([0.0, 1.0, 2.0, 10.0])  # last cell spans 6..14
        y = np.array([0.0, 1.0])
        z = np.array([[0.0, 1.0, 2.0, 3.0], [10.0, 11.0, 12.0, 13.0]])

        # x = 5 lies in the wide last cell (edge at 6) only after 6, so it belongs to cell x=2 (edges 1.5..6)
        self.assertEqual(vr.visible_min_max(x, y, z, (5.0, 5.5, 0.0, 0.0)), (2.0, 2.0))
        self.assertEqual(vr.visible_min_max(x, y, z, (7.0, 8.0, 0.0, 0.0)), (3.0, 3.0))

    def test_descending_axes_are_handled(self):
        x, y, z = _grid()

        flipped = vr.visible_min_max(x[::-1], y[::-1], z[::-1, ::-1], (2.0, 4.0, 3.0, 5.0))

        self.assertEqual(flipped, vr.visible_min_max(x, y, z, (2.0, 4.0, 3.0, 5.0)))

    def test_mismatched_axis_and_grid_shapes_return_none(self):
        x, y, z = _grid()

        self.assertIsNone(vr.visible_min_max(x[:5], y, z, (0, 1, 0, 1)))


class FullDomainTests(unittest.TestCase):
    def test_reset_window_is_the_full_domain(self):
        x, y, _ = _grid()

        self.assertTrue(vr.is_full_domain((0.0, 10.0, 0.0, 10.0), x, y))
        self.assertTrue(vr.is_full_domain((-0.4, 10.4, -0.4, 10.4), x, y))  # Plotly pads by half a cell

    def test_zoomed_window_is_not_the_full_domain(self):
        x, y, _ = _grid()

        self.assertFalse(vr.is_full_domain((2.0, 8.0, 0.0, 10.0), x, y))
        self.assertFalse(vr.is_full_domain((0.0, 10.0, 0.0, 5.0), x, y))


class OverlapsDomainTests(unittest.TestCase):
    def test_window_inside_or_touching_the_domain_overlaps(self):
        x, y, _ = _grid()

        self.assertTrue(vr.overlaps_domain((2.0, 4.0, 2.0, 4.0), x, y))
        self.assertTrue(vr.overlaps_domain((10.0, 20.0, -5.0, 0.0), x, y))  # touches the corner

    def test_window_outside_the_domain_does_not_overlap(self):
        x, y, _ = _grid()

        self.assertFalse(vr.overlaps_domain((20.0, 30.0, 0.0, 10.0), x, y))
        self.assertFalse(vr.overlaps_domain((0.0, 10.0, -9.0, -1.0), x, y))

    def test_descending_axes_and_empty_axes(self):
        x, y, _ = _grid()

        self.assertTrue(vr.overlaps_domain((2.0, 4.0, 2.0, 4.0), x[::-1], y[::-1]))
        self.assertFalse(vr.overlaps_domain((0.0, 1.0, 0.0, 1.0), np.array([]), y))


class PaddedRangeTests(unittest.TestCase):
    def test_ordinary_range_is_untouched(self):
        self.assertEqual(vr.padded_range(1.0, 2.0), (1.0, 2.0))

    def test_constant_field_is_widened_symmetrically(self):
        lo, hi = vr.padded_range(5.0, 5.0)

        self.assertLess(lo, 5.0)
        self.assertGreater(hi, 5.0)
        self.assertAlmostEqual((lo + hi) / 2.0, 5.0)

    def test_constant_zero_field_still_gets_a_valid_range(self):
        lo, hi = vr.padded_range(0.0, 0.0)

        self.assertLess(lo, hi)

    def test_non_finite_returns_none_and_reversed_input_is_ordered(self):
        self.assertIsNone(vr.padded_range(float("nan"), 1.0))
        self.assertEqual(vr.padded_range(3.0, 1.0), (1.0, 3.0))


if __name__ == "__main__":
    unittest.main()
