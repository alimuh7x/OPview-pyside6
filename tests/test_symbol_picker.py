"""Shared symbol controls operate on one complete synchronized label."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from graphs.symbol_picker import SYMBOL_GROUPS, SymbolPicker, attach_symbol_picker
from utils.label_formatting import label_to_html, label_to_matplotlib


class SymbolPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_groups_cover_greek_and_si_units(self):
        symbols = {s for _, items in SYMBOL_GROUPS for s in items}
        for expected in ("σ", "ε", "Δ", "μ", "φ", "ϕ", "ϑ", "ϵ", "N/m²", "m²/s", "s⁻¹"):
            self.assertIn(expected, symbols)

    def test_powers_and_ion_charges_are_available(self):
        symbols = {s for _, items in SYMBOL_GROUPS for s in items}
        for power in ("⁻⁴", "⁻³", "⁻²", "⁻¹", "¹", "²", "³", "⁴", "¹⁺", "²⁺", "³⁺", "⁴⁺"):
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
                edit = QLineEdit(ion)
                picker = attach_symbol_picker(edit)
                finished = []
                edit.editingFinished.connect(lambda: finished.append(edit.text()))
                button = next(b for b in picker.findChildren(QPushButton) if b.text() == charge)
                button.click()
                self.assertEqual(edit.text(), ion + charge)
                self.assertEqual(picker.script_input.text(), edit.text())
                self.assertEqual(finished, [ion + charge])

    def test_clicking_symbol_emits_it(self):
        picker = SymbolPicker()
        chosen = []
        picker.symbol_chosen.connect(chosen.append)
        button = next(b for b in picker.findChildren(QPushButton) if b.text() == "σ")
        button.click()
        self.assertEqual(chosen, ["σ"])
        self.assertEqual(picker.script_input.text(), "σ")

    def test_attached_picker_inserts_at_cursor_and_finishes_edit(self):
        edit = QLineEdit("Stress  [MPa]")
        finished = []
        edit.editingFinished.connect(lambda: finished.append(edit.text()))
        picker = attach_symbol_picker(edit)
        edit.setCursorPosition(7)
        picker.symbol_chosen.emit("σ")
        self.assertEqual(edit.text(), "Stress σ [MPa]")
        self.assertEqual(finished, ["Stress σ [MPa]"])

    def test_opens_centered_with_preview_at_top(self):
        edit = QLineEdit("Stress")
        picker = attach_symbol_picker(edit)
        picker.show_centered(edit)
        try:
            area = edit.screen().availableGeometry()
            self.assertLessEqual(abs(picker.geometry().center().x() - area.center().x()), 1)
            self.assertLessEqual(abs(picker.geometry().center().y() - area.center().y()), 1)
            self.assertIs(picker.layout().itemAt(0).widget(), picker.preview_label)
            self.assertEqual(picker.script_input.text(), "Stress")
        finally:
            picker.close()

    def test_selected_text_can_be_subscripted_and_superscripted(self):
        for mode in ("sub", "sup"):
            with self.subTest(mode=mode):
                edit = QLineEdit("σxx [MPa]")
                picker = attach_symbol_picker(edit)
                edit.setSelection(1, 2)
                committed = []
                edit.editingFinished.connect(lambda: committed.append(edit.text()))
                getattr(picker, f"{mode}_button").click()
                marker = "_" if mode == "sub" else "^"
                self.assertEqual(edit.text(), f"σ{marker}xx [MPa]")
                self.assertEqual(committed, [edit.text()])

    def test_empty_label_can_be_closed_without_changing_it(self):
        edit = QLineEdit("")
        picker = attach_symbol_picker(edit)
        picker.done_button.click()
        self.assertEqual(edit.text(), "")

    def test_no_selection_adds_a_script_template_at_cursor(self):
        edit = QLineEdit("σ [MPa]")
        edit.setCursorPosition(1)
        picker = attach_symbol_picker(edit)
        picker.show_centered(edit)
        try:
            picker.sup_button.click()
            self.assertEqual(picker.script_input.text(), "σ^{} [MPa]")
            QTest.keyClicks(picker.script_input, "xx")
            self.assertEqual(edit.text(), "σ^{xx} [MPa]")
            self.assertEqual(picker.preview_label.text(), "σ<sup>xx</sup> [MPa]")
        finally:
            picker.close()

    def test_full_editor_escapes_literal_markup_in_preview(self):
        edit = QLineEdit("")
        picker = attach_symbol_picker(edit)
        picker.script_input.setText("σ_{x<2 & y}")
        self.assertEqual(edit.text(), "σ_{x<2 & y}")
        self.assertEqual(picker.preview_label.text(), "σ<sub>x&lt;2 &amp; y</sub>")
        picker.close()

    def test_formatting_is_one_undo_step(self):
        edit = QLineEdit("σxx")
        picker = attach_symbol_picker(edit)
        edit.setSelection(1, 2)
        picker.sub_button.click()
        edit.undo()
        self.assertEqual(edit.text(), "σxx")
        self.assertEqual(picker.script_input.text(), "σxx")

    def test_non_bmp_characters_keep_correct_cursor_positions(self):
        edit = QLineEdit("𝜎xx [MPa]")
        picker = attach_symbol_picker(edit)
        edit.setSelection(2, 2)
        picker.sub_button.click()
        self.assertEqual(edit.text(), "𝜎_xx [MPa]")
        self.assertEqual(picker.preview_label.text(), "𝜎<sub>xx</sub> [MPa]")

    def test_reformatting_selection_including_notation_uses_visible_text(self):
        for label, start, length, expected in (("σ_xx", 1, 3, "σ^xx"), ("σ_{x y}", 1, 6, "σ^{x y}")):
            with self.subTest(label=label):
                edit = QLineEdit(label)
                picker = attach_symbol_picker(edit)
                edit.setSelection(start, length)
                picker.sup_button.click()
                self.assertEqual(edit.text(), expected)

    def test_legacy_label_is_converted_and_loaded_in_full_editor(self):
        edit = QLineEdit("σ<sub>xx</sub><sup>p</sup> [MPa]")
        picker = attach_symbol_picker(edit)
        self.assertEqual(edit.text(), "σ_xx^p [MPa]")
        self.assertEqual(picker.script_input.text(), edit.text())
        self.assertEqual(picker.preview_label.text(), "σ<sub>xx</sub><sup>p</sup> [MPa]")

    def test_normal_removes_formatting_from_full_and_partial_selection(self):
        for length, expected in ((2, "σxy"), (1, "σx_y")):
            with self.subTest(length=length):
                edit = QLineEdit("σ_xy")
                picker = attach_symbol_picker(edit)
                edit.setSelection(2, length)
                picker.normal_button.click()
                self.assertEqual(edit.text(), expected)
                self.assertEqual(picker.preview_label.text(), label_to_html(expected))

    def test_backspace_preserves_notation_and_non_bmp_characters(self):
        edit = QLineEdit("𝜎_xy")
        picker = attach_symbol_picker(edit)
        for expected in ("𝜎_x", "𝜎", ""):
            picker.backspace_button.click()
            self.assertEqual(edit.text(), expected)
            self.assertEqual(picker.script_input.text(), expected)

    def test_edited_label_exports_the_same_text_as_preview(self):
        edit = QLineEdit("A&Bx")
        picker = attach_symbol_picker(edit)
        picker.backspace_button.click()
        self.assertEqual(label_to_matplotlib(edit.text()), "A&B")
        picker.script_input.insert("<2")
        self.assertEqual(label_to_matplotlib(edit.text()), "A&B<2")
        picker.close()

    def test_clear_can_be_undone_in_both_fields(self):
        original = "σ_xx"
        edit = QLineEdit(original)
        picker = attach_symbol_picker(edit)
        commits = []
        edit.editingFinished.connect(lambda: commits.append(edit.text()))
        picker.clear_button.click()
        self.assertEqual(edit.text(), "")
        self.assertEqual(picker.script_input.text(), "")
        self.assertEqual(picker.preview_label.text(), "")
        self.assertEqual(commits, [""])
        edit.undo()
        self.assertEqual(edit.text(), original)
        self.assertEqual(picker.script_input.text(), original)

    def test_format_controls_keep_contrast_under_a_dark_palette(self):
        previous = self.app.palette()
        dark = QPalette(previous)
        dark.setColor(QPalette.ColorRole.Button, QColor("#111827"))
        dark.setColor(QPalette.ColorRole.ButtonText, QColor("#111827"))
        dark.setColor(QPalette.ColorRole.Base, QColor("#111827"))
        dark.setColor(QPalette.ColorRole.Text, QColor("#f8fafc"))
        self.app.setPalette(dark)
        edit = QLineEdit("σ")
        picker = attach_symbol_picker(edit)
        try:
            picker.show()
            self.app.processEvents()
            for button in (picker.sub_button, picker.sup_button, picker.normal_button):
                self.assertLess(button.palette().color(QPalette.ColorRole.ButtonText).lightness(), 100)
                self.assertGreater(button.palette().color(QPalette.ColorRole.Button).lightness(), 200)
            self.assertLess(picker.script_input.palette().color(QPalette.ColorRole.Text).lightness(), 100)
            self.assertGreater(picker.script_input.palette().color(QPalette.ColorRole.Base).lightness(), 200)
        finally:
            picker.close()
            self.app.setPalette(previous)


if __name__ == "__main__":
    unittest.main()
