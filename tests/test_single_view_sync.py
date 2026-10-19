"""Shared timesteps survive replacement of one panel's project file list."""

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from single_view.tab_widget import SingleViewTab
from viewer.panel_controls_widget import PanelControlsWidget


class SingleViewSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_panel(self, label, files):
        controls = PanelControlsWidget({"files": []})
        self.addCleanup(controls.deleteLater)
        controls.set_file_options(files)
        return SimpleNamespace(dataset_info={"label": label}, controls_widget=controls)

    def test_replacing_project_files_reapplies_shared_timestep(self):
        tab = SingleViewTab()
        self.addCleanup(tab.deleteLater)
        source = self.make_panel("A", ["/old/A_0.vts", "/old/A_500.vts"])
        target = self.make_panel("B", ["/old/B_0.vts", "/old/B_500.vts"])
        tab._attach_file_number_sharing(source)
        tab._attach_file_number_sharing(target)
        source.controls_widget.file_combo.setCurrentIndex(1)

        source.controls_widget.set_file_options(["/new/A_0.vts", "/new/A_500.vts"])

        self.assertEqual(source.controls_widget.current_file_path(), "/new/A_500.vts")
        self.assertEqual(target.controls_widget.current_file_path(), "/old/B_500.vts")
        self.assertEqual(tab._shared_file_number, 500)

    def test_project_without_shared_timestep_does_not_reset_other_tabs(self):
        tab = SingleViewTab()
        self.addCleanup(tab.deleteLater)
        source = self.make_panel("A", ["/old/A_0.vts", "/old/A_500.vts"])
        target = self.make_panel("B", ["/old/B_0.vts", "/old/B_500.vts"])
        tab._attach_file_number_sharing(source)
        tab._attach_file_number_sharing(target)
        source.controls_widget.file_combo.setCurrentIndex(1)

        source.controls_widget.set_file_options(["/new/A_0.vts"])

        self.assertEqual(target.controls_widget.current_file_path(), "/old/B_500.vts")
        self.assertEqual(tab._shared_file_number, 500)
