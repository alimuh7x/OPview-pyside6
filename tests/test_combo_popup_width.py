import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication, QComboBox
except ModuleNotFoundError as exc:
    QApplication = None
    QComboBox = None
    QIcon = None
    QPixmap = None
    MISSING_DEPENDENCY = exc.name
else:
    MISSING_DEPENDENCY = None

if MISSING_DEPENDENCY is None:
    from utils.combo_box_utils import compute_combo_popup_width, update_combo_popup_width
else:
    compute_combo_popup_width = None
    update_combo_popup_width = None


@unittest.skipIf(MISSING_DEPENDENCY is not None, f"missing dependency: {MISSING_DEPENDENCY}")
class ComboPopupWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_empty_combo_uses_closed_width_and_safety_padding(self):
        combo = QComboBox()
        combo.resize(80, 28)

        width = compute_combo_popup_width(combo)

        self.assertGreaterEqual(width, 72)

    def test_long_item_makes_popup_wider_than_closed_combo(self):
        combo = QComboBox()
        combo.resize(80, 28)
        combo.addItem("Short")
        combo.addItem("Very long scalar field name that should not be clipped")

        width = compute_combo_popup_width(combo)

        self.assertGreater(width, combo.width())

    def test_icon_width_is_included(self):
        combo_with_icon = QComboBox()
        combo_plain = QComboBox()
        long_text = "Long option"
        pixmap = QPixmap(24, 24)
        icon = QIcon(pixmap)
        combo_with_icon.addItem(icon, long_text)
        combo_plain.addItem(long_text)

        icon_width = compute_combo_popup_width(combo_with_icon)
        plain_width = compute_combo_popup_width(combo_plain)

        self.assertGreater(icon_width, plain_width)

    def test_popup_width_is_capped_when_requested(self):
        combo = QComboBox()
        combo.addItem("x" * 500)

        width = compute_combo_popup_width(combo, max_width=180)

        self.assertEqual(width, 180)

    def test_update_sets_view_minimum_width(self):
        combo = QComboBox()
        combo.resize(80, 28)
        combo.addItem("Very long option text for popup")

        width = update_combo_popup_width(combo)

        self.assertEqual(combo.view().minimumWidth(), width)


if __name__ == "__main__":
    unittest.main()
