# -*- coding: utf-8 -*-
"""用户存储（SQLite）"""
from typing import Optional
from sqlalchemy.orm import Session

from models.user import User
from auth.jwt_handler import hash_password


class UserStore:
    def __init__(self, db: Session):
        self.db = db

    def create(self, username: str, password: str) -> User:
        user_id = f"user_{self._count() + 1}"
        password_hash = hash_password(password)
        user = User(id=user_id, username=username, password_hash=password_hash)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def exists(self, username: str) -> bool:
        return self.db.query(User).filter(User.username == username).first() is not None

    def _count(self) -> int:
        return self.db.query(User).count()