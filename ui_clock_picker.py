"""
24 小时制时钟选择器对话框
用于为计划设置闹钟时间
支持上下箭头调整 + 直接输入数字
"""

import customtkinter as ctk


class ClockPickerDialog(ctk.CTkToplevel):
    """24 小时时钟选择器"""

    def __init__(self, parent, on_select, initial_time=None):
        super().__init__(parent)
        self.on_select = on_select

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1E1E2E")

        hour, minute = 8, 0
        if initial_time:
            parts = initial_time.split(':')
            hour, minute = int(parts[0]), int(parts[1])

        self._hour = hour
        self._minute = minute

        self._build_ui()

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 120
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 110
        self.geometry(f"240x210+{max(0,px)}+{max(0,py)}")

        self.bind('<FocusOut>', lambda e: self.after(150, self._check_focus))

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

        title = ctk.CTkLabel(outer, text="\u23f0 \u8bbe\u7f6e\u63d0\u9192\u65f6\u95f4",
                             font=ctk.CTkFont(size=14, weight="bold"),
                             text_color="#E5E7EB")
        title.pack(pady=(12, 8))

        picker = ctk.CTkFrame(outer, fg_color="transparent")
        picker.pack(pady=4)

        btn_cfg = dict(width=28, height=28, corner_radius=6,
                       fg_color="transparent", hover_color="#374151",
                       text_color="#60A5FA", font=ctk.CTkFont(size=16))

        # Hour column
        h_col = ctk.CTkFrame(picker, fg_color="transparent")
        h_col.pack(side="left", padx=8)
        ctk.CTkButton(h_col, text="\u25b2", command=lambda: self._adj_hour(1), **btn_cfg).pack()

        self._hour_entry = ctk.CTkEntry(
            h_col, width=56, height=40, justify="center",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#E5E7EB", fg_color="#2D2D44",
            border_width=1, border_color="#374151", corner_radius=8)
        self._hour_entry.insert(0, f"{self._hour:02d}")
        self._hour_entry.pack(pady=4)
        self._hour_entry.bind('<FocusOut>', lambda e: self._validate_hour())
        self._hour_entry.bind('<Return>', lambda e: self._min_entry.focus_set())

        ctk.CTkButton(h_col, text="\u25bc", command=lambda: self._adj_hour(-1), **btn_cfg).pack()

        sep = ctk.CTkLabel(picker, text=":", font=ctk.CTkFont(size=28, weight="bold"),
                           text_color="#9CA3AF")
        sep.pack(side="left", padx=2, pady=(0, 6))

        # Minute column
        m_col = ctk.CTkFrame(picker, fg_color="transparent")
        m_col.pack(side="left", padx=8)
        ctk.CTkButton(m_col, text="\u25b2", command=lambda: self._adj_min(5), **btn_cfg).pack()

        self._min_entry = ctk.CTkEntry(
            m_col, width=56, height=40, justify="center",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#E5E7EB", fg_color="#2D2D44",
            border_width=1, border_color="#374151", corner_radius=8)
        self._min_entry.insert(0, f"{self._minute:02d}")
        self._min_entry.pack(pady=4)
        self._min_entry.bind('<FocusOut>', lambda e: self._validate_min())
        self._min_entry.bind('<Return>', lambda e: self._confirm())

        ctk.CTkButton(m_col, text="\u25bc", command=lambda: self._adj_min(-5), **btn_cfg).pack()

        # Buttons
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 12))

        ctk.CTkButton(btn_row, text="\u53d6\u6d88", width=65, height=30,
                       fg_color="#374151", hover_color="#4B5563",
                       corner_radius=8, font=ctk.CTkFont(size=12),
                       command=self.destroy).pack(side="left")

        ctk.CTkButton(btn_row, text="\u6e05\u9664\u95f9\u949f", width=70, height=30,
                       fg_color="#6B7280", hover_color="#4B5563",
                       corner_radius=8, font=ctk.CTkFont(size=12),
                       command=self._clear).pack(side="left", padx=4)

        ctk.CTkButton(btn_row, text="\u2714 \u786e\u5b9a", width=65, height=30,
                       fg_color="#10B981", hover_color="#059669",
                       corner_radius=8, font=ctk.CTkFont(size=12),
                       command=self._confirm).pack(side="right")

    def _validate_hour(self):
        txt = self._hour_entry.get().strip()
        try:
            v = int(txt)
            self._hour = max(0, min(23, v))
        except ValueError:
            pass
        self._hour_entry.delete(0, "end")
        self._hour_entry.insert(0, f"{self._hour:02d}")

    def _validate_min(self):
        txt = self._min_entry.get().strip()
        try:
            v = int(txt)
            self._minute = max(0, min(59, v))
        except ValueError:
            pass
        self._min_entry.delete(0, "end")
        self._min_entry.insert(0, f"{self._minute:02d}")

    def _adj_hour(self, delta):
        self._validate_hour()
        self._hour = (self._hour + delta) % 24
        self._hour_entry.delete(0, "end")
        self._hour_entry.insert(0, f"{self._hour:02d}")

    def _adj_min(self, delta):
        self._validate_min()
        self._minute = (self._minute + delta) % 60
        self._min_entry.delete(0, "end")
        self._min_entry.insert(0, f"{self._minute:02d}")

    def _confirm(self):
        self._validate_hour()
        self._validate_min()
        time_str = f"{self._hour:02d}:{self._minute:02d}"
        self.on_select(time_str)
        self.destroy()

    def _clear(self):
        self.on_select(None)
        self.destroy()
