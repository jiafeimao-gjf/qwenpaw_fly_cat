# -*- coding: utf-8 -*-
"""消息队列管理（SQLite）"""
import uuid
import time
from typing import List, Optional
from sqlalchemy.orm import Session

from models.message import Message


class MessageQueue:
    def __init__(self, db: Session):
        self.db = db

    def add_message(self, user_id: str, session_id: str, text: str) -> str:
        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            user_id=user_id,
            session_id=session_id,
            text=text,
            timestamp=time.time(),
            status="pending",
        )
        self.db.add(message)
        self.db.commit()
        return message_id

    def poll_pending(self, limit: int = 10) -> List[dict]:
        messages = self.db.query(Message).filter(
            Message.status == "pending"
        ).limit(limit).all()

        result = []
        for msg in messages:
            result.append({
                "message_id": msg.message_id,
                "user_id": msg.user_id,
                "session_id": msg.session_id,
                "text": msg.text,
                "timestamp": msg.timestamp,
            })
            msg.status = "processing"
        self.db.commit()
        return result

    def set_response(self, message_id: str, response: str) -> bool:
        message = self.db.query(Message).filter(Message.message_id == message_id).first()
        if not message:
            return False
        message.response = response
        message.status = "completed"
        self.db.commit()
        return True

    def get_response(self, message_id: str) -> Optional[str]:
        message = self.db.query(Message).filter(Message.message_id == message_id).first()
        return message.response if message else None

    def get_history(self, user_id: str, session_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        """获取用户历史消息"""
        query = self.db.query(Message).filter(Message.user_id == user_id)
        if session_id:
            query = query.filter(Message.session_id == session_id)
        messages = query.order_by(Message.timestamp.desc()).limit(limit).all()

        result = []
        for msg in reversed(messages):
            result.append({
                "message_id": msg.message_id,
                "session_id": msg.session_id,
                "text": msg.text,
                "response": msg.response,
                "timestamp": msg.timestamp,
                "status": msg.status,
                "is_user": True,
            })
            if msg.response:
                result.append({
                    "message_id": msg.message_id + "_resp",
                    "session_id": msg.session_id,
                    "text": msg.response,
                    "response": None,
                    "timestamp": msg.timestamp + 0.001,
                    "status": msg.status,
                    "is_user": False,
                })
        return result

    def get_sessions(self, user_id: str) -> List[dict]:
        """获取用户会话列表"""
        messages = self.db.query(Message.session_id).filter(
            Message.user_id == user_id
        ).distinct().all()
        sessions = []
        for msg in messages:
            session_id = msg[0]
            last_msg = self.db.query(Message).filter(
                Message.user_id == user_id,
                Message.session_id == session_id
            ).order_by(Message.timestamp.desc()).first()
            sessions.append({
                "session_id": session_id,
                "last_message": last_msg.text[:50] if last_msg else "",
                "last_timestamp": last_msg.timestamp if last_msg else 0,
            })
        return sorted(sessions, key=lambda x: x["last_timestamp"], reverse=True)