"""Command-line argument parsing for OPView startup."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from app.debug import debug_print
from app.version import get_version


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse startup arguments without importing Qt."""
    debug_print("parse_args called")
    parser = argparse.ArgumentParser(description="Start OPView PySide6")
    parser.add_argument(
        "project_path",
        nargs="?",
        type=Path,
        help="Optional project folder or folder containing OpenPhase projects to scan at startup.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"OPView {get_version()}",
    )
    args = parser.parse_args(argv)
    debug_print(f"parse_args project_path={args.project_path}")
    return args
