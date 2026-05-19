"""Dataset configuration for Single View detection."""

from typing import Any, Dict, List, Optional

from config.constants import TENSOR_COMPONENTS


def tensor_scalars(array_name: str, prefix: str) -> List[Dict[str, Any]]:
    """Generate scalar descriptors for six-component tensors."""
    return [
        {"label": f"{prefix}_{component}", "array": array_name, "component": index}
        for index, component in enumerate(TENSOR_COMPONENTS)
    ]


TAB_CONFIGS = [
    {
        "id": "phase-field",
        "label": "Phase Field",
        "icon": "◌",
        "datasets": [
            {
                "id": "phase",
                "label": "PhaseField",
                "file_glob": "PhaseField_*.vts",
                "scalars": [
                    {"label": "PhaseFields", "array": "PhaseFields"},
                    {"label": "Interfaces", "array": "Interfaces"},
                    {"label": "Flags", "array": "Flags"},
                    {"label": "PhaseFraction_0", "array": "PhaseFraction_0"},
                ],
            },
        ],
    },
    {
        "id": "mechanics",
        "label": "Mechanics",
        "icon": "⚙",
        "datasets": [
            {
                "id": "elastic",
                "label": "Elastic Strains",
                "file_glob": "ElasticStrains_*.vts",
                "scalars": tensor_scalars("ElasticStrains", "eps"),
            },
            {
                "id": "stresses",
                "label": "Cauchy Stresses",
                "units": "MPa",
                "scale": 1e-6,
                "file_glob": "CauchyStresses_*.vts",
                "scalars": [
                    {"label": "von Mises", "array": "von Mises"},
                    {"label": "Pressure", "array": "Pressure"},
                    *tensor_scalars("CauchyStresses", "sigma"),
                ],
            },
        ],
    },
    {
        "id": "plasticity",
        "label": "Plasticity",
        "icon": "△",
        "datasets": [
            {
                "id": "crss",
                "label": "CRSS",
                "units": "MPa",
                "scale": 1e-6,
                "file_glob": "CRSS_*.vts",
                "scalars": [
                    {"label": f"CRSS {index}", "array": f"CRSS_0_{index}"}
                    for index in range(12)
                ],
            },
            {
                "id": "plastic-strain",
                "label": "Plastic Strain",
                "file_glob": "PlasticStrain_*.vts",
                "scalars": tensor_scalars("PlasticStrain", "eps_p"),
            },
        ],
    },
]


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
