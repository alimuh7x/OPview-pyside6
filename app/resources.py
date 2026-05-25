"""Shared application resource paths."""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
DOC_DIR = ROOT_DIR / "doc"

APP_LOGO_PATH = ASSETS_DIR / "OP_Logo_main.png"
HEATMAP_LOGO_PATH = APP_LOGO_PATH
DOCUMENTATION_PATH = DOC_DIR / "Documentation.md"
