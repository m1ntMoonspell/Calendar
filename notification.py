"""
PySide6 消息通知弹窗
在屏幕右下角显示计划提醒，自动淡出关闭
独立进程运行，通过命令行参数传入内容
"""

import sys
import os

# 确保 Qt 平台插件可用（Linux 无图形环境时回退到 offscreen）
if sys.platform != 'win32' and 'QT_QPA_PLATFORM' not in os.environ:
    os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen, QPainterPath, QIcon


class NotificationPopup(QWidget):
    """右下角通知弹窗"""

    def __init__(self, title, message, duration=6000):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 120)

        self._build_ui(title, message)
        self._position_bottom_right()

        QTimer.singleShot(duration, self._fade_out)

    def _build_ui(self, title, message):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)

        header = QHBoxLayout()
        icon_label = QLabel("\u23f0")
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        icon_label.setStyleSheet("color: #EF4444; background: transparent;")
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        title_label.setStyleSheet("color: #E5E7EB; background: transparent;")
        header.addWidget(title_label, 1)

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton { color: #9CA3AF; background: transparent; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #EF4444; }"
        )
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        msg_label = QLabel(message)
        msg_label.setFont(QFont("Microsoft YaHei", 12))
        msg_label.setStyleSheet("color: #D1D5DB; background: transparent;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 16
        y = screen.bottom() - self.height() - 16
        self.move(x, y)

    def _fade_out(self):
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(800)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.finished.connect(self.close)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        painter.fillPath(path, QBrush(QColor("#1E1E2E")))
        painter.setPen(QPen(QColor("#374151"), 1))
        painter.drawPath(path)


def show_notification(title, message):
    """供外部调用：在独立进程中显示通知"""
    import subprocess
    script_path = os.path.abspath(__file__)
    subprocess.Popen(
        [sys.executable, script_path, title, message],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == '__main__':
    title = sys.argv[1] if len(sys.argv) > 1 else "\u8ba1\u5212\u63d0\u9192"
    message = sys.argv[2] if len(sys.argv) > 2 else "\u4f60\u6709\u4e00\u6761\u8ba1\u5212\u5230\u671f\u4e86"

    app = QApplication(sys.argv)
    popup = NotificationPopup(title, message)
    popup.show()
    sys.exit(app.exec())
