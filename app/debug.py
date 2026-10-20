"""Debug helpers for optional console tracing."""

from __future__ import annotations

import os


def debug_print(message: str) -> None:
    """Print a verbose debug message only when OPVIEW_DEBUG is enabled."""
    if os.environ.get("OPVIEW_DEBUG", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    print(f"[DEBUG] {message}")
