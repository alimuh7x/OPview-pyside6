"""OPStudio corporate design for OPView: colours, light/dark mode and the palette.

The colours are OPStudio's (OPStudio/resources/QSS/OPStyle_linux.qss for the light mode,
OPStudio/src/colorscheme.cpp and make_dark_qss.py for the dark mode). OPView's style sheets
keep their own colour values; themed() maps each one to the OPStudio colour of the same role,
by what it colours (text, background or border) and by its hue and lightness, the same way
OPStudio writes its dark style sheets from the light ones. So both modes share one layout.

The mode follows OPStudio's File > Settings > DarkMode (ProgramSettings.ini), so the two
applications look alike; OPVIEW_THEME=light|dark overrides it.
"""

from __future__ import annotations

import colorsys
import os
import re
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QIcon, QImage, QPalette, QPixmap

from app.debug import debug_print

# Role -> (light, dark). Light: OPStudio's style sheets; dark: OPStudio's ColorScheme.
TOKENS = {
    "window":        ("#f3f3f3", "#1c1f24"),    # window background
    "surface":       ("#ffffff", "#262a31"),    # panels and inputs
    "subtle":        ("#ececec", "#2b3038"),    # hover and selection tints
    "element":       ("#d8d8d8", "#353b45"),    # element buttons, tiles, slider grooves
    "element_dark":  ("#a6a6a6", "#4a5260"),    # pressed elements, scroll bar handles
    "border":        ("#c7c7c7", "#3c434f"),
    "border_dark":   ("#959595", "#5d6470"),
    "text":          ("#1c1c1c", "#e8eaed"),
    "muted":         ("#787878", "#9aa0aa"),    # secondary and disabled text
    "primary":       ("#082b63", "#3a7bd5"),    # OPStudio blue: buttons, selected tabs
    "primary_text":  ("#082b63", "#5b9cf5"),    # OPStudio blue as text and labels
    "primary_hover": ("#123978", "#4e8af2"),
    "on_primary":    ("#ffffff", "#ffffff"),    # text on blue and red
    "accent":        ("#c90d23", "#f0445a"),    # OPStudio red
    "accent_dark":   ("#a00a1c", "#f0445a"),
    "accent_tint":   ("#fbe7ea", "#3a2328"),
    "accent_line":   ("#e8a0aa", "#6b2e38"),
}

FONT_FAMILY = "Montserrat"     # OPStudio: body text in Medium, labels and titles in SemiBold
_SETTINGS_FILE = "ProgramSettings.ini"
_DARK_MODE_KEY = "DarkMode"

_dark = False


