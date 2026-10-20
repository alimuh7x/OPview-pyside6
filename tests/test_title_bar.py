import ctypes
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from app import title_bar


class TitleBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dwm_flag_is_a_noop_off_windows(self):
        with mock.patch.object(title_bar.sys, "platform", "linux"):
            self.assertFalse(title_bar.apply_dark_title_bar(QWidget()))

    def test_dwm_flag_uses_attribute_20_on_windows_and_reports_success(self):
        dwm = mock.Mock(return_value=0)
        fake_windll = mock.Mock(dwmapi=mock.Mock(DwmSetWindowAttribute=dwm))
        with mock.patch.object(title_bar.sys, "platform", "win32"), mock.patch.object(
            ctypes, "windll", fake_windll, create=True
        ):
            self.assertTrue(title_bar.apply_dark_title_bar(QWidget()))

        self.assertEqual(dwm.call_count, 1)
        self.assertEqual(dwm.call_args.args[1].value, 20)

    def test_dwm_flag_falls_back_to_attribute_19_on_older_windows_10(self):
        dwm = mock.Mock(side_effect=[0x80070057, 0])
        fake_windll = mock.Mock(dwmapi=mock.Mock(DwmSetWindowAttribute=dwm))
        with mock.patch.object(title_bar.sys, "platform", "win32"), mock.patch.object(
            ctypes, "windll", fake_windll, create=True
        ):
            self.assertTrue(title_bar.apply_dark_title_bar(QWidget()))

        self.assertEqual([call.args[1].value for call in dwm.call_args_list], [20, 19])

    def test_dwm_failure_never_raises(self):
        fake_windll = mock.Mock(dwmapi=mock.Mock(DwmSetWindowAttribute=mock.Mock(side_effect=OSError("no dwm"))))
        with mock.patch.object(title_bar.sys, "platform", "win32"), mock.patch.object(
            ctypes, "windll", fake_windll, create=True
        ):
            self.assertFalse(title_bar.apply_dark_title_bar(QWidget()))

    def test_colour_scheme_request_returns_a_bool_and_keeps_the_light_widget_palette(self):
        from app.application_bootstrap import _build_light_palette

        self.assertIsInstance(title_bar.request_dark_color_scheme(self.app), bool)
        self.app.setPalette(_build_light_palette())
        self.assertEqual(self.app.palette().window().color().name(), "#f7f9fc")


if __name__ == "__main__":
    unittest.main()
