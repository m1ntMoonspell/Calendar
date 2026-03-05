"""
iOS风格 Windows 桌面助手 — 入口
"""

import sys
import os

# 确保模块路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database


def main():
    # 初始化数据库
    database.init_db()

    # 尝试使用 tkinterdnd2 增强版
    try:
        import tkinterdnd2
        # 设置 tkinterdnd2 的 DLL 路径（如果是独立安装）
        os.environ['TKDND_LIBRARY'] = os.path.join(
            os.path.dirname(tkinterdnd2.__file__), 'tkdnd'
        )
    except ImportError:
        print("提示: 未安装 tkinterdnd2，拖拽功能将使用文件选择对话框替代")
        print("安装命令: pip install tkinterdnd2")

    # 创建主应用
    from ui_main import MainApp
    app = MainApp()
    app.mainloop()


if __name__ == '__main__':
    main()
