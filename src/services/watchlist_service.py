"""Per-user stock watchlist (favorites) service."""
from __future__ import annotations
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from src.storage import UserWatchlist

logger = logging.getLogger(__name__)


class WatchlistService:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    def add(self, user_id: str, stock_code: str, stock_name: str = None) -> Dict[str, Any]:
        with self._sf() as session:
            existing = session.query(UserWatchlist).filter_by(
                user_id=user_id, stock_code=stock_code).first()
            if existing:
                return self._to_dict(existing)
            item = UserWatchlist(user_id=user_id, stock_code=stock_code, stock_name=stock_name)
            session.add(item)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return self._to_dict(session.query(UserWatchlist).filter_by(
                    user_id=user_id, stock_code=stock_code).first())
            return self._to_dict(item)

    def remove(self, user_id: str, stock_code: str) -> bool:
        with self._sf() as session:
            item = session.query(UserWatchlist).filter_by(
                user_id=user_id, stock_code=stock_code).first()
            if not item:
                return False
            session.delete(item)
            session.commit()
            return True

    def list(self, user_id: str) -> List[Dict[str, Any]]:
        with self._sf() as session:
            items = session.query(UserWatchlist).filter_by(user_id=user_id)\
                .order_by(UserWatchlist.created_at.desc()).all()
            return [self._to_dict(i) for i in items]

    def is_watched(self, user_id: str, stock_code: str) -> bool:
        with self._sf() as session:
            return session.query(UserWatchlist.id).filter_by(
                user_id=user_id, stock_code=stock_code).first() is not None

    @staticmethod
    def _to_dict(item: UserWatchlist) -> Dict[str, Any]:
        return {
            "stock_code": item.stock_code,
            "stock_name": item.stock_name,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
