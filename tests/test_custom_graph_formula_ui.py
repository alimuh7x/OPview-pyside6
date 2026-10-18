"""Custom Graph: the Custom entry of the From dropdown, which opens the formula dialog."""

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from graphs.tab_widget import CustomGraphTab

_FILE = "Time Stress Strain\ns MPa -\n0 100 0.5\n10 200 1.0\n20 300 2.0\n"


def _setup(text=_FILE, columns=("Stress", "Strain")):
    path = Path(tempfile.mkdtemp()) / "data.txt"
    path.write_text(text, encoding="utf-8")
    tab = CustomGraphTab()
    panel = tab._tabs.widget(0)
    panel.add_files([str(path)])
    path = str(path.resolve()) if str(path.resolve()) in panel._columns_by_file else str(path)
    panel._columns_by_file[path] = list(columns)
    panel._refresh_column_settings()
    return panel, path


def _choose_custom(panel, path, column, answer):
    """Pick Custom in the From dropdown while the dialog answers `answer` ((formula, unit) or None)."""
    asked = []

    def fake(file_path, col, formula, unit):
        asked.append((file_path, col, formula, unit))
        return answer

    panel._ask_formula = fake
    combo = panel._unit_combos[(path, column)]
    combo.setCurrentIndex(combo.findText("Custom"))
    combo.activated.emit(combo.currentIndex())
    return asked


class CustomColumnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_custom_is_the_last_entry_of_both_from_dropdowns(self):
        panel, path = _setup()
        for combo in (panel._unit_combos[(path, "Stress")], panel.x_axis_unit_combo):
            self.assertEqual(combo.itemText(combo.count() - 1), "Custom")
            self.assertEqual(combo.findData("Custom"), combo.count() - 1)

    def test_a_unit_from_the_file_is_listed_before_custom(self):
        panel, path = _setup()  # the file's units row says MPa, which is not one of the base units
        combo = panel._unit_combos[(path, "Stress")]
        data = [combo.itemData(i) for i in range(combo.count())]
        self.assertEqual(combo.currentData(), "MPa")
        self.assertEqual(combo.currentText(), "Mega (M)")
        self.assertEqual(data[-1], "Custom")
        self.assertEqual(data.count("MPa"), 1)

    def test_accepted_formula_converts_the_data_and_shows_the_unit(self):
        panel, path = _setup(columns=("Stress",))
        _choose_custom(panel, path, "Stress", ("x / 1000", "GPa"))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [0.1, 0.2, 0.3]))
        self.assertEqual(panel._unit_combos[(path, "Stress")].currentText(), "Custom")
        self.assertEqual(panel._conversion_combos[(path, "Stress")].currentText(), "GPa")
        self.assertIn("GPa", panel.y1_title_edit.text())

    def test_formula_can_use_other_columns(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x * Strain + Time", ""))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [50, 210, 620]))

    def test_cancelled_dialog_keeps_the_previous_unit(self):
        panel, path = _setup()
        before = panel._unit_combos[(path, "Stress")].currentText()
        _choose_custom(panel, path, "Stress", None)
        self.assertEqual(panel._unit_combos[(path, "Stress")].currentText(), before)
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "as-is")

    def test_reopening_custom_shows_the_saved_formula(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x*2", "kN"))
        asked = _choose_custom(panel, path, "Stress", ("x*3", "kN"))
        self.assertEqual(asked[0][2:], ("x*2", "kN"))
        self.assertEqual(panel._column_settings[path]["Stress"]["formula"], "x*3")

    def test_cancel_after_a_formula_keeps_the_formula(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x*2", ""))
        _choose_custom(panel, path, "Stress", None)
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "custom")
        self.assertEqual(panel._unit_combos[(path, "Stress")].currentText(), "Custom")

    def test_choosing_a_real_unit_after_custom_goes_back_to_unit_conversion(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x*2", ""))
        combo = panel._unit_combos[(path, "Stress")]
        combo.setCurrentIndex(combo.findData("MPa"))
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "as-is")
        self.assertIn("to:GPa", [panel._conversion_combos[(path, "Stress")].itemData(i)
                                 for i in range(panel._conversion_combos[(path, "Stress")].count())])

    def test_custom_without_a_unit_label_shows_no_unit_in_the_title(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x*2", ""))
        self.assertEqual(panel.y1_title_edit.text(), "Stress, Strain")


class CustomXAxisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_x_axis_formula_converts_x(self):
        panel, path = _setup()
        asked = []
        panel._ask_formula = lambda f, c, formula, unit: asked.append((c, formula)) or ("x / 60", "min")
        panel.x_axis_unit_combo.setCurrentIndex(panel.x_axis_unit_combo.findText("Custom"))
        panel.x_axis_unit_combo.activated.emit(panel.x_axis_unit_combo.currentIndex())
        self.assertEqual(asked[0][0], "Time")
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].x, [0, 10 / 60, 20 / 60]))
        self.assertIn("min", panel.x_title_edit.text())
        self.assertEqual(panel.x_axis_conversion_combo.currentText(), "min")

    def test_cancelled_x_dialog_keeps_the_unit(self):
        panel, path = _setup()
        panel._ask_formula = lambda *args: None
        before = panel.x_axis_unit_combo.currentText()
        panel.x_axis_unit_combo.setCurrentIndex(panel.x_axis_unit_combo.findText("Custom"))
        panel.x_axis_unit_combo.activated.emit(panel.x_axis_unit_combo.currentIndex())
        self.assertEqual(panel.x_axis_unit_combo.currentText(), before)


if __name__ == "__main__":
    unittest.main()
