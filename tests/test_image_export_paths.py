import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings

from utils.image_export_paths import image_export_path, remember_image_export_path


class ImageExportPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_file = str(Path(self.temp.name) / "settings.ini")
        settings = patch(
            "utils.image_export_paths.QSettings",
            side_effect=lambda *args: QSettings(self.settings_file, QSettings.IniFormat),
        )
        settings.start()
        self.addCleanup(settings.stop)

    def test_first_export_keeps_default_filename(self):
        self.assertEqual(image_export_path("heatmap.png"), "heatmap.png")

    def test_saved_folder_is_reused_with_next_filename_and_new_settings_instance(self):
        folder = Path(self.temp.name) / "images"
        folder.mkdir()
        remember_image_export_path(str(folder / "first.png"))
        self.assertEqual(image_export_path("next.png"), str(folder / "next.png"))

    def test_empty_path_does_not_replace_saved_folder(self):
        remember_image_export_path(str(Path(self.temp.name) / "first.png"))
        remember_image_export_path("")
        self.assertEqual(image_export_path("next.png"), str(Path(self.temp.name) / "next.png"))

    def test_deleted_folder_falls_back_to_default_filename(self):
        folder = Path(self.temp.name) / "removed"
        folder.mkdir()
        remember_image_export_path(str(folder / "first.png"))
        folder.rmdir()
        self.assertEqual(image_export_path("next.png"), "next.png")

    def make_controller(self):
        from viewer.heatmap_controller import HeatmapController

        controller = HeatmapController.__new__(HeatmapController)
        controller.dataset_info = {"label": "Sample"}
        controller.export_widget = Mock()
        controller.controls_widget = Mock()
        controller._save_high_resolution_export_png = Mock(return_value=True)
        controller._save_current_export_widget_png = Mock(return_value=False)
        return controller

    def test_next_export_from_another_controller_reopens_saved_folder(self):
        first = self.make_controller()
        second = self.make_controller()
        saved_path = str(Path(self.temp.name) / "chosen.png")
        with patch("viewer.heatmap_controller.QFileDialog.getSaveFileName", side_effect=[
            (saved_path, "PNG (*.png)"), ("", ""),
        ]) as dialog:
            first._export_png()
            second._export_png()

        expected = Path(self.temp.name) / second._default_export_filename("Sample")
        self.assertEqual(dialog.call_args_list[1].args[2], str(expected))
        self.assertEqual(image_export_path("next.png"), str(Path(self.temp.name) / "next.png"))
        second._save_high_resolution_export_png.assert_not_called()

    def test_failed_export_keeps_previous_folder(self):
        remember_image_export_path(str(Path(self.temp.name) / "previous.png"))
        failed_folder = Path(self.temp.name) / "failed"
        failed_folder.mkdir()
        controller = self.make_controller()
        controller._save_high_resolution_export_png.return_value = False
        with patch("viewer.heatmap_controller.QFileDialog.getSaveFileName", return_value=(
            str(failed_folder / "image.png"), "PNG (*.png)",
        )):
            controller._export_png()
        self.assertEqual(image_export_path("next.png"), str(Path(self.temp.name) / "next.png"))

    def test_plotly_remembers_folder_only_after_download_completes(self):
        from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
        from utils.webengine_downloads import install_save_dialog_download_handler

        web_view = Mock()
        download = Mock()
        download.suggestedFileName.return_value = "plot.png"
        download.DownloadState = QWebEngineDownloadRequest.DownloadState
        download.state.return_value = download.DownloadState.DownloadInProgress
        saved_path = str(Path(self.temp.name) / "plot.png")
        with patch("utils.webengine_downloads.QWebEngineProfile"), patch(
            "utils.webengine_downloads.QWebEnginePage"
        ), patch("utils.webengine_downloads.QFileDialog.getSaveFileName", return_value=(saved_path, "PNG (*.png)")):
            install_save_dialog_download_handler(web_view, Mock(), fallback_name="plot.png")
            web_view._opview_download_handler(download)

        callback = download.stateChanged.connect.call_args.args[0]
        callback()
        self.assertEqual(image_export_path("next.png"), "next.png")
        download.state.return_value = download.DownloadState.DownloadCompleted
        callback()
        self.assertEqual(image_export_path("next.png"), str(Path(self.temp.name) / "next.png"))
