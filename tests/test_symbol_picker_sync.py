"""The symbol popup edits the complete label and mirrors the original field live."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from graphs.symbol_picker import attach_symbol_picker
from utils.label_formatting import label_to_html


class SymbolPickerSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_picker(self, text="Stress [MPa]"):
        edit = QLineEdit(text)
        picker = attach_symbol_picker(edit)
        self.addCleanup(picker.close)
        return edit, picker

    def test_full_existing_label_is_loaded_in_dialog(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        self.assertEqual(picker.script_input.text(), "Stress [MPa]")
        self.assertEqual(picker.preview_label.text(), "Stress [MPa]")

    def test_dialog_edits_replace_full_label_live_without_appending(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        picker.script_input.setText("σ_xx [MPa]")
        self.assertEqual(edit.text(), "σ_xx [MPa]")
        self.assertEqual(picker.preview_label.text(), "σ<sub>xx</sub> [MPa]")

    def test_external_changes_update_dialog_and_preview(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        edit.setText("ε^p")
        self.assertEqual(picker.script_input.text(), "ε^p")
        self.assertEqual(picker.preview_label.text(), "ε<sup>p</sup>")

    def test_symbol_uses_dialog_cursor_instead_of_old_source_cursor(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        picker.script_input.setCursorPosition(0)
        sigma = next(button for button in picker.findChildren(QPushButton) if button.text() == "σ")
        sigma.click()
        self.assertEqual(edit.text(), "σStress [MPa]")
        self.assertEqual(picker.script_input.text(), edit.text())

    def test_symbol_replaces_dialog_selection(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        picker.script_input.setSelection(0, 6)
        picker.symbol_chosen.emit("σ")
        self.assertEqual(edit.text(), "σ [MPa]")

    def test_existing_text_can_be_deleted_with_keyboard_and_backspace_button(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        picker.script_input.setSelection(0, 6)
        QTest.keyClick(picker.script_input, Qt.Key.Key_Backspace)
        self.assertEqual(edit.text(), " [MPa]")
        picker.script_input.setCursorPosition(1)
        picker.backspace_button.click()
        self.assertEqual(edit.text(), "[MPa]")

    def test_mixed_formatting_is_synchronized_without_insert(self):
        edit, picker = self.make_picker("σxxyy")
        picker.show_centered(edit)
        picker.script_input.setSelection(1, 2)
        picker.sup_button.click()
        pending = picker.script_input.text()
        picker.script_input.setSelection(pending.index("yy"), 2)
        picker.sub_button.click()
        self.assertEqual(edit.text(), "σ^xx_yy")
        self.assertEqual(picker.script_input.text(), edit.text())
        self.assertEqual(picker.preview_label.text(), "σ<sup>xx</sup><sub>yy</sub>")

    def test_normal_removes_formatting_only_from_dialog_selection(self):
        edit, picker = self.make_picker("σ^xx_yy")
        picker.show_centered(edit)
        picker.script_input.setSelection(2, 2)
        picker.normal_button.click()
        self.assertEqual(edit.text(), "σxx_yy")

    def test_clear_keeps_both_fields_and_preview_empty(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        picker.clear_button.click()
        self.assertEqual(edit.text(), "")
        self.assertEqual(picker.script_input.text(), "")
        self.assertEqual(picker.preview_label.text(), "")

    def test_live_edits_survive_close_and_reopen(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        picker.script_input.setText("σ_xx")
        picker.close()
        picker.show_centered(edit)
        self.assertEqual(edit.text(), "σ_xx")
        self.assertEqual(picker.script_input.text(), "σ_xx")

    def test_source_undo_redo_is_mirrored_in_dialog(self):
        edit, picker = self.make_picker("σxx")
        picker.show_centered(edit)
        picker.script_input.setSelection(1, 2)
        picker.sub_button.click()
        edit.undo()
        self.assertEqual(edit.text(), "σxx")
        self.assertEqual(picker.script_input.text(), "σxx")
        edit.redo()
        self.assertEqual(picker.script_input.text(), "σ_xx")

    def test_typing_notifies_existing_label_handler_without_signal_loop(self):
        edit, picker = self.make_picker()
        picker.show_centered(edit)
        commits = []
        edit.editingFinished.connect(lambda: commits.append(edit.text()))
        picker.script_input.setText("σ_xx")
        QTest.qWait(250)
        self.assertEqual(commits, ["σ_xx"])
        self.assertEqual(picker.preview_label.text(), label_to_html(edit.text()))

    def test_dialog_undo_and_redo_are_mirrored_in_original_field(self):
        edit, picker = self.make_picker("Stress")
        picker.show_centered(edit)
        picker.script_input.insert(" xx")
        picker.script_input.undo()
        self.assertEqual(edit.text(), "Stress")
        picker.script_input.redo()
        self.assertEqual(edit.text(), "Stress xx")

    def test_reverse_selection_is_kept_when_opening_dialog(self):
        edit, picker = self.make_picker("Stress [MPa]")
        edit.setSelection(6, -6)
        picker.show_centered(edit)
        self.assertEqual(picker.script_input.selectedText(), "Stress")
        self.assertEqual(picker.script_input.cursorPosition(), 0)
        picker.symbol_chosen.emit("σ")
        self.assertEqual(edit.text(), "σ [MPa]")

    def test_backspace_can_remove_empty_format_template_without_removing_base(self):
        edit, picker = self.make_picker("σ")
        picker.show_centered(edit)
        picker.sup_button.click()
        self.assertEqual(edit.text(), "σ^{}")
        picker.backspace_button.click()
        self.assertEqual(edit.text(), "σ")
