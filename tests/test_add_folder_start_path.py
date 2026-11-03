import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


class AddFolderStartPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_add_folder_starts_at_startup_path_in_both_modes(self):
        with tempfile.TemporaryDirectory(prefix="opview project ") as tmp:
            project = Path(tmp)
            window = MainWindow(project_path=project)
            self.addCleanup(window.close)
            settings = Mock()
            settings.value.return_value = str(project / "previous-folder")
            window._settings = settings
            for mode in ("vtk", "custom_graph"):
                with self.subTest(mode=mode):
                    window.sidebar_widget.set_mode(mode)
                    with patch("app.main_window.QFileDialog.getExistingDirectory", return_value="") as dialog:
                        window._on_add_project_folder()

                    self.assertEqual(dialog.call_args.args[2], str(project))
                    settings.setValue.assert_not_called()

    def test_add_folder_without_startup_path_uses_saved_folder_in_both_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("pathlib.Path.cwd", return_value=Path(tmp)):
                window = MainWindow()
            self.addCleanup(window.close)
            settings = Mock()
            settings.value.return_value = tmp
            window._settings = settings
            for mode, key in (("vtk", "last_vtk_folder"), ("custom_graph", "last_text_folder")):
                with self.subTest(mode=mode):
                    window.sidebar_widget.set_mode(mode)
                    with patch("app.main_window.QFileDialog.getExistingDirectory", return_value="") as dialog:
                        window._on_add_project_folder()

                    self.assertEqual(dialog.call_args.args[2], tmp)
                    settings.value.assert_called_with(key, "")
                    settings.setValue.assert_not_called()
