"""
主台历界面
iOS 风格无边框台历卡片
- 锁定按钮：置顶 + 位置锁定 + 背景全透明（内容正常显示）
- 设置按钮：打开设置面板（透明度、关闭最小化到托盘、开机自启）
- 关闭按钮：根据设置 最小化到托盘 / 退出
- 窗口缩放时内容自适应
"""

import os
import sys
import re
import tkinter as tk
import customtkinter as ctk
from datetime import datetime, date

import holidays as holiday_module
import database
import file_manager
from ui_calendar import MiniCalendarPopup
from ui_settings import SettingsDialog, get_config

WEEKDAY_NAMES = ['\u661f\u671f\u4e00', '\u661f\u671f\u4e8c', '\u661f\u671f\u4e09',
                 '\u661f\u671f\u56db', '\u661f\u671f\u4e94', '\u661f\u671f\u516d', '\u661f\u671f\u65e5']

BASE_W, BASE_H = 360, 460

TRANSPARENT_KEY = '#010101'

NORMAL_BG = '#1E1E2E'
TITLEBAR_BG = '#16162A'
BORDER_COLOR = '#2D2D44'


class MainApp(ctk.CTk):

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
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0
        self._min_w = 280
        self._min_h = 360
        self._settings_popup = None
        self._close_to_tray = get_config("close_to_tray", False)
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
        self._set_icon()

        # Windows 下强制显示任务栏图标（overrideredirect 窗口默认不显示）
        if sys.platform == 'win32':
            self.after(100, self._force_taskbar_icon)

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

    def _force_taskbar_icon(self):
        """Windows: 强制 overrideredirect 窗口显示在任务栏"""
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            self.withdraw()
            self.after(50, self.deiconify)
        except Exception:
            pass

    def _build_ui(self):
        self.main_card = ctk.CTkFrame(self, corner_radius=16, fg_color=NORMAL_BG,
                                       border_width=1, border_color=BORDER_COLOR)
        self.main_card.pack(fill="both", expand=True, padx=0, pady=0)

        # ============ 标题栏 ============
        self.titlebar = ctk.CTkFrame(self.main_card, height=36, fg_color=TITLEBAR_BG,
                                      corner_radius=0)
        self.titlebar.pack(fill="x", padx=1, pady=(1, 0))
        self.titlebar.pack_propagate(False)

        ctk.CTkFrame(self.titlebar, width=16, fg_color="transparent").pack(side="left")

        self.title_lbl = ctk.CTkLabel(self.titlebar, text="\U0001f4c5 \u684c\u9762\u52a9\u624b",
                                       font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                                       text_color="#9CA3AF")
        self.title_lbl.pack(side="left", padx=2)

        self._close_btn = ctk.CTkButton(
            self.titlebar, text="\u2715", width=30, height=26,
            fg_color="transparent", hover_color="#EF4444",
            text_color="#9CA3AF", font=ctk.CTkFont(size=14),
            corner_radius=6, command=self._on_close)
        self._close_btn.pack(side="right", padx=(0, 4))

        self._lock_btn = ctk.CTkButton(
            self.titlebar, text="\U0001f513", width=30, height=26,
            fg_color="transparent", hover_color="#374151",
            text_color="#9CA3AF", font=ctk.CTkFont(size=13),
            corner_radius=6, command=self._toggle_lock)
        self._lock_btn.pack(side="right", padx=1)

        self._settings_btn = ctk.CTkButton(
            self.titlebar, text="\u2699", width=30, height=26,
            fg_color="transparent", hover_color="#374151",
            text_color="#9CA3AF", font=ctk.CTkFont(size=14),
            corner_radius=6, command=self._open_settings)
        self._settings_btn.pack(side="right", padx=1)

        self.titlebar.bind('<Button-1>', self._start_drag)
        self.titlebar.bind('<B1-Motion>', self._do_drag)
        self.title_lbl.bind('<Button-1>', self._start_drag)
        self.title_lbl.bind('<B1-Motion>', self._do_drag)

        # ============ 内容区（无红色装饰线）============
        self.content = ctk.CTkFrame(self.main_card, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=15, pady=(8, 10))

        today = date.today()
        weekday = WEEKDAY_NAMES[today.weekday()]

        self.date_label = ctk.CTkLabel(
            self.content,
            text=f"{today.year}\u5e74{today.month}\u6708{today.day}\u65e5 {weekday}",
            font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"),
            text_color="#E5E7EB")
        self.date_label.pack(pady=(6, 0))

        self.holiday_name_label = ctk.CTkLabel(
            self.content, text="\u6b63\u5728\u83b7\u53d6\u8282\u5047\u65e5\u4fe1\u606f...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13), text_color="#9CA3AF")
        self.holiday_name_label.pack(pady=(4, 0))

        self.days_label = ctk.CTkLabel(
            self.content, text="--",
            font=ctk.CTkFont(family="Microsoft YaHei", size=58, weight="bold"),
            text_color="#EF4444")
        self.days_label.pack(pady=(0, 0))

        self.days_unit_label = ctk.CTkLabel(
            self.content, text="\u5929",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color="#EF4444")
        self.days_unit_label.pack(pady=(0, 0))

        self.time_label = ctk.CTkLabel(
            self.content, text="--:--:--",
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color="#9CA3AF")
        self.time_label.pack(pady=(0, 2))

        self.days_off_label = ctk.CTkLabel(
            self.content, text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13), text_color="#34D399")
        self.days_off_label.pack(pady=(0, 6))

        self._sep_line = ctk.CTkFrame(self.content, height=1, fg_color=BORDER_COLOR)
        self._sep_line.pack(fill="x", padx=10, pady=4)

        today_str = f"\U0001f4c5 {today.month}\u6708{today.day}\u65e5"
        self.calendar_btn = ctk.CTkButton(
            self.content, text=today_str,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=BORDER_COLOR, hover_color="#374151",
            text_color="#E5E7EB", corner_radius=10, height=34, width=180,
            command=self._toggle_calendar)
        self.calendar_btn.pack(pady=6)

        self.drop_feedback = ctk.CTkLabel(
            self.content,
            text="\U0001f4ce \u62d6\u62fd\u6587\u4ef6\u5230\u7a97\u53e3\u5373\u53ef\u4fdd\u5b58",
            font=ctk.CTkFont(family="Microsoft YaHei", size=10), text_color="#4B5563")
        self.drop_feedback.pack(pady=(2, 0))

        # ============ 缩放手柄 ============
        self._resize_handle = ctk.CTkLabel(
            self.main_card, text="\u27cb",
            font=ctk.CTkFont(size=12), text_color="#4B5563", width=18, height=18)
        self._resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-4)
        self._resize_handle.bind('<Button-1>', self._start_resize)
        self._resize_handle.bind('<B1-Motion>', self._do_resize)

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

    # ======== 窗口拖拽/缩放 ========

    def _start_drag(self, event):
        if self._locked:
            return
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if self._locked:
            return
        self.geometry(f"+{event.x_root - self._drag_start_x}+{event.y_root - self._drag_start_y}")

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
        new_w = max(self._min_w, self._resize_start_w + event.x_root - self._resize_start_x)
        new_h = max(self._min_h, self._resize_start_h + event.y_root - self._resize_start_y)
        self.geometry(f"{new_w}x{new_h}")

    # ======== 锁定（置顶 + 位置锁定 + 背景透明） ========

    def _toggle_lock(self):
        self._locked = not self._locked
        if self._locked:
            self._lock_btn.configure(text="\U0001f512", text_color="#EF4444")
            self.attributes('-topmost', True)
            self._apply_transparent_bg()
        else:
            self._lock_btn.configure(text="\U0001f513", text_color="#9CA3AF")
            self.attributes('-topmost', False)
            self._restore_bg()

    def _apply_transparent_bg(self):
        """锁定模式：窗口边框透明，内容区保留深色背景确保文字无描边"""
        try:
            self.attributes('-transparentcolor', TRANSPARENT_KEY)
        except Exception:
            pass

        try:
            self.configure(fg_color=TRANSPARENT_KEY)
        except Exception:
            pass
        tk.Tk.configure(self, bg=TRANSPARENT_KEY)

        self.main_card.configure(corner_radius=0, border_width=0,
                                  fg_color=TRANSPARENT_KEY)

        self.titlebar.configure(fg_color=TRANSPARENT_KEY)
        for child in self.titlebar.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                child.configure(fg_color=TRANSPARENT_KEY)

        for btn in (self._lock_btn, self._close_btn, self._settings_btn):
            btn.configure(fg_color=TITLEBAR_BG)
            canvas = getattr(btn, '_canvas', None)
            if canvas:
                try:
                    canvas.configure(bg=TITLEBAR_BG)
                except Exception:
                    pass

        self.title_lbl.pack_forget()

        self.content.configure(fg_color=NORMAL_BG, corner_radius=12)

        self._sep_line.pack_forget()
        self._resize_handle.place_forget()
        self.drop_feedback.pack_forget()

        self.calendar_btn.configure(fg_color=BORDER_COLOR)

    def _restore_bg(self):
        """解锁模式：恢复正常外观"""
        try:
            self.attributes('-transparentcolor', '')
        except Exception:
            pass

        default_bg = ctk.ThemeManager.theme["CTk"]["fg_color"][1]
        try:
            self.configure(fg_color=default_bg)
        except Exception:
            pass
        tk.Tk.configure(self, bg=default_bg)

        self.main_card.configure(fg_color=NORMAL_BG, corner_radius=16,
                                  border_width=1, border_color=BORDER_COLOR)

        self.titlebar.configure(fg_color=TITLEBAR_BG)
        for child in self.titlebar.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                child.configure(fg_color="transparent")

        for btn in (self._lock_btn, self._close_btn, self._settings_btn):
            btn.configure(fg_color="transparent")

        self.title_lbl.pack(side="left", padx=2)

        self.content.configure(fg_color="transparent")

        self._force_ctk_redraw(self)

        self._sep_line.pack(fill="x", padx=10, pady=4, before=self.calendar_btn)
        self._sep_line.configure(fg_color=BORDER_COLOR)
        self._resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-4)
        self.drop_feedback.pack(pady=(2, 0))
        self.calendar_btn.configure(fg_color=BORDER_COLOR)

    @staticmethod
    def _force_ctk_redraw(widget):
        """递归调用所有 CTk 控件的 _draw() 强制重绘"""
        if hasattr(widget, '_draw'):
            try:
                widget._draw()
            except Exception:
                pass
        for child in widget.winfo_children():
            MainApp._force_ctk_redraw(child)

    # ======== 设置 ========

    def _open_settings(self):
        if self._settings_popup and self._settings_popup.winfo_exists():
            self._settings_popup.destroy()
            self._settings_popup = None
            return
        self._settings_popup = SettingsDialog(
            self, current_alpha=self._alpha,
            on_alpha_change=self._set_alpha,
            close_to_tray=self._close_to_tray,
            on_close_to_tray_change=self._on_close_to_tray_change)

    def _set_alpha(self, alpha):
        self._alpha = max(0.2, min(1.0, alpha))
        self.attributes('-alpha', self._alpha)

    def _on_close_to_tray_change(self, enabled):
        self._close_to_tray = enabled

    # ======== 关闭/托盘 ========

    def _on_close(self):
        if self._close_to_tray:
            self.withdraw()
        else:
            self.quit_app()

    def show_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        if self.tray:
            self.tray.stop()
        self.destroy()

    # ======== Configure ========

    def _on_configure(self, event):
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.reposition()
        self._apply_scaling()

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
                self.holiday_name_label.configure(text=f"\u8ddd{info['name']}\u8fd8\u6709\uff1a")
                self.days_label.configure(text=str(info['days']))
                self.time_label.configure(
                    text=f"{info['hours']:02d}:{info['minutes']:02d}:{info['seconds']:02d}")
                self.days_off_label.configure(text=f"\U0001f389 \u653e\u5047 {info['days_off']} \u5929")
            else:
                self.holiday_name_label.configure(text="\u6682\u65e0\u8282\u5047\u65e5\u4fe1\u606f")
                self.days_label.configure(text="--")
                self.time_label.configure(text="--:--:--")
                self.days_off_label.configure(text="")
        except Exception as e:
            self.holiday_name_label.configure(text="\u83b7\u53d6\u8282\u5047\u65e5\u4fe1\u606f\u5931\u8d25")
        today = date.today()
        weekday = WEEKDAY_NAMES[today.weekday()]
        self.date_label.configure(
            text=f"{today.year}\u5e74{today.month}\u6708{today.day}\u65e5 {weekday}")
        self.calendar_btn.configure(text=f"\U0001f4c5 {today.month}\u6708{today.day}\u65e5")
        self.after(1000, self._update_countdown)

    # ======== 日历 ========

    def _toggle_calendar(self):
        if self.calendar_popup is not None:
            try:
                if self.calendar_popup.winfo_exists():
                    self.calendar_popup.destroy()
                    return
            except Exception:
                pass
            self.calendar_popup = None
            return
        self.calendar_popup = MiniCalendarPopup(
            self, anchor_widget=self.calendar_btn,
            on_change=self._on_data_changed,
            on_destroy=self._on_calendar_destroyed)

    def _on_calendar_destroyed(self):
        self.calendar_popup = None

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
                        os.path.join(candidate, 'pkgIndex.tcl')):
                        tkdnd_path = candidate
                        break
                if not tkdnd_path:
                    raise FileNotFoundError("tkdnd not found")
            self.tk.call('lappend', 'auto_path', tkdnd_path)
            self.tk.call('package', 'require', 'tkdnd')
            self._setup_dnd_bindings()
            self.drop_enabled = True
        except Exception as e:
            self.drop_feedback.configure(text="\u26a0\ufe0f \u62d6\u62fd\u4e0d\u53ef\u7528")

    def _setup_dnd_bindings(self):
        self.tk.call('tkdnd::drop_target', 'register', self._w, 'DND_Files')
        self.tk.call('bind', self._w, '<<Drop:DND_Files>>', self.register(self._on_drop_raw) + ' %D')
        self.tk.call('bind', self._w, '<<DragEnter>>', self.register(self._on_drag_enter_raw) + ' %D')
        self.tk.call('bind', self._w, '<<DragLeave>>', self.register(self._on_drag_leave_raw))

    def _on_drop_raw(self, data):
        self.main_card.configure(border_color=BORDER_COLOR, border_width=1)
        files = re.findall(r'\{([^}]+)\}', data) if '{' in data else [f for f in data.split() if f.strip()]
        if files:
            self._show_save_results(file_manager.save_dropped_files(files))
        return 'copy'

    def _on_drag_enter_raw(self, data=''):
        self.main_card.configure(border_color="#3B82F6", border_width=2)
        self.drop_feedback.configure(text="\U0001f4e5 \u91ca\u653e\u4ee5\u4fdd\u5b58\u6587\u4ef6", text_color="#3B82F6")
        return 'copy'

    def _on_drag_leave_raw(self):
        self.main_card.configure(border_color=BORDER_COLOR, border_width=1)
        self.drop_feedback.configure(text="\U0001f4ce \u62d6\u62fd\u6587\u4ef6\u5230\u7a97\u53e3\u5373\u53ef\u4fdd\u5b58", text_color="#4B5563")
        return 'copy'

    def _show_save_results(self, results):
        ok = sum(1 for r in results if r.get('success'))
        if ok > 0:
            self.drop_feedback.configure(text=f"\u2705 \u5df2\u4fdd\u5b58 {ok}/{len(results)} \u4e2a\u6587\u4ef6", text_color="#22C55E")
            if self.calendar_popup and self.calendar_popup.winfo_exists():
                self.calendar_popup.refresh_dots()
        else:
            self.drop_feedback.configure(text="\u274c \u4fdd\u5b58\u5931\u8d25", text_color="#EF4444")
        self.after(3000, lambda: self.drop_feedback.configure(
            text="\U0001f4ce \u62d6\u62fd\u6587\u4ef6\u5230\u7a97\u53e3\u5373\u53ef\u4fdd\u5b58", text_color="#4B5563"))
