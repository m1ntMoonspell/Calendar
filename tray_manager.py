"""
系统托盘管理
Windows: 使用 ctypes 调用 Shell_NotifyIconW（最可靠）
Linux/fallback: 使用 pystray
"""

import os
import sys
import threading

TRAY_AVAILABLE = False
_backend = None

# -------- Windows 原生托盘 (ctypes) --------
if sys.platform == 'win32':
    try:
        import ctypes
        import ctypes.wintypes as wintypes

        TRAY_AVAILABLE = True
        _backend = 'win32'
    except Exception:
        pass

# -------- Linux fallback: pystray --------
if not TRAY_AVAILABLE:
    try:
        import pystray
        from PIL import Image
        TRAY_AVAILABLE = True
        _backend = 'pystray'
    except ImportError:
        pass


class TrayManager:

    def __init__(self, on_show=None, on_quit=None):
        self.on_show = on_show
        self.on_quit = on_quit
        self._impl = None

    def start(self):
        if not TRAY_AVAILABLE:
            return
        try:
            if _backend == 'win32':
                self._impl = _Win32Tray(self.on_show, self.on_quit)
            elif _backend == 'pystray':
                self._impl = _PystrayTray(self.on_show, self.on_quit)
            if self._impl:
                self._impl.start()
        except Exception as e:
            print(f"Tray start error: {e}")

    def stop(self):
        if self._impl:
            try:
                self._impl.stop()
            except Exception:
                pass
            self._impl = None


# ============================================================
# Windows 原生托盘实现
# ============================================================
class _Win32Tray:

    WM_TRAYICON = 0x8000 + 1
    WM_COMMAND = 0x0111
    NIM_ADD = 0x00
    NIM_DELETE = 0x02
    NIF_ICON = 0x02
    NIF_MESSAGE = 0x01
    NIF_TIP = 0x04
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    IDM_SHOW = 1001
    IDM_QUIT = 1002

    def __init__(self, on_show, on_quit):
        self.on_show = on_show
        self.on_quit = on_quit
        self._hwnd = None
        self._thread = None
        self._hicon = self._load_icon()

    def _load_icon(self):
        import ctypes
        icon_dir = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(icon_dir, "icon.ico")
        if os.path.exists(ico_path):
            hicon = ctypes.windll.user32.LoadImageW(
                None, ico_path, 1, 0, 0, 0x00000010)
            if hicon:
                return hicon
        return ctypes.windll.user32.LoadIconW(None, 32512)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        import ctypes
        from ctypes import wintypes

        WNDCLASS = ctypes.WNDPROC(self._wnd_proc)
        hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)

        wc = wintypes.WNDCLASSW()
        wc.lpfnWndProc = WNDCLASS
        wc.hInstance = hinstance
        wc.lpszClassName = "DesktopAssistantTray"
        ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))

        self._hwnd = ctypes.windll.user32.CreateWindowExW(
            0, "DesktopAssistantTray", "Tray", 0,
            0, 0, 0, 0, None, None, hinstance, None)

        # NOTIFYICONDATAW
        nid = _make_nid(self._hwnd, self._hicon, self.WM_TRAYICON,
                         "\u684c\u9762\u52a9\u624b")
        ctypes.windll.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(nid))

        msg = wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        import ctypes
        if msg == self.WM_TRAYICON:
            if lparam == self.WM_LBUTTONUP:
                if self.on_show:
                    self.on_show()
            elif lparam == self.WM_RBUTTONUP:
                self._show_menu(hwnd)
        elif msg == self.WM_COMMAND:
            cmd_id = wparam & 0xFFFF
            if cmd_id == self.IDM_SHOW and self.on_show:
                self.on_show()
            elif cmd_id == self.IDM_QUIT and self.on_quit:
                self.on_quit()
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_menu(self, hwnd):
        import ctypes
        from ctypes import wintypes
        hmenu = ctypes.windll.user32.CreatePopupMenu()
        ctypes.windll.user32.AppendMenuW(hmenu, 0, self.IDM_SHOW,
                                          "\u663e\u793a\u7a97\u53e3")
        ctypes.windll.user32.AppendMenuW(hmenu, 0x0800, 0, None)
        ctypes.windll.user32.AppendMenuW(hmenu, 0, self.IDM_QUIT, "\u9000\u51fa")

        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.TrackPopupMenu(
            hmenu, 0, pt.x, pt.y, 0, hwnd, None)
        ctypes.windll.user32.PostMessageW(hwnd, 0, 0, 0)

    def stop(self):
        if self._hwnd:
            import ctypes
            nid = _make_nid(self._hwnd, 0, 0, "")
            ctypes.windll.shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(nid))
            ctypes.windll.user32.PostMessageW(self._hwnd, 0x0012, 0, 0)


def _make_nid(hwnd, hicon, callback_msg, tip):
    """构造 NOTIFYICONDATAW 结构"""
    import ctypes
    from ctypes import wintypes

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", ctypes.c_wchar * 128),
        ]

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    flags = 0
    if hicon:
        flags |= 0x02
    if callback_msg:
        flags |= 0x01
    if tip:
        flags |= 0x04
    nid.uFlags = flags
    nid.uCallbackMessage = callback_msg
    nid.hIcon = hicon
    nid.szTip = tip[:127]
    return nid


# ============================================================
# Pystray fallback (Linux)
# ============================================================
class _PystrayTray:

    def __init__(self, on_show, on_quit):
        self.on_show = on_show
        self.on_quit = on_quit
        self._icon = None

    def start(self):
        from PIL import Image
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            img = Image.open(icon_path).convert('RGBA').resize((64, 64))
        else:
            img = Image.new('RGBA', (64, 64), (68, 68, 68, 255))

        import pystray
        self._icon = pystray.Icon(
            "desktop_assistant", img, "\u684c\u9762\u52a9\u624b",
            pystray.Menu(
                pystray.MenuItem("\u663e\u793a\u7a97\u53e3", lambda: self.on_show() if self.on_show else None, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("\u9000\u51fa", lambda: self.on_quit() if self.on_quit else None),
            ))
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
