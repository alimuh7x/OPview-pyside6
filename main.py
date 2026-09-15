"""Main entry point for the OOP shell."""

from __future__ import annotations

import os
from collections.abc import Sequence

# GPU opt-out for VMs / GL-less X servers (mirrors OPview-No-GPU.bat on
# Windows): disables Chromium GPU compositing and Qt's GLX/EGL integration.
# Must run before any PySide6/Qt import (below) triggers Qt library loading -
# these variables are read at Qt/Chromium init, not reassignable afterward.
# Formerly implemented only by the Linux packaging/linux/opview shell shim,
# which is gone now that OPView's executable installs directly rather than
# through a launcher wrapper.
if os.environ.get("OPVIEW_NO_GPU"):
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") + " --disable-gpu"
    )
    os.environ["QT_XCB_GL_INTEGRATION"] = "none"
    os.environ["QT_OPENGL"] = "software"

from app.application_bootstrap import ApplicationBootstrap  # noqa: E402
from app.startup_args import parse_args  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    """Run the application."""
    args = parse_args(argv)
    bootstrap = ApplicationBootstrap(project_path=args.project_path)
    return bootstrap.run()


if __name__ == "__main__":
    raise SystemExit(main())
