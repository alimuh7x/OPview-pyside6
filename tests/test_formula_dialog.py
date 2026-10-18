"""Custom conversion dialog: buttons that build a formula, live preview, validation."""

import os
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from graphs.formula_dialog import FormulaDialog

_DATA = {
    "Sigma": np.array([10.0, 20.0, 30.0]),
    "Epsilon xx": np.array([2.0, 4.0, 5.0]),
    "Time": np.array([1.0, 2.0, 3.0]),
}


def _button(dialog, text):
    return next(b for b in dialog.findChildren(QPushButton) if b.text() == text)


def _set(dialog, text):
    dialog.formula_edit.setPlainText(text)
    dialog.refresh_preview()


class FormulaDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, **kwargs):
        return FormulaDialog(None, current_column="Sigma", column_data=_DATA, **kwargs)

    def test_operator_buttons_insert_at_the_cursor(self):
        d = self.make()
        _button(d, "Sigma").click()
        _button(d, "*").click()
        d.insert_text("2")
        self.assertEqual(d.formula(), "Sigma * 2")

    def test_button_replaces_the_selection_and_keeps_focus_in_the_editor(self):
        d = self.make(formula="x + 1")
        cursor = d.formula_edit.textCursor()
        cursor.setPosition(4)
        cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
        d.formula_edit.setTextCursor(cursor)
        _button(d, "*").click()
        self.assertEqual(d.formula(), "x + *")
        self.assertEqual(d.formula_edit.textCursor().position(), 6)  # after the space that follows the entry

    def test_token_buttons_do_not_take_mouse_focus(self):
        d = self.make()
        self.assertEqual(_button(d, "+").focusPolicy(), Qt.FocusPolicy.TabFocus)

    def test_function_button_puts_the_caret_between_the_brackets(self):
        d = self.make()
        _button(d, "sqrt").click()
        d.insert_text("x")
        self.assertEqual(d.formula(), "sqrt(x)")  # no stray space before the closing bracket

    def test_function_button_wraps_a_selection(self):
        d = self.make(formula="x + 1")
        d.formula_edit.selectAll()
        _button(d, "abs").click()
        self.assertEqual(d.formula(), "abs(x + 1)")

    def test_valid_formula_enables_apply_and_previews_values(self):
        d = self.make()
        _set(d, "x / [Epsilon xx]")
        self.assertTrue(d.apply_button.isEnabled())
        self.assertIn("5", d.preview_label.text())
        self.assertEqual(d.preview_label.property("state"), "ok")

    def test_invalid_formula_disables_apply_and_says_why(self):
        d = self.make()
        _set(d, "x + Nope")
        self.assertFalse(d.apply_button.isEnabled())
        self.assertIn("Nope", d.preview_label.text())
        self.assertEqual(d.preview_label.property("state"), "error")

    def test_numbers_are_not_drawn_in_a_red_or_orange_colour(self):
        from graphs import formula_dialog_style as style

        colour = style.SYNTAX_NUMBER.lstrip("#")
        red, green, blue = (int(colour[i:i + 2], 16) for i in (0, 2, 4))
        self.assertLess(red, max(green, blue))  # teal/blue family, never red or orange
        d = self.make(formula="Sigma * 2.5")
        self.assertEqual(d.preview_label.property("state"), "ok")
        self.assertFalse(d.formula_edit.property("invalid"))

    def test_an_unfinished_formula_is_not_shown_as_an_error(self):
        d = self.make()
        for text in ("Sigma /", "Sigma * (", "sqrt(Sigma", "Sigma +"):
            _set(d, text)
            self.assertEqual(d.preview_label.property("state"), "idle", text)
            self.assertFalse(d.formula_edit.property("invalid"), text)
            self.assertFalse(d.apply_button.isEnabled(), text)

    def test_a_real_mistake_is_still_shown_as_an_error(self):
        d = self.make()
        _set(d, "Sigma + Nope")
        self.assertEqual(d.preview_label.property("state"), "error")

    def test_header_has_the_title_only(self):
        d = self.make()
        texts = [w.text() for w in d.findChildren(QLabel)]
        self.assertIn("Formula Editor", texts)
        self.assertFalse(any("Transform" in t for t in texts))

    def test_empty_formula_disables_apply(self):
        self.assertFalse(self.make().apply_button.isEnabled())

    def test_apply_is_off_until_the_new_text_has_been_checked(self):
        d = self.make()
        _set(d, "x * 2")
        d.formula_edit.setPlainText("x * ")  # typing: the debounce has not fired yet
        self.assertFalse(d.apply_button.isEnabled())

    def test_apply_accepts_only_a_valid_formula(self):
        d = self.make()
        d.formula_edit.setPlainText("x +")
        d._apply()
        self.assertNotEqual(d.result(), d.DialogCode.Accepted)
        d.formula_edit.setPlainText("x * 2")
        d._apply()
        self.assertEqual(d.result(), d.DialogCode.Accepted)

    def test_preview_never_modifies_the_data(self):
        data = {k: v.copy() for k, v in _DATA.items()}
        d = FormulaDialog(None, current_column="Sigma", column_data=data)
        _set(d, "x")
        d.formula_edit.setPlainText("x * 100 + Time")
        d.refresh_preview()
        for name in _DATA:
            self.assertTrue(np.array_equal(data[name], _DATA[name]))

    def test_multiline_formula_is_joined_to_one_line(self):
        d = self.make()
        _set(d, "x *\n  2")
        self.assertEqual(d.formula(), "x * 2")
        self.assertTrue(d.apply_button.isEnabled())

    def test_existing_formula_and_unit_are_loaded(self):
        d = self.make(formula="x/1000", unit="GPa")
        self.assertEqual(d.formula(), "x/1000")  # older formulas written with x still open and work
        self.assertEqual(d.unit(), "GPa")
        self.assertTrue(d.apply_button.isEnabled())

    def test_column_button_shows_the_column_name_and_inserts_it(self):
        d = self.make()
        self.assertEqual(d.x_button.text(), "Sigma")
        d.x_button.click()
        self.assertEqual(d.formula_edit.toPlainText(), "Sigma ")

    def test_column_with_spaces_is_inserted_in_brackets(self):
        data = {"Epsilon xx": np.array([1.0, 2.0])}
        d = FormulaDialog(None, current_column="Epsilon xx", column_data=data)
        d.x_button.click()
        self.assertEqual(d.formula(), "[Epsilon xx]")

    def test_long_column_names_are_shortened_on_the_button_only(self):
        name = "A_very_long_column_name_here"
        d = FormulaDialog(None, current_column=name, column_data={name: np.array([1.0])})
        self.assertLess(len(d.x_button.text()), len(name))
        d.x_button.click()
        self.assertEqual(d.formula(), name)

    def test_every_entry_is_followed_by_one_space(self):
        d = self.make()
        for text in ("+", "*", "("):
            _button(d, text).click()
        self.assertEqual(d.formula_edit.toPlainText(), "+ * ( ")
        d.formula_edit.clear()
        d.x_button.click()
        _button(d, "pi").click()
        self.assertEqual(d.formula_edit.toPlainText(), "Sigma pi ")

    def test_no_double_space_when_one_already_follows(self):
        d = self.make(formula="a b")
        cursor = d.formula_edit.textCursor()
        cursor.setPosition(1)
        d.formula_edit.setTextCursor(cursor)
        d.insert_text("+")
        self.assertEqual(d.formula_edit.toPlainText(), "a+ b")

    def test_function_leaves_a_space_after_its_brackets(self):
        d = self.make()
        _button(d, "sqrt").click()
        self.assertEqual(d.formula_edit.toPlainText(), "sqrt() ")
        self.assertEqual(d.formula_edit.textCursor().position(), 5)  # between the brackets

    def test_preview_names_the_column_and_there_is_no_x_label_or_example_placeholder(self):
        d = self.make(formula="Sigma * 2")
        self.assertIn("Sigma = 10", d.preview_label.text())
        self.assertNotIn("x = ", d.preview_label.text())
        self.assertFalse(hasattr(d, "context_label"))
        self.assertEqual(d.formula_edit.placeholderText(), "Sigma / 1000")
        self.assertNotIn("Epsilon", d.formula_edit.placeholderText())

    def test_formula_written_with_the_column_name_gives_the_same_result_as_x(self):
        d = self.make()
        _set(d, "Sigma / 1000")
        by_name = d.preview_label.text()
        _set(d, "x / 1000")
        self.assertEqual(by_name.split("\n")[:3], d.preview_label.text().split("\n")[:3])
        self.assertTrue(d.apply_button.isEnabled())

    def test_editor_is_large_and_monospace_styled(self):
        d = self.make()
        self.assertGreaterEqual(d.formula_edit.minimumHeight(), 100)
        self.assertIn("font-size: 15px", d.styleSheet())

    def test_insert_column_controls_are_gone(self):
        from PySide6.QtWidgets import QComboBox

        d = self.make()
        self.assertFalse(hasattr(d, "column_combo"))
        self.assertEqual(d.findChildren(QComboBox), [])
        labels = [w.text() for w in d.findChildren(QLabel)]
        self.assertFalse(any("insert column" in t.lower() for t in labels))

    def test_header_is_charcoal_and_apply_is_navy(self):
        sheet = self.make().styleSheet().lower()
        header = sheet[sheet.index("qframe#fdheader {"):]
        self.assertIn("background: #252526", header[: header.index("}")])
        primary = sheet[sheet.index("qpushbutton#fdprimary {"):]
        self.assertIn("background: #0f2d61", primary[: primary.index("}")])

    def test_unit_field_uses_the_full_width_of_its_panel(self):
        d = self.make()
        d.show()
        QApplication.processEvents()
        panel = d.unit_edit.parentWidget()
        self.assertGreater(d.unit_edit.width(), panel.width() * 0.8)

    def test_clickable_controls_have_pointer_cursors(self):
        d = self.make()
        for button in [*d.findChildren(QPushButton, "fdToken"), d.cancel_button]:
            self.assertEqual(button.cursor().shape(), Qt.CursorShape.PointingHandCursor, button.text())
        _set(d, "x * 2")
        self.assertEqual(d.apply_button.cursor().shape(), Qt.CursorShape.PointingHandCursor)
        _set(d, "x +")
        self.assertEqual(d.apply_button.cursor().shape(), Qt.CursorShape.ArrowCursor)

    def test_every_button_is_hit_exactly_where_it_is_drawn(self):
        """No overlay may sit on top of a button: the widget under a button's centre is that button."""
        d = self.make()
        d.show()
        QApplication.processEvents()
        buttons = [b for b in d.findChildren(QPushButton) if b.isVisible()]
        self.assertGreater(len(buttons), 10)
        for button in buttons:
            centre = button.mapTo(d, button.rect().center())
            self.assertIs(d.childAt(centre), button, button.text())

    def test_buttons_get_hover_events(self):
        d = self.make()
        for button in d.findChildren(QPushButton):
            self.assertTrue(button.testAttribute(Qt.WidgetAttribute.WA_Hover), button.text())

    def test_body_is_light_and_only_the_header_is_charcoal(self):
        sheet = FormulaDialog(None, current_column="Sigma", column_data=_DATA).styleSheet().lower()
        self.assertIn("background: #ffffff", sheet)
        self.assertIn("#f5f7fa", sheet)
        self.assertIn("#0f2d61", sheet)
        for dark in ("#1e1e1e", "#2d2d30"):
            self.assertNotIn(dark, sheet)
        self.assertEqual(sheet.count("background: #252526"), 1)  # the header only

    def test_window_is_frameless_translucent_and_rounded(self):
        d = self.make()
        self.assertTrue(d.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(d.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertIn("border-radius: 14px", d.styleSheet())

    def test_resize_edges_are_detected_on_the_transparent_border(self):
        from PySide6.QtCore import QPoint

        d = self.make()
        self.assertEqual(d._edges_at(QPoint(1, 300)), Qt.Edge.LeftEdge)
        self.assertEqual(
            d._edges_at(QPoint(d.width() - 1, d.height() - 1)), Qt.Edge.RightEdge | Qt.Edge.BottomEdge
        )
        self.assertEqual(d._edges_at(QPoint(350, 300)), Qt.Edge(0))

    def test_dialog_never_opens_smaller_than_its_layout_needs(self):
        d = self.make()
        d.show()
        self.assertGreaterEqual(d.width(), d.minimumWidth())
        self.assertGreaterEqual(d.height(), d.minimumHeight())

    def test_long_column_names_do_not_break_the_layout(self):
        long_name = "Very_long_column_name_" * 4
        d = FormulaDialog(None, current_column=long_name, column_data={long_name: np.array([1.0]), "b": np.array([2.0])})
        d.show()
        self.assertGreaterEqual(d.width(), d.minimumWidth())


class HighlighterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_functions_numbers_and_columns_get_different_formats(self):
        d = FormulaDialog(None, current_column="Sigma", column_data=_DATA, formula="sqrt(x) * Time + 2.5 / [Epsilon xx]")
        formats = {r.format.foreground().color().name() for r in d.formula_edit.document().firstBlock().layout().formats()}
        self.assertGreaterEqual(len(formats), 4)


if __name__ == "__main__":
    unittest.main()
