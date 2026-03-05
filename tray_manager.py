"""
系统托盘管理
使用 pystray 在后台线程中运行托盘图标
"""

import os
import sys
import threading

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


class TrayManager:
    """系统托盘管理器"""

    def __init__(self, on_show=None, on_quit=None):
        self.on_show = on_show
        self.on_quit = on_quit
        self._icon = None
        self._thread = None

        self._image = self._load_icon()

    def _load_icon(self):
        if not TRAY_AVAILABLE:
            return None
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        return Image.new('RGBA', (32, 32), (30, 30, 46, 255))

    def start(self):
        if not TRAY_AVAILABLE or self._icon is not None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("\u663e\u793a\u7a97\u53e3", self._on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("\u9000\u51fa", self._on_quit),
        )

        self._icon = pystray.Icon(
            "desktop_assistant",
            self._image,
            "\u684c\u9762\u52a9\u624b",
            menu,
        )

        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._icon:
            self._icon.stop()
            self._icon = None

    def _on_show(self, icon=None, item=None):
        if self.on_show:
            self.on_show()

    def _on_quit(self, icon=None, item=None):
        if self.on_quit:
            self.on_quit()
