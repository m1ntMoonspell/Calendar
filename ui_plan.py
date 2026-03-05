"""
计划创建/查看对话框
"""

import customtkinter as ctk
from datetime import datetime
import database


class PlanCreateDialog(ctk.CTkToplevel):
    """创建计划对话框"""

    def __init__(self, parent, date_str, on_save=None):
        super().__init__(parent)
        self.date_str = date_str
        self.on_save = on_save

        self.title(f"📝 创建计划 — {date_str}")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # 窗口居中
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 480) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 520) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

        self._build_ui()

    def _build_ui(self):
        # 标题
        title_label = ctk.CTkLabel(
            self, text=f"📅 {self.date_str} 的计划",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(20, 5))

        hint_label = ctk.CTkLabel(
            self, text="每行输入一个计划步骤",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        hint_label.pack(pady=(0, 10))

        # 文本输入区域
        self.text_input = ctk.CTkTextbox(
            self, width=420, height=350,
            font=ctk.CTkFont(size=14),
            border_width=2,
            border_color="#3B82F6",
            corner_radius=12,
        )
        self.text_input.pack(padx=20, pady=5)

        # 按钮区域
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        cancel_btn = ctk.CTkButton(
            btn_frame, text="取消", width=100,
            fg_color="#6B7280", hover_color="#4B5563",
            corner_radius=10,
            command=self.destroy
        )
        cancel_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(
            btn_frame, text="💾 保存计划", width=150,
            fg_color="#10B981", hover_color="#059669",
            corner_radius=10,
            command=self._save
        )
        save_btn.pack(side="right", padx=5)

    def _save(self):
        content = self.text_input.get("1.0", "end").strip()
        if not content:
            return

        # 逐行保存每个计划步骤
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        for line in lines:
            database.add_plan(self.date_str, line)

        if self.on_save:
            self.on_save()
        self.destroy()


class PlanViewDialog(ctk.CTkToplevel):
    """查看计划和文件的对话框"""

    def __init__(self, parent, date_str):
        super().__init__(parent)
        self.date_str = date_str

        self.title(f"📋 {date_str} 的计划与文件")
        self.geometry("520x600")
        self.resizable(False, True)
        self.transient(parent)
        self.grab_set()

        # 窗口居中
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

        self._build_ui()

    def _build_ui(self):
        # === 计划部分 ===
        plan_label = ctk.CTkLabel(
            self, text="📝 今日计划",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        plan_label.pack(fill="x", padx=20, pady=(15, 5))

        plans = database.get_plans_by_date(self.date_str)
        if plans:
            plan_frame = ctk.CTkScrollableFrame(
                self, height=220,
                corner_radius=12,
                border_width=1,
                border_color="#374151"
            )
            plan_frame.pack(fill="x", padx=20, pady=5)

            for i, plan in enumerate(plans):
                item_frame = ctk.CTkFrame(plan_frame, fg_color="transparent")
                item_frame.pack(fill="x", padx=5, pady=2)

                step_label = ctk.CTkLabel(
                    item_frame,
                    text=f"  {i+1}. {plan['content']}",
                    font=ctk.CTkFont(size=13),
                    anchor="w"
                )
                step_label.pack(side="left", fill="x", expand=True)

                time_label = ctk.CTkLabel(
                    item_frame,
                    text=plan['created_at'].split(' ')[1] if ' ' in plan['created_at'] else '',
                    font=ctk.CTkFont(size=11),
                    text_color="gray",
                    anchor="e"
                )
                time_label.pack(side="right", padx=5)
        else:
            no_plan = ctk.CTkLabel(
                self, text="暂无计划",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            no_plan.pack(padx=20, pady=10)

        # 分割线
        separator = ctk.CTkFrame(self, height=2, fg_color="#374151")
        separator.pack(fill="x", padx=20, pady=10)

        # === 文件部分 ===
        file_label = ctk.CTkLabel(
            self, text="📁 兴趣文件",
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
                    '图片': '🖼️', '文档': '📄', '音频': '🎵',
                    '视频': '🎬', '压缩包': '📦', '代码': '💻', '其他': '📎'
                }.get(f['file_type'], '📎')

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

        # 关闭按钮
        close_btn = ctk.CTkButton(
            self, text="关闭", width=100,
            fg_color="#6B7280", hover_color="#4B5563",
            corner_radius=10,
            command=self.destroy
        )
        close_btn.pack(pady=15)

    def _open_file(self, path):
        import os
        if os.path.exists(path):
            os.startfile(path)
