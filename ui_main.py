"""
主台历界面
iOS 风格无边框台历卡片，显示节假日倒计时，支持文件拖拽
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


# 星期映射
WEEKDAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']


class MainApp(ctk.CTk):
    """主台历应用 - 无边框窗口"""

    def __init__(self):
        super().__init__()

        # 窗口设置 - 无边框
        self.overrideredirect(True)
        self.geometry("360x460")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 状态
        self._alpha = 0.95
        self.attributes('-alpha', self._alpha)
        self.attributes('-topmost', False)
        self.calendar_popup = None
        self.drop_enabled = False
        self._locked = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._resizing = False
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0
        self._min_w = 300
        self._min_h = 380

        self._build_ui()
        self._update_countdown()
        self._setup_drag_drop()

        # 窗口居中
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

        # 窗口移动时更新日历位置
        self.bind('<Configure>', self._on_configure)

    def _build_ui(self):
        # ============ 主容器 - 台历卡片 ============
        self.main_card = ctk.CTkFrame(
            self,
            corner_radius=16,
            fg_color="#1E1E2E",
            border_width=1,
            border_color="#2D2D44"
        )
        self.main_card.pack(fill="both", expand=True, padx=0, pady=0)

        # ============ 自定义标题栏 ============
        self.titlebar = ctk.CTkFrame(
            self.main_card,
            height=36,
            fg_color="#16162A",
            corner_radius=0
        )
        self.titlebar.pack(fill="x", padx=1, pady=(1, 0))
        self.titlebar.pack_propagate(False)

        # 标题栏左侧圆角填充
        ctk.CTkFrame(
            self.titlebar, width=16, fg_color="transparent"
        ).pack(side="left")

        # 标题文字
        title_lbl = ctk.CTkLabel(
            self.titlebar, text="📅 桌面助手",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color="#9CA3AF"
        )
        title_lbl.pack(side="left", padx=2)

        # 标题栏右侧按钮
        close_btn = ctk.CTkButton(
            self.titlebar, text="✕", width=30, height=26,
            fg_color="transparent", hover_color="#EF4444",
            text_color="#9CA3AF", font=ctk.CTkFont(size=14),
            corner_radius=6, command=self.destroy
        )
        close_btn.pack(side="right", padx=(0, 4))

        # 锁定按钮
        self._lock_btn = ctk.CTkButton(
            self.titlebar, text="🔓", width=30, height=26,
            fg_color="transparent", hover_color="#374151",
            text_color="#9CA3AF", font=ctk.CTkFont(size=13),
            corner_radius=6, command=self._toggle_lock
        )
        self._lock_btn.pack(side="right", padx=1)

        # 置顶按钮
        self._pin_btn = ctk.CTkButton(
            self.titlebar, text="📌", width=30, height=26,
            fg_color="transparent", hover_color="#374151",
            text_color="#6B7280", font=ctk.CTkFont(size=13),
            corner_radius=6, command=self._toggle_topmost
        )
        self._pin_btn.pack(side="right", padx=1)

        # 透明度减按钮
        alpha_down = ctk.CTkButton(
            self.titlebar, text="◉", width=26, height=26,
            fg_color="transparent", hover_color="#374151",
            text_color="#6B7280", font=ctk.CTkFont(size=11),
            corner_radius=6, command=lambda: self._change_alpha(-0.1)
        )
        alpha_down.pack(side="right", padx=0)

        # 透明度加按钮
        alpha_up = ctk.CTkButton(
            self.titlebar, text="◎", width=26, height=26,
            fg_color="transparent", hover_color="#374151",
            text_color="#9CA3AF", font=ctk.CTkFont(size=11),
            corner_radius=6, command=lambda: self._change_alpha(0.1)
        )
        alpha_up.pack(side="right", padx=0)

        # 拖拽绑定 - 标题栏拖动窗口
        self.titlebar.bind('<Button-1>', self._start_drag)
        self.titlebar.bind('<B1-Motion>', self._do_drag)
        title_lbl.bind('<Button-1>', self._start_drag)
        title_lbl.bind('<B1-Motion>', self._do_drag)

        # ============ 内容区 ============
        content = ctk.CTkFrame(self.main_card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=(8, 10))

        # 红色顶部装饰线
        deco = ctk.CTkFrame(content, height=4, corner_radius=2, fg_color="#EF4444")
        deco.pack(fill="x", padx=15, pady=(0, 8))

        # 今天日期
        today = date.today()
        weekday = WEEKDAY_NAMES[today.weekday()]
        self.date_label = ctk.CTkLabel(
            content,
            text=f"{today.year}年{today.month}月{today.day}日 {weekday}",
            font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"),
            text_color="#E5E7EB"
        )
        self.date_label.pack(pady=(2, 0))

        # "距XX还有："
        self.holiday_name_label = ctk.CTkLabel(
            content,
            text="正在获取节假日信息...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color="#9CA3AF"
        )
        self.holiday_name_label.pack(pady=(4, 0))

        # 天数（大号红色）
        self.days_label = ctk.CTkLabel(
            content,
            text="--",
            font=ctk.CTkFont(family="Microsoft YaHei", size=58, weight="bold"),
            text_color="#EF4444"
        )
        self.days_label.pack(pady=(0, 0))

        # "天" 字
        self.days_unit_label = ctk.CTkLabel(
            content,
            text="天",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color="#EF4444"
        )
        self.days_unit_label.pack(pady=(0, 0))

        # 时分秒
        self.time_label = ctk.CTkLabel(
            content,
            text="--:--:--",
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color="#9CA3AF"
        )
        self.time_label.pack(pady=(0, 2))

        # 放假天数
        self.days_off_label = ctk.CTkLabel(
            content,
            text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color="#34D399"
        )
        self.days_off_label.pack(pady=(0, 6))

        # 分割线
        ctk.CTkFrame(
            content, height=1, fg_color="#2D2D44"
        ).pack(fill="x", padx=10, pady=4)

        # 日期按钮（点击弹出小日历 - 向上弹出）
        today_str = f"📅 {today.month}月{today.day}日"
        self.calendar_btn = ctk.CTkButton(
            content,
            text=today_str,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color="#2D2D44",
            hover_color="#374151",
            text_color="#E5E7EB",
            corner_radius=10,
            height=34,
            width=180,
            command=self._toggle_calendar
        )
        self.calendar_btn.pack(pady=6)

        # 拖拽反馈标签
        self.drop_feedback = ctk.CTkLabel(
            content,
            text="📎 拖拽文件到窗口即可保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            text_color="#4B5563"
        )
        self.drop_feedback.pack(pady=(2, 0))

        # ============ 右下角缩放手柄 ============
        self._resize_handle = ctk.CTkLabel(
            self.main_card,
            text="⟋",
            font=ctk.CTkFont(size=12),
            text_color="#4B5563",
            width=18, height=18,
            cursor="size_nw_se"
        )
        self._resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-4, y=-4)
        self._resize_handle.bind('<Button-1>', self._start_resize)
        self._resize_handle.bind('<B1-Motion>', self._do_resize)

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
            self._lock_btn.configure(text="🔒", text_color="#EF4444")
        else:
            self._lock_btn.configure(text="🔓", text_color="#9CA3AF")

    def _toggle_topmost(self):
        current = self.attributes('-topmost')
        self.attributes('-topmost', not current)
        if not current:
            self._pin_btn.configure(text_color="#F59E0B")
        else:
            self._pin_btn.configure(text_color="#6B7280")

    def _change_alpha(self, delta):
        self._alpha = max(0.2, min(1.0, self._alpha + delta))
        self.attributes('-alpha', self._alpha)

    def _on_configure(self, event):
        """窗口移动/大小改变时，更新日历位置"""
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.reposition()

    # ======== 倒计时 ========

    def _update_countdown(self):
        """每秒更新倒计时"""
        try:
            info = holiday_module.get_holiday_countdown()
            if info:
                self.holiday_name_label.configure(
                    text=f"距{info['name']}还有：")
                self.days_label.configure(text=str(info['days']))
                self.time_label.configure(
                    text=f"{info['hours']:02d}:{info['minutes']:02d}:{info['seconds']:02d}")
                self.days_off_label.configure(
                    text=f"🎉 放假 {info['days_off']} 天")
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
        self.date_label.configure(
            text=f"{today.year}年{today.month}月{today.day}日 {weekday}")
        self.calendar_btn.configure(text=f"📅 {today.month}月{today.day}日")

        self.after(1000, self._update_countdown)

    # ======== 日历 ========

    def _toggle_calendar(self):
        """打开/关闭小日历（向上弹出，跟随主窗口）"""
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.destroy()
            self.calendar_popup = None
        else:
            self.calendar_popup = MiniCalendarPopup(
                self,
                anchor_widget=self.calendar_btn,
                on_change=self._on_data_changed
            )

    def _on_data_changed(self):
        if self.calendar_popup and self.calendar_popup.winfo_exists():
            self.calendar_popup.refresh_dots()

    # ======== 拖拽 ========

    def _setup_drag_drop(self):
        """设置文件拖拽功能 - 通过 Tcl 直接加载 tkdnd"""
        try:
            import tkinterdnd2
            import struct
            base_tkdnd = os.path.join(
                os.path.dirname(tkinterdnd2.__file__), 'tkdnd'
            )
            # tkinterdnd2 0.4.x 使用平台子目录 (win-x64, win-x86 等)
            bits = struct.calcsize('P') * 8
            arch = 'x64' if bits == 64 else 'x86'
            platform_path = os.path.join(base_tkdnd, f'win-{arch}')

            # 找到包含 pkgIndex.tcl 的目录
            if os.path.exists(os.path.join(platform_path, 'pkgIndex.tcl')):
                tkdnd_path = platform_path
            elif os.path.exists(os.path.join(base_tkdnd, 'pkgIndex.tcl')):
                tkdnd_path = base_tkdnd
            else:
                # 搜索所有子目录
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
            print(f"拖拽功能已启用: {tkdnd_path}")
        except Exception as e:
            print(f"拖拽功能初始化失败: {e}")
            self.drop_feedback.configure(text="⚠️ 拖拽不可用")

    def _setup_dnd_bindings(self):
        """通过 Tcl 命令设置拖放绑定到整个窗口"""
        self.tk.call(
            'tkdnd::drop_target', 'register',
            self._w, 'DND_Files'
        )

        drop_cmd = self.register(self._on_drop_raw)
        self.tk.call(
            'bind', self._w, '<<Drop:DND_Files>>',
            drop_cmd + ' %D'
        )
        enter_cmd = self.register(self._on_drag_enter_raw)
        self.tk.call(
            'bind', self._w, '<<DragEnter>>',
            enter_cmd + ' %D'
        )
        leave_cmd = self.register(self._on_drag_leave_raw)
        self.tk.call(
            'bind', self._w, '<<DragLeave>>',
            leave_cmd
        )

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
        self.drop_feedback.configure(
            text="📥 释放以保存文件",
            text_color="#3B82F6"
        )
        return 'copy'

    def _on_drag_leave_raw(self):
        self.main_card.configure(border_color="#2D2D44", border_width=1)
        self.drop_feedback.configure(
            text="📎 拖拽文件到窗口即可保存",
            text_color="#4B5563"
        )
        return 'copy'

    def _show_save_results(self, results):
        success_count = sum(1 for r in results if r.get('success'))
        total = len(results)

        if success_count > 0:
            self.drop_feedback.configure(
                text=f"✅ 已保存 {success_count}/{total} 个文件",
                text_color="#22C55E"
            )
            if self.calendar_popup and self.calendar_popup.winfo_exists():
                self.calendar_popup.refresh_dots()
        else:
            self.drop_feedback.configure(
                text="❌ 保存失败",
                text_color="#EF4444"
            )

        self.after(3000, lambda: self.drop_feedback.configure(
            text="📎 拖拽文件到窗口即可保存",
            text_color="#4B5563"
        ))
