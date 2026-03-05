# QQ 机器人 + 云端同步 完整搭建指南

## 架构概览

```
┌──────────────┐     ┌───────────────────┐     ┌────────────────────┐
│  📱 手机QQ    │────▶│  🤖 QQ机器人       │────▶│  ☁️ 云端同步服务器   │
│  发送指令     │◀────│  (bot/qq_bot.py)  │◀────│  (server/)         │
└──────────────┘     └───────────────────┘     └────────┬───────────┘
                                                        │ REST API
                                               ┌────────▼───────────┐
                                               │  🖥️ 桌面日历软件    │
                                               │  (启动时自动同步)   │
                                               └────────────────────┘
```

**数据流**: 手机发指令 → QQ机器人 → 存入云端服务器 → 桌面日历启动时拉取

---

## 第一步：注册 QQ 机器人

### 1.1 创建机器人应用

1. 打开 [QQ 开放平台](https://q.qq.com)，使用 QQ 号登录
2. 点击 **「创建机器人」**
3. 填写机器人信息：
   - **名称**: 桌面助手 (或你喜欢的名字)
   - **简介**: 管理日历计划和文件
4. 创建成功后，进入机器人管理页面

### 1.2 获取 AppID 和 Secret

在机器人管理页面 → **「开发」** → **「开发设置」**：

| 配置项 | 说明 |
|--------|------|
| **AppID** | 机器人的唯一标识，形如 `102012345` |
| **AppSecret** | 点击「查看」获取，形如 `abc123def456` |

⚠️ **请妥善保存 AppSecret，不要泄露！**

### 1.3 配置消息事件订阅

在 **「开发设置」** → **「事件订阅」** 中开启：

- ✅ `C2C_MESSAGE_CREATE` — 接收单聊消息
- ✅ `GROUP_AT_MESSAGE_CREATE` — 接收群聊@消息
- ✅ `AT_MESSAGE_CREATE` — 接收频道@消息（可选）

### 1.4 沙箱/上线配置

- 开发测试阶段可使用 **沙箱模式**
- 在 **「功能配置」** 中添加你的 QQ 号为测试用户
- 正式使用后可申请上线

---

## 第二步：部署云端同步服务器

### 2.1 服务器要求

- 任意有公网 IP 的云服务器（阿里云/腾讯云/华为云等）
- Python 3.9+
- 推荐最低配置: 1核 1G 内存

### 2.2 部署步骤

```bash
# 1. 上传 server/ 目录到你的云服务器
scp -r server/ user@your-server:/opt/calendar-sync/

# 2. 在服务器上安装依赖
cd /opt/calendar-sync
pip install -r requirements.txt

# 3. 设置 API 密钥（重要！请修改为你自己的密钥）
export SYNC_API_KEY="your-very-secure-random-key-here"

# 4. 启动服务器
python sync_server.py
# 默认监听 0.0.0.0:5000
```

### 2.3 生产部署（推荐 systemd）

创建 `/etc/systemd/system/calendar-sync.service`:

```ini
[Unit]
Description=Calendar Sync Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/calendar-sync
Environment=SYNC_API_KEY=your-very-secure-random-key-here
Environment=PORT=5000
ExecStart=/usr/bin/python3 sync_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable calendar-sync
sudo systemctl start calendar-sync
```

### 2.4 验证服务器

```bash
# 健康检查
curl http://your-server:5000/api/health

# 添加一条计划
curl -X POST http://your-server:5000/api/plans \
  -H "X-API-Key: your-very-secure-random-key-here" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-03-05", "content": "测试计划"}'

# 查看计划
curl http://your-server:5000/api/plans?date=2026-03-05 \
  -H "X-API-Key: your-very-secure-random-key-here"
```

### 2.5 使用 Nginx 反向代理（可选但推荐）

```nginx
server {
    listen 443 ssl;
    server_name sync.yourdomain.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 第三步：在服务器上部署 QQ 机器人

> ⚠️ QQ 机器人应部署在云服务器上（和同步服务器一起），这样 24 小时在线，不需要你的电脑一直开着。

### 3.1 上传机器人代码到服务器

和上传 `server/` 目录一样，通过宝塔面板将 `bot/` 文件夹上传到服务器 `/root/` 目录下。

### 3.2 在服务器上安装依赖

```bash
cd ~/bot
pip3 install -r requirements.txt
```

> 如果 `pip3 install qq-botpy` 失败（国内网络问题），可使用镜像源：
> ```bash
> pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

### 3.3 创建配置文件

```bash
cd ~/bot
cp config.example.yaml config.yaml
```

编辑 `config.yaml`（可通过宝塔面板的文件管理器编辑）：

```yaml
# 第一步获取的 AppID 和 AppSecret
appid: "你的AppID"
secret: "你的AppSecret"

# 同步服务器在本机，直接用 127.0.0.1
sync_server_url: "http://127.0.0.1:5000"

# 与 sync_server 的 SYNC_API_KEY 一致
sync_api_key: "your-very-secure-random-key-here"
```

### 3.3 后台启动机器人

```bash
cd ~/bot
nohup python3 qq_bot.py > bot.log 2>&1 &
```

查看是否启动成功：

```bash
tail -f bot.log
```

看到 `🤖 桌面助手 QQ 机器人已上线!` 表示成功，按 `Ctrl+C` 退出日志查看。

### 3.4 测试机器人

在手机 QQ 上找到你的机器人，发送：

```
/帮助
```

收到指令列表后，试一下：

```
/添加计划 今天 去超市买菜
/今日计划
```

---

## 第四步：配置桌面日历同步

### 4.1 在日历设置中配置（推荐）

1. 启动日历软件 `python main.py`
2. 点击标题栏的 **⚙ 设置** 按钮
3. 滚动到底部 **☁️ 云端同步** 区域
4. 开启 **启用同步** 开关
5. 填入 **服务器地址**: `http://你的服务器公网IP:5000`
6. 填入 **API 密钥**: 与服务器端 `SYNC_API_KEY` 一致
7. 点击 **💾 保存配置**
8. 点击 **☁️ 立即同步** 验证连接

### 4.2 验证同步

在手机 QQ 上通过机器人添加一条计划，然后在日历设置中点击 **☁️ 立即同步**，计划就会出现在日历上。每次启动日历也会自动同步。

---

## QQ 机器人指令参考

| 指令 | 说明 | 示例 |
|------|------|------|
| `/添加计划 日期 内容` | 添加计划 | `/添加计划 2026-03-05 写周报` |
| `/添加计划 今天 内容` | 今天添加计划 | `/添加计划 今天 去超市买菜` |
| `/今日计划` | 查看今天的计划 | `/今日计划` |
| `/查看计划 日期` | 查看指定日期的计划 | `/查看计划 2026-03-05` |
| `/删除计划 ID` | 删除指定 ID 的计划 | `/删除计划 3` |
| `/添加文件 日期 文件名` | 记录文件条目 | `/添加文件 今天 报告.pdf` |
| `/帮助` | 显示帮助信息 | `/帮助` |

---

## 云端 API 接口文档

### 认证

所有 API 请求需携带 `X-API-Key` Header 或 `api_key` URL 参数。

### 计划接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/plans` | 添加计划 `{ "date": "...", "content": "..." }` |
| `GET` | `/api/plans?date=YYYY-MM-DD` | 获取指定日期的计划 |
| `GET` | `/api/plans` | 获取全部计划 |
| `PUT` | `/api/plans/<id>` | 更新计划 `{ "content": "..." }` |
| `DELETE` | `/api/plans/<id>` | 删除计划 |
| `GET` | `/api/plans/dates` | 获取有计划的日期列表 |

### 文件接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/files` | 添加文件记录 |
| `GET` | `/api/files?date=YYYY-MM-DD` | 获取指定日期的文件 |
| `DELETE` | `/api/files/<id>` | 删除文件记录 |

### 同步接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/sync/pull` | 拉取全部数据 |
| `POST` | `/api/sync/push` | 推送本地数据 |

---

## 常见问题

### Q: 机器人收不到消息？

1. 确认在 QQ 开放平台的「事件订阅」中已开启 `C2C_MESSAGE_CREATE`
2. 确认你的 QQ 号已加入机器人的测试白名单（沙箱模式下）
3. 检查 AppID 和 Secret 是否正确

### Q: 机器人回复「无法连接云端服务器」？

1. 确认 `sync_server.py` 正在运行
2. 确认防火墙已放行对应端口（默认 5000）
3. 如果机器人和服务器在不同机器上，确认服务器地址填写正确

### Q: 日历没有显示从手机添加的计划？

1. 确认 `.config.json` 中 `sync_enabled` 为 `true`
2. 确认 `sync_server_url` 和 `sync_api_key` 配置正确
3. 重新启动日历软件触发同步

### Q: 如何在群聊中使用？

将机器人添加到 QQ 群，然后 @机器人 发送指令即可，例如：
```
@桌面助手 /今日计划
```

### Q: 数据安全吗？

- API Key 用于认证所有请求，请确保使用强密钥
- 建议使用 HTTPS（通过 Nginx + SSL 证书）
- 数据存储在你自己的服务器上

---

## 文件目录结构

```
Calendar/
├── main.py              # 日历入口（已集成启动同步）
├── sync_client.py       # 同步客户端模块
├── .config.json         # 日历配置（含同步设置）
│
├── server/              # 云端同步服务器
│   ├── sync_server.py   # Flask API 服务
│   ├── requirements.txt
│   └── sync.db          # 服务端数据库（自动创建）
│
├── bot/                 # QQ 机器人
│   ├── qq_bot.py        # 机器人主程序
│   ├── config.yaml      # 机器人配置（从 config.example.yaml 复制）
│   ├── config.example.yaml
│   └── requirements.txt
│
└── ...                  # 其他日历文件
```
