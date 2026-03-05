"""
云端同步服务器
提供 REST API 供 QQ 机器人写入数据、桌面日历客户端拉取数据
使用 Flask + SQLite，可部署到任意云服务器

启动: python sync_server.py
默认监听: 0.0.0.0:5000
"""

import os
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, g
import sqlite3

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync.db")
API_KEY = os.environ.get("SYNC_API_KEY", "change-me-to-a-secure-key")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


# ──────────────── 数据库 ────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            alarm_time TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            saved_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            date TEXT NOT NULL,
            file_url TEXT,
            saved_at TEXT NOT NULL,
            deleted INTEGER DEFAULT 0
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_plans_date ON plans(date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_files_date ON files(date)")
    conn.commit()
    conn.close()
    os.makedirs(UPLOAD_DIR, exist_ok=True)


# ──────────────── 鉴权 ────────────────

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key != API_KEY:
            return jsonify({"error": "无效的 API Key"}), 401
        return f(*args, **kwargs)
    return decorated


# ──────────────── 计划 API ────────────────

@app.route("/api/plans", methods=["POST"])
@require_api_key
def add_plan():
    data = request.get_json(force=True)
    date_str = data.get("date")
    content = data.get("content", "").strip()
    alarm_time = data.get("alarm_time")
    if not date_str or not content:
        return jsonify({"error": "date 和 content 必填"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    cur = db.execute(
        "INSERT INTO plans (date, content, alarm_time, created_at, updated_at) VALUES (?,?,?,?,?)",
        (date_str, content, alarm_time, now, now)
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "message": "计划已添加"}), 201


@app.route("/api/plans", methods=["GET"])
@require_api_key
def get_plans():
    date_str = request.args.get("date")
    db = get_db()
    if date_str:
        rows = db.execute(
            "SELECT * FROM plans WHERE date=? AND deleted=0 ORDER BY created_at", (date_str,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM plans WHERE deleted=0 ORDER BY date, created_at"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/plans/<int:plan_id>", methods=["PUT"])
@require_api_key
def update_plan(plan_id):
    data = request.get_json(force=True)
    content = data.get("content")
    alarm_time = data.get("alarm_time")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    if content is not None:
        db.execute("UPDATE plans SET content=?, updated_at=? WHERE id=?", (content, now, plan_id))
    if alarm_time is not None:
        db.execute("UPDATE plans SET alarm_time=?, updated_at=? WHERE id=?", (alarm_time, now, plan_id))
    db.commit()
    return jsonify({"message": "已更新"})


@app.route("/api/plans/<int:plan_id>", methods=["DELETE"])
@require_api_key
def delete_plan(plan_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute("UPDATE plans SET deleted=1, updated_at=? WHERE id=?", (now, plan_id))
    db.commit()
    return jsonify({"message": "已删除"})


@app.route("/api/plans/dates", methods=["GET"])
@require_api_key
def get_plan_dates():
    db = get_db()
    rows = db.execute("SELECT DISTINCT date FROM plans WHERE deleted=0").fetchall()
    return jsonify([r["date"] for r in rows])


# ──────────────── 文件 API ────────────────

@app.route("/api/files", methods=["POST"])
@require_api_key
def add_file():
    data = request.get_json(force=True)
    original_name = data.get("original_name", "")
    file_type = data.get("file_type", "其他")
    date_str = data.get("date")
    file_url = data.get("file_url", "")
    if not date_str or not original_name:
        return jsonify({"error": "date 和 original_name 必填"}), 400

    ext = os.path.splitext(original_name)[1]
    saved_name = f"{uuid.uuid4().hex}{ext}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    cur = db.execute(
        "INSERT INTO files (original_name, saved_name, file_type, date, file_url, saved_at) VALUES (?,?,?,?,?,?)",
        (original_name, saved_name, file_type, date_str, file_url, now)
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "saved_name": saved_name, "message": "文件记录已添加"}), 201


@app.route("/api/files", methods=["GET"])
@require_api_key
def get_files():
    date_str = request.args.get("date")
    db = get_db()
    if date_str:
        rows = db.execute(
            "SELECT * FROM files WHERE date=? AND deleted=0 ORDER BY saved_at", (date_str,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM files WHERE deleted=0 ORDER BY date DESC, saved_at"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/files/<int:file_id>", methods=["DELETE"])
@require_api_key
def delete_file(file_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute("UPDATE files SET deleted=1, saved_at=? WHERE id=?", (now, file_id))
    db.commit()
    return jsonify({"message": "已删除"})


# ──────────────── 全量同步 API ────────────────

@app.route("/api/sync/pull", methods=["GET"])
@require_api_key
def sync_pull():
    """客户端拉取全部有效数据"""
    db = get_db()
    plans = db.execute("SELECT * FROM plans WHERE deleted=0 ORDER BY date, created_at").fetchall()
    files = db.execute("SELECT * FROM files WHERE deleted=0 ORDER BY date, saved_at").fetchall()
    return jsonify({
        "plans": [dict(r) for r in plans],
        "files": [dict(r) for r in files],
        "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/sync/push", methods=["POST"])
@require_api_key
def sync_push():
    """客户端推送本地数据（用于本地→云端同步）"""
    data = request.get_json(force=True)
    db = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    added_plans = 0
    for p in data.get("plans", []):
        existing = db.execute(
            "SELECT id FROM plans WHERE date=? AND content=? AND deleted=0",
            (p["date"], p["content"])
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO plans (date, content, alarm_time, created_at, updated_at) VALUES (?,?,?,?,?)",
                (p["date"], p["content"], p.get("alarm_time"), p.get("created_at", now), now)
            )
            added_plans += 1
    db.commit()
    return jsonify({"message": f"同步完成，新增 {added_plans} 条计划"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


# ──────────────── 启动 ────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"☁️  同步服务器启动于 http://0.0.0.0:{port}")
    print(f"🔑 API Key: {API_KEY}")
    app.run(host="0.0.0.0", port=port, debug=debug)
