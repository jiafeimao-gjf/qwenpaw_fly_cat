# -*- coding: utf-8 -*-
"""FlyCat Channel 配置"""
from typing import Optional
from pydantic import BaseModel, Field


class FlyCatConfig(BaseModel):
    """FlyCat Channel 配置项"""

    enabled: bool = False

    # 服务器配置
    base_url: str = Field(default="", description="App 服务端基础地址")
    poll_path: str = Field(default="/api/messages/poll", description="轮询获取消息路径")
    send_path: str = Field(default="/api/messages/send", description="发送消息路径")

    # 认证配置
    login_path: str = Field(default="/api/auth/login", description="登录接口路径")
    refresh_path: str = Field(default="/api/auth/refresh", description="Token 刷新路径")
    client_id: str = Field(default="", description="App 客户端 ID")
    client_secret: str = Field(default="", description="App 客户端密钥")

    # 兜底登录配置（用于无 refresh_token 时自动登录）
    username: str = Field(default="", description="用户名（可选，用于自动登录）")
    password: str = Field(default="", description="密码（可选，用于自动登录）")

    # 轮询配置
    poll_interval: float = Field(default=5.0, description="轮询间隔（秒）")

    # 通用配置（继承自 BaseChannelConfig）
    bot_prefix: str = ""
    filter_tool_messages: bool = False
    filter_thinking: bool = False
    dm_policy: str = "open"
    group_policy: str = "open"
    allow_from: Optional[list] = None
    deny_message: str = ""
    require_mention: bool = False