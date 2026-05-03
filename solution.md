# App Server 实现方案

## 概述

App Server 是配合 QwenPaw MyApp Channel 使用的消息服务端，负责：
- 用户认证（登录/Token 刷新）
- 消息队列管理（接收用户消息、提供给 QwenPaw 轮询）
- 响应传递（接收 QwenPaw 的 AI 响应并推送给用户）

## 技术栈

- **Web 框架**: FastAPI（与 QwenPaw 一致）
- **消息队列**: 内存队列（单机部署）/ Redis（分布式部署）
- **数据存储**: SQLite（轻量）/ PostgreSQL（生产环境）
- **认证**: JWT（JSON Web Token）

## 项目结构

```
app_server/
├── main.py              # FastAPI 入口
├── config.py            # 配置管理
├── auth/
│   ├── __init__.py
│   ├── jwt_handler.py   # JWT 生成/验证
│   └── routes.py        # 认证路由 (/api/auth/*)
├── messages/
│   ├── __init__.py
│   ├── queue.py         # 消息队列管理
│   └── routes.py        # 消息路由 (/api/messages/*)
├── models/
│   ├── __init__.py
│   ├── user.py          # 用户模型
│   └── message.py       # 消息模型
├── requirements.txt
└── README.md
```

## 核心实现

### 1. 依赖

```txt
fastapi>=0.100.0
uvicorn>=0.23.0
python-jose[cryptography]  # JWT
passlib[bcrypt]            # 密码哈希
pydantic>=2.0
redis>=4.0                 # 可选：分布式部署
sqlalchemy>=2.0            # 可选：数据库
```

### 2. 配置 (config.py)

```python
# -*- coding: utf-8 -*-
"""App Server 配置"""
import os
from pydantic import BaseModel


class Settings(BaseModel):
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8080

    # JWT 配置
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire: int = 3600        # 1 小时
    refresh_token_expire: int = 7 * 86400  # 7 天

    # 客户端认证（用于 QwenPaw Channel）
    client_id: str = os.getenv("CLIENT_ID", "qwenpaw-client")
    client_secret: str = os.getenv("CLIENT_SECRET", "change-me-in-production")

    # Redis 配置（可选）
    redis_url: str = os.getenv("REDIS_URL", "")


settings = Settings()
```

### 3. 用户模型 (models/user.py)

```python
# -*- coding: utf-8 -*-
"""用户模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    username: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.now)


class UserCreate(BaseModel):
    username: str
    password: str


class UserInDB(User):
    """数据库中的用户（包含密码哈希）"""


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class LoginRequest(BaseModel):
    client_id: str
    client_secret: str
    username: str
    password: str


class RefreshRequest(BaseModel):
    client_id: str
    client_secret: str
    refresh_token: str
```

### 4. JWT 处理 (auth/jwt_handler.py)

```python
# -*- coding: utf-8 -*-
"""JWT Token 处理"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.utcnow() + timedelta(seconds=settings.access_token_expire)
    to_encode = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(seconds=settings.refresh_token_expire)
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 Token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[dict]:
    """验证 Access Token"""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def verify_refresh_token(token: str) -> Optional[dict]:
    """验证 Refresh Token"""
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None
```

### 5. 消息模型 (models/message.py)

```python
# -*- coding: utf-8 -*-
"""消息模型"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    PENDING = "pending"      # 待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败


class Message(BaseModel):
    """消息模型"""
    message_id: str                    # 消息唯一 ID
    user_id: str                       # 用户 ID
    session_id: str                    # 会话 ID
    text: str                          # 消息内容
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    status: MessageStatus = MessageStatus.PENDING
    response: Optional[str] = None     # AI 响应内容


class MessageQueueItem(BaseModel):
    """轮询返回的消息项"""
    message_id: str
    user_id: str
    session_id: str
    text: str
    timestamp: float


class SendMessageRequest(BaseModel):
    """发送消息请求（QwenPaw 回调）"""
    message_id: str
    user_id: str
    text: str
```

### 6. 消息队列 (messages/queue.py)

