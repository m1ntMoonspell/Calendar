"""
QQ 机器人 — 通过手机 QQ 向云端服务器添加/查看每日计划和兴趣文件
使用腾讯官方 botpy SDK (qq-botpy)

支持的指令（在 C2C 单聊或群聊 @机器人 时发送）:
  /添加计划 2026-03-05 去超市买菜         → 在指定日期添加计划
  /今日计划                               → 查看今天的计划
  /查看计划 2026-03-05                    → 查看指定日期的计划
  /删除计划 <id>                          → 删除指定 ID 的计划
  /添加文件 2026-03-05 文件名.txt          → 记录一个文件条目
  /帮助                                   → 查看所有指令

启动: python qq_bot.py
配置: 设置环境变量或编辑 config.yaml
"""

import os
import re
import yaml
import requests
from datetime import date

import botpy
from botpy import logging
from botpy.message import C2CMessage, GroupMessage, Message

log = logging.get_logger()

# ──────────────── 配置加载 ────────────────

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")


def load_config():
    cfg = {
        "appid": os.environ.get("QQ_BOT_APPID", ""),
        "secret": os.environ.get("QQ_BOT_SECRET", ""),
        "sync_server_url": os.environ.get("SYNC_SERVER_URL", "http://127.0.0.1:5000"),
        "sync_api_key": os.environ.get("SYNC_API_KEY", "change-me-to-a-secure-key"),
    }
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            file_cfg = yaml.safe_load(f) or {}
            for k, v in file_cfg.items():
                if v:
                    cfg[k] = str(v)
    return cfg


CONFIG = load_config()

# ──────────────── 云端 API 调用 ────────────────

FILE_TYPE_MAP = {
    '.jpg': '图片', '.jpeg': '图片', '.png': '图片', '.gif': '图片',
    '.bmp': '图片', '.webp': '图片',
    '.pdf': '文档', '.doc': '文档', '.docx': '文档', '.txt': '文档',
    '.xls': '文档', '.xlsx': '文档', '.ppt': '文档', '.pptx': '文档',
    '.csv': '文档', '.md': '文档',
    '.mp3': '音频', '.wav': '音频', '.flac': '音频', '.m4a': '音频',
    '.mp4': '视频', '.avi': '视频', '.mkv': '视频', '.mov': '视频',
    '.zip': '压缩包', '.rar': '压缩包', '.7z': '压缩包',
    '.py': '代码', '.js': '代码', '.java': '代码', '.c': '代码',
    '.cpp': '代码', '.go': '代码', '.rs': '代码', '.html': '代码',
}


def api_headers():
    return {"X-API-Key": CONFIG["sync_api_key"], "Content-Type": "application/json"}


def api_url(path):
    return f"{CONFIG['sync_server_url']}{path}"


def api_add_plan(date_str, content, alarm_time=None):
    resp = requests.post(api_url("/api/plans"), json={
        "date": date_str, "content": content, "alarm_time": alarm_time
    }, headers=api_headers(), timeout=10)
    return resp.json()


def api_get_plans(date_str):
    resp = requests.get(api_url("/api/plans"), params={"date": date_str},
                        headers=api_headers(), timeout=10)
    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(data["error"])
    return data if isinstance(data, list) else []


def api_delete_plan(plan_id):
    resp = requests.delete(api_url(f"/api/plans/{plan_id}"),
                           headers=api_headers(), timeout=10)
    return resp.json()


def api_add_file(date_str, original_name, file_url=""):
    ext = os.path.splitext(original_name)[1].lower()
    file_type = FILE_TYPE_MAP.get(ext, "其他")
    resp = requests.post(api_url("/api/files"), json={
        "date": date_str, "original_name": original_name,
        "file_type": file_type, "file_url": file_url
    }, headers=api_headers(), timeout=10)
    return resp.json()


# ──────────────── 指令解析 ────────────────

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

