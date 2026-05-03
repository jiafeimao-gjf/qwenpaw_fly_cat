# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## App Server 项目

配合 QwenPaw MyApp Channel 使用的消息服务端，负责用户认证和消息队列管理。

### 启动服务

```bash
cd app_server
pip install -r requirements.txt
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 环境变量

```bash
export JWT_SECRET="your-secret-key"
export CLIENT_ID="qwenpaw-client"
export CLIENT_SECRET="your-client-secret"
```

### API 接口

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/refresh` | POST | 刷新 Token |
| `/api/messages/poll` | GET | QwenPaw 轮询消息 |
| `/api/messages/send` | POST | QwenPaw 发送响应 |
| `/api/messages/submit` | POST | App 提交消息 |
| `/api/messages/response/{id}` | GET | App 获取响应 |
| `/health` | GET | 健康检查 |

### 默认测试用户

- 用户名: `test`
- 密码: `test123`

### 架构

```
app_server/
├── main.py              # FastAPI 入口
├── config.py            # 配置管理
├── database.py          # SQLAlchemy 数据库配置
├── auth/                # 认证模块
│   ├── jwt_handler.py   # JWT 生成/验证
│   ├── user_store.py    # 用户存储（SQLite）
│   └── routes.py        # 认证路由
├── messages/           # 消息模块
│   ├── queue.py         # 消息队列（SQLite）
│   └── routes.py        # 消息路由
├── models/             # SQLAlchemy ORM 模型
├── schemas/             # Pydantic schemas
└── requirements.txt
```

### 数据持久化

SQLite 数据库（`app_server.db`），启动时自动创建表。

## App Client 前端

Vue 3 Web 客户端，供用户与 QwenPaw 通过 App Server 进行对话。

### 启动

```bash
cd app_client
npm install
npm run dev
```

启动后自动绑定本机局域网 IP（如 192.168.x.x:3000），方便手机/其他设备访问。

### 环境变量

```bash
HOST=0.0.0.0 PORT=3000 API_TARGET=http://localhost:8080 npm run dev
```

### 组件结构

```
app_client/src/
├── App.vue              # 根组件
├── api/client.js        # API 调用封装
├── stores/auth.js       # 认证状态管理
└── components/
    ├── Login.vue        # 登录页
    ├── ChatRoom.vue     # 聊天室
    └── MessageBubble.vue # 消息气泡
```

### 消息流程

1. 用户登录后发送消息 → `/api/messages/submit`
2. 客户端每秒轮询 `/api/messages/response/{id}` 获取 AI 响应
3. 响应到达后显示在聊天界面