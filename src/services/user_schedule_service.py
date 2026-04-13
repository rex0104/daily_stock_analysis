"""Per-user scheduled watchlist analysis."""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import sessionmaker

from src.storage import User, UserWatchlist

logger = logging.getLogger(__name__)


class UserScheduleService:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    def get_schedule(self, user_id: str) -> Dict[str, Any]:
        with self._sf() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return {"enabled": False, "time": "09:15"}
            return {
                "enabled": user.schedule_enabled,
                "time": user.schedule_time,
            }

    def update_schedule(self, user_id: str, enabled: bool, time: str) -> Dict[str, Any]:
        if not _valid_time(time):
            raise ValueError("Time must be in HH:MM format (00:00 - 23:59)")
        with self._sf() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            user.schedule_enabled = enabled
            user.schedule_time = time
            session.commit()
            return {"enabled": user.schedule_enabled, "time": user.schedule_time}

    def get_due_users(self, hhmm: str) -> List[Dict[str, Any]]:
        """Get all users whose schedule matches the given HH:MM."""
        with self._sf() as session:
            users = (
                session.query(User)
                .filter(User.schedule_enabled == True, User.schedule_time == hhmm)
                .all()
            )
            result = []
            for u in users:
                watchlist = (
                    session.query(UserWatchlist.stock_code)
                    .filter_by(user_id=u.id)
                    .all()
                )
                if watchlist:
                    result.append({
                        "user_id": u.id,
                        "email": u.email,
                        "settings": json.loads(u.settings) if u.settings else {},
                        "stock_codes": [w.stock_code for w in watchlist],
                    })
            return result

    def run_user_analysis(self, user_id: str) -> Dict[str, Any]:
        """Analyze all watchlist stocks for a user using their config."""
        with self._sf() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            watchlist = (
                session.query(UserWatchlist.stock_code)
                .filter_by(user_id=user_id)
                .all()
            )
            stock_codes = [w.stock_code for w in watchlist]
            if not stock_codes:
                return {"success": True, "analyzed": 0, "message": "No stocks in watchlist"}

        user_settings = json.loads(user.settings) if user.settings else {}
        _inject_user_settings(user_settings)

        try:
            from src.services.analysis_service import AnalysisService
            service = AnalysisService()
            results = []
            for code in stock_codes:
                try:
                    result = service.analyze_stock(
                        stock_code=code,
                        report_type="simple",
                        user_id=user_id,
                    )
                    results.append({"code": code, "success": result is not None})
                except Exception as e:
                    logger.warning("Scheduled analysis failed for %s (user %s): %s", code, user_id, e)
                    results.append({"code": code, "success": False, "error": str(e)})
            return {
                "success": True,
                "analyzed": len([r for r in results if r["success"]]),
                "total": len(stock_codes),
                "results": results,
            }
        finally:
            _restore_env(user_settings)


def _valid_time(t: str) -> bool:
    try:
        parts = t.split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except (ValueError, TypeError):
        return False


_saved_env: Dict[str, Optional[str]] = {}


def _inject_user_settings(settings: Dict[str, str]) -> None:
    """Temporarily inject user settings into os.environ."""
    global _saved_env
    _saved_env = {}
    for k, v in settings.items():
        _saved_env[k] = os.environ.get(k)
        if v:
            os.environ[k] = str(v)


def _restore_env(settings: Dict[str, str]) -> None:
    """Restore original environment after user analysis."""
    for k in settings:
        original = _saved_env.get(k)
        if original is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = original
