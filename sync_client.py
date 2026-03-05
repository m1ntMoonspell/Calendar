"""
云端同步客户端
从云端服务器拉取计划和文件数据，合并到本地 SQLite 数据库
在桌面日历启动时调用

用法:
    from sync_client import sync_from_cloud
    sync_from_cloud()  # 启动时同步
"""

import json
import os
import threading
import requests

import database
from ui_settings import get_config, set_config

SYNC_CONFIG_KEYS = {
    "sync_enabled": False,
    "sync_server_url": "http://127.0.0.1:5000",
    "sync_api_key": "change-me-to-a-secure-key",
}


def get_sync_config():
    cfg = {}
    for key, default in SYNC_CONFIG_KEYS.items():
        cfg[key] = get_config(key, default)
    return cfg


def _api_headers(api_key):
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def pull_from_cloud(server_url, api_key):
    """
    从云端拉取全部计划和文件数据
    返回 (plans_list, files_list) 或 None
    """
    try:
        resp = requests.get(
            f"{server_url}/api/sync/pull",
            headers=_api_headers(api_key),
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("plans", []), data.get("files", [])
    except Exception as e:
        print(f"Sync pull error: {e}")
    return None


def push_to_cloud(server_url, api_key):
    """
    将本地计划推送到云端
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plans ORDER BY date, created_at")
        rows = cursor.fetchall()
        conn.close()

        plans = []
        for r in rows:
            plans.append({
                "date": r["date"],
                "content": r["content"],
                "alarm_time": r["alarm_time"],
                "created_at": r["created_at"],
            })

        resp = requests.post(
            f"{server_url}/api/sync/push",
            json={"plans": plans},
            headers=_api_headers(api_key),
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Sync push error: {e}")
    return None


def merge_plans(remote_plans):
    """
    将云端计划合并到本地数据库（去重：按 date+content 判断）
    返回新增数量
    """
    added = 0
    conn = database.get_connection()
    cursor = conn.cursor()

    for p in remote_plans:
        existing = cursor.execute(
            "SELECT id FROM plans WHERE date=? AND content=?",
            (p["date"], p["content"])
        ).fetchone()
        if not existing:
            cursor.execute(
                "INSERT INTO plans (date, content, created_at, alarm_time) VALUES (?,?,?,?)",
                (p["date"], p["content"],
                 p.get("created_at", ""),
                 p.get("alarm_time"))
            )
            added += 1

    conn.commit()
    conn.close()
    return added


def merge_files(remote_files):
    """
    将云端文件记录合并到本地数据库（去重：按 date+original_name 判断）
    返回新增数量
    """
    added = 0
    conn = database.get_connection()
    cursor = conn.cursor()

    for f in remote_files:
        existing = cursor.execute(
            "SELECT id FROM saved_files WHERE date=? AND original_name=?",
            (f["date"], f["original_name"])
        ).fetchone()
        if not existing:
            saved_path = f.get("file_url") or f.get("saved_name", "")
            cursor.execute(
                "INSERT INTO saved_files (original_name, saved_path, file_type, date, saved_at) VALUES (?,?,?,?,?)",
                (f["original_name"], saved_path, f.get("file_type", "其他"),
                 f["date"], f.get("saved_at", ""))
            )
            added += 1

    conn.commit()
    conn.close()
    return added


def sync_from_cloud(callback=None):
    """
    从云端同步数据到本地（在后台线程执行）
    callback(success: bool, message: str) 会在完成时被调用
    """
    cfg = get_sync_config()
    if not cfg["sync_enabled"]:
        if callback:
            callback(False, "同步未启用")
        return

    def _do_sync():
        server_url = cfg["sync_server_url"].rstrip("/")
        api_key = cfg["sync_api_key"]

        result = pull_from_cloud(server_url, api_key)
        if result is None:
            if callback:
                callback(False, "无法连接云端服务器")
            return

        plans, files = result
        new_plans = merge_plans(plans)
        new_files = merge_files(files)

        push_to_cloud(server_url, api_key)

        msg = f"同步完成：新增 {new_plans} 条计划"
        if new_files:
            msg += f"，{new_files} 个文件记录"
        print(f"☁️ {msg}")
        if callback:
            callback(True, msg)

    thread = threading.Thread(target=_do_sync, daemon=True)
    thread.start()


if __name__ == "__main__":
    database.init_db()
    cfg = get_sync_config()
    print(f"同步服务器: {cfg['sync_server_url']}")
    print(f"同步启用: {cfg['sync_enabled']}")

    if cfg["sync_enabled"]:
        result = pull_from_cloud(cfg["sync_server_url"], cfg["sync_api_key"])
        if result:
            plans, files = result
            new_plans = merge_plans(plans)
            new_files = merge_files(files)
            print(f"✅ 新增 {new_plans} 条计划，{new_files} 个文件记录")

            push_result = push_to_cloud(cfg["sync_server_url"], cfg["sync_api_key"])
            if push_result:
                print(f"✅ {push_result.get('message', '推送完成')}")
        else:
            print("❌ 同步失败")
    else:
        print("提示: 在 .config.json 中设置 sync_enabled=true 以启用同步")
