# -*- coding: utf-8 -*-
"""认证路由"""
from fastapi import APIRouter, HTTPException, Depends

from config import settings
from schemas.user import LoginRequest, RefreshRequest, TokenResponse
from auth.jwt_handler import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from database import get_db
from sqlalchemy.orm import Session
from auth.user_store import UserStore

router = APIRouter(prefix="/api/auth", tags=["认证"])


def get_user_store(db: Session = Depends(get_db)):
    from auth.user_store import UserStore
    return UserStore(db)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, user_store: UserStore = Depends(get_user_store)):
    if request.client_id != settings.client_id:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if request.client_secret != settings.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    user = user_store.get_by_username(request.username)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, user_store: UserStore = Depends(get_user_store)):
    if request.client_id != settings.client_id:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if request.client_secret != settings.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    user = user_store.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire,
    )