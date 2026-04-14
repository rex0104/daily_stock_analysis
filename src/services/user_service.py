"""User registration, login, and password management."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.storage import User

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 100_000
MIN_PASSWORD_LEN = 6


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return base64.b64encode(dk).decode("ascii")


def _verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    salt = base64.b64decode(salt_b64)
    computed = _hash_password(password, salt)
    return computed == hash_b64


class UserService:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    def register(self, email: str, password: str) -> Dict[str, Any]:
        email = email.strip().lower()
        if len(password) < MIN_PASSWORD_LEN:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters")
        salt = os.urandom(32)
        salt_b64 = base64.b64encode(salt).decode("ascii")
        hash_b64 = _hash_password(password, salt)
        user_id = uuid.uuid4().hex
        nickname = email.split("@")[0]
        with self._sf() as session:
            user = User(id=user_id, email=email, nickname=nickname,
                        password_hash=hash_b64, password_salt=salt_b64)
            session.add(user)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ValueError(f"Email {email} is already registered")
            return {"id": user.id, "email": user.email, "nickname": user.nickname}

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        email = email.strip().lower()
        with self._sf() as session:
            user = session.query(User).filter_by(email=email).first()
            if not user:
                return None
            if not _verify_password(password, user.password_salt, user.password_hash):
                return None
            return {"id": user.id, "email": user.email, "nickname": user.nickname}

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        if len(new_password) < MIN_PASSWORD_LEN:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters")
        with self._sf() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            if not _verify_password(current_password, user.password_salt, user.password_hash):
                raise ValueError("Current password is incorrect")
            salt = os.urandom(32)
            user.password_salt = base64.b64encode(salt).decode("ascii")
            user.password_hash = _hash_password(new_password, salt)
            session.commit()

    def reset_password(self, user_id: str, new_password: str) -> None:
        """Reset a user's password without requiring the current password."""
        if len(new_password) < MIN_PASSWORD_LEN:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters")
        with self._sf() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            salt = os.urandom(32)
            user.password_salt = base64.b64encode(salt).decode("ascii")
            user.password_hash = _hash_password(new_password, salt)
            session.commit()

    def has_users(self) -> bool:
        with self._sf() as session:
            return session.query(User.id).first() is not None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._sf() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            return {"id": user.id, "email": user.email, "nickname": user.nickname}
