"""Custom Graph: unit-aware conversions (source unit, convert-to, custom factor/offset)."""

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from graphs.graph_canvas import GraphCanvas
from graphs.tab_widget import CustomGraphTab

_UNITS_FILE = "Time Stress Strain\ns MPa -\n0 100 0.5\n10 200 1.0\n"
_PLAIN_FILE = "Time Stress\n0 100\n10 200\n"


def _write(text):
    path = Path(tempfile.mkdtemp()) / "data.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _panel_with(path):
    tab = CustomGraphTab()
    panel = tab._tabs.widget(0)
    panel.add_files([path])
    return tab, panel


def _targets(combo):
    return [combo.itemData(i) for i in range(combo.count())]


class ColumnConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_file_units_row_prefills_source_unit_and_targets(self):
        path = _write(_UNITS_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        self.assertEqual(panel._column_settings[path]["Stress"]["source_unit"], "MPa")
        targets = _targets(panel._conversion_combos[(path, "Stress")])
        # no conversion, then the scale without the unit chosen in From
        self.assertEqual(targets, ["as-is", "to:mPa", "to:Pa", "to:kPa", "to:GPa", "custom"])

    def test_unrecognised_unit_offers_no_change_and_custom(self):
        path = _write("Time Force\ns mol\n0 1\n1 2\n")
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Force"]
        panel._refresh_column_settings()
        targets = _targets(panel._conversion_combos[(path, "Force")])
        self.assertEqual(targets, ["as-is", "custom"])

    def test_empty_unit_shows_dash_and_both_dropdowns_are_equally_wide(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        unit = panel._unit_combos[(path, "Stress")]
        to = panel._conversion_combos[(path, "Stress")]
        self.assertEqual(unit.currentData(), "-")
        self.assertEqual(unit.currentText(), "base")  # the base unit is not named, only its prefixes
        self.assertEqual(unit.width(), to.width())
        self.assertEqual(panel.x_axis_unit_combo.width(), panel.x_axis_conversion_combo.width())

    def test_custom_graph_from_dropdown_lists_prefixes_then_the_units_to_declare(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        combo = panel.x_axis_unit_combo
        labels = [combo.itemText(i) for i in range(combo.count())]
        self.assertEqual(
            labels,
            ["nano (n)", "micro (µ)", "milli (m)", "percent (%)", "base", "kilo (k)", "Mega (M)", "Giga (G)",
             "s", "K", "°C"],
        )  # unit unknown: every prefix, then the units the data can be declared in

    def test_temperature_converts_between_celsius_and_kelvin(self):
        path = _write("Time T\ns °C\n0 0\n1 100\n")
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["T"]
        panel._refresh_column_settings()
        combo = panel._conversion_combos[(path, "T")]
        combo.setCurrentIndex(combo.findData("to:K"))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [273.15, 373.15]))

    def test_from_dropdown_lists_each_unit_once(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        combo = panel.x_axis_unit_combo
        items = [combo.itemData(i) for i in range(combo.count())]
        self.assertEqual(len(items), len(set(items)))
        self.assertEqual(combo.currentData(), "-")

    def test_from_dropdown_opens_from_anywhere_and_shows_unrecognised_units(self):
        path = _write("Time Force\ns mol\n0 1\n1 2\n")
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Force"]
        panel._refresh_column_settings()
        combo = panel._unit_combos[(path, "Force")]
        self.assertFalse(combo.isEditable())  # an editable combo only opens from its arrow
        self.assertEqual(combo.currentData(), "mol")

    def test_from_and_to_show_one_scale_for_a_unit_from_the_file(self):
        path = _write(_UNITS_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        combo = panel._unit_combos[(path, "Stress")]
        self.assertEqual([combo.itemData(i) for i in range(combo.count())], ["mPa", "Pa", "kPa", "MPa", "GPa"])
        labels = ["milli (m)", "base", "kilo (k)", "Mega (M)", "Giga (G)"]
        self.assertEqual([combo.itemText(i) for i in range(5)], labels)  # prefixes only: the file gave the unit
        to = panel._conversion_combos[(path, "Stress")]
        self.assertEqual(
            [to.itemText(i) for i in range(to.count())], ["\u2014", "milli (m)", "base", "kilo (k)", "Giga (G)", "Custom…"]
        )
        self.assertEqual(to.currentText(), "\u2014")  # no conversion; Mega is not repeated

    def test_kilo_to_base_and_choosing_another_base_unit(self):
        path = _write("Time Force\ns kPa\n0 1\n1 2\n")
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Force"]
        panel._refresh_column_settings()
        to = panel._conversion_combos[(path, "Force")]
        to.setCurrentIndex(to.findData("to:Pa"))  # "kilo (k)" to "base"
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [1000, 2000]))

    def test_data_without_a_unit_can_be_declared_and_then_scaled(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        unit = panel._unit_combos[(path, "Stress")]
        unit.setCurrentIndex(unit.findData("s"))  # "this column is in seconds"
        to = panel._conversion_combos[(path, "Stress")]
        self.assertEqual(
            [to.itemText(i) for i in range(to.count())],
            ["\u2014", "milli (m)", "minute (min)", "hour (h)", "day", "Custom…"],
        )
        to.setCurrentIndex(to.findData("to:min"))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [100 / 60, 200 / 60]))
        self.assertIn("min", panel.y1_title_edit.text())
        self.assertNotIn("No unit", [unit.itemText(i) for i in range(unit.count())])

    def test_the_from_list_stays_the_same_when_seconds_is_picked(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        unit = panel._unit_combos[(path, "Stress")]
        before = [unit.itemData(i) for i in range(unit.count())]
        unit.setCurrentIndex(unit.findData("s"))
        self.assertEqual([unit.itemData(i) for i in range(unit.count())], before)
        self.assertIn("milli (m)", [unit.itemText(i) for i in range(unit.count())])
        x = panel.x_axis_unit_combo
        x_before = [x.itemData(i) for i in range(x.count())]
        x.setCurrentIndex(x.findData("s"))
        self.assertEqual([x.itemData(i) for i in range(x.count())], x_before)

    def test_data_without_a_unit_scales_by_prefix_alone_and_prints_no_unit(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        to = panel._conversion_combos[(path, "Stress")]
        to.setCurrentIndex(to.findData("to:k-"))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [0.1, 0.2]))
        self.assertNotIn("(", panel.y1_title_edit.text())

    def test_mpa_to_gpa_scales_data(self):
        path = _write(_UNITS_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        panel._set_conversion(path, "Stress", "to:GPa")
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [0.1, 0.2]))
        self.assertIn("GPa", panel.y1_title_edit.text())

    def test_changing_source_unit_rebuilds_targets(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        panel._set_source_unit(path, "Stress", "GPa")
        targets = _targets(panel._conversion_combos[(path, "Stress")])
        self.assertIn("to:MPa", targets)
        self.assertEqual(panel._column_settings[path]["Stress"]["source_unit"], "GPa")

    def test_legacy_settings_still_work_without_source_unit(self):
        canvas = GraphCanvas()
        t = canvas.column_transform({"conversion": "mpa"})
        self.assertAlmostEqual(t.a, 1e-6)
        self.assertEqual(t.unit, "MPa")

    def test_user_picked_from_unit_enables_conversion(self):
        path = _write(_PLAIN_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        unit = panel._unit_combos[(path, "Stress")]
        unit.setCurrentIndex(unit.findData("s"))
        combo = panel._conversion_combos[(path, "Stress")]
        combo.setCurrentIndex(combo.findData("to:ms"))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [100000, 200000]))

    def test_temperature_offset_applies(self):
        canvas = GraphCanvas()
        t = canvas.column_transform({"conversion": "to:°C", "source_unit": "K"})
        self.assertTrue(np.allclose(t.apply(np.array([273.15, 373.15])), [0.0, 100.0]))


class XAxisConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_x_seconds_to_minutes_uses_file_unit(self):
        path = _write(_UNITS_FILE)
        _tab, panel = _panel_with(path)
        panel._columns_by_file[path] = ["Stress"]
        panel._refresh_column_settings()
        self.assertEqual(panel.x_axis_unit_combo.currentData(), "s")
        index = panel.x_axis_conversion_combo.findData("to:min")
        self.assertGreaterEqual(index, 0)
        panel.x_axis_conversion_combo.setCurrentIndex(index)
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].x, [0, 10 / 60]))
        self.assertIn("min", panel.x_title_edit.text())

    def test_x_legacy_state_unchanged(self):
        canvas = GraphCanvas()
        t = canvas.x_transform({"x_axis_conversion": "sec-to-min"})
        self.assertAlmostEqual(t.a, 1 / 60)


if __name__ == "__main__":
    unittest.main()
