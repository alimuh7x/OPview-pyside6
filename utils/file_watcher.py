"""File system watcher service for auto-detecting project and VTK file changes."""

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, Signal

from app.debug import debug_print


class FileWatcherService(QObject):
    """Watches cwd, vtk folders, and loaded files for changes."""

    cwd_changed         = Signal()       # new/removed folder in cwd
    vtk_folder_changed  = Signal(str)    # file added/removed inside a vtk_path dir
    loaded_file_changed = Signal(str)    # a currently open VTK file was modified on disk

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._cwd: str = ""
        self._vtk_paths: set[str] = set()
        self._loaded_files: set[str] = set()
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._watcher.fileChanged.connect(self._on_file_changed)
        debug_print("FileWatcherService initialised")

    def set_cwd(self, path: Path) -> None:
        """Watch the root scan directory for new/removed project folders."""
        path_str = str(path)
        if self._cwd and self._cwd in self._watcher.directories():
            self._watcher.removePath(self._cwd)
        self._cwd = path_str
        self._watcher.addPath(path_str)
        debug_print(f"FileWatcherService watching cwd: {path_str}")

    def set_vtk_paths(self, paths: list[Path]) -> None:
        """Replace the watched vtk_path directories with a new list."""
        # Remove old vtk paths (but not cwd or loaded files)
        for old in list(self._vtk_paths):
            if old in self._watcher.directories():
                self._watcher.removePath(old)
        self._vtk_paths = set()

        for path in paths:
            path_str = str(path)
            if Path(path_str).exists():
                self._watcher.addPath(path_str)
                self._vtk_paths.add(path_str)

        debug_print(f"FileWatcherService watching {len(self._vtk_paths)} vtk folders")

    def add_watched_file(self, file_path: str) -> None:
        """Watch a specific VTK file for content changes (called when a panel loads it)."""
        if file_path and file_path not in self._loaded_files:
            self._watcher.addPath(file_path)
            self._loaded_files.add(file_path)
            debug_print(f"FileWatcherService watching file: {file_path}")

    def remove_watched_file(self, file_path: str) -> None:
        """Stop watching a specific file (called when a panel is closed)."""
        if file_path in self._loaded_files:
            self._watcher.removePath(file_path)
            self._loaded_files.discard(file_path)
            debug_print(f"FileWatcherService stopped watching file: {file_path}")

    def _on_directory_changed(self, path: str) -> None:
        debug_print(f"FileWatcherService directoryChanged: {path}")
        if path == self._cwd:
            self.cwd_changed.emit()
        else:
            self.vtk_folder_changed.emit(path)

    def _on_file_changed(self, path: str) -> None:
        debug_print(f"FileWatcherService fileChanged: {path}")
        # Some editors/tools replace the file (delete + recreate) — re-add the path
        if path in self._loaded_files:
            self._watcher.addPath(path)
            self.loaded_file_changed.emit(path)