```python
# -*- coding: utf-8 -*-
"""消息队列管理"""
import uuid
import time
import threading
from typing import Dict, List, Optional
from collections import defaultdict

from models.message import Message, MessageQueueItem, MessageStatus


class MessageQueue:
    """内存消息队列（单机部署）"""

    def __init__(self):
        # message_id -> Message
        self._messages: Dict[str, Message] = {}
        # session_id -> List[message_id]（按时间排序）
        self._sessions: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def add_message(self, user_id: str, session_id: str, text: str) -> str:
        """添加用户消息到队列"""
        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            user_id=user_id,
            session_id=session_id,
            text=text,
            timestamp=time.time(),
            status=MessageStatus.PENDING,
        )

        with self._lock:
            self._messages[message_id] = message
            self._sessions[session_id].append(message_id)

        return message_id

    def poll_pending(self, limit: int = 10) -> List[MessageQueueItem]:
        """轮询待处理消息（QwenPaw 调用）"""
        result = []
        with self._lock:
            for msg_id, msg in self._messages.items():
                if msg.status == MessageStatus.PENDING:
                    result.append(MessageQueueItem(
                        message_id=msg.message_id,
                        user_id=msg.user_id,
                        session_id=msg.session_id,
                        text=msg.text,
                        timestamp=msg.timestamp,
                    ))
                    msg.status = MessageStatus.PROCESSING

        return result[:limit]

    def set_response(self, message_id: str, response: str) -> bool:
        """设置消息的 AI 响应"""
        with self._lock:
            if message_id not in self._messages:
                return False
            msg = self._messages[message_id]
            msg.response = response
            msg.status = MessageStatus.COMPLETED
        return True

    def get_response(self, message_id: str) -> Optional[str]:
        """获取消息的 AI 响应"""
        with self._lock:
            msg = self._messages.get(message_id)
            return msg.response if msg else None


# 全局消息队列实例
message_queue = MessageQueue()
```

### 7. 认证路由 (auth/routes.py)

```python
# -*- coding: utf-8 -*-
"""认证路由"""
from fastapi import APIRouter, HTTPException, status

from config import settings
from models.user import LoginRequest, RefreshRequest, TokenResponse
from auth.jwt_handler import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from auth.user_store import user_store  # 用户存储（见下方）


router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    # 验证客户端凭证
    if request.client_id != settings.client_id:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if request.client_secret != settings.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    # 验证用户
    user = user_store.get_by_username(request.username)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # 生成 Token
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """刷新 Access Token"""
    # 验证客户端凭证
    if request.client_id != settings.client_id:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if request.client_secret != settings.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    # 验证 Refresh Token
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 获取用户
    user_id = payload.get("sub")
    user = user_store.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 生成新 Token
    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire,
    )
```

### 8. 用户存储 (auth/user_store.py)

```python
# -*- coding: utf-8 -*-
"""用户存储（内存实现，生产环境请使用数据库）"""
import threading
from typing import Dict, Optional

from models.user import User, UserInDB
from auth.jwt_handler import hash_password


class UserStore:
    """用户存储（内存版）"""

    def __init__(self):
        self._users: Dict[str, UserInDB] = {}
        self._username_index: Dict[str, str] = {}  # username -> user_id
        self._lock = threading.Lock()

    def create(self, username: str, password: str) -> User:
        """创建用户"""
        user_id = f"user_{len(self._users) + 1}"
        password_hash = hash_password(password)
        user = UserInDB(
            id=user_id,
            username=username,
            password_hash=password_hash,
        )

        with self._lock:
            self._users[user_id] = user
            self._username_index[username] = user_id

        return User(id=user_id, username=username, password_hash=password_hash)

    def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        return self._users.get(user_id)

    def get_by_username(self, username: str) -> Optional[UserInDB]:
        user_id = self._username_index.get(username)
        return self._users.get(user_id) if user_id else None

    def exists(self, username: str) -> bool:
        return username in self._username_index


# 全局用户存储
user_store = UserStore()

# 创建默认测试用户
user_store.create("test", "test123")
```

### 9. 消息路由 (messages/routes.py)

