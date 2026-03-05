# AGENTS.md

## Cursor Cloud specific instructions

This is a single-process Python desktop GUI application (桌面助手 / Desktop Calendar Assistant) built with CustomTkinter. It has no backend services, no Docker, no build system. Entry point is `python main.py`.

### Running the application

- **Dependencies**: `pip install -r requirements.txt` (customtkinter, tkinterdnd2, requests). Also requires system package `python3-tk`.
- **Display**: The app requires a display server. On headless Linux, start Xvfb first: `Xvfb :99 -screen 0 1280x720x24 &` then `export DISPLAY=:99`.
- **Platform caveat**: The code uses Windows cursor name `size_nw_se` in `ui_main.py` line 254. On Linux/X11 this causes `_tkinter.TclError`. To run on Linux, monkey-patch `tk.Widget.configure` to replace `size_nw_se` with `bottom_right_corner` before importing `ui_main`.
- **Drag-and-drop**: `tkinterdnd2` native lib is Windows-only; on Linux the app gracefully degrades with message "⚠️ 拖拽不可用". This is expected.

### Project structure

| File | Purpose |
|---|---|
| `main.py` | Entry point |
| `ui_main.py` | Main calendar card UI |
| `ui_calendar.py` | Mini calendar popup |
| `ui_plan.py` | Plan create/view dialogs |
| `ui_file_viewer.py` | File browser dialog |
| `database.py` | SQLite data layer (`assistant.db`) |
| `holidays.py` | Chinese holiday data (network + fallback) |
| `file_manager.py` | File save/categorize logic |

### Testing

No automated test suite or linter is configured in this project. Verify functionality by running the app and exercising core features (holiday countdown, plan creation, calendar navigation) via `python main.py`.
