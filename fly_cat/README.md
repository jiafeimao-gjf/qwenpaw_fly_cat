# FlyCat Channel 部署指南

## 目录结构

```
~/.qwenpaw/custom_channels/fly_cat/
├── __init__.py   # 频道主实现（含 Token 管理）
└── config.py     # 配置类
```

## 配置方式

### 方式一：环境变量

```bash
# App 服务端基础地址
export FLYCAT_BASE_URL="http://your-app-server"

# 接口路径配置
export FLYCAT_POLL_PATH="/api/messages/poll"      # 轮询获取消息
export FLYCAT_SEND_PATH="/api/messages/send"      # 发送消息
export FLYCAT_LOGIN_PATH="/api/auth/login"         # 登录
export FLYCAT_REFRESH_PATH="/api/auth/refresh"     # Token 刷新

# 认证配置
export FLYCAT_CLIENT_ID="your-client-id"
export FLYCAT_CLIENT_SECRET="your-client-secret"

# 轮询间隔（秒）
export FLYCAT_POLL_INTERVAL="5"
```

### 方式二：配置文件

在 `~/.qwenpaw/config.yaml` 中配置：

```yaml
channels:
  fly_cat:
    enabled: true
    base_url: "http://your-app-server"
    poll_path: "/api/messages/poll"
    send_path: "/api/messages/send"
    login_path: "/api/auth/login"
    refresh_path: "/api/auth/refresh"
    client_id: "your-client-id"
    client_secret: "your-client-secret"
    poll_interval: 5.0

    # 通用配置（可选）
    bot_prefix: ""
    filter_tool_messages: false
    filter_thinking: false
    dm_policy: "open"
    group_policy: "open"
    require_mention: false
```

## 配置项说明

| 配置项 | 环境变量 | 类型 | 默认值 | 说明 |
|--------|----------|------|--------|------|
| `enabled` | - | bool | `false` | 是否启用该频道 |
| `base_url` | `FLYCAT_BASE_URL` | str | `""` | App 服务端基础地址 |
| `poll_path` | `FLYCAT_POLL_PATH` | str | `/api/messages/poll` | 轮询获取消息路径 |
| `send_path` | `FLYCAT_SEND_PATH` | str | `/api/messages/send` | 发送消息路径 |
| `login_path` | `FLYCAT_LOGIN_PATH` | str | `/api/auth/login` | 登录接口路径 |
| `refresh_path` | `FLYCAT_REFRESH_PATH` | str | `/api/auth/refresh` | Token 刷新路径 |
| `client_id` | `FLYCAT_CLIENT_ID` | str | `""` | App 客户端 ID |
| `client_secret` | `FLYCAT_CLIENT_SECRET` | str | `""` | App 客户端密钥 |
| `poll_interval` | `FLYCAT_POLL_INTERVAL` | float | `5.0` | 轮询间隔（秒） |
| `bot_prefix` | - | str | `""` | 机器人回复前缀 |
| `filter_tool_messages` | - | bool | `false` | 是否过滤工具消息 |
| `filter_thinking` | - | bool | `false` | 是否过滤思考过程 |
| `dm_policy` | - | str | `"open"` | 私聊策略：`open` 或 `allowlist` |
| `group_policy` | - | str | `"open"` | 群聊策略：`open` 或 `allowlist` |
| `allow_from` | - | list | `None` | 白名单用户 ID 列表 |
| `deny_message` | - | str | `""` | 拒绝访问提示语 |
| `require_mention` | - | bool | `false` | 群聊是否需要 @机器人 |

## App 服务端接口要求

### 1. 登录接口 (POST)

获取 Access Token 和 Refresh Token。

**请求**
```
POST /api/auth/login
Content-Type: application/json

{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "username": "user@example.com",
  "password": "user-password"
}
```

**响应**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g...",
  "expires_in": 3600
}
```

### 2. Token 刷新接口 (POST)

当 Access Token 过期时使用 Refresh Token 获取新的 Access Token。

**请求**
```
POST /api/auth/refresh
Content-Type: application/json

{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g..."
}
```

**响应**
```json
{
  "access_token": "new-access-token...",
  "refresh_token": "new-refresh-token...",  // 可选
  "expires_in": 3600
}
```

### 3. 轮询获取消息接口 (GET)

**请求**
```
GET /api/messages/poll
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**响应**
```json
[
  {
    "message_id": "12345",
    "user_id": "user_001",
    "session_id": "sess_abc",
    "text": "你好",
    "timestamp": 1234567890
  }
]
```

### 4. 发送消息接口 (POST)

**请求**
```
POST /api/messages/send
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "message_id": "12345",
  "user_id": "user_001",
  "text": "你好，我是 AI 助手"
}
```

**响应**
```json
{"status": "ok"}
```

## 认证流程

```
┌─────────────────────────────────────────────────────────────┐
│                      TokenManager                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. user_login(username, password)                           │
│     → POST /api/auth/login                                   │
│     → 获取 access_token + refresh_token                      │
│     → 存储到 TokenManager                                    │
│                                                              │
│  2. _request_with_auth(method, url)                         │
│     → 检查 Token 是否有效                                    │
│     → 有/无 Token 带上 Bearer header                        │
│     → 请求失败返回 401 => 尝试刷新                           │
│                                                              │
│  3. Token 过期/无效 => refresh()                             │
│     → POST /api/auth/refresh                                │
│     → 获取新 access_token                                   │
│     → 重试原请求                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 自动刷新机制

- **主动刷新**：每次请求前检查 Token 是否即将过期（提前 60 秒）
- **被动刷新**：收到 401 响应时自动尝试刷新 Token，然后重试请求
- **刷新失败**：Token 刷新失败时，清除本地 Token，下次请求会重新登录

## 用户会话管理

```python
# 用户登录
result = await channel.user_login("user@example.com", "password")
# {"success": True, "user_id": "user_abc12345"}

# 获取用户信息
info = await channel.get_user_info("user_abc12345")
# {"username": "user@example.com", "login_time": 1234567890.0}

# 用户登出
await channel.user_logout("user_abc12345")
```

## 消息流程

```
用户操作  →  App 写入消息队列
              ↓
QwenPaw  →  GET /api/messages/poll (带 Bearer Token)
              ↓
         获取消息列表
              ↓
         Agent 处理
              ↓
QwenPaw  →  POST /api/messages/send (带 Bearer Token)
              ↓
         App 展现给用户
```

## 测试验证

1. 启动 QwenPaw:
```bash
qwenpaw app
```

2. 检查日志确认加载:
```
INFO - Custom channel registered: fly_cat
INFO - FlyCat channel started (poll_interval=5.0)
INFO - Token login successful
```

3. 触发 401 时:
```
INFO - Got 401, attempting token refresh...
INFO - Token refreshed successfully
```

## 注意事项

- 确保 App 服务端在 QwenPaw 可访问的网络范围内
- `client_id` 和 `client_secret` 用于双方认证，请妥善保管
- Refresh Token 有效期通常比 Access Token 长，请根据业务设置合理的过期时间
- 环境变量配置会覆盖配置文件中的值