HELP_TEXT = """📅 桌面助手 QQ 机器人指令：

📎 直接发送文件
  发送任意文件/图片/视频，自动保存到今天的兴趣文件

/添加计划 日期 内容
  例: /添加计划 2026-03-05 去超市买菜
  例: /添加计划 今天 写周报

/今日计划
  查看今天的所有计划

/查看计划 日期
  例: /查看计划 2026-03-05

/删除计划 ID
  例: /删除计划 3

/帮助
  显示本帮助信息"""


def parse_date(text):
    """从文本中解析日期，支持 '今天'、'明天' 和 YYYY-MM-DD"""
    if "今天" in text:
        return date.today().isoformat()
    if "明天" in text:
        from datetime import timedelta
        return (date.today() + timedelta(days=1)).isoformat()
    m = DATE_RE.search(text)
    return m.group(1) if m else None


def handle_command(text):
    """解析用户指令并返回回复文本"""
    text = text.strip()
    if not text.startswith("/"):
        return None

    parts = text.split(maxsplit=2)
    cmd = parts[0]

    try:
        if cmd == "/帮助" or cmd == "/help":
            return HELP_TEXT

        elif cmd == "/今日计划":
            today = date.today().isoformat()
            plans = api_get_plans(today)
            if not plans:
                return f"📋 {today} 暂无计划"
            lines = [f"📋 {today} 的计划："]
            for i, p in enumerate(plans, 1):
                alarm = f" ⏰{p['alarm_time']}" if p.get("alarm_time") else ""
                created = p.get("created_at", "")
                time_str = f" ({created[11:16]})" if len(created) >= 16 else ""
                lines.append(f"  {i}. {p['content']}{alarm}{time_str}")
            return "\n".join(lines)

        elif cmd == "/添加计划":
            if len(parts) < 2:
                return "❌ 格式: /添加计划 日期 内容\n例: /添加计划 2026-03-05 去超市买菜"
            date_str = parse_date(parts[1])
            if not date_str:
                return "❌ 无法解析日期，请使用 YYYY-MM-DD 格式或 '今天'/'明天'"
            content = parts[2] if len(parts) > 2 else ""
            if not content:
                return "❌ 请输入计划内容"
            result = api_add_plan(date_str, content)
            return f"✅ 计划已添加到 {date_str}\n📝 {content}\n🆔 ID: {result.get('id', '?')}"

        elif cmd == "/查看计划":
            if len(parts) < 2:
                return "❌ 格式: /查看计划 日期\n例: /查看计划 2026-03-05"
            date_str = parse_date(parts[1])
            if not date_str:
                return "❌ 无法解析日期"
            plans = api_get_plans(date_str)
            if not plans:
                return f"📋 {date_str} 暂无计划"
            lines = [f"📋 {date_str} 的计划："]
            for i, p in enumerate(plans, 1):
                alarm = f" ⏰{p['alarm_time']}" if p.get("alarm_time") else ""
                created = p.get("created_at", "")
                time_str = f" ({created[11:16]})" if len(created) >= 16 else ""
                lines.append(f"  {i}. {p['content']}{alarm}{time_str}")
            return "\n".join(lines)

        elif cmd == "/删除计划":
            if len(parts) < 2:
                return "❌ 格式: /删除计划 ID"
            try:
                plan_id = int(parts[1])
            except ValueError:
                return "❌ ID 必须是数字"
            api_delete_plan(plan_id)
            return f"🗑️ 计划 ID:{plan_id} 已删除"

        else:
            return f"❓ 未知指令: {cmd}\n输入 /帮助 查看所有指令"

    except requests.exceptions.ConnectionError:
        return "❌ 无法连接云端服务器，请检查服务器是否正在运行"
    except Exception as e:
        return f"❌ 执行失败: {e}"


# ──────────────── botpy 客户端 ────────────────

