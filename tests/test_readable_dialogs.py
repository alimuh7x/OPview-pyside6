import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from app.readable_dialogs import build_readable_message_box


class ReadableDialogsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_readable_message_box_uses_light_text_and_background(self):
        box = build_readable_message_box(
            None,
            QMessageBox.Icon.Question,
            "Install FFmpeg?",
            "MP4 export requires FFmpeg.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        stylesheet = box.styleSheet()
        self.assertEqual(box.objectName(), "readableMessageBox")
        self.assertIn("background: #f7f9fc", stylesheet)
        self.assertIn("color: #102a52", stylesheet)
        self.assertEqual(box.standardButtons(), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)


if __name__ == "__main__":
    unittest.main()
