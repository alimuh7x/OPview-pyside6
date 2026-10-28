"""Symbol insertion in the label editors outside Custom Graph."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from graphs.symbol_picker import SymbolPicker
from graphs.graph_panel_widget import GraphPanelWidget
from multi_property.multi_property_cell import MultiPropertyCell
from multi_property.multi_property_panel import MultiPropertyPanel
from multi_view.multi_view_cell import MultiViewHeader
from multi_view.multi_view_panel import MultiViewPanel
from viewer.panel_controls_widget import PanelControlsWidget
from viewer.panel_widget import PanelWidget


class LabelSymbolPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.addCleanup(lambda: QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete))

    def check_insertion(self, edit):
        picker = edit.findChild(SymbolPicker)
        self.assertIsNotNone(picker, "Label editor must offer the symbol picker")
        self.assertTrue(any(action.text() == "Insert symbol" for action in edit.actions()))
        edit.setText("Stress  [MPa]")
        edit.setCursorPosition(7)
        finished = []
        edit.editingFinished.connect(lambda: finished.append(edit.text()))
        picker.symbol_chosen.emit("σ")
        self.assertEqual(edit.text(), "Stress σ [MPa]")
        self.assertEqual(finished, ["Stress σ [MPa]"])

    def test_single_view_colorbar_label(self):
        panel = PanelWidget({"label": "Test", "files": []})
        self.addCleanup(panel.deleteLater)
        self.check_insertion(panel.colorbar_label_edit)

    def test_custom_graph_title_can_be_cleared_and_replaced_inside_popup(self):
        panel = GraphPanelWidget(1)
        self.addCleanup(panel.deleteLater)
        edit = panel.x_title_edit
        picker = edit.findChild(SymbolPicker)
        picker.show_centered(edit)
        self.addCleanup(picker.close)
        self.assertEqual(picker.script_input.text(), "Time")
        picker.clear_button.click()
        QTest.qWait(250)
        self.assertEqual(edit.text(), "")
        self.assertEqual(picker.script_input.text(), "")
        picker.script_input.setText("σ_xx")
        QTest.qWait(250)
        self.assertEqual(edit.text(), "σ_xx")
        self.assertEqual(picker.preview_label.text(), "σ<sub>xx</sub>")

    def test_multi_view_colorbar_label(self):
        panel = MultiViewPanel({"available_projects": []})
        self.addCleanup(panel.deleteLater)
        self.check_insertion(panel.colorbar_label_edit)

    def test_multi_view_legend_updates_existing_signal(self):
        header = MultiViewHeader("PhaseField_00000001.vts")
        self.addCleanup(header.deleteLater)
        renamed = []
        header.legend_name_changed.connect(lambda path, name: renamed.append((path, name)))
        self.check_insertion(header._name_edit)
        self.assertEqual(renamed, [(header.file_path, "Stress σ [MPa]")])

    def test_multi_property_analysis_value_label(self):
        panel = MultiPropertyPanel({"available_projects": []})
        self.addCleanup(panel.deleteLater)
        self.check_insertion(panel.analysis_value_label_edit)
        self.assertEqual(panel._analysis_value_label(), "Stress σ [MPa]")

    def test_property_rename_dialog_keeps_symbols_until_confirmed(self):
        cell = MultiPropertyCell("stress", "Stress", bottom_row=False)
        self.addCleanup(cell.deleteLater)
        dialog = cell._build_rename_dialog()
        self.check_insertion(dialog.findChild(QLineEdit))
        self.assertEqual(dialog.textValue(), "Stress σ [MPa]")
        self.assertEqual(cell.label, "Stress")

    def test_phase_rename_dialog_keeps_symbols_until_confirmed(self):
        controls = PanelControlsWidget({"files": []})
        self.addCleanup(controls.deleteLater)
        dialog = controls._build_phase_fraction_rename_dialog("PhaseFraction_0", "Phase 0")
        self.check_insertion(dialog.findChild(QLineEdit))
        self.assertEqual(dialog.textValue(), "Stress σ [MPa]")


if __name__ == "__main__":
    unittest.main()
