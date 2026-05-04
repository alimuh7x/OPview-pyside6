"""Dataset auto-detection helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from app.debug import debug_print
from config.constants import ALLOWED_VTK_EXTENSIONS


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


def detect_available_datasets(vtk_folder: Path, tab_configs: List[Dict[str, Any]]) -> List[DatasetInfo]:
    """Find configured datasets with at least one matching file."""
    debug_print("detect_available_datasets called")
    if not vtk_folder or not vtk_folder.exists():
        debug_print("VTK folder missing, returning empty dataset list")
        return []
    available: List[DatasetInfo] = []
    for module_config in tab_configs:
        module_id = module_config.get("id", "")
        module_label = module_config.get("label", "")
        module_icon = module_config.get("icon", "•")
        for dataset_config in module_config.get("datasets", []):
            file_glob = dataset_config.get("file_glob", "")
            if not file_glob:
                continue
            matched = sorted(vtk_folder.glob(file_glob))
            debug_print(f"Pattern {file_glob} matched {len(matched)} files")
            if matched:
                available.append(
                    DatasetInfo(
                        dataset_id=f"{module_id}-{dataset_config.get('id', dataset_config.get('label', '')).lower()}",
                        label=dataset_config.get("label", ""),
                        module_id=module_id,
                        module_label=module_label,
                        module_icon=module_icon,
                        file_glob=file_glob,
                        matched_files=matched,
                        dataset_config=dataset_config,
                    )
                )
    return available


def detect_unconfigured_vtk_files(vtk_folder: Path, tab_configs: List[Dict[str, Any]]) -> List[Path]:
    """Find VTK files that are not covered by configured dataset patterns."""
    debug_print("detect_unconfigured_vtk_files called")
    if not vtk_folder or not vtk_folder.exists():
        return []
    all_files = [
        file_path for file_path in vtk_folder.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_VTK_EXTENSIONS
    ]
    configured_patterns = [
        dataset.get("file_glob", "")
        for module in tab_configs
        for dataset in module.get("datasets", [])
        if dataset.get("file_glob")
    ]
    remaining: List[Path] = []
    for file_path in all_files:
        if any(file_path.match(pattern) for pattern in configured_patterns):
            continue
        remaining.append(file_path)
    debug_print(f"Unconfigured VTK file count={len(remaining)}")
    return sorted(remaining)
