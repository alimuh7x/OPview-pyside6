import unittest

from app.styles import build_app_stylesheet


class SidebarHoverStylesTests(unittest.TestCase):
    def test_sidebar_accent_buttons_define_light_hover_effect(self):
        stylesheet = build_app_stylesheet()

        self.assertIn('QWidget#sidebarShell QPushButton[accent="true"]:hover', stylesheet)
        self.assertIn("background: rgba(255, 255, 255, 0.16);", stylesheet)
        self.assertIn("border-color: rgba(255, 255, 255, 0.28);", stylesheet)


if __name__ == "__main__":
    unittest.main()
