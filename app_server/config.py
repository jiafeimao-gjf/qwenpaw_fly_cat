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