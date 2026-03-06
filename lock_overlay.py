"""
PySide6 锁定覆盖窗口
参考 H75helper 的 holiday_float.py 实现方案:
- 使用 Qt.WA_TranslucentBackground 实现真正的逐像素 Alpha 透明
- 无色键(transparentcolor)，无文字描边，无圆角黑边
- 独立进程运行，通过命令行参数传入内容

用法 (由 ui_main.py 自动调用):
  python lock_overlay.py --x 100 --y 100 --w 360 --h 460
"""

import sys
import os
import json
from datetime import datetime, date, timedelta

if sys.platform != 'win32' and 'QT_QPA_PLATFORM' not in os.environ:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                                QHBoxLayout, QPushButton, QSizeGrip)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPainterPath, QMouseEvent


# ──── 节假日数据（内联简化版，避免依赖主程序模块）────

def _load_holiday_data():
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
    year = date.today().year
    cache_file = os.path.join(cache_dir, f"{year}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _get_next_holiday():
    data = _load_holiday_data()
    if not data or 'days' not in data:
        return None

    from collections import defaultdict
    today = date.today()
    groups = defaultdict(list)
    for day in data['days']:
        if day.get('isOffDay', False):
            d = date.fromisoformat(day['date'])
            groups[day['name']].append(d)

    holidays = []
    for name, dates in groups.items():
        dates.sort()
        if dates and dates[0] >= today:
            holidays.append({'name': name, 'start': dates[0], 'days_off': len(dates)})

    holidays.sort(key=lambda h: h['start'])
    return holidays[0] if holidays else None


def _get_countdown():
    now = datetime.now()
    holiday = _get_next_holiday()
    if not holiday:
        return None
    start = datetime(holiday['start'].year, holiday['start'].month, holiday['start'].day)
    delta = start - now
    if delta.total_seconds() < 0:
        return None
    total = int(delta.total_seconds())
    days = total // 86400
    hours = (total % 86400) // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return {
        'name': holiday['name'], 'days': days,
        'hours': hours, 'minutes': minutes, 'seconds': seconds,
        'days_off': holiday['days_off'],
    }


WEEKDAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']


# ──── 覆盖窗口 ────

class LockOverlay(QWidget):

    def __init__(self, x=0, y=0, w=360, h=460):
        super().__init__()

        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.95)
        self.setGeometry(x, y, w, h)
        self.setMinimumSize(280, 360)

        self.is_locked = True
        self._drag_pos = None

        self._build_ui()
        self._update_countdown()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_countdown)
        self._timer.start(1000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.bg_widget = QWidget(self)
        self.bg_widget.setObjectName("floatBg")
        self.bg_widget.setStyleSheet(
            "QWidget#floatBg { background-color: transparent; border: none; }")
        layout.addWidget(self.bg_widget)

        bg_layout = QVBoxLayout(self.bg_widget)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)

        # ── 标题栏 ──
        header = QWidget()
        header.setFixedHeight(34)
        header.setStyleSheet("background-color: rgba(22,22,42,200); border: none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 4, 0)

        btn_style = ("QPushButton { color: #9CA3AF; background: transparent; "
                     "border: none; font-size: 13px; padding: 2px 6px; border-radius: 4px; }"
                     "QPushButton:hover { background: #374151; }")

        self.btn_lock = QPushButton("🔓 解锁")
        self.btn_lock.setStyleSheet(
            btn_style.replace("#9CA3AF", "#EF4444").replace("#374151", "#7F1D1D"))
        self.btn_lock.clicked.connect(self._unlock)
        header_layout.addWidget(self.btn_lock)

        header_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setStyleSheet(btn_style.replace("#374151", "#EF4444"))
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)

        bg_layout.addWidget(header)

        # ── 内容区 ──
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(15, 8, 15, 10)
        content_layout.setSpacing(0)

        font_normal = QFont("Microsoft YaHei", 13)
        font_date = QFont("Microsoft YaHei", 15)
        font_date.setBold(True)
        font_days = QFont("Microsoft YaHei", 58)
        font_days.setBold(True)
        font_unit = QFont("Microsoft YaHei", 18)
        font_unit.setBold(True)
        font_time = QFont("Consolas", 22)
        font_time.setBold(True)

        label_style = "color: {color}; background: transparent;"

        self.date_label = QLabel()
        self.date_label.setFont(font_date)
        self.date_label.setStyleSheet(label_style.format(color="#E5E7EB"))
        self.date_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.date_label)

        self.holiday_label = QLabel()
        self.holiday_label.setFont(font_normal)
        self.holiday_label.setStyleSheet(label_style.format(color="#9CA3AF"))
        self.holiday_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.holiday_label)

        self.days_label = QLabel("--")
        self.days_label.setFont(font_days)
        self.days_label.setStyleSheet(label_style.format(color="#EF4444"))
        self.days_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.days_label)

        self.unit_label = QLabel("天")
        self.unit_label.setFont(font_unit)
        self.unit_label.setStyleSheet(label_style.format(color="#EF4444"))
        self.unit_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.unit_label)

        self.time_label = QLabel("--:--:--")
        self.time_label.setFont(font_time)
        self.time_label.setStyleSheet(label_style.format(color="#9CA3AF"))
        self.time_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.time_label)

        self.off_label = QLabel()
        self.off_label.setFont(font_normal)
        self.off_label.setStyleSheet(label_style.format(color="#34D399"))
        self.off_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.off_label)

        content_layout.addStretch()
        bg_layout.addWidget(self.content_widget, 1)

    def _update_countdown(self):
        today = date.today()
        wd = WEEKDAY_NAMES[today.weekday()]
        self.date_label.setText(f"{today.year}年{today.month}月{today.day}日 {wd}")

        info = _get_countdown()
        if info:
            self.holiday_label.setText(f"距{info['name']}还有：")
            self.days_label.setText(str(info['days']))
            self.time_label.setText(
                f"{info['hours']:02d}:{info['minutes']:02d}:{info['seconds']:02d}")
            self.off_label.setText(f"🎉 放假 {info['days_off']} 天")
        else:
            self.holiday_label.setText("暂无节假日信息")
            self.days_label.setText("--")
            self.time_label.setText("--:--:--")
            self.off_label.setText("")

    def _unlock(self):
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        painter.fillPath(path, QBrush(QColor(30, 30, 46, 1)))
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', type=int, default=100)
    parser.add_argument('--y', type=int, default=100)
    parser.add_argument('--w', type=int, default=360)
    parser.add_argument('--h', type=int, default=460)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    overlay = LockOverlay(args.x, args.y, args.w, args.h)
    overlay.show()
    sys.exit(app.exec())
