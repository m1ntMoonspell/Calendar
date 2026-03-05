"""
计划查看/编辑对话框
双击日期打开后可直接新建和编辑计划（单行输入，回车确认并新增下一行）
"""

import customtkinter as ctk
import database


class PlanViewDialog(ctk.CTkToplevel):
    """查看、新建、编辑计划和文件的对话框"""

    def __init__(self, parent, date_str, on_change=None):
        super().__init__(parent)
        self.date_str = date_str
        self.on_change = on_change

        self.title(f"\U0001f4cb {date_str} 的计划与文件")
        self.geometry("520x600")
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

        self._entries = []
        self._build_ui()

    def _build_ui(self):
        # === 计划部分 ===
        plan_label = ctk.CTkLabel(
            self, text="\U0001f4dd 今日计划",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        plan_label.pack(fill="x", padx=20, pady=(15, 5))

        self.plan_frame = ctk.CTkScrollableFrame(
            self, height=220,
            corner_radius=12,
            border_width=1,
            border_color="#374151"
        )
        self.plan_frame.pack(fill="x", padx=20, pady=5)

        plans = database.get_plans_by_date(self.date_str)
        for plan in plans:
            self._add_entry(plan_id=plan['id'], content=plan['content'])
        self._add_entry()

        # 分割线
        separator = ctk.CTkFrame(self, height=2, fg_color="#374151")
        separator.pack(fill="x", padx=20, pady=10)

        # === 文件部分 ===
        file_label = ctk.CTkLabel(
            self, text="\U0001f4c1 兴趣文件",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        file_label.pack(fill="x", padx=20, pady=(5, 5))

        files = database.get_files_by_date(self.date_str)
        if files:
            file_frame = ctk.CTkScrollableFrame(
                self, height=220,
                corner_radius=12,
                border_width=1,
                border_color="#374151"
            )
            file_frame.pack(fill="x", padx=20, pady=5)

            for f in files:
                row = ctk.CTkFrame(file_frame, fg_color="transparent")
                row.pack(fill="x", padx=5, pady=2)

                type_emoji = {
                    '图片': '\U0001f5bc\ufe0f', '文档': '\U0001f4c4',
                    '音频': '\U0001f3b5', '视频': '\U0001f3ac',
                    '压缩包': '\U0001f4e6', '代码': '\U0001f4bb', '其他': '\U0001f4ce'
                }.get(f['file_type'], '\U0001f4ce')

                name_label = ctk.CTkLabel(
                    row,
                    text=f"  {type_emoji} {f['original_name']}",
                    font=ctk.CTkFont(size=13),
                    anchor="w"
                )
                name_label.pack(side="left", fill="x", expand=True)

                open_btn = ctk.CTkButton(
                    row, text="打开", width=50, height=24,
                    font=ctk.CTkFont(size=11),
                    fg_color="#3B82F6", hover_color="#2563EB",
                    corner_radius=6,
                    command=lambda p=f['saved_path']: self._open_file(p)
                )
                open_btn.pack(side="right", padx=5)
        else:
            no_file = ctk.CTkLabel(
                self, text="暂无文件",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            no_file.pack(padx=20, pady=10)

        close_btn = ctk.CTkButton(
            self, text="关闭", width=100,
            fg_color="#6B7280", hover_color="#4B5563",
            corner_radius=10,
            command=self.destroy
        )
        close_btn.pack(pady=15)

    def _add_entry(self, plan_id=None, content=""):
        """添加一个计划输入行"""
        row = ctk.CTkFrame(self.plan_frame, fg_color="transparent")
        row.pack(fill="x", padx=5, pady=2)

        idx = len(self._entries) + 1
        num_label = ctk.CTkLabel(
            row, text=f"{idx}.",
            font=ctk.CTkFont(size=13),
            width=28, anchor="e"
        )
        num_label.pack(side="left", padx=(0, 5))

        entry = ctk.CTkEntry(
            row,
            font=ctk.CTkFont(size=13),
            height=32,
            border_width=1,
            border_color="#374151",
            corner_radius=6,
            placeholder_text="输入计划，回车确认..."
        )
        entry.pack(side="left", fill="x", expand=True)

        if content:
            entry.insert(0, content)

        info = {
            'plan_id': plan_id,
            'entry': entry,
            'row': row,
            'original': content,
        }
        self._entries.append(info)

        entry.bind('<Return>', lambda e, i=info: self._on_enter(i))

        if not content:
            self.after(100, entry.focus_set)

        return info

    def _on_enter(self, info):
        """回车键处理：保存/更新计划，创建新行"""
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

    def _notify_change(self):
        if self.on_change:
            self.on_change()

    def _open_file(self, path):
        import os
        if os.path.exists(path):
            os.startfile(path)
