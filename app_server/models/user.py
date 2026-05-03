# -*- coding: utf-8 -*-
"""用户模型 - SQLAlchemy ORM"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)