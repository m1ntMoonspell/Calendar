"""
SQLite 数据层
管理每日计划和兴趣文件记录
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistant.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            date TEXT NOT NULL,
            saved_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_plan(date_str, content):
    """添加一条计划，返回新计划的 id"""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO plans (date, content, created_at) VALUES (?, ?, ?)",
        (date_str, content, created_at)
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id


def update_plan(plan_id, content):
    """更新一条计划的内容"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE plans SET content = ? WHERE id = ?",
        (content, plan_id)
    )
    conn.commit()
    conn.close()


def get_plans_by_date(date_str):
    """获取某天的所有计划"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM plans WHERE date = ? ORDER BY created_at",
        (date_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_plan(plan_id):
    """删除一条计划"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()


def add_file_record(original_name, saved_path, file_type, date_str):
    """添加文件保存记录"""
    conn = get_connection()
    cursor = conn.cursor()
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO saved_files (original_name, saved_path, file_type, date, saved_at) VALUES (?, ?, ?, ?, ?)",
        (original_name, saved_path, file_type, date_str, saved_at)
    )
    conn.commit()
    conn.close()


def get_files_by_date(date_str):
    """获取某天的所有保存文件"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM saved_files WHERE date = ? ORDER BY saved_at",
        (date_str,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_files():
    """获取所有保存文件"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM saved_files ORDER BY date DESC, file_type, saved_at")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dates_with_plans():
    """获取所有有计划的日期集合"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM plans")
    rows = cursor.fetchall()
    conn.close()
    return set(r['date'] for r in rows)


def get_dates_with_files():
    """获取所有有保存文件的日期集合"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM saved_files")
    rows = cursor.fetchall()
    conn.close()
    return set(r['date'] for r in rows)