def opstudio_settings_path() -> Path | None:
    """OPStudio's ProgramSettings.ini (openphase::Paths::userConfigDir() / ProgramSettings.ini)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        return Path(base) / "OpenPhase" / _SETTINGS_FILE if base else None
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "OpenPhase" / _SETTINGS_FILE


def dark_mode_requested() -> bool:
    """OPVIEW_THEME if set, else OPStudio's DarkMode setting, else light (OPStudio's default)."""
    override = os.environ.get("OPVIEW_THEME", "").strip().lower()
    if override in {"light", "dark"}:
        debug_print(f"theme OPVIEW_THEME={override}")
        return override == "dark"
    path = opstudio_settings_path()
    if path is None or not path.is_file():
        debug_print(f"theme no OPStudio settings at {path}; light mode")
        return False
    value = QSettings(str(path), QSettings.Format.IniFormat).value(_DARK_MODE_KEY, False)
    dark = str(value).strip().lower() in {"1", "true", "yes", "on"}
    debug_print(f"theme OPStudio {path} {_DARK_MODE_KEY}={value!r} -> dark={dark}")
    return dark


def set_dark(dark: bool) -> None:
    global _dark
    _dark = bool(dark)


def is_dark() -> bool:
    return _dark


def color(role: str) -> str:
    """The colour of `role` in the current mode."""
    light, dark = TOKENS[role]
    return dark if _dark else light


def build_palette() -> QPalette:
    """Fixed palette for the current mode, so unstyled widgets never follow the OS theme."""
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: "window",
        QPalette.ColorRole.WindowText: "text",
        QPalette.ColorRole.Base: "surface",
        QPalette.ColorRole.AlternateBase: "subtle",
        QPalette.ColorRole.Text: "text",
        QPalette.ColorRole.Button: "surface",
        QPalette.ColorRole.ButtonText: "text",
        QPalette.ColorRole.ToolTipBase: "surface",
        QPalette.ColorRole.ToolTipText: "text",
        QPalette.ColorRole.Highlight: "primary",
        QPalette.ColorRole.HighlightedText: "on_primary",
        QPalette.ColorRole.Link: "primary_text",
        QPalette.ColorRole.BrightText: "accent",
        QPalette.ColorRole.Light: "element_dark",
        QPalette.ColorRole.Midlight: "border",
        QPalette.ColorRole.Mid: "element",
        QPalette.ColorRole.Dark: "border_dark",
    }
    for qt_role, role in roles.items():
        palette.setColor(qt_role, QColor(color(role)))
    text = QColor(color("text"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(text.red(), text.green(), text.blue(), 128))
    for qt_role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, qt_role, QColor(color("muted")))
    return palette


def _role(rgb: tuple[int, int, int], kind: str) -> str:
    """OPStudio role of an OPView colour: by what it colours, its hue and its lightness."""
    h, lightness, s = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    hue = h * 360.0
    red = s > 0.45 and (hue < 20 or hue > 340)
    navy = s > 0.32 and 190 <= hue <= 250 and lightness < 0.5
    if red:
        if lightness > 0.82:
            return "accent_tint" if kind == "background" else "accent_line"
        return "accent_dark" if lightness < 0.33 else "accent"
    if s > 0.6 and 50 <= hue <= 160 and lightness < 0.6:   # the green focus frame
        return "primary"
    if kind == "text":
        if lightness > 0.9:
            return "on_primary"
        if navy:
            return "primary_text"
        return "text" if lightness < 0.3 else "muted"
    if navy:
        return "primary_hover" if lightness > 0.24 else "primary"
    if kind == "border":
        return "border" if lightness > 0.72 else "border_dark"
    if lightness > 0.985:
        return "surface"
    if lightness > 0.94:
        return "window"
    if lightness > 0.86:
        return "subtle"
    if lightness > 0.72:
        return "element"
    if lightness > 0.3:
        return "element_dark"
    return "primary"                                        # dark headers: OPStudio's blue info header


_DECLARATION = re.compile(r"(?P<prop>[a-z-]+)(?P<sep>\s*:\s*)(?P<value>[^;{}]*)(?P<end>;|(?=\}))", re.I)
_COLOUR = re.compile(
    r"#[0-9a-f]{6}\b|rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)|\bwhite\b|\bblack\b", re.I
)
_NAMED = {"white": (255, 255, 255), "black": (0, 0, 0)}


def _kind(prop: str) -> str | None:
    if prop in {"color", "selection-color"}:
        return "text"
    if prop.startswith(("background", "selection-background", "alternate-background")):
        return "background"
    if prop.startswith("border"):
        return "border"
    return None


def _swap(match: re.Match, kind: str) -> str:
    text = match.group(0)
    if match.group(1) is not None:
        rgb = tuple(int(match.group(i)) for i in (1, 2, 3))
        new = QColor(color(_role(rgb, kind)))
        return f"rgba({new.red()}, {new.green()}, {new.blue()}, {match.group(4)})"
    rgb = _NAMED.get(text.lower()) or tuple(int(text[i:i + 2], 16) for i in (1, 3, 5))
    return color(_role(rgb, kind))


_RADIUS = re.compile(r"border(-[a-z]+)*-radius", re.I)
_PIXELS = re.compile(r"\s*(\d+(?:\.\d+)?)px\s*", re.I)
_ROUND_MIN = 9      # radii from 9 px are circles (slider handles, bullets) and stay round


def _squared(value: str) -> str:
    """OPStudio has square corners: rounded-corner radii become 0."""
    match = _PIXELS.fullmatch(value)
    if match is None or float(match.group(1)) >= _ROUND_MIN:
        return value
    return value[:match.start(1)] + "0" + value[match.end(1):]


def themed(sheet: str) -> str:
    """`sheet` with every text, background and border colour replaced by its OPStudio colour,
    square corners, and bold text in OPStudio's SemiBold."""
    def declaration(match: re.Match) -> str:
        if match.group("prop").lower() == "font-weight" and match.group("value").strip().lower() in {"700", "bold"}:
            value = re.sub(r"700|bold", "600", match.group("value"), flags=re.I)        # OPStudio's SemiBold
            return match.group("prop") + match.group("sep") + value + match.group("end")
        if _RADIUS.fullmatch(match.group("prop")):
            return match.group("prop") + match.group("sep") + _squared(match.group("value")) + match.group("end")
        kind = _kind(match.group("prop").lower())
        if kind is None:
            return match.group(0)
        value = _COLOUR.sub(lambda m: _swap(m, kind), match.group("value"))
        return match.group("prop") + match.group("sep") + value + match.group("end")

    return _DECLARATION.sub(declaration, sheet)


