import unittest

from viewer.colorbar_ticks import format_colorbar_ticks


class ColorbarTickFormattingTests(unittest.TestCase):
    def test_integer_tick_spacing_uses_integer_labels(self):
        self.assertEqual(
            format_colorbar_ticks([1, 3, 5, 7, 9]),
            ["1", "3", "5", "7", "9"],
        )
        self.assertEqual(
            format_colorbar_ticks([10, 20, 30, 40, 50]),
            ["10", "20", "30", "40", "50"],
        )

    def test_fractional_tick_spacing_controls_decimal_places(self):
        self.assertEqual(
            format_colorbar_ticks([1, 2.5, 4, 5.5, 7]),
            ["1.0", "2.5", "4.0", "5.5", "7.0"],
        )
        self.assertEqual(
            format_colorbar_ticks([0, 0.25, 0.5, 0.75, 1]),
            ["0.00", "0.25", "0.50", "0.75", "1.00"],
        )
        self.assertEqual(
            format_colorbar_ticks([0, 0.1, 0.2, 0.3, 0.4]),
            ["0.0", "0.1", "0.2", "0.3", "0.4"],
        )

    def test_zero_to_ten_range_uses_integer_labels(self):
        self.assertEqual(
            format_colorbar_ticks([0, 2.5, 5, 7.5, 10]),
            ["0", "2", "5", "8", "10"],
        )
        self.assertEqual(
            format_colorbar_ticks([0, 2.292121887207, 4.584243774414, 6.876365661621, 9.168487548828]),
            ["0", "2", "5", "7", "9"],
        )

    def test_small_nonzero_interface_range_does_not_show_float_noise(self):
        self.assertEqual(
            format_colorbar_ticks([1.0, 1.89581298828125, 2.7916259765625, 3.68743896484375, 4.583251953125]),
            ["1.00", "1.90", "2.79", "3.69", "4.58"],
        )

    def test_tick_spacing_greater_than_ten_uses_integer_labels(self):
        self.assertEqual(
            format_colorbar_ticks([0, 12.5, 25, 37.5, 50]),
            ["0", "12", "25", "38", "50"],
        )

    def test_scientific_notation_is_used_for_large_or_tiny_values(self):
        self.assertEqual(
            format_colorbar_ticks([0.0001, 0.0002, 0.0003]),
            ["1.0e-4", "2.0e-4", "3.0e-4"],
        )
        self.assertEqual(
            format_colorbar_ticks([10000, 20000, 30000]),
            ["1.0e4", "2.0e4", "3.0e4"],
        )

    def test_values_at_one_thousand_switch_to_scientific(self):
        self.assertEqual(
            format_colorbar_ticks([250, 500, 750, 1000]),
            ["2.5e2", "5.0e2", "7.5e2", "1.0e3"],
        )


if __name__ == "__main__":
    unittest.main()
