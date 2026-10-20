"""Dark native title bar for the main window (Windows and Linux).

The title bar belongs to the operating system, so there are two requests:
- Qt's colour scheme hint (Qt >= 6.8): the Windows 11 title bar and Linux platform themes
  (Wayland / GTK / KDE) follow it. The app's own widgets keep their fixed light palette.
- Windows DWM dark-mode flag: the same effect on Windows 10 / 11 for any Qt version.
On Linux window managers that draw the frame themselves (some X11 setups) the system theme decides.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from app.debug import debug_print

# DWMWA_USE_IMMERSIVE_DARK_MODE: 20 on Windows 10 20H1+ / 11, 19 on earlier Windows 10 builds.
_DWMWA_DARK_MODE_ATTRIBUTES = (20, 19)


def request_dark_color_scheme(application: QApplication) -> bool:
    """Ask Qt for the dark colour scheme so the native title bar turns dark. False if unsupported."""
    debug_print("title_bar.request_dark_color_scheme called")
    hints = application.styleHints()
    if not hasattr(hints, "setColorScheme"):
        debug_print("title_bar colour scheme API unavailable (Qt < 6.8)")
        return False
    hints.setColorScheme(Qt.ColorScheme.Dark)
    debug_print("title_bar colour scheme set to dark")
    return True


def apply_dark_title_bar(window: QWidget) -> bool:
    """Turn the Windows title bar of `window` dark through DWM. No-op elsewhere; False on failure."""
    debug_print("title_bar.apply_dark_title_bar called")
    if sys.platform != "win32":
        debug_print("title_bar DWM flag skipped: not Windows")
        return False
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(window.winId()))
        enabled = ctypes.c_int(1)
        for attribute in _DWMWA_DARK_MODE_ATTRIBUTES:
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, ctypes.c_uint(attribute), ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
            debug_print(f"title_bar DwmSetWindowAttribute attribute={attribute} result={result}")
            if result == 0:
                return True
    except Exception as exc:  # a missing dwmapi or a bad handle must never stop the app starting
        debug_print(f"title_bar DWM dark mode failed: {exc}")
    return False
