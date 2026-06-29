"""Dataset auto-detection helpers."""

from dataclasses import dataclass
from fnmatch import fnmatchcase
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List

from app.debug import debug_print
from config.constants import ALLOWED_VTK_EXTENSIONS

_MAX_EAGER_FILES_PER_DATASET = int(os.environ.get("OPVIEW_MAX_EAGER_VTK_FILES", "500"))
_VTK_FOLDER_CACHE: dict[tuple[str, int, int], List[Path]] = {}


@dataclass
class DatasetInfo:
    """Resolved dataset metadata for a project VTK folder."""

    dataset_id: str
    label: str
    module_id: str
    module_label: str
    module_icon: str
    file_glob: str
    matched_files: List[Path]
    dataset_config: Dict[str, Any]
    matched_count: int = 0
    files_limited: bool = False

    def __post_init__(self) -> None:
        if self.matched_count <= 0:
            self.matched_count = len(self.matched_files)
        self.files_limited = self.files_limited or len(self.matched_files) < self.matched_count


def detect_available_datasets(vtk_folder: Path, tab_configs: List[Dict[str, Any]]) -> List[DatasetInfo]:
    """Find configured datasets with at least one matching file using one directory scan."""
    debug_print("detect_available_datasets called")
    start = perf_counter()
    if not vtk_folder or not vtk_folder.exists():
        debug_print("VTK folder missing, returning empty dataset list")
        return []

    all_files = _list_vtk_files_once(vtk_folder)
    debug_print(f"detect_available_datasets scanned files={len(all_files)}")
    available: List[DatasetInfo] = []
    for module_config in tab_configs:
        module_id = module_config.get("id", "")
        module_label = module_config.get("label", "")
        module_icon = module_config.get("icon", "•")
        for dataset_config in module_config.get("datasets", []):
            file_glob = dataset_config.get("file_glob", "")
            if not file_glob:
                continue
            matched = [file_path for file_path in all_files if fnmatchcase(file_path.name, file_glob)]
            matched_count = len(matched)
            limited = matched[:_MAX_EAGER_FILES_PER_DATASET]
            debug_print(
                f"Pattern {file_glob} matched {matched_count} files; eager={len(limited)}"
            )
            if matched_count:
                available.append(
                    DatasetInfo(
                        dataset_id=f"{module_id}-{dataset_config.get('id', dataset_config.get('label', '')).lower()}",
                        label=dataset_config.get("label", ""),
                        module_id=module_id,
                        module_label=module_label,
                        module_icon=module_icon,
                        file_glob=file_glob,
                        matched_files=limited,
                        matched_count=matched_count,
                        files_limited=matched_count > len(limited),
                        dataset_config=dataset_config,
                    )
                )
    debug_print(f"detect_available_datasets complete seconds={perf_counter() - start:.3f}")
    return available


def detect_unconfigured_vtk_files(vtk_folder: Path, tab_configs: List[Dict[str, Any]]) -> List[Path]:
    """Find VTK files that are not covered by configured dataset patterns."""
    debug_print("detect_unconfigured_vtk_files called")
    start = perf_counter()
    if not vtk_folder or not vtk_folder.exists():
        return []
    all_files = _list_vtk_files_once(vtk_folder)
    configured_patterns = [
        dataset.get("file_glob", "")
        for module in tab_configs
        for dataset in module.get("datasets", [])
        if dataset.get("file_glob")
    ]
    remaining: List[Path] = []
    remaining_count = 0
    for file_path in all_files:
        if any(fnmatchcase(file_path.name, pattern) for pattern in configured_patterns):
            continue
        remaining_count += 1
        if len(remaining) < _MAX_EAGER_FILES_PER_DATASET:
            remaining.append(file_path)
    debug_print(
        f"Unconfigured VTK file count={remaining_count}; eager={len(remaining)}; seconds={perf_counter() - start:.3f}"
    )
    return remaining


def _list_vtk_files_once(vtk_folder: Path) -> List[Path]:
    start = perf_counter()
    try:
        stat = vtk_folder.stat()
    except (OSError, PermissionError) as exc:
        debug_print(f"VTK folder stat failed folder={vtk_folder} error={exc}")
        return []
    cache_key = (str(vtk_folder.resolve()), stat.st_mtime_ns, stat.st_size)
    cached = _VTK_FOLDER_CACHE.get(cache_key)
    if cached is not None:
        debug_print(f"_list_vtk_files_once cache hit count={len(cached)} seconds={perf_counter() - start:.3f}")
        return cached

    files: List[Path] = []
    try:
        with os.scandir(vtk_folder) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue
                suffix = Path(entry.name).suffix.lower()
                if suffix not in ALLOWED_VTK_EXTENSIONS:
                    continue
                files.append(Path(entry.path))
    except (OSError, PermissionError) as exc:
        debug_print(f"VTK folder scan failed folder={vtk_folder} error={exc}")
        return []
    files.sort(key=lambda path: path.name)
    _VTK_FOLDER_CACHE.clear()
    _VTK_FOLDER_CACHE[cache_key] = files
    debug_print(f"_list_vtk_files_once scanned count={len(files)} seconds={perf_counter() - start:.3f}")
    return files
