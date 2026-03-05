"""
设置对话框
包含：透明度调整、开机自启动
"""

import os
import sys
import customtkinter as ctk


def _autostart_dir():
    if sys.platform == 'win32':
        return None
    return os.path.expanduser("~/.config/autostart")


def _autostart_desktop_path():
    d = _autostart_dir()
    if d:
        return os.path.join(d, "desktop-assistant.desktop")
    return None


def _win_autostart_key():
    return r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_autostart_enabled():
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _win_autostart_key(), 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "DesktopAssistant")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False
    else:
        path = _autostart_desktop_path()
        return path is not None and os.path.exists(path)


def set_autostart(enabled):
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _win_autostart_key(), 0,
                                winreg.KEY_SET_VALUE)
            if enabled:
                exe = sys.executable.replace('python.exe', 'pythonw.exe')
                script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))
                winreg.SetValueEx(key, "DesktopAssistant", 0, winreg.REG_SZ,
                                  f'"{exe}" "{script}"')
            else:
                try:
                    winreg.DeleteValue(key, "DesktopAssistant")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Auto-start registry error: {e}")
    else:
        path = _autostart_desktop_path()
        if path is None:
            return
        if enabled:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Desktop Assistant\n"
                f"Exec={sys.executable} {script}\n"
                "Hidden=false\n"
                "X-GNOME-Autostart-enabled=true\n"
                "Terminal=false\n"
            )
            with open(path, 'w') as f:
                f.write(content)
        else:
            if os.path.exists(path):
                os.remove(path)


class SettingsDialog(ctk.CTkToplevel):
    """设置对话框"""

    def __init__(self, parent, current_alpha=0.95, on_alpha_change=None):
        super().__init__(parent)
        self.on_alpha_change = on_alpha_change

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1E1E2E")

        self._alpha_val = current_alpha
        self._autostart = is_autostart_enabled()

        self._build_ui()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 150
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 100
        self.geometry(f"300x220+{max(0,px)}+{max(0,py)}")

        self.bind('<FocusOut>', lambda e: self.after(200, self._check_focus))

    def _check_focus(self):
        try:
            if not self.focus_get():
                self.destroy()
        except Exception:
            pass

    def _build_ui(self):
        outer = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=14,
                             border_width=1, border_color="#374151")
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        # Title bar
        header = ctk.CTkFrame(outer, fg_color="transparent", height=36)
        header.pack(fill="x", padx=10, pady=(8, 0))
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="\u2699\ufe0f \u8bbe\u7f6e",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#E5E7EB").pack(side="left")

        ctk.CTkButton(header, text="\u2715", width=26, height=26,
                       fg_color="transparent", hover_color="#374151",
                       text_color="#9CA3AF", font=ctk.CTkFont(size=13),
                       corner_radius=6, command=self.destroy).pack(side="right")

        # Transparency slider
        alpha_frame = ctk.CTkFrame(outer, fg_color="transparent")
        alpha_frame.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(alpha_frame, text="\u900f\u660e\u5ea6",
                     font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")

        self._alpha_label = ctk.CTkLabel(alpha_frame, text=f"{int(self._alpha_val*100)}%",
                                          font=ctk.CTkFont(size=12), text_color="#60A5FA",
                                          width=40)
        self._alpha_label.pack(side="right")

        self._slider = ctk.CTkSlider(outer, from_=20, to=100, number_of_steps=16,
                                      width=260, height=18,
                                      fg_color="#374151", progress_color="#3B82F6",
                                      button_color="#60A5FA", button_hover_color="#93C5FD",
                                      command=self._on_slider)
        self._slider.set(self._alpha_val * 100)
        self._slider.pack(padx=16, pady=(0, 12))

        # Separator
        ctk.CTkFrame(outer, height=1, fg_color="#2D2D44").pack(fill="x", padx=16, pady=2)

        # Auto-start toggle
        auto_frame = ctk.CTkFrame(outer, fg_color="transparent")
        auto_frame.pack(fill="x", padx=16, pady=(8, 4))

        ctk.CTkLabel(auto_frame, text="\u5f00\u673a\u81ea\u542f\u52a8",
                     font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")

        self._auto_switch = ctk.CTkSwitch(auto_frame, text="",
                                           width=44, height=22,
                                           fg_color="#374151", progress_color="#10B981",
                                           command=self._on_autostart_toggle)
        if self._autostart:
            self._auto_switch.select()
        self._auto_switch.pack(side="right")

    def _on_slider(self, value):
        alpha = value / 100.0
        self._alpha_val = alpha
        self._alpha_label.configure(text=f"{int(value)}%")
        if self.on_alpha_change:
            self.on_alpha_change(alpha)

    def _on_autostart_toggle(self):
        enabled = self._auto_switch.get()
        set_autostart(enabled)
