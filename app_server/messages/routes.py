# -*- coding: utf-8 -*-
"""消息路由"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header, status, Body, Depends, Query
from typing import Optional, List, TYPE_CHECKING

from schemas.message import SendMessageRequest, MessageQueueItem
from auth.jwt_handler import verify_access_token
from database import get_db
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from messages.queue import MessageQueue

router = APIRouter(prefix="/api/messages", tags=["消息"])


def get_message_queue(db: Session = Depends(get_db)):
    from messages.queue import MessageQueue
    return MessageQueue(db)


async def verify_auth(authorization: Optional[str]) -> dict:
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
async def poll_messages(authorization: str = Header(...), queue: MessageQueue = Depends(get_message_queue)):
    await verify_auth(authorization)
    messages = queue.poll_pending(limit=10)
    return messages


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    authorization: str = Header(...),
    queue: MessageQueue = Depends(get_message_queue),
):
    await verify_auth(authorization)
    success = queue.set_response(request.message_id, request.text)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "ok"}


@router.post("/submit")
async def submit_message(
    authorization: str = Header(...),
    payload: dict = Body(...),
    queue: MessageQueue = Depends(get_message_queue),
):
    auth_payload = await verify_auth(authorization)

    text = payload.get("text")
    session_id = payload.get("session_id")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    if not session_id:
        session_id = f"session_{auth_payload.get('sub')}"

    user_id = auth_payload.get("sub")
    message_id = queue.add_message(user_id, session_id, text)

    return {"message_id": message_id, "status": "queued"}


@router.get("/response/{message_id}")
async def get_response(
    message_id: str,
    authorization: str = Header(...),
    queue: MessageQueue = Depends(get_message_queue),
):
    await verify_auth(authorization)
    response = queue.get_response(message_id)
    if response is None:
        return {"status": "pending", "response": None}
    return {"status": "completed", "response": response}


@router.get("/history")
async def get_history(
    authorization: str = Header(...),
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    queue: MessageQueue = Depends(get_message_queue),
):
    """获取历史消息"""
    auth_payload = await verify_auth(authorization)
    user_id = auth_payload.get("sub")
    messages = queue.get_history(user_id, session_id, limit)
    return {"messages": messages, "count": len(messages)}


@router.get("/sessions")
async def get_sessions(
    authorization: str = Header(...),
    queue: MessageQueue = Depends(get_message_queue),
):
    """获取用户会话列表"""
    auth_payload = await verify_auth(authorization)
    user_id = auth_payload.get("sub")
    sessions = queue.get_sessions(user_id)
    return {"sessions": sessions}