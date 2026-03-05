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
        icon_dir = os.path.dirname(os.path.abspath(__file__))

        # 尝试加载 icon.png 并转换为 ICO 兼容格式
        for name in ("icon.png", "icon.ico"):
            path = os.path.join(icon_dir, name)
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    # pystray 在 Windows 上需要 ICO 格式内部结构
                    # 确保图标是正确尺寸的 RGBA 图片
                    img = img.convert('RGBA')
                    # Windows 托盘图标最佳尺寸为 64x64 或 32x32
                    if img.width > 64 or img.height > 64:
                        img = img.resize((64, 64), Image.LANCZOS)
                    return img
                except Exception as e:
                    print(f"Load icon {name} error: {e}")

        return Image.new('RGBA', (64, 64), (68, 68, 68, 255))

    def start(self):
        if not TRAY_AVAILABLE or self._icon is not None:
            return
        if self._image is None:
            return

        try:
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

            self._thread = threading.Thread(target=self._run_icon, daemon=True)
            self._thread.start()
        except Exception as e:
            print(f"Tray start error: {e}")

    def _run_icon(self):
        try:
            self._icon.run()
        except Exception as e:
            print(f"Tray run error: {e}")

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def _on_show(self, icon=None, item=None):
        if self.on_show:
            self.on_show()

    def _on_quit(self, icon=None, item=None):
        if self.on_quit:
            self.on_quit()
