import unittest
import os
from pathlib import Path
from unittest.mock import patch

from app.resources import APP_LOGO_PATH, DOCUMENTATION_PATH, HEATMAP_LOGO_PATH
from app.application_bootstrap import _configure_no_gpu_environment, _is_supported_font_file


class AppResourcesTests(unittest.TestCase):
    def test_app_logo_uses_main_logo_asset(self):
        self.assertEqual(APP_LOGO_PATH.name, "OP_Logo.png")
        self.assertTrue(APP_LOGO_PATH.exists())

    def test_heatmap_logo_uses_existing_logo_asset(self):
        self.assertEqual(HEATMAP_LOGO_PATH.name, "OP_Logo.png")
        self.assertTrue(HEATMAP_LOGO_PATH.exists())

    def test_documentation_points_to_local_markdown(self):
        self.assertEqual(DOCUMENTATION_PATH.name, "Documentation.md")
        self.assertTrue(DOCUMENTATION_PATH.exists())

    def test_font_loader_rejects_html_saved_as_ttf(self):
        self.assertFalse(_is_supported_font_file(Path("assets/fonts/RobotoCondensed.ttf")))

    def test_no_gpu_environment_sets_qt_webengine_flags(self):
        env = {"OPVIEW_NO_GPU": "1"}

        with patch.dict("os.environ", env, clear=True):
            _configure_no_gpu_environment()

            self.assertEqual(os.environ["QT_OPENGL"], "software")
            self.assertEqual(os.environ["QT_QUICK_BACKEND"], "software")
            self.assertEqual(os.environ["QTWEBENGINE_DISABLE_GPU"], "1")
            self.assertIn("--disable-gpu-compositing", os.environ["QTWEBENGINE_CHROMIUM_FLAGS"])


if __name__ == "__main__":
    unittest.main()
