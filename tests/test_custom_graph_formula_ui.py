"""Custom Graph: custom formulas belong in the To conversion dropdown."""

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionComboBox

from graphs.tab_widget import CustomGraphTab
from app.styles import build_app_stylesheet

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
    """Pick Custom in To while the dialog answers `answer` ((formula, unit) or None)."""
    asked = []

    def fake(file_path, col, formula, unit):
        asked.append((file_path, col, formula, unit))
        return answer

    panel._ask_formula = fake
    combo = panel._conversion_combos[(path, column)]
    combo.setCurrentIndex(combo.findData("custom"))
    combo.activated.emit(combo.currentIndex())
    return asked


class CustomColumnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_custom_is_the_last_entry_of_both_to_dropdowns_and_absent_from_from(self):
        panel, path = _setup()
        for combo in (panel._conversion_combos[(path, "Stress")], panel.x_axis_conversion_combo):
            self.assertEqual(combo.itemText(combo.count() - 1), "Custom…")
            self.assertEqual(combo.findData("custom"), combo.count() - 1)
        for combo in (panel._unit_combos[(path, "Stress")], panel.x_axis_unit_combo):
            self.assertEqual(combo.findText("Custom"), -1)
            self.assertEqual(combo.findData("custom"), -1)

    def test_source_unit_from_the_file_stays_in_from(self):
        panel, path = _setup()  # the file's units row says MPa, which is not one of the base units
        combo = panel._unit_combos[(path, "Stress")]
        data = [combo.itemData(i) for i in range(combo.count())]
        self.assertEqual(combo.currentData(), "MPa")
        self.assertEqual(combo.currentText(), "Mega (M)")
        self.assertNotIn("Custom", data)
        self.assertEqual(data.count("MPa"), 1)

    def test_accepted_formula_converts_the_data_and_shows_the_unit(self):
        panel, path = _setup(columns=("Stress",))
        _choose_custom(panel, path, "Stress", ("x / 1000", "GPa"))
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [0.1, 0.2, 0.3]))
        self.assertEqual(panel._unit_combos[(path, "Stress")].currentData(), "MPa")
        self.assertEqual(panel._conversion_combos[(path, "Stress")].currentText(), "Custom (GPa)")
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
        self.assertEqual(panel._unit_combos[(path, "Stress")].currentData(), "MPa")
        self.assertEqual(panel._conversion_combos[(path, "Stress")].currentData(), "custom")

    def test_choosing_a_real_unit_after_custom_goes_back_to_unit_conversion(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x*2", ""))
        combo = panel._conversion_combos[(path, "Stress")]
        combo.setCurrentIndex(combo.findData("to:GPa"))
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "to:GPa")
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].y, [0.1, 0.2, 0.3]))
        self.assertIn("to:GPa", [panel._conversion_combos[(path, "Stress")].itemData(i)
                                 for i in range(panel._conversion_combos[(path, "Stress")].count())])

    def test_custom_without_a_unit_label_shows_no_unit_in_the_title(self):
        panel, path = _setup()
        _choose_custom(panel, path, "Stress", ("x*2", ""))
        self.assertEqual(panel.y1_title_edit.text(), "Stress, Strain")

    def test_cancelling_custom_restores_previous_regular_target(self):
        panel, path = _setup(columns=("Stress",))
        combo = panel._conversion_combos[(path, "Stress")]
        combo.setCurrentIndex(combo.findData("to:GPa"))
        _choose_custom(panel, path, "Stress", None)
        self.assertEqual(combo.currentData(), "to:GPa")
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "to:GPa")

    def test_pending_custom_selection_does_not_change_saved_conversion(self):
        panel, path = _setup(columns=("Stress",))
        combo = panel._conversion_combos[(path, "Stress")]
        combo.setCurrentIndex(combo.findData("custom"))
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "as-is")

    def test_rebuilding_settings_keeps_formula_in_to_and_source_in_from(self):
        panel, path = _setup(columns=("Stress",))
        _choose_custom(panel, path, "Stress", ("x/1000", "GPa"))
        panel._refresh_column_settings()
        self.assertEqual(panel._unit_combos[(path, "Stress")].currentData(), "MPa")
        self.assertEqual(panel._conversion_combos[(path, "Stress")].currentText(), "Custom (GPa)")

    def test_changing_source_unit_keeps_the_selected_formula(self):
        panel, path = _setup(columns=("Stress",))
        _choose_custom(panel, path, "Stress", ("x/1000", "GPa"))
        source = panel._unit_combos[(path, "Stress")]
        source.setCurrentIndex(source.findData("GPa"))
        self.assertEqual(source.currentData(), "GPa")
        self.assertEqual(panel._column_settings[path]["Stress"]["conversion"], "custom")
        self.assertEqual(panel._conversion_combos[(path, "Stress")].currentText(), "Custom (GPa)")

    def test_custom_target_label_fits_inside_closed_to_dropdown(self):
        previous = self.app.styleSheet()
        self.addCleanup(lambda: self.app.setStyleSheet(previous))
        self.app.setStyleSheet(build_app_stylesheet())
        panel, path = _setup(columns=("Stress",))
        _choose_custom(panel, path, "Stress", ("x/1000", "GPa"))
        combo = panel._conversion_combos[(path, "Stress")]
        combo.ensurePolished()
        option = QStyleOptionComboBox()
        combo.initStyleOption(option)
        text_rect = combo.style().subControlRect(QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxEditField, combo)
        self.assertGreaterEqual(text_rect.width(), combo.fontMetrics().horizontalAdvance(combo.currentText()))


class CustomXAxisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_x_axis_formula_converts_x(self):
        panel, path = _setup()
        asked = []
        panel._ask_formula = lambda f, c, formula, unit: asked.append((c, formula)) or ("x / 60", "min")
        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("custom"))
        panel.x_axis_conversion_combo.activated.emit(panel.x_axis_conversion_combo.currentIndex())
        self.assertEqual(asked[0][0], "Time")
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].x, [0, 10 / 60, 20 / 60]))
        self.assertIn("min", panel.x_title_edit.text())
        self.assertEqual(panel.x_axis_conversion_combo.currentText(), "Custom (min)")
        self.assertEqual(panel.x_axis_unit_combo.currentData(), "s")

    def test_cancelled_x_dialog_keeps_the_unit(self):
        panel, path = _setup()
        panel._ask_formula = lambda *args: None
        before = panel.x_axis_unit_combo.currentText()
        panel.x_axis_conversion_combo.setCurrentIndex(panel.x_axis_conversion_combo.findData("custom"))
        panel.x_axis_conversion_combo.activated.emit(panel.x_axis_conversion_combo.currentIndex())
        self.assertEqual(panel.x_axis_unit_combo.currentText(), before)

    def test_x_cancel_restores_previous_regular_target_and_saved_state(self):
        panel, path = _setup()
        combo = panel.x_axis_conversion_combo
        combo.setCurrentIndex(combo.findData("to:min"))
        panel._ask_formula = lambda *args: None
        combo.setCurrentIndex(combo.findData("custom"))
        self.assertEqual(panel.state()["x_axis_conversion"], "to:min")
        combo.activated.emit(combo.currentIndex())
        self.assertEqual(combo.currentData(), "to:min")
        self.assertEqual(panel.state()["x_axis_conversion"], "to:min")

    def test_x_formula_can_be_reopened_cancelled_and_replaced_by_regular_conversion(self):
        panel, path = _setup()
        combo = panel.x_axis_conversion_combo
        panel._ask_formula = lambda *args: ("x/60", "min")
        combo.setCurrentIndex(combo.findData("custom"))
        combo.activated.emit(combo.currentIndex())
        asked = []
        panel._ask_formula = lambda *args: asked.append(args) or None
        combo.activated.emit(combo.currentIndex())
        self.assertEqual(asked[0][2:], ("x/60", "min"))
        self.assertEqual(combo.currentText(), "Custom (min)")
        self.assertEqual(panel.state()["x_axis_conversion"], "custom")
        combo.setCurrentIndex(combo.findData("to:h"))
        self.assertEqual(panel.state()["x_axis_conversion"], "to:h")
        figure = panel.canvas._build_figure(panel.state())
        self.assertTrue(np.allclose(figure.data[0].x, [0, 10/3600, 20/3600]))

    def test_x_changing_source_unit_keeps_formula_until_target_is_changed(self):
        panel, path = _setup()
        panel._ask_formula = lambda *args: ("x/60", "min")
        target = panel.x_axis_conversion_combo
        target.setCurrentIndex(target.findData("custom"))
        target.activated.emit(target.currentIndex())
        source = panel.x_axis_unit_combo
        source.setCurrentIndex(source.findData("min"))
        self.assertEqual(source.currentData(), "min")
        self.assertEqual(target.currentText(), "Custom (min)")
        self.assertEqual(panel.state()["x_axis_conversion"], "custom")


if __name__ == "__main__":
    unittest.main()
