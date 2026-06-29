"""Main entry point for the OOP shell."""

from __future__ import annotations

from collections.abc import Sequence

from app.application_bootstrap import ApplicationBootstrap
from app.startup_args import parse_args


def main(argv: Sequence[str] | None = None) -> int:
    """Run the application."""
    args = parse_args(argv)
    bootstrap = ApplicationBootstrap(project_path=args.project_path)
    return bootstrap.run()


if __name__ == "__main__":
    raise SystemExit(main())
