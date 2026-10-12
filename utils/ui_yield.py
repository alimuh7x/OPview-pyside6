"""Qt-free hook that lets long blocking work give the UI a chance to repaint.

The GUI installs a callback (for example one that runs ``processEvents``) while a
blocking action such as Reload runs. Worker code calls ``maybe_yield()`` in its
loops; the call is throttled and does nothing when no callback is installed.
"""

from __future__ import annotations

from time import perf_counter
from typing import Callable

_MIN_INTERVAL_S = 0.03

_callback: Callable[[], None] | None = None
_last_call = 0.0


def set_yield_callback(callback: Callable[[], None] | None) -> None:
    global _callback, _last_call
    _callback = callback
    _last_call = 0.0


def maybe_yield() -> None:
    global _last_call
    if _callback is None:
        return
    now = perf_counter()
    if now - _last_call < _MIN_INTERVAL_S:
        return
    _last_call = now
    _callback()
    _last_call = perf_counter()
