"""
兴趣文件浏览对话框
按日期和文件类型分组展示所有已保存的文件
"""

import os
import customtkinter as ctk
import database
from file_manager import get_saved_files_tree


class FileViewerDialog(ctk.CTkToplevel):
    """文件浏览器对话框"""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("📁 兴趣文件浏览器")
        self.geometry("600x650")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # 窗口居中
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 600) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 650) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

        self._build_ui()

    def _build_ui(self):
        # 标题
        title = ctk.CTkLabel(
            self, text="📁 兴趣文件浏览器",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(15, 10))

        # 文件树形列表
        tree = get_saved_files_tree()
        if not tree:
            no_data = ctk.CTkLabel(
                self, text="还没有保存任何文件\n拖拽文件到主界面即可保存",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_data.pack(expand=True)
            return

        scroll_frame = ctk.CTkScrollableFrame(
            self, corner_radius=12,
            border_width=1,
            border_color="#374151"
        )
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        type_emoji = {
            '图片': '🖼️', '文档': '📄', '音频': '🎵',
            '视频': '🎬', '压缩包': '📦', '代码': '💻', '其他': '📎'
        }

        for date_str in sorted(tree.keys(), reverse=True):
            # 日期标题
            date_frame = ctk.CTkFrame(
                scroll_frame,
                fg_color=("#E5E7EB", "#1F2937"),
                corner_radius=10
            )
            date_frame.pack(fill="x", padx=5, pady=(10, 3))

            date_label = ctk.CTkLabel(
                date_frame,
                text=f"  📅 {date_str}",
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w"
            )
            date_label.pack(fill="x", padx=10, pady=8)

            types = tree[date_str]
            for file_type in sorted(types.keys()):
                files = types[file_type]
                emoji = type_emoji.get(file_type, '📎')

                # 类型标题
                type_label = ctk.CTkLabel(
                    scroll_frame,
                    text=f"    {emoji} {file_type} ({len(files)}个)",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color="#60A5FA",
                    anchor="w"
                )
                type_label.pack(fill="x", padx=15, pady=(5, 2))

                # 文件列表
                for f in files:
                    file_row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
                    file_row.pack(fill="x", padx=25, pady=1)

                    name_label = ctk.CTkLabel(
                        file_row,
                        text=f"• {f['original_name']}",
                        font=ctk.CTkFont(size=12),
                        anchor="w"
                    )
                    name_label.pack(side="left", fill="x", expand=True)

                    time_label = ctk.CTkLabel(
                        file_row,
                        text=f['saved_at'].split(' ')[1] if ' ' in f['saved_at'] else '',
                        font=ctk.CTkFont(size=10),
                        text_color="gray"
                    )
                    time_label.pack(side="right", padx=(5, 2))

                    open_btn = ctk.CTkButton(
                        file_row, text="打开", width=45, height=22,
                        font=ctk.CTkFont(size=10),
                        fg_color="#3B82F6", hover_color="#2563EB",
                        corner_radius=6,
                        command=lambda p=f['saved_path']: self._open_file(p)
                    )
                    open_btn.pack(side="right", padx=2)

        # 关闭按钮
        close_btn = ctk.CTkButton(
            self, text="关闭", width=120,
            fg_color="#6B7280", hover_color="#4B5563",
            corner_radius=10,
            command=self.destroy
        )
        close_btn.pack(pady=12)

    def _open_file(self, path):
        if os.path.exists(path):
            os.startfile(path)
