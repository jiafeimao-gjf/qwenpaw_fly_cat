# FlyCat Channel 部署指南

## 目录结构

```
fly_cat/
├── __init__.py   # 频道主实现（含 TokenManager）
└── config.py     # 配置类
```

## 配置方式

在 `~/.qwenpaw/config.json` 中配置 `channels.fly_cat`：

```json
{
  "channels": {
    "fly_cat": {
      "enabled": true,
      "base_url": "http://your-app-server",
      "poll_path": "/api/messages/poll",
      "send_path": "/api/messages/send",
      "login_path": "/api/auth/login",
      "refresh_path": "/api/auth/refresh",
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "username": "your-username",
      "password": "your-password",
      "poll_interval": 3.0
    }
  }
}
```

## 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enabled` | bool | `false` | 是否启用该频道 |
| `base_url` | str | `""` | App 服务端基础地址 |
| `poll_path` | str | `/api/messages/poll` | 轮询获取消息路径 |
| `send_path` | str | `/api/messages/send` | 发送消息路径 |
| `login_path` | str | `/api/auth/login` | 登录接口路径 |
| `refresh_path` | str | `/api/auth/refresh` | Token 刷新路径 |
| `client_id` | str | `""` | App 客户端 ID |
| `client_secret` | str | `""` | App 客户端密钥 |
| `username` | str | `""` | 兜底登录用户名（无 refresh_token 时自动登录用） |
| `password` | str | `""` | 兜底登录密码 |
| `poll_interval` | float | `3.0` | 轮询间隔（秒） |

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
  "refresh_token": "new-refresh-token...",
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
TokenManager
│
├── user_login(username, password)
│   → POST /api/auth/login
│   → 获取 access_token + refresh_token
│   → 存储到 TokenManager
│
├── _request_with_auth(method, url)
│   → 检查 Token 是否有效
│   → 有 Token 带上 Bearer header
│   → 请求失败返回 401 => 尝试刷新
│
└── refresh()
    → POST /api/auth/refresh
    → 获取新 access_token
    → 重试原请求
```

## 自动刷新机制

- **主动刷新**：每次请求前检查 Token 是否即将过期（提前 60 秒）
- **被动刷新**：收到 401 响应时自动尝试刷新 Token，然后重试请求
- **兜底机制**：当无 refresh_token 时，自动用 username/password 重新登录
- **刷新失败**：Token 刷新失败时，清除本地 Token，下次请求会重新登录

## 消息流程

```
App (用户)            App Server        QwenPaw
   │                     │                 │
   │── POST /submit ────>│                 │
   │                     │                 │
   │                     │<── GET /poll ───│
   │                     │── [消息列表] ──>│
   │                     │                 │
   │                     │    Agent 处理   │
   │                     │                 │
   │<── GET /resp ──────│<── POST /send ──│
   │                     │                 │
```

## 测试验证

1. 启动 QwenPaw:
```bash
qwenpaw app
```

2. 检查日志确认加载:
```
INFO - Custom channel registered: fly_cat
INFO - FlyCat channel started (poll_interval=3.0)
```

3. 触发 401 时:
```
INFO - Got 401, attempting token refresh...
INFO - Token refreshed successfully
```

4. 无 refresh_token 兜底登录:
```
INFO - No refresh token, attempting fallback login...
INFO - Token login successful
```

## 注意事项

- 确保 App 服务端在 QwenPaw 可访问的网络范围内
- `client_id` 和 `client_secret` 用于双方认证，请妥善保管
- `username` 和 `password` 用于无 refresh_token 时的兜底自动登录
- Refresh Token 有效期通常比 Access Token 长