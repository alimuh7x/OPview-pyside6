"""Registry of detected datasets for a selected project."""

from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

from app.debug import debug_print
from utils.dataset_detector import (
    DatasetInfo,
    detect_available_datasets,
    detect_unconfigured_vtk_files,
    eager_file_limit,
)


class DatasetRegistry:
    """Discover and organize datasets for one VTK folder."""

    def __init__(self, vtk_folder: Path, tab_configs: List[Dict[str, Any]]):
        debug_print("DatasetRegistry.__init__ start")
        self.vtk_folder = Path(vtk_folder)
        self.tab_configs = tab_configs
        self._datasets: List[DatasetInfo] = []
        self._by_id: Dict[str, DatasetInfo] = {}
        debug_print(f"DatasetRegistry vtk_folder={self.vtk_folder}")
        debug_print("DatasetRegistry.__init__ complete")

    def detect(self, verbose: bool = True) -> None:
        """Populate the registry from configured and unconfigured files."""
        debug_print("DatasetRegistry.detect called")
        start = perf_counter()
        self._datasets = detect_available_datasets(self.vtk_folder, self.tab_configs)
        unconfigured_files = detect_unconfigured_vtk_files(self.vtk_folder, self.tab_configs)
        grouped: Dict[str, List[Path]] = {}
        for file_path in unconfigured_files:
            base_name = self._extract_base_name(file_path)
            grouped.setdefault(base_name, []).append(file_path)
        debug_print(f"DatasetRegistry unconfigured group count={len(grouped)}")
        for base_name, files in grouped.items():
            matched_count = len(files)
            limited_files = files[:eager_file_limit()]
            debug_print(f"DatasetRegistry unconfigured group={base_name}")
            debug_print(f"DatasetRegistry unconfigured matched_count={matched_count}")
            debug_print(f"DatasetRegistry unconfigured eager_count={len(limited_files)}")
            dataset_id = f"auto-{base_name.lower()}"
            self._datasets.append(
                DatasetInfo(
                    dataset_id=dataset_id,
                    label=base_name,
                    module_id="unconfigured",
                    module_label="Other Files",
                    module_icon="•",
                    file_glob=f"{base_name}_*{files[0].suffix}",
                    matched_files=limited_files,
                    matched_count=matched_count,
                    files_limited=matched_count > len(limited_files),
                    dataset_config={"id": dataset_id, "label": base_name, "scalars": None},
                )
            )
        self._by_id = {dataset.dataset_id: dataset for dataset in self._datasets}
        debug_print(f"DatasetRegistry.detect complete datasets={len(self._datasets)} seconds={perf_counter() - start:.3f}")
        if verbose:
            debug_print(f"DatasetRegistry detected {len(self._datasets)} datasets")

    def _extract_base_name(self, vtk_file: Path) -> str:
        stem = vtk_file.stem
        prefix, _, suffix = stem.rpartition("_")
        if prefix and suffix.isdigit():
            return prefix
        return stem

    def get_by_id(self, dataset_id: str) -> Optional[DatasetInfo]:
        return self._by_id.get(dataset_id)

    def get_dropdown_options(self) -> List[Dict[str, Any]]:
        """Return simple flat options for the sidebar combo."""
        debug_print("DatasetRegistry.get_dropdown_options called")
        options: List[Dict[str, Any]] = []
        for dataset in self._datasets:
            payload = {
                "id": dataset.dataset_id,
                "label": dataset.label,
                "files": [str(path.resolve()) for path in dataset.matched_files],
                "file_count": dataset.matched_count,
                "files_limited": dataset.files_limited,
                "dataset_config": dataset.dataset_config,
                "module_id": dataset.module_id,
                "module_label": dataset.module_label,
            }
            options.append({"label": f"{dataset.module_label}: {dataset.label}", "value": payload})
        return options

    @property
    def all_datasets(self) -> List[DatasetInfo]:
        return self._datasets
