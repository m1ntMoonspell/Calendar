"""
主台历界面
iOS 风格无边框台历卡片
- 锁定按钮：鼠标穿透
- 设置按钮：打开设置面板（透明度、开机自启）
- 关闭按钮：最小化到托盘
- 窗口缩放时内容自适应
"""

import os
import sys
import re
import ctypes
import tkinter as tk
import customtkinter as ctk
from datetime import datetime, date

import holidays as holiday_module
import database
import file_manager
from ui_calendar import MiniCalendarPopup
from ui_settings import SettingsDialog

WEEKDAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']

BASE_W, BASE_H = 360, 460


class MainApp(ctk.CTk):
    """主台历应用"""

    def __init__(self):
        super().__init__()

        self.overrideredirect(True)
        self.geometry(f"{BASE_W}x{BASE_H}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._alpha = 0.95
        self.attributes('-alpha', self._alpha)
        self.attributes('-topmost', False)
        self.calendar_popup = None
        self.drop_enabled = False
        self._locked = False
        self._passthrough = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._resizing = False
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0
        self._min_w = 280
        self._min_h = 360
        self._settings_popup = None

        # Tray manager (set by main.py)
        self.tray = None

        self._build_ui()
        self._update_countdown()
        self._setup_drag_drop()

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

        self.bind('<Configure>', self._on_configure)

        # Set icon
        self._set_icon()

    def _set_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(False, self._icon_photo)
            except Exception:
                pass

    def _build_ui(self):
        self.main_card = ctk.CTkFrame(self, corner_radius=16, fg_color="#1E1E2E",
                                       border_width=1, border_color="#2D2D44")
        self.main_card.pack(fill="both", expand=True, padx=0, pady=0)

        # ============ 标题栏 ============
        self.titlebar = ctk.CTkFrame(self.main_card, height=36, fg_color="#16162A",
                                      corner_radius=0)
        self.titlebar.pack(fill="x", padx=1, pady=(1, 0))
        self.titlebar.pack_propagate(False)

        ctk.CTkFrame(self.titlebar, width=16, fg_color="transparent").pack(side="left")

        self.title_lbl = ctk.CTkLabel(self.titlebar, text="\U0001f4c5 桌面助手",
                                       font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                                       text_color="#9CA3AF")
        self.title_lbl.pack(side="left", padx=2)

        # Close → tray
        close_btn = ctk.CTkButton(self.titlebar, text="\u2715", width=30, height=26,
                                   fg_color="transparent", hover_color="#EF4444",
                                   text_color="#9CA3AF", font=ctk.CTkFont(size=14),
                                   corner_radius=6, command=self._close_to_tray)
        close_btn.pack(side="right", padx=(0, 4))

        # Lock / passthrough
        self._lock_btn = ctk.CTkButton(self.titlebar, text="\U0001f513", width=30, height=26,
                                        fg_color="transparent", hover_color="#374151",
                                        text_color="#9CA3AF", font=ctk.CTkFont(size=13),
                                        corner_radius=6, command=self._toggle_lock)
        self._lock_btn.pack(side="right", padx=1)

        # Pin
        self._pin_btn = ctk.CTkButton(self.titlebar, text="\U0001f4cc", width=30, height=26,
                                       fg_color="transparent", hover_color="#374151",
                                       text_color="#6B7280", font=ctk.CTkFont(size=13),
                                       corner_radius=6, command=self._toggle_topmost)
        self._pin_btn.pack(side="right", padx=1)

        # Settings
        settings_btn = ctk.CTkButton(self.titlebar, text="\u2699", width=30, height=26,
                                      fg_color="transparent", hover_color="#374151",
                                      text_color="#9CA3AF", font=ctk.CTkFont(size=14),
                                      corner_radius=6, command=self._open_settings)
        settings_btn.pack(side="right", padx=1)

        self.titlebar.bind('<Button-1>', self._start_drag)
        self.titlebar.bind('<B1-Motion>', self._do_drag)
        self.title_lbl.bind('<Button-1>', self._start_drag)
        self.title_lbl.bind('<B1-Motion>', self._do_drag)

        # ============ 内容区 ============
        self.content = ctk.CTkFrame(self.main_card, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=15, pady=(8, 10))

        self.deco_line = ctk.CTkFrame(self.content, height=4, corner_radius=2, fg_color="#EF4444")
        self.deco_line.pack(fill="x", padx=15, pady=(0, 8))

        today = date.today()
        weekday = WEEKDAY_NAMES[today.weekday()]

        self.date_label = ctk.CTkLabel(self.content,
                                        text=f"{today.year}年{today.month}月{today.day}日 {weekday}",
                                        font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"),
                                        text_color="#E5E7EB")
        self.date_label.pack(pady=(2, 0))

        self.holiday_name_label = ctk.CTkLabel(self.content, text="正在获取节假日信息...",
                                                font=ctk.CTkFont(family="Microsoft YaHei", size=13),
                                                text_color="#9CA3AF")
        self.holiday_name_label.pack(pady=(4, 0))

        self.days_label = ctk.CTkLabel(self.content, text="--",
                                        font=ctk.CTkFont(family="Microsoft YaHei", size=58, weight="bold"),
                                        text_color="#EF4444")
        self.days_label.pack(pady=(0, 0))

        self.days_unit_label = ctk.CTkLabel(self.content, text="天",
                                             font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
                                             text_color="#EF4444")
        self.days_unit_label.pack(pady=(0, 0))

        self.time_label = ctk.CTkLabel(self.content, text="--:--:--",
                                        font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
                                        text_color="#9CA3AF")
        self.time_label.pack(pady=(0, 2))

        self.days_off_label = ctk.CTkLabel(self.content, text="",
                                            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
                                            text_color="#34D399")
        self.days_off_label.pack(pady=(0, 6))

        ctk.CTkFrame(self.content, height=1, fg_color="#2D2D44").pack(fill="x", padx=10, pady=4)

        today_str = f"\U0001f4c5 {today.month}月{today.day}日"
        self.calendar_btn = ctk.CTkButton(self.content, text=today_str,
                                           font=ctk.CTkFont(family="Microsoft YaHei", size=13),
                                           fg_color="#2D2D44", hover_color="#374151",
                                           text_color="#E5E7EB", corner_radius=10,
                                           height=34, width=180,
                                           command=self._toggle_calendar)
        self.calendar_btn.pack(pady=6)

        self.drop_feedback = ctk.CTkLabel(self.content, text="\U0001f4ce 拖拽文件到窗口即可保存",
                                           font=ctk.CTkFont(family="Microsoft YaHei", size=10),
                                           text_color="#4B5563")
        self.drop_feedback.pack(pady=(2, 0))

        # ============ 缩放手柄 ============
        self._resize_handle = ctk.CTkLabel(self.main_card, text="\u27cb",
                                            font=ctk.CTkFont(size=12), text_color="#4B5563",
                                            width=18, height=18)
        self._resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-4)
        self._resize_handle.bind('<Button-1>', self._start_resize)
        self._resize_handle.bind('<B1-Motion>', self._do_resize)

        # Store base font sizes for scaling
        self._font_map = [
            (self.date_label, "Microsoft YaHei", 15, "bold"),
            (self.holiday_name_label, "Microsoft YaHei", 13, ""),
            (self.days_label, "Microsoft YaHei", 58, "bold"),
            (self.days_unit_label, "Microsoft YaHei", 18, "bold"),
            (self.time_label, "Consolas", 22, "bold"),
            (self.days_off_label, "Microsoft YaHei", 13, ""),
            (self.calendar_btn, "Microsoft YaHei", 13, ""),
            (self.drop_feedback, "Microsoft YaHei", 10, ""),
        ]

    # ======== 窗口控制 ========

    def _start_drag(self, event):
        if self._locked:
            return
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if self._locked:
            return
        x = event.x_root - self._drag_start_x
        y = event.y_root - self._drag_start_y
        self.geometry(f"+{x}+{y}")

    def _start_resize(self, event):
        if self._locked:
            return
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self.winfo_width()
        self._resize_start_h = self.winfo_height()

    def _do_resize(self, event):
        if self._locked:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_w = max(self._min_w, self._resize_start_w + dx)
        new_h = max(self._min_h, self._resize_start_h + dy)
        self.geometry(f"{new_w}x{new_h}")

    def _toggle_lock(self):
        self._locked = not self._locked
        if self._locked:
            self._lock_btn.configure(text="\U0001f512", text_color="#EF4444")
            self._set_passthrough(True)
        else:
            self._lock_btn.configure(text="\U0001f513", text_color="#9CA3AF")
            self._set_passthrough(False)

    def _set_passthrough(self, enabled):
        self._passthrough = enabled
        try:
            if sys.platform == 'win32':
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                GWL_EXSTYLE = -20
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_LAYERED = 0x00080000
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                if enabled:
                    style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
                else:
                    style &= ~WS_EX_TRANSPARENT
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            else:
                # X11: set input shape to empty region for passthrough
                wid = self.winfo_id()
                if enabled:
                    os.system(f'xdotool windowfocus --sync {wid} 2>/dev/null; '
                              f'xprop -id {wid} -remove _NET_WM_OPAQUE_REGION 2>/dev/null')
                    try:
                        x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
                        xfixes = ctypes.cdll.LoadLibrary("libXfixes.so.3")
                        display_ptr = x11.XOpenDisplay(None)
                        if display_ptr:
                            region = xfixes.XFixesCreateRegion(display_ptr, None, 0)
                            xfixes.XFixesSetWindowShapeRegion(display_ptr, wid, 2, 0, 0, region)
                            xfixes.XFixesDestroyRegion(display_ptr, region)
                            x11.XFlush(display_ptr)
                            x11.XCloseDisplay(display_ptr)
                    except Exception:
                        pass
                else:
                    try:
                        x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
                        xfixes = ctypes.cdll.LoadLibrary("libXfixes.so.3")
                        display_ptr = x11.XOpenDisplay(None)
                        if display_ptr:
                            xfixes.XFixesSetWindowShapeRegion(display_ptr, wid, 2, 0, 0, 0)
                            x11.XFlush(display_ptr)
                            x11.XCloseDisplay(display_ptr)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Passthrough error: {e}")

    def _toggle_topmost(self):
        current = self.attributes('-topmost')
        self.attributes('-topmost', not current)
        if not current:
            self._pin_btn.configure(text_color="#F59E0B")
        else:
            self._pin_btn.configure(text_color="#6B7280")

    def _open_settings(self):
        if self._settings_popup and self._settings_popup.winfo_exists():
            self._settings_popup.destroy()
            self._settings_popup = None
            return
        self._settings_popup = SettingsDialog(
            self, current_alpha=self._alpha,
            on_alpha_change=self._set_alpha)

    def _set_alpha(self, alpha):
        self._alpha = max(0.2, min(1.0, alpha))
        self.attributes('-alpha', self._alpha)

    def _close_to_tray(self):
        self.withdraw()
        if self.tray:
            pass  # tray already running

    def show_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        if self.tray:
            self.tray.stop()
        self.destroy()

    def _on_configure(self, event):
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.reposition()
        self._apply_scaling()

    # ======== 内容缩放 ========

    def _apply_scaling(self):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        scale = min(w / BASE_W, h / BASE_H)
        for widget, family, base_size, weight in self._font_map:
            new_size = max(8, int(base_size * scale))
            try:
                kw = {"family": family, "size": new_size}
                if weight:
                    kw["weight"] = weight
                widget.configure(font=ctk.CTkFont(**kw))
            except Exception:
                pass

    # ======== 倒计时 ========

    def _update_countdown(self):
        try:
            info = holiday_module.get_holiday_countdown()
            if info:
                self.holiday_name_label.configure(text=f"距{info['name']}还有：")
                self.days_label.configure(text=str(info['days']))
                self.time_label.configure(
                    text=f"{info['hours']:02d}:{info['minutes']:02d}:{info['seconds']:02d}")
                self.days_off_label.configure(text=f"\U0001f389 放假 {info['days_off']} 天")
            else:
                self.holiday_name_label.configure(text="暂无节假日信息")
                self.days_label.configure(text="--")
                self.time_label.configure(text="--:--:--")
                self.days_off_label.configure(text="")
        except Exception as e:
            self.holiday_name_label.configure(text="获取节假日信息失败")
            print(f"Holiday error: {e}")

        today = date.today()
        weekday = WEEKDAY_NAMES[today.weekday()]
        self.date_label.configure(text=f"{today.year}年{today.month}月{today.day}日 {weekday}")
        self.calendar_btn.configure(text=f"\U0001f4c5 {today.month}月{today.day}日")

        self.after(1000, self._update_countdown)

    # ======== 日历 ========

    def _toggle_calendar(self):
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.destroy()
            self.calendar_popup = None
        else:
            self.calendar_popup = MiniCalendarPopup(
                self, anchor_widget=self.calendar_btn,
                on_change=self._on_data_changed)

    def _on_data_changed(self):
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.refresh_dots()

    # ======== 拖拽 ========

    def _setup_drag_drop(self):
        try:
            import tkinterdnd2
            import struct
            base_tkdnd = os.path.join(os.path.dirname(tkinterdnd2.__file__), 'tkdnd')
            bits = struct.calcsize('P') * 8
            arch = 'x64' if bits == 64 else 'x86'
            platform_path = os.path.join(base_tkdnd, f'win-{arch}')

            if os.path.exists(os.path.join(platform_path, 'pkgIndex.tcl')):
                tkdnd_path = platform_path
            elif os.path.exists(os.path.join(base_tkdnd, 'pkgIndex.tcl')):
                tkdnd_path = base_tkdnd
            else:
                tkdnd_path = None
                for item in os.listdir(base_tkdnd):
                    candidate = os.path.join(base_tkdnd, item)
                    if os.path.isdir(candidate) and os.path.exists(
                        os.path.join(candidate, 'pkgIndex.tcl')
                    ):
                        tkdnd_path = candidate
                        break
                if not tkdnd_path:
                    raise FileNotFoundError("找不到 tkdnd pkgIndex.tcl")

            self.tk.call('lappend', 'auto_path', tkdnd_path)
            self.tk.call('package', 'require', 'tkdnd')
            self._setup_dnd_bindings()
            self.drop_enabled = True
        except Exception as e:
            print(f"拖拽功能初始化失败: {e}")
            self.drop_feedback.configure(text="\u26a0\ufe0f 拖拽不可用")

    def _setup_dnd_bindings(self):
        self.tk.call('tkdnd::drop_target', 'register', self._w, 'DND_Files')
        drop_cmd = self.register(self._on_drop_raw)
        self.tk.call('bind', self._w, '<<Drop:DND_Files>>', drop_cmd + ' %D')
        enter_cmd = self.register(self._on_drag_enter_raw)
        self.tk.call('bind', self._w, '<<DragEnter>>', enter_cmd + ' %D')
        leave_cmd = self.register(self._on_drag_leave_raw)
        self.tk.call('bind', self._w, '<<DragLeave>>', leave_cmd)

    def _on_drop_raw(self, data):
        self.main_card.configure(border_color="#2D2D44", border_width=1)
        if '{' in data:
            files = re.findall(r'\{([^}]+)\}', data)
        else:
            files = [f for f in data.split() if f.strip()]
        if files:
            results = file_manager.save_dropped_files(files)
            self._show_save_results(results)
        return 'copy'

    def _on_drag_enter_raw(self, data=''):
        self.main_card.configure(border_color="#3B82F6", border_width=2)
        self.drop_feedback.configure(text="\U0001f4e5 释放以保存文件", text_color="#3B82F6")
        return 'copy'

    def _on_drag_leave_raw(self):
        self.main_card.configure(border_color="#2D2D44", border_width=1)
        self.drop_feedback.configure(text="\U0001f4ce 拖拽文件到窗口即可保存", text_color="#4B5563")
        return 'copy'

    def _show_save_results(self, results):
        success_count = sum(1 for r in results if r.get('success'))
        total = len(results)
        if success_count > 0:
            self.drop_feedback.configure(text=f"\u2705 已保存 {success_count}/{total} 个文件",
                                          text_color="#22C55E")
            if self.calendar_popup and self.calendar_popup.winfo_exists():
                self.calendar_popup.refresh_dots()
        else:
            self.drop_feedback.configure(text="\u274c 保存失败", text_color="#EF4444")
        self.after(3000, lambda: self.drop_feedback.configure(
            text="\U0001f4ce 拖拽文件到窗口即可保存", text_color="#4B5563"))
