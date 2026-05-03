# -*- coding: utf-8 -*-
"""消息模型 - SQLAlchemy ORM"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Text
from database import Base


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    text = Column(Text)
    timestamp = Column(Float)
    status = Column(String, default="pending")
    response = Column(Text, nullable=True)