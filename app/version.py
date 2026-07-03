"""Application version, injected at package-build time via ROOT_DIR/version.txt."""

from __future__ import annotations

from app.resources import ROOT_DIR

_FALLBACK = "0.0.0.dev"


def get_version() -> str:
    """Return the packaged version, or a dev fallback when running from source."""
    version_file = ROOT_DIR / "version.txt"
    try:
        return version_file.read_text(encoding="utf-8").strip() or _FALLBACK
    except OSError:
        return _FALLBACK
