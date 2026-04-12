"""One-time migration: assign orphan data to the first registered user."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_TABLES_WITH_USER_ID = [
    "analysis_history",
    "conversation_messages",
    "backtest_results",
    "backtest_summaries",
    "llm_usage",
]


def claim_orphan_data(session_factory: sessionmaker, user_id: str) -> None:
    """Assign all user_id=NULL rows to the given user and clean up old auth files."""
    try:
        with session_factory() as session:
            for table in _TABLES_WITH_USER_ID:
                result = session.execute(
                    text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                    {"uid": user_id},
                )
                if result.rowcount:
                    logger.info("Claimed %d orphan rows in %s", result.rowcount, table)

            # portfolio_accounts uses owner_id
            result = session.execute(
                text("UPDATE portfolio_accounts SET owner_id = :uid "
                     "WHERE owner_id IS NULL OR owner_id = ''"),
                {"uid": user_id},
            )
            if result.rowcount:
                logger.info("Claimed %d orphan portfolio accounts", result.rowcount)

            # news_intel uses requester_user_id
            result = session.execute(
                text("UPDATE news_intel SET requester_user_id = :uid "
                     "WHERE requester_user_id IS NULL OR requester_user_id = ''"),
                {"uid": user_id},
            )
            if result.rowcount:
                logger.info("Claimed %d orphan news_intel rows", result.rowcount)

            session.commit()
    except Exception:
        logger.exception("Failed to claim orphan data for user %s", user_id)

    _migrate_env_to_user_settings(session_factory, user_id)
    _cleanup_old_auth_files()


def _migrate_env_to_user_settings(session_factory: sessionmaker, user_id: str) -> None:
    """Copy current .env values into the first user's settings column."""
    import json

    from dotenv import dotenv_values
    from src.storage import User

    env_path = (
        Path(os.getenv("ENV_FILE")).resolve()
        if os.getenv("ENV_FILE")
        else Path(__file__).resolve().parent.parent.parent / ".env"
    )
    if not env_path.exists():
        return

    env_values = dotenv_values(env_path)
    settings = {k: v for k, v in env_values.items() if v is not None and v.strip()}

    if not settings:
        return

    try:
        with session_factory() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.settings = json.dumps(settings, ensure_ascii=False)
                session.commit()
                logger.info("Migrated %d .env settings to first user", len(settings))
    except Exception:
        logger.exception("Failed to migrate .env settings for user %s", user_id)


def _cleanup_old_auth_files() -> None:
    db_path = os.getenv("DATABASE_PATH", "./data/stock_analysis.db")
    data_dir = Path(db_path).resolve().parent
    for name in (".admin_password_hash", ".session_secret"):
        path = data_dir / name
        if path.exists():
            try:
                path.unlink()
                logger.info("Removed legacy auth file: %s", path)
            except OSError:
                logger.warning("Could not remove %s", path)
