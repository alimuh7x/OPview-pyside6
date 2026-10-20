import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from graphs.symbol_picker import SYMBOL_GROUPS, SymbolPicker, attach_symbol_picker


class SymbolPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_groups_cover_greek_and_si_units(self):
        symbols = {s for _, items in SYMBOL_GROUPS for s in items}
        for expected in ("σ", "ε", "Δ", "μ", "φ", "ϕ", "ϑ", "ϵ", "N/m²", "m²/s", "s⁻¹"):
            self.assertIn(expected, symbols)

    def test_powers_replace_operator_and_comparison_signs(self):
        symbols = {s for _, items in SYMBOL_GROUPS for s in items}
        for power in ("⁻⁴", "⁻³", "⁻²", "⁻¹", "¹", "²", "³", "⁴"):
            self.assertIn(power, symbols)
        for removed in ("×", "÷", "=", "≠", "≈", "≤", "≥", "√"):
            self.assertNotIn(removed, symbols)

    def test_greek_buttons_use_serif_italic_font(self):
        picker = SymbolPicker()
        sigma = next(b for b in picker.findChildren(QPushButton) if b.text() == "σ")
        unit = next(b for b in picker.findChildren(QPushButton) if b.text() == "MPa")
        self.assertTrue(sigma.font().italic())
        self.assertEqual(sigma.font().family(), "STIX Two Text")
        self.assertFalse(unit.font().italic())

    def test_ion_charge_buttons_insert_superscript_charges(self):
        for charge, ion in (("¹⁺", "Na"), ("²⁺", "Ca"), ("³⁺", "Fe"), ("⁴⁺", "Ti")):
            with self.subTest(charge=charge):
                self.assertIn(charge, dict(SYMBOL_GROUPS)["Powers"])
                edit = QLineEdit(ion)
                picker = attach_symbol_picker(edit)
                finished = []
                edit.editingFinished.connect(lambda: finished.append(edit.text()))
                button = next(b for b in picker.findChildren(QPushButton) if b.text() == charge)
                button.click()
                self.assertEqual(edit.text(), ion + charge)
                self.assertEqual(finished, [ion + charge])

    def test_clicking_symbol_emits_it(self):
        picker = SymbolPicker()
        chosen = []
        picker.symbol_chosen.connect(chosen.append)
        button = next(b for b in picker.findChildren(QPushButton) if b.text() == "σ")
        button.click()
        self.assertEqual(chosen, ["σ"])

    def test_attached_picker_inserts_at_cursor_and_finishes_edit(self):
        edit = QLineEdit("Stress  [MPa]")
        finished = []
        edit.editingFinished.connect(lambda: finished.append(edit.text()))
        picker = attach_symbol_picker(edit)
        edit.setCursorPosition(7)
        picker.symbol_chosen.emit("σ")
        self.assertEqual(edit.text(), "Stress σ [MPa]")
        self.assertEqual(finished, ["Stress σ [MPa]"])

    def test_opens_in_center_of_screen(self):
        edit = QLineEdit()
        picker = SymbolPicker(edit)
        picker.show_centered(edit)
        area = edit.screen().availableGeometry()
        self.assertLessEqual(abs(picker.geometry().center().x() - area.center().x()), 1)
        self.assertLessEqual(abs(picker.geometry().center().y() - area.center().y()), 1)
        picker.close()


if __name__ == "__main__":
    unittest.main()
