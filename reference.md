# Class Reference: AppMenuBar

## Who calls AppMenuBar

| Caller | File | How |
|--------|------|-----|
| `MainWindow` | `app/main_window.py` | Instantiates `AppMenuBar(self)` in `_build_window()`, registers it via `self.setMenuBar()` |

---

## What AppMenuBar calls

| Called | Source | Why |
|--------|--------|-----|
| `QMenuBar` (PySide6) | `app/menu_bar.py` | Base class — provides menu bar widget |
| `QAction` (PySide6) | `app/menu_bar.py` | Each menu item is a `QAction` |
| `QApplication.quit` (PySide6) | `app/menu_bar.py` | File → Quit action |
| `QDesktopServices.openUrl` (PySide6) | `app/menu_bar.py` | Help → Documentation opens GitHub URL |
| `QMessageBox.about` (PySide6) | `app/menu_bar.py` | Help → About shows info dialog |
| `debug_print` | `app/debug.py` | Trace logging throughout |

---

## Signals emitted by AppMenuBar (consumed by MainWindow)

| Signal | Type | Connected to |
|--------|------|--------------|
| `toggle_sidebar` | `Signal(bool)` | `SidebarWidget.setVisible()` |
| `toggle_overlay` | `Signal(bool)` | *(not yet connected)* |
| `open_project_requested` | `Signal()` | *(not yet connected)* |
| `export_requested` | `Signal()` | *(not yet connected)* |
| `reset_view_requested` | `Signal()` | *(not yet connected)* |

---

## Diagram

```
ApplicationBootstrap
        |
        v
   MainWindow  (app/main_window.py)
        |
        |-- instantiates --> AppMenuBar  (app/menu_bar.py)
        |                         |-- extends --> QMenuBar
        |                         |-- uses    --> QAction
        |                         |-- uses    --> QApplication.quit
        |                         |-- uses    --> QDesktopServices.openUrl
        |                         |-- uses    --> QMessageBox.about
        |                         |-- uses    --> debug_print  (app/debug.py)
        |                         |
        |                    signals:
        |<-- toggle_sidebar -------|
        |<-- toggle_overlay -------|  (pending)
        |<-- open_project_requested| (pending)
        |<-- export_requested ------|  (pending)
        |<-- reset_view_requested --|  (pending)
        |
        |-- owns --> SidebarWidget   (sidebar/sidebar_widget.py)
        |-- owns --> SingleViewTab   (single_view/tab_widget.py)
```
