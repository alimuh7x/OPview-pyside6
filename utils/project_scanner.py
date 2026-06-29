"""Project discovery helpers."""

from pathlib import Path
from typing import Any, Dict, List

from app.debug import debug_print
from config import ALLOWED_TEXTDATA_EXTENSIONS, ALLOWED_VTK_EXTENSIONS, SKIP_FOLDERS


def scan_project_folders(base_path: Path | None = None, quick_scan: bool = True) -> Dict[str, Dict[str, Any]]:
    """Scan for OpenPhase project folders below a base path or at the path itself."""
    debug_print("scan_project_folders called")
    if base_path is None:
        base_path = Path.cwd()
    base_path = Path(base_path).expanduser()
    debug_print(f"scan_project_folders base_path={base_path}")
    projects: Dict[str, Dict[str, Any]] = {}
    if not base_path.exists() or not base_path.is_dir():
        debug_print("scan_project_folders base path missing or not a directory")
        return projects

    candidates = [base_path] if _is_project_folder(base_path) else [
        item for item in base_path.iterdir()
        if item.is_dir() and item.name not in SKIP_FOLDERS and not item.name.startswith(".")
    ]
    debug_print(f"scan_project_folders candidate count={len(candidates)}")
    for item in candidates:
        _add_project_if_supported(projects, item, quick_scan)
    debug_print(f"scan_project_folders returning {len(projects)} entries")
    return projects


def _is_project_folder(project_dir: Path) -> bool:
    debug_print(f"_is_project_folder called path={project_dir}")
    has_vtk = (project_dir / "VTK").is_dir()
    has_textdata = _find_textdata_path(project_dir) is not None
    debug_print(f"_is_project_folder has_vtk={has_vtk} has_textdata={has_textdata}")
    return has_vtk or has_textdata


def _add_project_if_supported(projects: Dict[str, Dict[str, Any]], item: Path, quick_scan: bool) -> None:
    vtk_path = item / "VTK"
    textdata_path = _find_textdata_path(item)
    has_vtk = vtk_path.is_dir()
    has_textdata = textdata_path is not None
    if not has_vtk and not has_textdata:
        debug_print(f"Skipping folder without VTK/TextData: {item}")
        return
    debug_print(f"Project candidate {item.name} has_vtk={has_vtk} has_textdata={has_textdata}")
    vtk_count = -1 if quick_scan else _count_files(vtk_path, ALLOWED_VTK_EXTENSIONS)
    text_count = -1 if quick_scan else _count_files(textdata_path, ALLOWED_TEXTDATA_EXTENSIONS)
    projects[item.name] = {
        "path": item,
        "has_vtk": has_vtk,
        "has_textdata": has_textdata,
        "vtk_path": vtk_path if has_vtk else None,
        "textdata_path": textdata_path,
        "vtk_file_count": vtk_count,
        "textdata_file_count": text_count,
        "is_subdirectory": False,
        "parent_folder": None,
    }
    if has_vtk:
        projects[f"{item.name}/VTK"] = {
            "path": vtk_path,
            "has_vtk": True,
            "has_textdata": False,
            "vtk_path": vtk_path,
            "textdata_path": None,
            "vtk_file_count": vtk_count,
            "textdata_file_count": 0,
            "is_subdirectory": True,
            "parent_folder": item.name,
        }


def group_projects_by_parent(discovered_folders: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """Group VTK/TextData subfolders by root project name."""
    debug_print("group_projects_by_parent called")
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for folder_name, folder_info in sorted(discovered_folders.items()):
        if not folder_info.get("is_subdirectory", False):
            continue
        parent = folder_info.get("parent_folder")
        if not parent:
            continue
        grouped.setdefault(parent, []).append(
            {"label": folder_name.split("/")[-1], "value": folder_name}
        )
    return grouped


def get_textdata_files(
    project_folders: Dict[str, Dict[str, Any]],
    selected_project_names: List[str] | None = None,
) -> List[str]:
    """Find supported text-data files without requiring a TextData directory."""
    debug_print("get_textdata_files called")
    debug_print(f"get_textdata_files selected_project_names={selected_project_names}")
    names = selected_project_names or list(project_folders.keys())
    skip_names = set(SKIP_FOLDERS) | {"VTK", "vtk", ".git", "__pycache__"}
    found: set[str] = set()
    for name in names:
        debug_print(f"get_textdata_files scanning name={name}")
        info = project_folders.get(name)
        if not info:
            debug_print(f"get_textdata_files missing info name={name}")
            continue
        roots: list[Path] = []
        if info.get("textdata_path"):
            roots.append(Path(info["textdata_path"]))
            debug_print(f"get_textdata_files add textdata_path={info['textdata_path']}")
        if info.get("path"):
            roots.append(Path(info["path"]))
            debug_print(f"get_textdata_files add path={info['path']}")
        for root in roots:
            if not root.exists() or not root.is_dir():
                debug_print(f"get_textdata_files skip missing root={root}")
                continue
            try:
                for path in root.rglob("*"):
                    if not path.is_file():
                        continue
                    if any(part in skip_names for part in path.parts):
                        continue
                    if path.suffix.lower() not in ALLOWED_TEXTDATA_EXTENSIONS:
                        continue
                    resolved = str(path.resolve())
                    debug_print(f"get_textdata_files found={resolved}")
                    found.add(resolved)
            except (OSError, PermissionError) as exc:
                debug_print(f"get_textdata_files scan error root={root} error={exc}")
                continue
    result = sorted(found)
    debug_print(f"get_textdata_files returning count={len(result)}")
    return result


def _scan_vtk_dir(directory: Path) -> List[str]:
    """Recursively list supported VTK files."""
    debug_print("_scan_vtk_dir called")
    if not directory or not Path(directory).exists():
        return []
    return sorted(
        str(path.resolve())
        for path in Path(directory).rglob("*")
        if path.is_file() and path.suffix.lower() in ALLOWED_VTK_EXTENSIONS
    )


def _find_textdata_path(project_dir: Path) -> Path | None:
    for variant in ("TextData", "Textdata", "textdata", "TEXTDATA"):
        candidate = project_dir / variant
        if candidate.is_dir():
            return candidate
    return None


def _count_files(directory: Path | None, extensions) -> int:
    if not directory or not Path(directory).exists():
        return 0
    return sum(1 for path in Path(directory).iterdir() if path.is_file() and path.suffix.lower() in extensions)
