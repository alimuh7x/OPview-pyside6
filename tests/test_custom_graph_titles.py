"""Custom Graph: automatic axis titles, sensible default X column, and load-failure reasons."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QCheckBox, QLabel

from graphs.tab_widget import CustomGraphTab

_STRESS_STRAIN = str(Path("Project1/TextData/StressStrainFile.txt").resolve())


def _panel_with(*files):
    tab = CustomGraphTab()
    panel = tab._tabs.widget(0)
    panel.add_files([str(f) for f in files])
    return tab, panel


def _check(panel, name):
    return next(c for c in panel.findChildren(QCheckBox) if c.text() == name)


def _convert(panel, file_path, column, source, target):
    """Pick the From entry, then the To entry, as a user does (entries keep their unit as data)."""
    unit = panel._unit_combos[(file_path, column)]
    unit.setCurrentIndex(unit.findData(source))
    combo = panel._conversion_combos[(file_path, column)]
    combo.setCurrentIndex(combo.findData("as-is" if target == source else f"to:{target}"))


def _convert_x(panel, source, target):
    panel.x_axis_unit_combo.setCurrentIndex(panel.x_axis_unit_combo.findData(source))
    combo = panel.x_axis_conversion_combo
    combo.setCurrentIndex(combo.findData("as-is" if target == source else f"to:{target}"))



def _type_into(edit, text):
    """What a user typing does: the text changes and `textEdited` fires (setText alone does not)."""
    edit.setText(text)
    edit.textEdited.emit(text)
    edit.editingFinished.emit()


class DefaultXColumnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_time_is_preferred_over_the_first_column_timestep(self):
        _tab, panel = _panel_with(_STRESS_STRAIN)

        self.assertEqual(panel.x_axis_combo.itemData(0), "TimeStep")  # the file's first column ...
        self.assertEqual(panel.x_axis_combo.currentData(), "Time")  # ... is not the default

    def test_first_column_is_used_when_there_is_no_time_column(self):
        path = Path(tempfile.mkdtemp()) / "nt.txt"
        path.write_text("Strain Stress\n0 0\n1 2\n", encoding="utf-8")

        _tab, panel = _panel_with(path)

        self.assertEqual(panel.x_axis_combo.currentData(), "Strain")

    def test_a_column_the_user_chose_is_kept_when_more_files_are_added(self):
        _tab, panel = _panel_with(_STRESS_STRAIN)
        panel.x_axis_combo.setCurrentIndex(panel.x_axis_combo.findData("Epsilon_xx"))

        panel.add_files([str(Path("Project1/TextData/CRSSFile.txt").resolve())])

        self.assertEqual(panel.x_axis_combo.currentData(), "Epsilon_xx")


class AutoTitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tab, self.panel = _panel_with(_STRESS_STRAIN)

    def _select_x(self, column):
        self.panel.x_axis_combo.setCurrentIndex(self.panel.x_axis_combo.findData(column))

    def test_x_title_follows_the_x_column(self):
        self._select_x("Epsilon_xx")

        self.assertEqual(self.panel.x_title_edit.text(), "Epsilon_xx")
        self.assertEqual(self.panel.state()["x_axis_title"], "Epsilon_xx")

    def test_y_title_follows_the_selected_column(self):
        _check(self.panel, "Sigma_xx").setChecked(True)

        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx")

    def test_two_columns_are_listed_and_more_are_abbreviated(self):
        for name in ("Sigma_xx", "Mises"):
            _check(self.panel, name).setChecked(True)
        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx, Mises")

        for name in ("Sigma_yy", "Pressure"):
            _check(self.panel, name).setChecked(True)
        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx, Mises, …")

    def test_unchecking_all_columns_returns_the_generic_title(self):
        check = _check(self.panel, "Sigma_xx")
        check.setChecked(True)

        check.setChecked(False)

        self.assertEqual(self.panel.y1_title_edit.text(), "Y1")
        self.assertEqual(self.panel.y2_title_edit.text(), "Y2")

    def test_second_axis_title_follows_columns_assigned_to_y2(self):
        _check(self.panel, "Sigma_xx").setChecked(True)
        _check(self.panel, "Mises").setChecked(True)
        settings = self.panel._column_settings[_STRESS_STRAIN]["Mises"]

        self.panel._set_yaxis(_STRESS_STRAIN, "Mises", "y2")

        self.assertEqual(settings["yaxis"], "y2")
        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx")
        self.assertEqual(self.panel.y2_title_edit.text(), "Mises")

    def test_conversion_units_appear_in_the_titles(self):
        _check(self.panel, "Sigma_xx").setChecked(True)
        _convert(self.panel, _STRESS_STRAIN, "Sigma_xx", "s", "ms")
        self._select_x("Epsilon_xx")
        _convert_x(self.panel, "-", "%")

        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx (ms)")
        self.assertEqual(self.panel.x_title_edit.text(), "Epsilon_xx (%)")

    def test_time_conversions_name_their_unit(self):
        _convert_x(self.panel, "s", "min")

        self.assertEqual(self.panel.x_title_edit.text(), "Time (min)")

    def test_mixed_units_on_one_axis_give_no_unit(self):
        _check(self.panel, "Sigma_xx").setChecked(True)
        _check(self.panel, "Mises").setChecked(True)

        _convert(self.panel, _STRESS_STRAIN, "Mises", "s", "min")

        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx, Mises")

    def test_a_title_you_typed_is_never_overwritten(self):
        _type_into(self.panel.y1_title_edit, "Stress")

        _check(self.panel, "Sigma_xx").setChecked(True)
        _check(self.panel, "Mises").setChecked(True)

        self.assertEqual(self.panel.y1_title_edit.text(), "Stress")
        self.assertEqual(self.panel.state()["yaxis1_title"], "Stress")

    def test_clearing_a_typed_title_returns_to_automatic(self):
        _check(self.panel, "Sigma_xx").setChecked(True)
        _type_into(self.panel.y1_title_edit, "Stress")

        _type_into(self.panel.y1_title_edit, "")

        self.assertEqual(self.panel.y1_title_edit.text(), "Sigma_xx")

    def test_titles_reach_the_plot(self):
        _check(self.panel, "Sigma_xx").setChecked(True)
        self._select_x("Epsilon_xx")

        figure = self.panel.canvas._build_figure(self.panel.state())

        self.assertEqual(figure.layout.xaxis.title.text, "Epsilon_xx")
        self.assertEqual(figure.layout.yaxis.title.text, "Sigma_xx")

    def test_units_from_the_file_are_used_when_no_conversion_is_applied(self):
        path = Path(tempfile.mkdtemp()) / "units.txt"
        path.write_text("Time Stress\n[s] [Pa]\n0 1.5\n1 2.5\n", encoding="utf-8")
        _tab, panel = _panel_with(path)

        _check(panel, "Stress").setChecked(True)

        self.assertEqual(panel.x_title_edit.text(), "Time (s)")
        self.assertEqual(panel.y1_title_edit.text(), "Stress (Pa)")

    def test_a_conversion_replaces_the_file_unit(self):
        path = Path(tempfile.mkdtemp()) / "units2.txt"
        path.write_text("Time Stress\n[s] [Pa]\n0 1.5\n1 2.5\n", encoding="utf-8")
        _tab, panel = _panel_with(path)
        _check(panel, "Stress").setChecked(True)

        panel._set_conversion(str(path.resolve()), "Stress", "mpa")

        self.assertEqual(panel.y1_title_edit.text(), "Stress (MPa)")


class LoadFailureReasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _labels(self, panel):
        return [label.text() for label in panel.findChildren(QLabel)]

    def test_the_reason_is_shown_instead_of_a_generic_message(self):
        _tab, panel = _panel_with(Path("Project1/TextData/PlasticityDiagnosis.txt").resolve())

        texts = self._labels(panel)

        self.assertNotIn("Could not load file", texts)
        self.assertTrue(any("header" in text.lower() for text in texts), texts)

    def test_a_text_only_file_says_there_are_no_numeric_columns(self):
        path = Path(tempfile.mkdtemp()) / "words.txt"
        path.write_text("a b\nx y\nz w\n", encoding="utf-8")
        _tab, panel = _panel_with(path)

        self.assertTrue(any("numeric" in text.lower() for text in self._labels(panel)))


if __name__ == "__main__":
    unittest.main()
