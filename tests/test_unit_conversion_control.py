"""The shared From -> to scale control used by Single View, Multi View and Multi Property."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from utils.unit_conversion_control import UnitConversionControl


def _labels(combo):
    return [combo.itemText(i) for i in range(combo.count())]


def _units(combo):
    return [combo.itemData(i) for i in range(combo.count())]


def _pick(combo, unit):
    combo.setCurrentIndex(combo.findData(unit))


class UnitConversionControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.control = UnitConversionControl()
        self.changes = []
        self.control.currentIndexChanged.connect(self.changes.append)

    def test_starts_without_a_conversion(self):
        self.assertEqual(self.control.currentData(), (1.0, ""))
        self.assertEqual(self.control.from_unit(), "-")
        self.assertEqual(self.control.to_unit(), "-")

    def test_dropdowns_name_prefixes_and_never_the_base_unit(self):
        self.control.set_native_unit("MPa")
        self.assertEqual(_labels(self.control.from_combo), ["milli (m)", "base", "kilo (k)", "Mega (M)", "Giga (G)"])
        self.assertEqual(_labels(self.control.to_combo), ["\u2014", "milli (m)", "base", "kilo (k)", "Giga (G)"])
        for combo in (self.control.from_combo, self.control.to_combo):
            for label in _labels(combo):
                self.assertNotIn("Pa", label)

    def test_the_unit_chosen_in_from_is_not_listed_again_in_to(self):
        self.control.set_native_unit("MPa")
        self.assertNotIn("MPa", _units(self.control.to_combo)[1:])
        self.assertNotIn("Mega (M)", _labels(self.control.to_combo))
        _pick(self.control.from_combo, "kPa")
        self.assertNotIn("kilo (k)", _labels(self.control.to_combo))
        self.assertIn("Mega (M)", _labels(self.control.to_combo))

    def test_to_starts_on_no_conversion_shown_as_a_dash(self):
        self.control.set_native_unit("MPa")
        self.assertEqual(self.control.to_combo.currentText(), "\u2014")
        self.assertEqual(self.control.to_unit(), "MPa")  # the same unit: nothing is converted
        self.assertEqual(self.control.currentData(), (1.0, "MPa"))
    def test_from_and_to_show_the_same_scale_with_the_native_unit_selected(self):
        self.control.set_native_unit("MPa")
        self.assertEqual(self.control.from_unit(), "MPa")
        self.assertEqual(self.control.to_unit(), "MPa")
        self.assertEqual(self.control.from_combo.currentText(), "Mega (M)")

    def test_the_base_unit_is_in_from_in_its_place_and_not_repeated_in_to(self):
        self.control.set_native_unit("Pa")
        self.assertEqual(_labels(self.control.from_combo)[1], "base")
        self.assertEqual(_labels(self.control.to_combo), ["\u2014", "milli (m)", "kilo (k)", "Mega (M)", "Giga (G)"])
    def test_length_and_force_scales(self):
        self.control.set_native_unit("mm")
        self.assertEqual(
            _labels(self.control.to_combo), ["\u2014", "nano (n)", "micro (µ)", "centi (c)", "base", "kilo (k)"]
        )
        self.control.set_native_unit("kN")
        self.assertEqual(_units(self.control.to_combo), ["kN", "mN", "N", "MN", "GN"])
    def test_data_with_no_unit_offers_every_prefix_and_percent(self):
        self.assertEqual(
            _labels(self.control.to_combo),
            ["\u2014", "nano (n)", "micro (µ)", "milli (m)", "percent (%)", "kilo (k)", "Mega (M)", "Giga (G)"],
        )
    def test_data_with_no_unit_can_be_declared_in_a_base_unit(self):
        self.assertEqual(_units(self.control.from_combo)[-1:], ["s"])
        for removed in ("Pa", "N", "J", "W", "m", "g"):
            self.assertNotIn(removed, _units(self.control.from_combo))  # those come with the data
        _pick(self.control.from_combo, "s")
        self.assertEqual(self.control.from_unit(), "s")
        self.assertEqual(_labels(self.control.to_combo), ["\u2014", "milli (m)", "minute (min)", "hour (h)", "day"])
        _pick(self.control.to_combo, "min")
        self.assertAlmostEqual(self.control.currentData()[0], 1 / 60)
        self.assertEqual(self.control.currentData()[1], "min")
    def test_the_from_list_does_not_change_when_a_unit_is_picked(self):
        before = _units(self.control.from_combo)
        _pick(self.control.from_combo, "s")
        self.assertEqual(_units(self.control.from_combo), before)  # milli, percent, ... are still there
        self.assertEqual(self.control.from_unit(), "s")
        self.assertEqual(_labels(self.control.to_combo), ["\u2014", "milli (m)", "minute (min)", "hour (h)", "day"])
    def test_a_declaration_is_undone_by_picking_base_again(self):
        _pick(self.control.from_combo, "s")
        _pick(self.control.from_combo, "-")
        self.assertEqual(self.control.from_unit(), "-")
        self.assertIn("percent (%)", _labels(self.control.to_combo))
        self.assertNotIn("No unit", _labels(self.control.from_combo))

    def test_data_that_already_has_a_unit_cannot_be_redeclared(self):
        self.control.set_native_unit("MPa")
        self.assertEqual(_units(self.control.from_combo), ["mPa", "Pa", "kPa", "MPa", "GPa"])

    def test_data_with_no_unit_converts_by_prefix_and_prints_no_unit(self):
        _pick(self.control.from_combo, "M-")
        _pick(self.control.to_combo, "k-")
        scale, suffix = self.control.currentData()
        self.assertAlmostEqual(scale, 1e3)
        self.assertEqual(suffix, "")

    def test_time_offers_milli_minute_hour_day_and_the_unit_itself_is_the_source(self):
        self.control.set_native_unit("s")
        self.assertEqual(_labels(self.control.to_combo), ["\u2014", "milli (m)", "minute (min)", "hour (h)", "day"])
    def test_choosing_a_target_gives_the_scale_and_the_unit_suffix(self):
        self.control.set_native_unit("MPa")
        _pick(self.control.to_combo, "GPa")
        scale, suffix = self.control.currentData()
        self.assertAlmostEqual(scale, 1e-3)
        self.assertEqual(suffix, "GPa")

    def test_converting_from_kilo_to_base_and_from_milli_to_mega(self):
        self.control.set_native_unit("kPa")
        _pick(self.control.to_combo, "Pa")
        self.assertAlmostEqual(self.control.currentData()[0], 1e3)
        _pick(self.control.from_combo, "mPa")
        _pick(self.control.to_combo, "MPa")
        self.assertAlmostEqual(self.control.currentData()[0], 1e-9)

    def test_no_unit_to_percent_multiplies_by_100(self):
        _pick(self.control.to_combo, "%")
        self.assertAlmostEqual(self.control.currentData()[0], 100.0)
        self.assertEqual(self.control.currentData()[1], "%")

    def test_the_suffix_is_empty_for_dimensionless_data(self):
        self.assertEqual(self.control.currentData()[1], "")

    def test_changing_from_keeps_the_target(self):
        self.control.set_native_unit("MPa")
        _pick(self.control.to_combo, "GPa")
        _pick(self.control.from_combo, "kPa")
        self.assertEqual(self.control.to_unit(), "GPa")
        self.assertAlmostEqual(self.control.currentData()[0], 1e-6)

    def test_unrecognised_native_unit_has_nothing_to_convert(self):
        self.control.set_native_unit("mol")
        self.assertEqual(_labels(self.control.to_combo), ["\u2014"])
        self.assertEqual(self.control.currentData(), (1.0, "mol"))
    def test_temperature_converts_nothing_here(self):
        self.control.set_native_unit("K")
        self.assertEqual(_units(self.control.to_combo), ["K"])
        self.assertEqual(self.control.currentData()[0], 1.0)

    def test_an_unlisted_prefix_from_the_data_is_shown_in_its_place(self):
        self.control.set_native_unit("TPa")
        self.assertEqual(self.control.from_unit(), "TPa")
        self.assertEqual(_labels(self.control.from_combo)[-1], "Tera (T)")
        self.assertNotIn("Tera (T)", _labels(self.control.to_combo))
    def test_same_native_unit_keeps_the_users_choices_but_a_new_one_resets(self):
        self.control.set_native_unit("MPa")
        _pick(self.control.to_combo, "GPa")
        self.control.set_native_unit("MPa")
        self.assertEqual(self.control.to_unit(), "GPa")
        self.control.set_native_unit("-")
        self.assertEqual(self.control.from_unit(), "-")
        self.assertEqual(self.control.to_unit(), "-")

    def test_set_native_unit_reports_whether_it_changed(self):
        self.assertTrue(self.control.set_native_unit("MPa"))
        self.assertFalse(self.control.set_native_unit("MPa"))
        self.assertFalse(self.control.set_native_unit("mpa"))
        self.assertTrue(self.control.set_native_unit("s"))

    def test_empty_native_unit_means_dimensionless(self):
        self.control.set_native_unit("MPa")
        self.control.set_native_unit("")
        self.assertEqual(self.control.from_unit(), "-")
        self.control.set_native_unit("MPa")
        self.control.set_native_unit(None)
        self.assertEqual(self.control.from_unit(), "-")

    def test_user_changes_emit_once_but_set_native_unit_is_silent(self):
        self.control.set_native_unit("MPa")
        self.assertEqual(self.changes, [])
        _pick(self.control.to_combo, "GPa")
        self.assertEqual(len(self.changes), 1)
        _pick(self.control.from_combo, "kPa")
        self.assertEqual(len(self.changes), 2)

    def test_both_dropdowns_have_the_same_width(self):
        self.assertEqual(self.control.from_combo.maximumWidth(), self.control.to_combo.maximumWidth())

    def test_dropdowns_use_the_viewer_style(self):
        self.assertEqual(self.control.from_combo.objectName(), "viewerCombo")
        self.assertEqual(self.control.to_combo.objectName(), "viewerCombo")


if __name__ == "__main__":
    unittest.main()
