"""
计划查看/编辑对话框
- 无边框自定义 header，与整体 UI 风格融为一体
- 单行输入，回车新增行
- 退格键在空行时删除该行并返回上一行焦点
- 每行前有闹钟标志，点击可设置提醒时间
"""

import customtkinter as ctk
import database
from ui_clock_picker import ClockPickerDialog


class PlanViewDialog(ctk.CTkToplevel):
    """查看、新建、编辑计划和文件的对话框"""

    def __init__(self, parent, date_str, on_change=None):
        super().__init__(parent)
        self.date_str = date_str
        self.on_change = on_change

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1E1E2E")
        self.geometry("520x600")

        self._entries = []
        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

    def _build_ui(self):
        main_card = ctk.CTkFrame(self, corner_radius=16, fg_color="#1E1E2E",
                                  border_width=1, border_color="#2D2D44")
        main_card.pack(fill="both", expand=True)

        # === 自定义标题栏 ===
        titlebar = ctk.CTkFrame(main_card, height=36, fg_color="#16162A", corner_radius=0)
        titlebar.pack(fill="x", padx=1, pady=(1, 0))
        titlebar.pack_propagate(False)

        ctk.CTkFrame(titlebar, width=12, fg_color="transparent").pack(side="left")

        title_lbl = ctk.CTkLabel(titlebar,
                                  text=f"\U0001f4cb {self.date_str} \u7684\u8ba1\u5212\u4e0e\u6587\u4ef6",
                                  font=ctk.CTkFont(size=12), text_color="#9CA3AF")
        title_lbl.pack(side="left", padx=2)

        close_btn = ctk.CTkButton(titlebar, text="\u2715", width=30, height=26,
                                   fg_color="transparent", hover_color="#EF4444",
                                   text_color="#9CA3AF", font=ctk.CTkFont(size=14),
                                   corner_radius=6, command=self.destroy)
        close_btn.pack(side="right", padx=(0, 4))

        titlebar.bind('<Button-1>', self._start_drag)
        titlebar.bind('<B1-Motion>', self._do_drag)
        title_lbl.bind('<Button-1>', self._start_drag)
        title_lbl.bind('<B1-Motion>', self._do_drag)

        # === 红色装饰线 ===
        content = ctk.CTkFrame(main_card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=(6, 10))

        ctk.CTkFrame(content, height=3, corner_radius=2, fg_color="#EF4444").pack(fill="x", padx=12, pady=(0, 6))

        # === 计划部分 ===
        ctk.CTkLabel(content, text="\U0001f4dd \u4eca\u65e5\u8ba1\u5212",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#E5E7EB", anchor="w").pack(fill="x", pady=(4, 4))

        self.plan_frame = ctk.CTkScrollableFrame(content, height=200, corner_radius=12,
                                                  fg_color="#16162A",
                                                  border_width=1, border_color="#2D2D44")
        self.plan_frame.pack(fill="x", pady=4)

        plans = database.get_plans_by_date(self.date_str)
        for plan in plans:
            self._add_entry(plan_id=plan['id'], content=plan['content'],
                            alarm_time=plan.get('alarm_time'))
        self._add_entry()

        # === 分割线 ===
        ctk.CTkFrame(content, height=1, fg_color="#2D2D44").pack(fill="x", padx=8, pady=6)

        # === 文件部分 ===
        ctk.CTkLabel(content, text="\U0001f4c1 \u5174\u8da3\u6587\u4ef6",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#E5E7EB", anchor="w").pack(fill="x", pady=(4, 4))

        files = database.get_files_by_date(self.date_str)
        if files:
            file_frame = ctk.CTkScrollableFrame(content, height=180, corner_radius=12,
                                                 fg_color="#16162A",
                                                 border_width=1, border_color="#2D2D44")
            file_frame.pack(fill="x", pady=4)

            for f in files:
                row = ctk.CTkFrame(file_frame, fg_color="transparent")
                row.pack(fill="x", padx=5, pady=2)
                type_emoji = {
                    '\u56fe\u7247': '\U0001f5bc\ufe0f', '\u6587\u6863': '\U0001f4c4',
                    '\u97f3\u9891': '\U0001f3b5', '\u89c6\u9891': '\U0001f3ac',
                    '\u538b\u7f29\u5305': '\U0001f4e6', '\u4ee3\u7801': '\U0001f4bb',
                    '\u5176\u4ed6': '\U0001f4ce'
                }.get(f['file_type'], '\U0001f4ce')
                ctk.CTkLabel(row, text=f"  {type_emoji} {f['original_name']}",
                             font=ctk.CTkFont(size=12), text_color="#D1D5DB",
                             anchor="w").pack(side="left", fill="x", expand=True)
                ctk.CTkButton(row, text="\u6253\u5f00", width=45, height=22,
                               font=ctk.CTkFont(size=10),
                               fg_color="#3B82F6", hover_color="#2563EB",
                               corner_radius=6,
                               command=lambda p=f['saved_path']: self._open_file(p)
                               ).pack(side="right", padx=5)
        else:
            ctk.CTkLabel(content, text="\u6682\u65e0\u6587\u4ef6",
                         font=ctk.CTkFont(size=12), text_color="#4B5563").pack(pady=6)

    # ---- drag ----
    def _start_drag(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ---- entries ----
    def _add_entry(self, plan_id=None, content="", alarm_time=None):
        row = ctk.CTkFrame(self.plan_frame, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=2)

        idx = len(self._entries) + 1

        alarm_btn = ctk.CTkButton(row, text="\u23f0", width=26, height=26,
                                   fg_color="transparent",
                                   hover_color="#374151",
                                   text_color="#4B5563" if not alarm_time else "#F59E0B",
                                   font=ctk.CTkFont(size=13), corner_radius=6)
        alarm_btn.pack(side="left", padx=(0, 2))

        num_label = ctk.CTkLabel(row, text=f"{idx}.",
                                  font=ctk.CTkFont(size=12), text_color="#6B7280",
                                  width=22, anchor="e")
        num_label.pack(side="left", padx=(0, 3))

        entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=12), height=30,
                              border_width=0, fg_color="#1E1E2E",
                              corner_radius=6, text_color="#E5E7EB",
                              placeholder_text="\u8f93\u5165\u8ba1\u5212\uff0c\u56de\u8f66\u786e\u8ba4...")
        entry.pack(side="left", fill="x", expand=True)

        if content:
            entry.insert(0, content)

        info = {
            'plan_id': plan_id,
            'entry': entry,
            'row': row,
            'original': content,
            'alarm_time': alarm_time,
            'alarm_btn': alarm_btn,
            'num_label': num_label,
        }
        self._entries.append(info)

        entry.bind('<Return>', lambda e, i=info: self._on_enter(i))
        entry.bind('<BackSpace>', lambda e, i=info: self._on_backspace(e, i))

        alarm_btn.configure(command=lambda i=info: self._open_clock_picker(i))

        if not content:
            def _safe_focus(e=entry):
                try:
                    if e.winfo_exists():
                        e.focus_set()
                except Exception:
                    pass
            self.after(100, _safe_focus)

        return info

    def _on_enter(self, info):
        content = info['entry'].get().strip()
        if not content:
            return

        if info['plan_id'] is None:
            plan_id = database.add_plan(self.date_str, content)
            info['plan_id'] = plan_id
            info['original'] = content
            self._notify_change()
            self._add_entry()
        else:
            if content != info['original']:
                database.update_plan(info['plan_id'], content)
                info['original'] = content
                self._notify_change()
            current_idx = self._entries.index(info)
            if current_idx < len(self._entries) - 1:
                self._entries[current_idx + 1]['entry'].focus_set()
            else:
                self._add_entry()

    def _on_backspace(self, event, info):
        content = info['entry'].get()
        if content:
            return

        current_idx = self._entries.index(info)
        if current_idx == 0:
            return

        if info['plan_id'] is not None:
            database.delete_plan(info['plan_id'])
            self._notify_change()

        info['row'].destroy()
        self._entries.remove(info)

        self._renumber()

        prev = self._entries[current_idx - 1]
        prev['entry'].focus_set()
        prev['entry'].icursor('end')

        return "break"

    def _renumber(self):
        for i, info in enumerate(self._entries):
            info['num_label'].configure(text=f"{i+1}.")

    def _open_clock_picker(self, info):
        if info['plan_id'] is None:
            content = info['entry'].get().strip()
            if not content:
                return
            plan_id = database.add_plan(self.date_str, content)
            info['plan_id'] = plan_id
            info['original'] = content
            self._notify_change()

        def on_time_selected(time_str):
            database.update_plan_alarm(info['plan_id'], time_str)
            info['alarm_time'] = time_str
            color = "#F59E0B" if time_str else "#4B5563"
            info['alarm_btn'].configure(text_color=color)

        ClockPickerDialog(self, on_select=on_time_selected,
                          initial_time=info.get('alarm_time'))

    def _notify_change(self):
        if self.on_change:
            self.on_change()

    def _open_file(self, path):
        import os
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)


import sys
