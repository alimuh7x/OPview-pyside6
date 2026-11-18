import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app import theme
from app.styles import build_app_stylesheet

_OPSTUDIO_COLOURS = {c for pair in theme.TOKENS.values() for c in pair}


class ThemeModeTests(unittest.TestCase):
    def tearDown(self):
        theme.set_dark(False)

    def test_opview_theme_overrides_opstudio(self):
        with mock.patch.dict("os.environ", {"OPVIEW_THEME": "dark"}):
            self.assertTrue(theme.dark_mode_requested())
        with mock.patch.dict("os.environ", {"OPVIEW_THEME": "light"}):
            self.assertFalse(theme.dark_mode_requested())

    def test_follows_opstudio_dark_mode_setting(self):
        with tempfile.TemporaryDirectory() as config:
            ini = Path(config) / "OpenPhase" / "ProgramSettings.ini"
            ini.parent.mkdir()
            with mock.patch.dict("os.environ", {"OPVIEW_THEME": "", "XDG_CONFIG_HOME": config, "APPDATA": config}):
                self.assertFalse(theme.dark_mode_requested())         # no OPStudio settings: light
                ini.write_text("[General]\nDarkMode=true\n")
                self.assertTrue(theme.dark_mode_requested())
                ini.write_text("[General]\nDarkMode=false\n")
                self.assertFalse(theme.dark_mode_requested())

    def test_palette_follows_the_mode(self):
        self.assertEqual(theme.build_palette().window().color().name(), "#f3f3f3")
        theme.set_dark(True)
        self.assertEqual(theme.build_palette().window().color().name(), "#1c1f24")


class ThemedStyleSheetTests(unittest.TestCase):
    def tearDown(self):
        theme.set_dark(False)

    def test_colours_map_by_what_they_colour(self):
        sheet = theme.themed("QPushButton { color: white; background: #123764; border: 1px solid #ccd7e8; }")
        self.assertIn("color: #ffffff", sheet)
        self.assertIn("background: #082b63", sheet)
        self.assertIn("border: 1px solid #c7c7c7", sheet)
        theme.set_dark(True)
        sheet = theme.themed("QWidget { color: #102a52; background: #ffffff; } QLabel { color: #cc0c24 }")
        self.assertIn("color: #5b9cf5", sheet)
        self.assertIn("background: #262a31", sheet)
        self.assertIn("color: #f0445a", sheet)

    def test_rgba_keeps_its_alpha(self):
        self.assertIn("rgba(8, 43, 99, 0.12)", theme.themed("QWidget { background: rgba(16, 42, 82, 0.12); }"))

    def test_non_colour_properties_are_untouched(self):
        sheet = "QComboBox::down-arrow { image: url(C:/a/#123456.png); width: 10px; }"
        self.assertEqual(theme.themed(sheet), sheet)

    def test_app_sheet_uses_only_opstudio_colours_in_both_modes(self):
        for dark in (False, True):
            theme.set_dark(dark)
            colours = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b", build_app_stylesheet())}
            self.assertEqual(colours - _OPSTUDIO_COLOURS, set(), f"dark={dark}")


if __name__ == "__main__":
    unittest.main()
