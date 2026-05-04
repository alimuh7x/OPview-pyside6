"""Main entry point for the OOP shell."""

from app.application_bootstrap import ApplicationBootstrap


def main() -> int:
    """Run the application."""
    bootstrap = ApplicationBootstrap()
    return bootstrap.run()


if __name__ == "__main__":
    raise SystemExit(main())
