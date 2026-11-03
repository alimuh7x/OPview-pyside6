"""Dataset configuration for Single View detection."""

from typing import Any, Dict, List, Optional

from app.debug import debug_print
from config.constants import TENSOR_COMPONENTS


def tensor_scalars(array_name: str, prefix: str) -> List[Dict[str, Any]]:
    """Generate scalar descriptors for six-component tensors."""
    return [
        {"label": f"{prefix}_{component}", "array": array_name, "component": index}
        for index, component in enumerate(TENSOR_COMPONENTS)
    ]


# Discover datasets and arrays from files instead of built-in presets.
TAB_CONFIGS: List[Dict[str, Any]] = []
debug_print("Dataset presets disabled; discovering datasets and arrays from VTK files")


class TabConfig:
    """Wrapper around one tab configuration."""

    def __init__(self, config_dict: Dict[str, Any]):
        self.id = config_dict.get("id", "")
        self.label = config_dict.get("label", "")
        self.datasets = config_dict.get("datasets", [])

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        for dataset in self.datasets:
            if dataset.get("id") == dataset_id:
                return dataset
        return None
