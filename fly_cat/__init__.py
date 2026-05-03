# -*- coding: utf-8 -*-
"""
MyApp Channel - 轮询模式对接 App 服务端

功能特性：
  - 登录认证（获取/刷新 Access Token）
  - 自动 Token 刷新（401 时）
  - 轮询获取消息
  - 发送消息

配置项（环境变量）:
  - MYAPP_BASE_URL:      App 服务端基础地址
  - MYAPP_LOGIN_URL:     登录接口路径
  - MYAPP_REFRESH_URL:   Token 刷新接口路径
  - MYAPP_CLIENT_ID:     App 客户端 ID
  - MYAPP_CLIENT_SECRET: App 客户端密钥
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Callable, Optional

import httpx

from qwenpaw.app.channels.base import (
    BaseChannel,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
    TextContent,
    ContentType,
)
from qwenpaw.app.channels.schema import ChannelType

logger = logging.getLogger(__name__)


class TokenManager:
    """Token 管理器：存储、刷新、自动续期"""

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        login_url: str,
        refresh_url: str,
        http: httpx.AsyncClient,
        username: str = "",
        password: str = "",
    ):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.login_url = login_url
        self.refresh_url = refresh_url
        self._http = http
        self._username = username
        self._password = password

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0  # Unix timestamp

    async def login(self, username: str, password: str) -> bool:
        """用户登录，获取 Token"""
        try:
            response = await self._http.post(
                f"{self.base_url}{self.login_url}",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": username,
                    "password": password,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)
            self._expires_at = time.time() + expires_in

            logger.info("Token login successful")
            return True

        except Exception as e:
            logger.error("Token login failed: %s", e)
            return False

    async def refresh(self) -> bool:
        """刷新 Access Token"""
        if not self._refresh_token:
            # 兜底：如果没有 refresh_token，尝试用用户名密码重新登录
            if self._username and self._password:
                logger.info("No refresh token, attempting fallback login...")
                if await self.login(self._username, self._password):
                    return True
            logger.warning("No refresh token available")
            return False

        try:
            response = await self._http.post(
                f"{self.base_url}{self.refresh_url}",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self._refresh_token,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            expires_in = data.get("expires_in", 3600)
            self._expires_at = time.time() + expires_in

            logger.info("Token refreshed successfully")
            return True

        except Exception as e:
            logger.error("Token refresh failed: %s", e)
            self._access_token = None
            self._refresh_token = None
            return False

    async def ensure_valid(self) -> bool:
        """确保 Token 有效，必要时刷新"""
        if self._access_token and time.time() < self._expires_at - 60:
            return True  # Token 有效

        return await self.refresh()

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    def clear(self):
        """清除 Token（登出）"""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = 0


class FlyCatChannel(BaseChannel):
    """轮询模式 Channel，对接 App 服务端，支持登录认证"""

    channel = ChannelType("fly_cat")

    def __init__(
        self,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
        base_url: str = "",
        poll_path: str = "/api/messages/poll",
        send_path: str = "/api/messages/send",
        login_path: str = "/api/auth/login",
        refresh_path: str = "/api/auth/refresh",
        client_id: str = "",
        client_secret: str = "",
        poll_interval: float = 5.0,
        username: str = "",
        password: str = "",
        **kwargs,
    ):
        super().__init__(process, on_reply_sent, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.poll_path = poll_path
        self.send_path = send_path
        self.login_path = login_path
        self.refresh_path = refresh_path
        self.client_id = client_id
        self.client_secret = client_secret
        self.poll_interval = poll_interval
        self.username = username
        self.password = password

        self._poll_task: Optional[asyncio.Task] = None
        self._running = False
        self._http = httpx.AsyncClient(timeout=30.0)
        self._token_manager = TokenManager(
            base_url=self.base_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
            login_url=self.login_path,
            refresh_url=self.refresh_path,
            http=self._http,
            username=self.username,
            password=self.password,
        )

        # 用户会话存储：user_id -> session_data
        self._user_sessions: dict[str, dict] = {}

    @classmethod
    def from_env(cls, process, on_reply_sent=None) -> "FlyCatChannel":
        return cls(
            process=process,
            on_reply_sent=on_reply_sent,
            base_url=os.getenv("FLYCAT_BASE_URL", ""),
            poll_path=os.getenv("FLYCAT_POLL_PATH", "/api/messages/poll"),
            send_path=os.getenv("FLYCAT_SEND_PATH", "/api/messages/send"),
            login_path=os.getenv("FLYCAT_LOGIN_PATH", "/api/auth/login"),
            refresh_path=os.getenv("FLYCAT_REFRESH_PATH", "/api/auth/refresh"),
            client_id=os.getenv("FLYCAT_CLIENT_ID", ""),
            client_secret=os.getenv("FLYCAT_CLIENT_SECRET", ""),
            poll_interval=float(os.getenv("FLYCAT_POLL_INTERVAL", "5")),
        )

    @classmethod
    def from_config(cls, process, config, on_reply_sent=None, workspace_dir=None) -> "FlyCatChannel":
        return cls(
            process=process,
            on_reply_sent=on_reply_sent,
            base_url=config.base_url or "",
            poll_path=getattr(config, "poll_path", "/api/messages/poll"),
            send_path=getattr(config, "send_path", "/api/messages/send"),
            login_path=getattr(config, "login_path", "/api/auth/login"),
            refresh_path=getattr(config, "refresh_path", "/api/auth/refresh"),
            client_id=getattr(config, "client_id", ""),
            client_secret=getattr(config, "client_secret", ""),
            poll_interval=getattr(config, "poll_interval", 5.0),
            username=getattr(config, "username", ""),
            password=getattr(config, "password", ""),
        )

    async def start(self) -> None:
        """启动轮询任务"""
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("MyApp channel started (poll_interval=%.1f)", self.poll_interval)

    async def stop(self) -> None:
        """停止轮询任务"""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        await self._http.aclose()
        logger.info("MyApp channel stopped")

    # ── 认证接口 ────────────────────────────────────────────────

    async def user_login(self, username: str, password: str) -> dict:
        """
        用户登录

        Returns:
            {"success": True, "user_id": "xxx"} 或 {"success": False, "error": "..."}
        """
        success = await self._token_manager.login(username, password)
        if success:
            # 生成伪 user_id 用于会话关联
            import uuid
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            self._user_sessions[user_id] = {
                "username": username,
                "login_time": time.time(),
            }
            return {"success": True, "user_id": user_id}
        return {"success": False, "error": "Login failed"}

    async def user_logout(self, user_id: str) -> None:
        """用户登出"""
        if user_id in self._user_sessions:
            del self._user_sessions[user_id]
        self._token_manager.clear()

    async def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户会话信息"""
        return self._user_sessions.get(user_id)

    # ── Token 自动刷新 ─────────────────────────────────────────

    async def _request_with_auth(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """
        带认证的请求，自动处理 401 刷新
        """
        headers = kwargs.pop("headers", {})
        token = self._token_manager.access_token
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = await self._http.request(method, url, headers=headers, **kwargs)

        # 401 => 尝试刷新 Token 后重试
        if response.status_code == 401:
            logger.info("Got 401, attempting token refresh...")
            if await self._token_manager.refresh():
                headers["Authorization"] = f"Bearer {self._token_manager.access_token}"
                response = await self._http.request(method, url, headers=headers, **kwargs)

        return response

    # ── 轮询逻辑 ────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """定期轮询消息队列"""
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("MyApp poll error")
            await asyncio.sleep(self.poll_interval)

    async def _poll_once(self) -> None:
        """一次轮询，获取并处理消息"""
        # 确保 Token 有效
        if not await self._token_manager.ensure_valid():
            logger.debug("No valid token, skipping poll")
            return

        try:
            url = f"{self.base_url}{self.poll_path}"
            response = await self._request_with_auth("GET", url)
            response.raise_for_status()
            messages = response.json()
        except Exception as e:
            logger.debug("MyApp poll failed: %s", e)
            return

        if not messages or not isinstance(messages, list):
            return

        for msg in messages:
            payload = self._normalize_message(msg)
            if payload:
                self._enqueue(payload)

    def _normalize_message(self, msg: dict) -> dict | None:
        """
        将 App 消息格式转换为 native_payload 格式

        App 消息格式:
        {
            "message_id": "12345",
            "user_id": "user_001",
            "session_id": "sess_abc",
            "text": "你好",
            "timestamp": 1234567890
        }
        """
        try:
            text = msg.get("text", "")
            user_id = msg.get("user_id", "")
            session_id = msg.get("session_id", "")
            message_id = msg.get("message_id", "")

            return {
                "channel_id": self.channel,
                "sender_id": user_id,
                "user_id": user_id,
                "session_id": f"{self.channel}:{session_id}",
                "content_parts": [TextContent(type=ContentType.TEXT, text=text)],
                "meta": {
                    "message_id": message_id,
                    "timestamp": msg.get("timestamp"),
                    "send_url": f"{self.base_url}{self.send_path}",
                },
            }
        except Exception as e:
            logger.warning("Failed to normalize message: %s", e)
            return None

    # ── AgentRequest 转换 ─────────────────────────────────────

    def build_agent_request_from_native(self, native_payload: dict) -> Any:
        sender_id = native_payload.get("sender_id", "")
        content_parts = native_payload.get("content_parts", [])
        session_id = native_payload.get("session_id", "")
        channel_meta = native_payload.get("meta", {})

        request = self.build_agent_request_from_user_content(
            channel_id=self.channel,
            sender_id=sender_id,
            session_id=session_id,
            content_parts=content_parts,
            channel_meta=channel_meta,
        )
        request.channel_meta = channel_meta
        return request

    # ── 发送响应 ──────────────────────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[dict] = None,
    ) -> None:
        """发送文本消息到 App 服务端"""
        meta = meta or {}
        send_url = meta.get("send_url") or f"{self.base_url}{self.send_path}"
        message_id = meta.get("message_id", "")

        payload = {
            "message_id": message_id,
            "user_id": to_handle,
            "text": text,
        }

        try:
            response = await self._request_with_auth("POST", send_url, json=payload)
            response.raise_for_status()
            logger.debug("MyApp send success: %s", message_id)
        except Exception as e:
            logger.error("MyApp send failed: %s", e)

    async def send_content_parts(
        self,
        to_handle: str,
        parts: list[OutgoingContentPart],
        meta: Optional[dict] = None,
    ) -> None:
        """发送多种内容类型"""
        text_parts = []
        for p in parts:
            if hasattr(p, "type") and p.type == ContentType.TEXT:
                text_parts.append(getattr(p, "text", ""))
            elif hasattr(p, "type") and p.type == "refusal":
                text_parts.append(f"[拒绝]: {getattr(p, 'refusal', '')}")
            else:
                text_parts.append(f"[{getattr(p, 'type', 'unknown')}]")

        text = "\n".join(text_parts)
        await self.send(to_handle, text, meta)

    # ── 健康检查 ──────────────────────────────────────────────

    async def health_check(self) -> dict:
        return {
            "channel": self.channel,
            "status": "healthy" if self._running else "stopped",
            "base_url": self.base_url,
            "poll_interval": self.poll_interval,
            "token_valid": self._token_manager.access_token is not None,
        }