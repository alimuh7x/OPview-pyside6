"""Cached access to VTK readers."""

from pathlib import Path
from typing import Any, Dict, List

from app.debug import debug_print


class ReaderCache:
    """Simple file-path to VTKReader cache."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def clear(self) -> None:
        debug_print("ReaderCache.clear called")
        self._cache.clear()

    def get(self, key: str, default=None):
        return self._cache.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __getitem__(self, key: str):
        return self._cache[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._cache[key] = value


reader_cache = ReaderCache()


def get_reader(file_path: str):
    """Get a cached reader or load a new one."""
    debug_print("get_reader called")
    from utils.vtk_reader import VTKReader

    resolved = str(Path(file_path).resolve())
    debug_print(f"get_reader resolved={resolved}")
    if resolved not in reader_cache:
        debug_print("get_reader cache miss")
        reader_cache[resolved] = VTKReader(resolved)
    else:
        debug_print("get_reader cache hit")
    return reader_cache[resolved]


def list_vtk_files(directory=None) -> List[str]:
    """List supported VTK files for one directory."""
    debug_print("list_vtk_files called")
    from utils.project_scanner import _scan_vtk_dir

    if directory is None:
        return []
    return _scan_vtk_dir(Path(directory))
