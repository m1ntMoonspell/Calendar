"""
设置对话框
包含：透明度调整、开机自启动、关闭时最小化到托盘
配置持久化到 .config.json
"""

import os
import sys
import json
import customtkinter as ctk

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config.json")


def load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Save config error: {e}")


def get_config(key, default=None):
    return load_config().get(key, default)


def set_config(key, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


# ---- auto-start helpers ----

def _autostart_dir():
    if sys.platform == 'win32':
        return None
    return os.path.expanduser("~/.config/autostart")


def _autostart_desktop_path():
    d = _autostart_dir()
    if d:
        return os.path.join(d, "desktop-assistant.desktop")
    return None


def is_autostart_enabled():
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_READ)
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
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_SET_VALUE)
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

    def __init__(self, parent, current_alpha=0.95, on_alpha_change=None,
                 close_to_tray=False, on_close_to_tray_change=None):
        super().__init__(parent)
        self.on_alpha_change = on_alpha_change
        self.on_close_to_tray_change = on_close_to_tray_change

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1E1E2E")

        self._alpha_val = current_alpha
        self._close_to_tray = close_to_tray
        self._autostart = is_autostart_enabled()

        self._build_ui()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 170
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 240
        self.geometry(f"340x480+{max(0,px)}+{max(0,py)}")

    def _build_ui(self):
        outer = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=14,
                             border_width=1, border_color="#374151")
        outer.pack(fill="both", expand=True, padx=2, pady=2)

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

        scroll = ctk.CTkScrollableFrame(outer, fg_color="transparent",
                                         scrollbar_button_color="#374151")
        scroll.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        # ──── 透明度 ────
        alpha_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        alpha_frame.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(alpha_frame, text="\u900f\u660e\u5ea6",
                     font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")
        self._alpha_label = ctk.CTkLabel(alpha_frame, text=f"{int(self._alpha_val*100)}%",
                                          font=ctk.CTkFont(size=12), text_color="#60A5FA", width=40)
        self._alpha_label.pack(side="right")

        self._slider = ctk.CTkSlider(scroll, from_=20, to=100, number_of_steps=16,
                                      width=260, height=18,
                                      fg_color="#374151", progress_color="#3B82F6",
                                      button_color="#60A5FA", button_hover_color="#93C5FD",
                                      command=self._on_slider)
        self._slider.set(self._alpha_val * 100)
        self._slider.pack(padx=12, pady=(0, 6))

        ctk.CTkFrame(scroll, height=1, fg_color="#2D2D44").pack(fill="x", padx=12, pady=2)

        # ──── 关闭到托盘 ────
        tray_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        tray_frame.pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(tray_frame, text="\u5173\u95ed\u65f6\u6700\u5c0f\u5316\u5230\u6258\u76d8",
                     font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")
        self._tray_switch = ctk.CTkSwitch(tray_frame, text="", width=44, height=22,
                                           fg_color="#374151", progress_color="#10B981",
                                           command=self._on_tray_toggle)
        if self._close_to_tray:
            self._tray_switch.select()
        self._tray_switch.pack(side="right")

        ctk.CTkFrame(scroll, height=1, fg_color="#2D2D44").pack(fill="x", padx=12, pady=2)

        # ──── 开机自启 ────
        auto_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        auto_frame.pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(auto_frame, text="\u5f00\u673a\u81ea\u542f\u52a8",
                     font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")
        self._auto_switch = ctk.CTkSwitch(auto_frame, text="", width=44, height=22,
                                           fg_color="#374151", progress_color="#10B981",
                                           command=self._on_autostart_toggle)
        if self._autostart:
            self._auto_switch.select()
        self._auto_switch.pack(side="right")

        # ──── 云端同步 分割线+标题 ────
        ctk.CTkFrame(scroll, height=2, fg_color="#3B82F6").pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(scroll, text="\u2601\ufe0f \u4e91\u7aef\u540c\u6b65",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#E5E7EB", anchor="w").pack(fill="x", padx=12, pady=(2, 4))

        # 同步开关
        sync_toggle_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        sync_toggle_frame.pack(fill="x", padx=12, pady=(2, 4))
        ctk.CTkLabel(sync_toggle_frame, text="\u542f\u7528\u540c\u6b65",
                     font=ctk.CTkFont(size=13), text_color="#9CA3AF").pack(side="left")
        self._sync_switch = ctk.CTkSwitch(sync_toggle_frame, text="", width=44, height=22,
                                           fg_color="#374151", progress_color="#10B981",
                                           command=self._on_sync_toggle)
        if get_config("sync_enabled", False):
            self._sync_switch.select()
        self._sync_switch.pack(side="right")

        # 服务器地址
        ctk.CTkLabel(scroll, text="\u670d\u52a1\u5668\u5730\u5740",
                     font=ctk.CTkFont(size=12), text_color="#6B7280",
                     anchor="w").pack(fill="x", padx=12, pady=(4, 0))
        self._url_entry = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=12), height=30,
                                        fg_color="#16162A", border_color="#374151",
                                        text_color="#E5E7EB",
                                        placeholder_text="http://\u670d\u52a1\u5668IP:5000")
        self._url_entry.pack(fill="x", padx=12, pady=(2, 4))
        saved_url = get_config("sync_server_url", "")
        if saved_url:
            self._url_entry.insert(0, saved_url)

        # API 密钥
        ctk.CTkLabel(scroll, text="API \u5bc6\u94a5",
                     font=ctk.CTkFont(size=12), text_color="#6B7280",
                     anchor="w").pack(fill="x", padx=12, pady=(4, 0))
        self._key_entry = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=12), height=30,
                                        fg_color="#16162A", border_color="#374151",
                                        text_color="#E5E7EB", show="\u2022",
                                        placeholder_text="\u4e0e\u670d\u52a1\u5668\u7aef\u4e00\u81f4")
        self._key_entry.pack(fill="x", padx=12, pady=(2, 4))
        saved_key = get_config("sync_api_key", "")
        if saved_key:
            self._key_entry.insert(0, saved_key)

        # 保存 + 立即同步 按钮
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkButton(btn_frame, text="\U0001f4be \u4fdd\u5b58\u914d\u7f6e", width=120, height=30,
                       font=ctk.CTkFont(size=12),
                       fg_color="#374151", hover_color="#4B5563",
                       corner_radius=6,
                       command=self._save_sync_config).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_frame, text="\u2601\ufe0f \u7acb\u5373\u540c\u6b65", width=120, height=30,
                       font=ctk.CTkFont(size=12),
                       fg_color="#3B82F6", hover_color="#2563EB",
                       corner_radius=6,
                       command=self._do_sync).pack(side="right")

        # 同步状态
        self._sync_status = ctk.CTkLabel(scroll, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color="#6B7280", anchor="w")
        self._sync_status.pack(fill="x", padx=12, pady=(2, 6))

    def _on_slider(self, value):
        alpha = value / 100.0
        self._alpha_val = alpha
        self._alpha_label.configure(text=f"{int(value)}%")
        if self.on_alpha_change:
            self.on_alpha_change(alpha)

    def _on_tray_toggle(self):
        enabled = bool(self._tray_switch.get())
        set_config("close_to_tray", enabled)
        if self.on_close_to_tray_change:
            self.on_close_to_tray_change(enabled)

    def _on_autostart_toggle(self):
        enabled = bool(self._auto_switch.get())
        set_autostart(enabled)

    def _on_sync_toggle(self):
        enabled = bool(self._sync_switch.get())
        set_config("sync_enabled", enabled)

    def _save_sync_config(self):
        url = self._url_entry.get().strip()
        key = self._key_entry.get().strip()
        if url:
            set_config("sync_server_url", url)
        if key:
            set_config("sync_api_key", key)
        set_config("sync_enabled", bool(self._sync_switch.get()))
        self._sync_status.configure(text="\u2705 \u914d\u7f6e\u5df2\u4fdd\u5b58", text_color="#22C55E")

    def _do_sync(self):
        self._sync_status.configure(text="\u2601\ufe0f \u6b63\u5728\u540c\u6b65...", text_color="#60A5FA")
        self._save_sync_config()

        def on_done(success, message):
            try:
                if self.winfo_exists():
                    color = "#22C55E" if success else "#EF4444"
                    icon = "\u2705" if success else "\u274c"
                    self._sync_status.configure(text=f"{icon} {message}", text_color=color)
            except Exception:
                pass

        try:
            from sync_client import sync_from_cloud
            sync_from_cloud(callback=lambda ok, msg: self.after(0, lambda: on_done(ok, msg)))
        except Exception as e:
            self._sync_status.configure(text=f"\u274c {e}", text_color="#EF4444")
