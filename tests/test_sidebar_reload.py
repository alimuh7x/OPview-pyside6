import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from sidebar.sidebar_widget import SidebarWidget
from utils.project_scanner import scan_project_folders


class SidebarReloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_reload_retains_startup_project_outside_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "launcher"
            cwd.mkdir()
            project = root / "DemoProject"
            (project / "VTK").mkdir(parents=True)
            with patch("pathlib.Path.cwd", return_value=cwd):
                window = MainWindow(project_path=project)
                self.addCleanup(window.close)
                sidebar = window.sidebar_widget
                item = sidebar.project_list.item(0)
                item.setCheckState(Qt.CheckState.Checked)

                sidebar.reload_projects_button.click()

                self.assertIn("DemoProject/VTK", sidebar._projects)
                self.assertEqual(sidebar._projects["DemoProject"]["path"], project)
                self.assertEqual(sidebar.project_list.item(0).checkState(), Qt.CheckState.Checked)

    def test_reload_discovers_projects_under_startup_parent_and_keeps_manual_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "launcher"
            cwd.mkdir()
            parent = root / "projects"
            (parent / "First" / "VTK").mkdir(parents=True)
            manual = root / "Manual"
            (manual / "VTK").mkdir(parents=True)
            with patch("pathlib.Path.cwd", return_value=cwd):
                window = MainWindow(project_path=parent)
                self.addCleanup(window.close)
                sidebar = window.sidebar_widget
                sidebar.add_manual_project("Manual", scan_project_folders(manual)["Manual"])
                (parent / "Second" / "VTK").mkdir(parents=True)

                sidebar.reload_projects_button.click()

                self.assertIn("First/VTK", sidebar._projects)
                self.assertIn("Second/VTK", sidebar._projects)
                self.assertIn("Manual", sidebar._projects)

    def test_reload_without_startup_path_uses_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "LocalProject" / "VTK").mkdir(parents=True)
            with patch("pathlib.Path.cwd", return_value=cwd):
                sidebar = SidebarWidget()
                self.addCleanup(sidebar.close)

                sidebar.reload_projects_button.click()

                self.assertIn("LocalProject/VTK", sidebar._projects)
