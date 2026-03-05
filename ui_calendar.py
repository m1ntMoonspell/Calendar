"""
弹出小日历组件
基于 Canvas 自绘，支持:
- 当天红色实心底色
- 选中日期虚线框
- 有计划的日期下方绿色圆点
- 有文件的日期下方红色圆点
- 双击查看/编辑计划和文件
- 向上弹出，跟随主窗口移动
"""

import tkinter as tk
import customtkinter as ctk
import calendar
from datetime import date, datetime
import database
from ui_plan import PlanViewDialog


class MiniCalendarPopup(ctk.CTkToplevel):
    """弹出式小日历 - 向上弹出，跟随主窗口"""

    COLORS = {
        'bg': '#1E1E2E',
        'header_bg': '#2D2D44',
        'today_bg': '#EF4444',
        'today_fg': '#FFFFFF',
        'selected_border': '#60A5FA',
        'weekday_fg': '#9CA3AF',
        'weekend_fg': '#F87171',
        'normal_fg': '#E5E7EB',
        'other_month_fg': '#4B5563',
        'plan_dot': '#22C55E',
        'file_dot': '#EF4444',
        'hover_bg': '#374151',
        'nav_fg': '#60A5FA',
    }

    CELL_SIZE = 44
    DOT_RADIUS = 3
    HEADER_HEIGHT = 42
    WEEKDAY_HEIGHT = 28

    def __init__(self, parent, anchor_widget=None, on_change=None, on_destroy=None):
        super().__init__(parent)
        self.parent_window = parent
        self.anchor_widget = anchor_widget or parent
        self.on_change = on_change
        self.on_destroy_cb = on_destroy

        self.overrideredirect(True)
        self.attributes('-topmost', True)

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = None
        self.hover_date = None

        self._width = self.CELL_SIZE * 7 + 20
        self._height = self.HEADER_HEIGHT + self.WEEKDAY_HEIGHT + self.CELL_SIZE * 6 + 30

        self.plan_dates = database.get_dates_with_plans()
        self.file_dates = database.get_dates_with_files()

        self._build_ui()

        # 延迟定位，确保窗口已经完全创建
        self.after(50, self.reposition)

        # 点击日历窗口外部时自动关闭
        self._parent_bind_id = self.parent_window.bind(
            '<Button-1>', self._on_parent_click, add='+')
        self.bind('<Escape>', lambda e: self.destroy())

    def _on_parent_click(self, event):
        """主窗口被点击时关闭日历弹窗（点击日历按钮本身除外，由 toggle 处理）"""
        try:
            w = event.widget
            if w == self.anchor_widget or w == getattr(self.anchor_widget, '_canvas', None) \
                    or w == getattr(self.anchor_widget, '_text_label', None):
                return
        except Exception:
            pass
        self.after(50, self.destroy)

    def destroy(self):
        try:
            self.parent_window.unbind('<Button-1>', self._parent_bind_id)
        except Exception:
            pass
        if self.on_destroy_cb:
            try:
                self.on_destroy_cb()
            except Exception:
                pass
        super().destroy()

    def reposition(self):
        """重新定位 - 在锚点组件上方弹出"""
        try:
            self.update_idletasks()
            aw = self.anchor_widget
            ax = aw.winfo_rootx()
            ay = aw.winfo_rooty()

            x = ax + (aw.winfo_width() - self._width) // 2
            y = ay - self._height - 5

            if y < 0:
                y = ay + aw.winfo_height() + 5

            screen_w = self.winfo_screenwidth()
            x = max(0, min(x, screen_w - self._width))

            self.geometry(f"{self._width}x{self._height}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # 设置 CTkToplevel 背景为实际颜色，不要用 "transparent"
        self.configure(fg_color=self.COLORS['bg'])

        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=self.COLORS['bg'],
            corner_radius=14,
            border_width=1,
            border_color="#374151"
        )
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        inner = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=6)

        nav_frame = ctk.CTkFrame(inner, fg_color="transparent", height=self.HEADER_HEIGHT)
        nav_frame.pack(fill="x", pady=(2, 0))
        nav_frame.pack_propagate(False)

        prev_btn = ctk.CTkButton(
            nav_frame, text="\u25c0", width=32, height=28,
            fg_color="transparent", hover_color="#374151",
            text_color=self.COLORS['nav_fg'],
            font=ctk.CTkFont(size=14), corner_radius=6,
            command=self._prev_month
        )
        prev_btn.pack(side="left")

        self.month_label = ctk.CTkLabel(
            nav_frame, text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#E5E7EB"
        )
        self.month_label.pack(side="left", expand=True)

        next_btn = ctk.CTkButton(
            nav_frame, text="\u25b6", width=32, height=28,
            fg_color="transparent", hover_color="#374151",
            text_color=self.COLORS['nav_fg'],
            font=ctk.CTkFont(size=14), corner_radius=6,
            command=self._next_month
        )
        next_btn.pack(side="right")

        canvas_width = self.CELL_SIZE * 7
        canvas_height = self.WEEKDAY_HEIGHT + self.CELL_SIZE * 6 + 10
        self.canvas = tk.Canvas(
            inner,
            width=canvas_width,
            height=canvas_height,
            bg=self.COLORS['bg'],
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(pady=(0, 2))

        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Double-Button-1>', self._on_double_click)
        self.canvas.bind('<Motion>', self._on_motion)
        self.canvas.bind('<Leave>', self._on_leave)

        self._draw_calendar()

    def _draw_calendar(self):
        self.canvas.delete("all")
        self.month_label.configure(text=f"{self.current_year}\u5e74 {self.current_month}\u6708")

        weekdays = ['\u4e00', '\u4e8c', '\u4e09', '\u56db', '\u4e94', '\u516d', '\u65e5']
        for i, wd in enumerate(weekdays):
            x = i * self.CELL_SIZE + self.CELL_SIZE // 2
            y = self.WEEKDAY_HEIGHT // 2
            color = self.COLORS['weekend_fg'] if i >= 5 else self.COLORS['weekday_fg']
            self.canvas.create_text(
                x, y, text=wd,
                font=("Microsoft YaHei", 10, "bold"),
                fill=color
            )

        cal = calendar.monthcalendar(self.current_year, self.current_month)
        today = date.today()
        self._date_cells = {}

        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue

                cell_date = date(self.current_year, self.current_month, day)
                self._date_cells[(row_idx, col_idx)] = cell_date

                cx = col_idx * self.CELL_SIZE + self.CELL_SIZE // 2
                cy = self.WEEKDAY_HEIGHT + row_idx * self.CELL_SIZE + self.CELL_SIZE // 2 - 2

                date_str = cell_date.isoformat()
                is_today = cell_date == today
                is_selected = cell_date == self.selected_date
                is_hover = cell_date == self.hover_date
                has_plan = date_str in self.plan_dates
                has_file = date_str in self.file_dates

                r = self.CELL_SIZE // 2 - 4

                if is_today:
                    self.canvas.create_oval(
                        cx - r, cy - r, cx + r, cy + r,
                        fill=self.COLORS['today_bg'], outline='', tags="cell_bg"
                    )
                elif is_hover:
                    self.canvas.create_oval(
                        cx - r, cy - r, cx + r, cy + r,
                        fill=self.COLORS['hover_bg'], outline='', tags="cell_bg"
                    )

                if is_selected:
                    self.canvas.create_oval(
                        cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1,
                        outline=self.COLORS['selected_border'],
                        width=2, dash=(4, 3), tags="cell_select"
                    )

                text_color = self.COLORS['today_fg'] if is_today else (
                    self.COLORS['weekend_fg'] if col_idx >= 5 else self.COLORS['normal_fg']
                )
                self.canvas.create_text(
                    cx, cy - 2, text=str(day),
                    font=("Microsoft YaHei", 12, "bold" if is_today else "normal"),
                    fill=text_color, tags="cell_text"
                )

                dot_y = cy + r - 5
                if has_plan:
                    self.canvas.create_oval(
                        cx - self.DOT_RADIUS, dot_y - self.DOT_RADIUS,
                        cx + self.DOT_RADIUS, dot_y + self.DOT_RADIUS,
                        fill=self.COLORS['plan_dot'], outline='', tags="dot"
                    )
                    dot_y += self.DOT_RADIUS * 2 + 2

                if has_file:
                    self.canvas.create_oval(
                        cx - self.DOT_RADIUS, dot_y - self.DOT_RADIUS,
                        cx + self.DOT_RADIUS, dot_y + self.DOT_RADIUS,
                        fill=self.COLORS['file_dot'], outline='', tags="dot"
                    )

    def _get_date_at(self, event):
        col = event.x // self.CELL_SIZE
        row = (event.y - self.WEEKDAY_HEIGHT) // self.CELL_SIZE
        if 0 <= col < 7 and 0 <= row < 6:
            return self._date_cells.get((row, col))
        return None

    def _on_click(self, event):
        d = self._get_date_at(event)
        if d:
            self.selected_date = d
            self._draw_calendar()

    def _on_double_click(self, event):
        d = self._get_date_at(event)
        if d:
            self.selected_date = d

            def _on_plan_changed():
                self.plan_dates = database.get_dates_with_plans()
                self._draw_calendar()
                if self.on_change:
                    self.on_change()

            PlanViewDialog(self, d.isoformat(), on_change=_on_plan_changed)

    def _on_motion(self, event):
        d = self._get_date_at(event)
        if d != self.hover_date:
            self.hover_date = d
            self._draw_calendar()

    def _on_leave(self, event):
        self.hover_date = None
        self._draw_calendar()

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self._draw_calendar()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self._draw_calendar()

    def refresh_dots(self):
        self.plan_dates = database.get_dates_with_plans()
        self.file_dates = database.get_dates_with_files()
        self._draw_calendar()
