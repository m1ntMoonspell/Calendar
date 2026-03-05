"""
iOS风格 Windows 桌面助手 — 入口
"""

import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database


def _check_alarms(app):
    """每 30 秒检查一次到期闹钟"""
    try:
        now = datetime.now()
        date_str = now.date().isoformat()
        time_str = now.strftime("%H:%M")
        due = database.get_due_alarms(date_str, time_str)
        for plan in due:
            _fire_notification(plan['content'])
            database.clear_alarm(plan['id'])
    except Exception as e:
        print(f"Alarm check error: {e}")

    app.after(30000, lambda: _check_alarms(app))


def _fire_notification(message):
    """通过 PySide6 独立进程弹出通知"""
    try:
        from notification import show_notification
        show_notification("\u23f0 计划提醒", message)
    except Exception as e:
        print(f"Notification error: {e}")


def main():
    database.init_db()

    try:
        from sync_client import sync_from_cloud
        sync_from_cloud()
    except Exception as e:
        print(f"Sync init: {e}")

    try:
        import tkinterdnd2
        os.environ['TKDND_LIBRARY'] = os.path.join(
            os.path.dirname(tkinterdnd2.__file__), 'tkdnd'
        )
    except ImportError:
        pass

    from ui_main import MainApp
    app = MainApp()

    # 系统托盘
    try:
        from tray_manager import TrayManager, TRAY_AVAILABLE
        if TRAY_AVAILABLE:
            tray = TrayManager(
                on_show=lambda: app.after(0, app.show_from_tray),
                on_quit=lambda: app.after(0, app.quit_app),
            )
            app.tray = tray
            tray.start()
    except Exception as e:
        print(f"Tray init error: {e}")

    # 启动闹钟检查器
    app.after(5000, lambda: _check_alarms(app))

    app.mainloop()


if __name__ == '__main__':
    main()
