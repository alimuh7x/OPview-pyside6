import unittest

from app.styles import build_app_stylesheet


class SidebarHoverStylesTests(unittest.TestCase):
    def test_sidebar_accent_buttons_define_light_hover_effect(self):
        stylesheet = build_app_stylesheet()

        self.assertIn('QWidget#sidebarShell QPushButton[accent="true"]:hover', stylesheet)
        hover = stylesheet[stylesheet.index('QWidget#sidebarShell QPushButton[accent="true"]:hover'):]
        self.assertIn("background: #ffffff;", hover[: hover.index("}")])


if __name__ == "__main__":
    unittest.main()
