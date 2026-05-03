# -*- coding: utf-8 -*-
"""消息模型 - Pydantic schemas"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    text: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    status: MessageStatus = MessageStatus.PENDING
    response: Optional[str] = None


class MessageQueueItem(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    text: str
    timestamp: float


class SendMessageRequest(BaseModel):
    message_id: str
    user_id: str
    text: str