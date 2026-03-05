"""
中国法定节假日数据模块
使用 NateScarlet/holiday-cn GitHub 仓库的 JSON 数据
"""

import json
import os
import requests
from datetime import datetime, date, timedelta
from collections import defaultdict

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

# CDN 地址
CDN_URLS = [
    "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json",
    "https://fastly.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json",
    "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json",
]

# 内置 fallback 数据（2026年），以防网络不可用
FALLBACK_2026 = {
    "year": 2026,
    "days": [
        {"name": "元旦", "date": "2026-01-01", "isOffDay": True},
        {"name": "元旦", "date": "2026-01-02", "isOffDay": True},
        {"name": "元旦", "date": "2026-01-03", "isOffDay": True},
        {"name": "元旦", "date": "2026-01-04", "isOffDay": False},
        {"name": "春节", "date": "2026-02-14", "isOffDay": False},
        {"name": "春节", "date": "2026-02-15", "isOffDay": True},
        {"name": "春节", "date": "2026-02-16", "isOffDay": True},
        {"name": "春节", "date": "2026-02-17", "isOffDay": True},
        {"name": "春节", "date": "2026-02-18", "isOffDay": True},
        {"name": "春节", "date": "2026-02-19", "isOffDay": True},
        {"name": "春节", "date": "2026-02-20", "isOffDay": True},
        {"name": "春节", "date": "2026-02-21", "isOffDay": True},
        {"name": "春节", "date": "2026-02-22", "isOffDay": True},
        {"name": "春节", "date": "2026-02-23", "isOffDay": True},
        {"name": "春节", "date": "2026-02-28", "isOffDay": False},
        {"name": "清明节", "date": "2026-04-04", "isOffDay": True},
        {"name": "清明节", "date": "2026-04-05", "isOffDay": True},
        {"name": "清明节", "date": "2026-04-06", "isOffDay": True},
        {"name": "劳动节", "date": "2026-05-01", "isOffDay": True},
        {"name": "劳动节", "date": "2026-05-02", "isOffDay": True},
        {"name": "劳动节", "date": "2026-05-03", "isOffDay": True},
        {"name": "劳动节", "date": "2026-05-04", "isOffDay": True},
        {"name": "劳动节", "date": "2026-05-05", "isOffDay": True},
        {"name": "劳动节", "date": "2026-05-09", "isOffDay": False},
        {"name": "端午节", "date": "2026-06-19", "isOffDay": True},
        {"name": "端午节", "date": "2026-06-20", "isOffDay": True},
        {"name": "端午节", "date": "2026-06-21", "isOffDay": True},
        {"name": "中秋节", "date": "2026-09-25", "isOffDay": True},
        {"name": "中秋节", "date": "2026-09-26", "isOffDay": True},
        {"name": "中秋节", "date": "2026-09-27", "isOffDay": True},
        {"name": "国庆节", "date": "2026-09-27", "isOffDay": False},
        {"name": "国庆节", "date": "2026-10-01", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-02", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-03", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-04", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-05", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-06", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-07", "isOffDay": True},
        {"name": "国庆节", "date": "2026-10-10", "isOffDay": False},
    ]
}


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(year):
    return os.path.join(CACHE_DIR, f"{year}.json")


def _fetch_year_data(year):
    """从网络获取指定年份的节假日数据"""
    for url_template in CDN_URLS:
        url = url_template.format(year=year)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # 缓存到本地
                _ensure_cache_dir()
                with open(_cache_path(year), 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
        except Exception:
            continue
    return None


def _load_year_data(year):
    """加载指定年份的节假日数据（优先缓存 -> 网络 -> fallback）"""
    # 1. 尝试读取缓存
    cache_file = _cache_path(year)
    if os.path.exists(cache_file):
        try:
            # 如果缓存超过7天，尝试刷新
            mtime = os.path.getmtime(cache_file)
            age_days = (datetime.now().timestamp() - mtime) / 86400
            if age_days < 7:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

    # 2. 尝试从网络获取
    data = _fetch_year_data(year)
    if data:
        return data

    # 3. 尝试读取旧缓存
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    # 4. Fallback
    if year == 2026:
        return FALLBACK_2026
    return None


def _parse_holidays(data):
    """
    解析节假日数据，返回按节日名称分组的假期信息列表
    每项: { 'name': str, 'start_date': date, 'days_off': int, 'off_dates': [date,...] }
    """
    if not data or 'days' not in data:
        return []

    # 按名称分组，只统计 isOffDay=True 的天
    groups = defaultdict(list)
    for day in data['days']:
        if day.get('isOffDay', False):
            d = date.fromisoformat(day['date'])
            groups[day['name']].append(d)

    holidays = []
    for name, dates in groups.items():
        dates.sort()
        if dates:
            holidays.append({
                'name': name,
                'start_date': dates[0],
                'end_date': dates[-1],
                'days_off': len(dates),
                'off_dates': dates,
            })

    holidays.sort(key=lambda h: h['start_date'])
    return holidays


def get_all_holidays_for_year(year):
    """获取某年所有节假日信息"""
    data = _load_year_data(year)
    return _parse_holidays(data)


def get_next_holiday(today=None):
    """
    获取距离今天最近的下一个法定节假日
    返回: { 'name': str, 'start_date': date, 'days_off': int } 或 None
    """
    if today is None:
        today = date.today()

    # 检查今年和明年
    for year in [today.year, today.year + 1]:
        holidays = get_all_holidays_for_year(year)
        for h in holidays:
            # 假期还没开始，或假期正在进行中
            if h['start_date'] >= today:
                return h

    return None


def get_holiday_countdown(now=None):
    """
    获取到下一个节假日的倒计时信息
    返回: {
        'name': str,          # 节假日名称
        'days': int,          # 剩余天数
        'hours': int,         # 剩余小时
        'minutes': int,       # 剩余分钟
        'seconds': int,       # 剩余秒
        'days_off': int,      # 放假天数
        'start_date': date,   # 开始日期
    } 或 None
    """
    if now is None:
        now = datetime.now()

    holiday = get_next_holiday(now.date())
    if not holiday:
        return None

    # 计算到假期开始的时间差
    holiday_start = datetime(
        holiday['start_date'].year,
        holiday['start_date'].month,
        holiday['start_date'].day,
        0, 0, 0
    )

    delta = holiday_start - now
    if delta.total_seconds() < 0:
        # 假期已经开始，找下一个
        next_h = get_next_holiday(holiday['end_date'] + timedelta(days=1))
        if next_h:
            holiday = next_h
            holiday_start = datetime(
                holiday['start_date'].year,
                holiday['start_date'].month,
                holiday['start_date'].day,
                0, 0, 0
            )
            delta = holiday_start - now
        else:
            return None

    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    remaining = total_seconds % 86400
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    seconds = remaining % 60

    return {
        'name': holiday['name'],
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'days_off': holiday['days_off'],
        'start_date': holiday['start_date'],
    }


if __name__ == '__main__':
    info = get_holiday_countdown()
    if info:
        print(f"距{info['name']}还有: {info['days']}天 {info['hours']:02d}:{info['minutes']:02d}:{info['seconds']:02d}")
        print(f"放假 {info['days_off']} 天")
    else:
        print("暂无节假日数据")