def handle_attachments(attachments):
    """处理消息中的文件附件，自动保存到今天的文件记录，返回回复文本"""
    if not attachments:
        return None

    today = date.today().isoformat()
    results = []
    for att in attachments:
        filename = getattr(att, "filename", None) or ""
        file_url = getattr(att, "url", None) or ""
        content_type = getattr(att, "content_type", None) or ""
        if not filename:
            if "image" in content_type:
                ext = content_type.split("/")[-1].split(";")[0]
                filename = f"image.{ext}"
            elif "video" in content_type:
                filename = "video.mp4"
            elif "audio" in content_type or "voice" in content_type:
                filename = "voice.silk"
            else:
                filename = "file"
        try:
            result = api_add_file(today, filename, file_url)
            results.append(filename)
            log.info(f"File saved: {filename} -> {today}")
        except Exception as e:
            log.error(f"File save failed: {filename}: {e}")

    if not results:
        return None

    if len(results) == 1:
        return f"已保存文件 {results[0]} 到 {today}"
    return f"已保存 {len(results)} 个文件到 {today}"


class CalendarBot(botpy.Client):
    """QQ 机器人客户端，处理 C2C 单聊和群聊 @机器人消息"""

    async def on_ready(self):
        log.info("🤖 桌面助手 QQ 机器人已上线!")

    async def on_c2c_message_create(self, message: C2CMessage):
        """处理 C2C 单聊消息：自动识别文件附件 + 文本指令"""
        replies = []

        attachments = getattr(message, "attachments", None)
        if attachments:
            file_reply = handle_attachments(attachments)
            if file_reply:
                replies.append(file_reply)

        content = (getattr(message, "content", "") or "").strip()
        if content.startswith("/"):
            cmd_reply = handle_command(content)
            if cmd_reply:
                replies.append(cmd_reply)

        if replies:
            try:
                await message.reply(content="\n".join(replies), msg_type=0)
            except Exception as e:
                log.error(f"C2C reply error: {e}")

    async def on_group_at_message_create(self, message: GroupMessage):
        """处理群聊 @机器人消息：自动识别文件附件 + 文本指令"""
        replies = []

        attachments = getattr(message, "attachments", None)
        if attachments:
            file_reply = handle_attachments(attachments)
            if file_reply:
                replies.append(file_reply)

        content = (getattr(message, "content", "") or "")
        content = re.sub(r"<@!\d+>", "", content).strip()
        if content.startswith("/"):
            cmd_reply = handle_command(content)
            if cmd_reply:
                replies.append(cmd_reply)

        if replies:
            try:
                await message.reply(content="\n".join(replies), msg_type=0)
            except Exception as e:
                log.error(f"Group reply error: {e}")

    async def on_at_message_create(self, message: Message):
        """处理频道 @机器人消息 (兼容频道场景)"""
        replies = []

        attachments = getattr(message, "attachments", None)
        if attachments:
            file_reply = handle_attachments(attachments)
            if file_reply:
                replies.append(file_reply)

        content = (getattr(message, "content", "") or "")
        content = re.sub(r"<@!\d+>", "", content).strip()
        if content.startswith("/"):
            cmd_reply = handle_command(content)
            if cmd_reply:
                replies.append(cmd_reply)

        if replies:
            try:
                await message.reply(content="\n".join(replies))
            except Exception as e:
                log.error(f"Channel reply error: {e}")


# ──────────────── 入口 ────────────────

if __name__ == "__main__":
    appid = CONFIG["appid"]
    secret = CONFIG["secret"]

    if not appid or not secret:
        print("❌ 请配置 QQ_BOT_APPID 和 QQ_BOT_SECRET")
        print("   方式1: 设置环境变量 QQ_BOT_APPID / QQ_BOT_SECRET")
        print("   方式2: 编辑 bot/config.yaml")
        exit(1)

    print(f"🤖 启动 QQ 机器人... (appid={appid})")
    print(f"☁️  同步服务器: {CONFIG['sync_server_url']}")

    intents = botpy.Intents(
        public_guild_messages=True,
        public_messages=True,
    )
    client = CalendarBot(intents=intents)
    client.run(appid=appid, secret=secret)
