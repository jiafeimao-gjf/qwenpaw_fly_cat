# -*- coding: utf-8 -*-
"""用户模型 - Pydantic schemas"""
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


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
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