```python
# -*- coding: utf-8 -*-
"""消息路由"""
from fastapi import APIRouter, HTTPException, Header, status
from typing import List, Optional

from models.message import MessageQueueItem, SendMessageRequest
from auth.jwt_handler import verify_access_token
from messages.queue import message_queue


router = APIRouter(prefix="/api/messages", tags=["消息"])


async def verify_auth(authorization: Optional[str]) -> dict:
    """验证 Bearer Token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = parts[1]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return payload


@router.get("/poll")
async def poll_messages(authorization: str = Header(...)):
    """轮询获取待处理消息（QwenPaw 调用）"""
    await verify_auth(authorization)
    messages = message_queue.poll_pending(limit=10)
    return messages


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    authorization: str = Header(...),
):
    """发送消息响应（QwenPaw 调用）"""
    await verify_auth(authorization)

    success = message_queue.set_response(request.message_id, request.text)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"status": "ok"}


# ── 以下为 App 端调用的接口（用于发送用户消息） ───────────────────────

@router.post("/submit")
async def submit_message(
    authorization: str = Header(...),
    session_id: str = None,
    text: str = None,
):
    """提交用户消息（App 调用）"""
    payload = await verify_auth(authorization)

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    if not session_id:
        session_id = f"session_{payload.get('sub')}"

    user_id = payload.get("sub")
    message_id = message_queue.add_message(user_id, session_id, text)

    return {"message_id": message_id, "status": "queued"}


@router.get("/response/{message_id}")
async def get_response(
    message_id: str,
    authorization: str = Header(...),
):
    """获取消息响应（App 轮询）"""
    await verify_auth(authorization)

    response = message_queue.get_response(message_id)
    if response is None:
        return {"status": "pending", "response": None}

    return {"status": "completed", "response": response}
```

### 10. 主入口 (main.py)

```python
# -*- coding: utf-8 -*-
"""App Server 主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from auth.routes import router as auth_router
from messages.routes import router as messages_router


app = FastAPI(
    title="QwenPaw App Server",
    description="配合 QwenPaw MyApp Channel 的消息服务端",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(messages_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
```

## 接口清单

| 接口 | 方法 | 认证 | 用途 |
|------|------|------|------|
| `/api/auth/login` | POST | client_id/secret | 用户登录，获取 Token |
| `/api/auth/refresh` | POST | client_id/secret | 刷新 Access Token |
| `/api/messages/poll` | GET | Bearer Token | QwenPaw 轮询获取消息 |
| `/api/messages/send` | POST | Bearer Token | QwenPaw 发送 AI 响应 |
| `/api/messages/submit` | POST | Bearer Token | App 提交用户消息 |
| `/api/messages/response/{id}` | GET | Bearer Token | App 获取 AI 响应 |
| `/health` | GET | 无 | 健康检查 |

## 部署

```bash
# 安装依赖
pip install fastapi uvicorn python-jose passlib pydantic

# 配置环境变量
export JWT_SECRET="your-secret-key"
export CLIENT_ID="qwenpaw-client"
export CLIENT_SECRET="your-client-secret"

# 启动服务
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 消息流程

```
App (用户)                App Server                  QwenPaw
   │                         │                          │
   │── POST /submit ─────────>│                          │
   │   (用户发消息)           │                          │
   │                         │                          │
   │                         │<─ GET /messages/poll ─────│
   │                         │   (QwenPaw 轮询)          │
   │                         │── [消息列表] ─────────────>│
   │                         │                          │
   │                         │              Agent 处理   │
   │                         │                          │
   │<── GET /response/{id} ──│                          │
   │   (轮询响应)             │<─ POST /messages/send ───│
   │                         │   (AI 响应)               │
   │                         │                          │
```

## 生产环境建议

1. **数据库**：将 UserStore 和 MessageQueue 替换为 PostgreSQL/SQLite
2. **Redis**：使用 Redis 队列支持分布式部署和多实例
3. **HTTPS**：生产环境务必使用 HTTPS
4. **Token 安全**：JWT Secret 使用足够长的随机字符串
5. **限流**：对 `/api/auth/*` 接口添加限流防止暴力破解