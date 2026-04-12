"""Per-user stock watchlist (favorites) service."""
from __future__ import annotations
import logging
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from src.storage import UserWatchlist, UserWatchlistGroup

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

    # ------------------------------------------------------------------
    # Group CRUD
    # ------------------------------------------------------------------

    def create_group(self, user_id: str, name: str) -> Dict[str, Any]:
        gid = uuid.uuid4().hex[:16]
        with self._sf() as session:
            # Determine next sort_order
            max_order = (
                session.query(UserWatchlistGroup.sort_order)
                .filter(UserWatchlistGroup.user_id == user_id)
                .order_by(UserWatchlistGroup.sort_order.desc())
                .first()
            )
            next_order = (max_order[0] + 1) if max_order else 1
            group = UserWatchlistGroup(
                id=gid, user_id=user_id, name=name, sort_order=next_order,
            )
            session.add(group)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.query(UserWatchlistGroup).filter_by(
                    user_id=user_id, name=name).first()
                if existing:
                    return self._group_to_dict(existing)
                raise
            return self._group_to_dict(group)

    def rename_group(self, user_id: str, group_id: str, name: str) -> bool:
        with self._sf() as session:
            group = session.query(UserWatchlistGroup).filter_by(
                id=group_id, user_id=user_id).first()
            if not group:
                return False
            group.name = name
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
            return True

    def delete_group(self, user_id: str, group_id: str) -> bool:
        if group_id == "default":
            return False
        with self._sf() as session:
            group = session.query(UserWatchlistGroup).filter_by(
                id=group_id, user_id=user_id).first()
            if not group:
                return False
            # Move items in this group back to default
            session.query(UserWatchlist).filter_by(
                user_id=user_id, group_id=group_id
            ).update({"group_id": "default"})
            session.delete(group)
            session.commit()
            return True

    def list_groups(self, user_id: str) -> List[Dict[str, Any]]:
        with self._sf() as session:
            groups = (
                session.query(UserWatchlistGroup)
                .filter(UserWatchlistGroup.user_id == user_id)
                .order_by(UserWatchlistGroup.sort_order)
                .all()
            )
            return [self._group_to_dict(g) for g in groups]

    # ------------------------------------------------------------------
    # Reorder
    # ------------------------------------------------------------------

    def reorder(self, user_id: str, items: List[Dict[str, Any]]) -> None:
        with self._sf() as session:
            for entry in items:
                session.query(UserWatchlist).filter_by(
                    user_id=user_id, stock_code=entry["stock_code"],
                ).update({
                    "sort_order": entry["sort_order"],
                    "group_id": entry["group_id"],
                })
            session.commit()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(item: UserWatchlist) -> Dict[str, Any]:
        return {
            "stock_code": item.stock_code,
            "stock_name": item.stock_name,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

    @staticmethod
    def _group_to_dict(group: UserWatchlistGroup) -> Dict[str, Any]:
        return {
            "group_id": group.id,
            "name": group.name,
            "sort_order": group.sort_order,
            "created_at": group.created_at.isoformat() if group.created_at else None,
        }
