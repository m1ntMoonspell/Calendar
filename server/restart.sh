#!/bin/bash
# 一键重启同步服务器和QQ机器人
# 用法: bash restart.sh
# 请先修改下面的 API_KEY 为你自己的密钥

API_KEY="${SYNC_API_KEY:-my-secret-key-123}"
PYTHON="python3.9"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT_DIR="$(dirname "$SCRIPT_DIR")/bot"

# 检测可用的 Python
if ! command -v $PYTHON &>/dev/null; then
    PYTHON="python3"
fi

echo "=============================="
echo "  桌面助手 一键重启脚本"
echo "=============================="

# ── 重启同步服务器 ──
echo ""
echo "▶ 停止同步服务器..."
pkill -f "sync_server.py" 2>/dev/null
sleep 1

echo "▶ 启动同步服务器..."
cd "$SCRIPT_DIR"
export SYNC_API_KEY="$API_KEY"
nohup $PYTHON sync_server.py > sync.log 2>&1 &
echo "  PID: $!"

sleep 2
if curl -s http://127.0.0.1:5000/api/health | grep -q '"ok"'; then
    echo "  ✅ 同步服务器启动成功"
else
    echo "  ❌ 同步服务器启动失败，查看 sync.log"
fi

# ── 重启QQ机器人 ──
if [ -d "$BOT_DIR" ] && [ -f "$BOT_DIR/qq_bot.py" ]; then
    echo ""
    echo "▶ 停止QQ机器人..."
    pkill -f "qq_bot.py" 2>/dev/null
    sleep 1

    echo "▶ 启动QQ机器人..."
    cd "$BOT_DIR"
    export SYNC_API_KEY="$API_KEY"
    nohup $PYTHON qq_bot.py > bot.log 2>&1 &
    echo "  PID: $!"
    sleep 3

    if grep -q "已上线" bot.log 2>/dev/null; then
        echo "  ✅ QQ机器人启动成功"
    else
        echo "  ⏳ QQ机器人正在连接...（查看 bot.log）"
    fi
else
    echo ""
    echo "⚠️  未找到 bot 目录，跳过QQ机器人"
fi

echo ""
echo "=============================="
echo "  重启完成！"
echo "  同步服务器日志: $SCRIPT_DIR/sync.log"
if [ -d "$BOT_DIR" ]; then
    echo "  QQ机器人日志:   $BOT_DIR/bot.log"
fi
echo "=============================="