# --- Icons -------------------------------------------------------------------------------
# OPView's icons are drawn black/grey (some with navy) for the light mode. In the dark mode
# their grey levels are turned around, black -> text, light grey fills -> element, and navy
# -> the blue text colour, so the same files stay readable. Coloured pixels (red, the bar
# chart) are kept.

def _rgb(role: str) -> np.ndarray:
    c = QColor(color(role))
    return np.array([c.red(), c.green(), c.blue()], dtype=np.float32)


@lru_cache(maxsize=None)
def _dark_icon_image(path: str) -> QImage:
    image = QImage(path).convertToFormat(QImage.Format.Format_ARGB32)
    if image.isNull():
        return image
    width, height = image.width(), image.height()
    buffer = np.frombuffer(image.constBits(), dtype=np.uint8, count=image.sizeInBytes())
    bgra = buffer.reshape(height, image.bytesPerLine() // 4, 4)[:, :width].astype(np.float32)
    rgb = bgra[..., 2::-1] / 255.0                          # ARGB32 is B, G, R, A in memory
    high, low = rgb.max(axis=-1), rgb.min(axis=-1)
    lightness, chroma = (high + low) / 2.0, high - low
    neutral = chroma < 0.12
    navy = ~neutral & (rgb[..., 2] >= rgb[..., 0] + 0.1) & (lightness < 0.5)
    out = rgb * 255.0
    t = np.clip(lightness / 0.9, 0.0, 1.0)[..., None]      # black -> text, #e6e6e6 -> element
    grey = _rgb("text") * (1.0 - t) + _rgb("element") * t
    out = np.where(neutral[..., None], grey, out)
    out = np.where(navy[..., None], _rgb("primary_text"), out)
    result = np.empty((height, width, 4), dtype=np.uint8)
    result[..., 2::-1] = np.clip(out, 0, 255).astype(np.uint8)
    result[..., 3] = bgra[..., 3].astype(np.uint8)
    themed_image = QImage(result.tobytes(), width, height, width * 4, QImage.Format.Format_ARGB32)
    return themed_image.copy()                              # own the pixels, not the bytes object


def themed_pixmap(path) -> QPixmap:
    """The icon at `path` for the current mode (recoloured for the dark mode)."""
    if not _dark:
        return QPixmap(str(path))
    return QPixmap.fromImage(_dark_icon_image(str(path)))


def themed_icon(path) -> QIcon:
    """QIcon of the icon at `path` for the current mode."""
    return QIcon(themed_pixmap(path))


def themed_asset_url(path) -> str:
    """Path of the icon at `path` for a style sheet url(): a recoloured copy in the dark mode."""
    path = Path(path)
    if _dark and path.suffix.lower() == ".png":
        folder = Path(tempfile.gettempdir()) / "opview-dark-icons"
        folder.mkdir(exist_ok=True)
        target = folder / path.name
        if _dark_icon_image(str(path)).save(str(target)):
            path = target
        else:
            debug_print(f"theme could not write the dark icon {target}; using {path}")
    return str(path).replace("\\", "/")
