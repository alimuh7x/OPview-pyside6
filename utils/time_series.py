"""Helpers for collecting timestep series from VTK filenames."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.debug import debug_print

_SERIES_RE = re.compile(r"^(?P<prefix>.+_)(?P<step>\d+)(?P<suffix>\.[^.]+)$")


@dataclass(frozen=True)
class TimeSeriesFile:
    """One file in a VTK timestep series."""

    step: int
    path: str


def _parse_series_name(path: str | Path):
    debug_print("time_series._parse_series_name called")
    name = Path(path).name
    match = _SERIES_RE.match(name)
    if not match:
        debug_print(f"time_series parse failed name={name}")
        return None
    parsed = (match.group("prefix"), int(match.group("step")), match.group("suffix"))
    debug_print(f"time_series parsed name={name} prefix={parsed[0]} step={parsed[1]} suffix={parsed[2]}")
    return parsed


def collect_same_series_files(current_file: str, file_paths) -> list[TimeSeriesFile]:
    """Return files matching current_file's prefix/suffix, sorted by timestep."""

    debug_print("collect_same_series_files called")
    current = _parse_series_name(current_file)
    if current is None:
        debug_print("collect_same_series_files using combo order fallback")
        return [TimeSeriesFile(index, str(path)) for index, path in enumerate(file_paths) if path]
    prefix, _, suffix = current
    series: list[TimeSeriesFile] = []
    for path in file_paths:
        if not path:
            debug_print("collect_same_series_files skipped empty path")
            continue
        parsed = _parse_series_name(path)
        if parsed is None:
            debug_print(f"collect_same_series_files skipped unparsable path={path}")
            continue
        item_prefix, step, item_suffix = parsed
        if item_prefix != prefix or item_suffix != suffix:
            debug_print(f"collect_same_series_files skipped other series path={path}")
            continue
        series.append(TimeSeriesFile(step, str(path)))
        debug_print(f"collect_same_series_files accepted step={step} path={path}")
    series.sort(key=lambda item: (item.step, item.path))
    debug_print(f"PlotOverTime same-series file count={len(series)}")
    return series
