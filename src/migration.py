"""
Startup schema migration — runs once per version bump.

Convention:
  - Version 0: baseline (pre-multi-user schema, handled by create_all)
  - Version 1: add user_id columns to existing tables
  - Future versions: append new _migrate_vN functions
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_CURRENT_VERSION = 1


def ensure_schema_current(engine: Engine) -> None:
    """Check schema version and apply pending migrations."""
    _ensure_version_table(engine)
    current = _get_version(engine)
    if current >= _CURRENT_VERSION:
        return

    migrations: List[tuple] = [
        (1, _migrate_v1),
    ]

    for ver, fn in migrations:
        if current < ver:
            logger.info("Applying schema migration v%d …", ver)
            try:
                fn(engine)
                _set_version(engine, ver)
                logger.info("Schema migration v%d applied.", ver)
            except Exception:
                logger.exception("Schema migration v%d FAILED — skipping.", ver)
                return


def _ensure_version_table(engine: Engine) -> None:
    inspector = inspect(engine)
    if "_schema_version" not in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE _schema_version ("
                "  version INTEGER NOT NULL,"
                "  applied_at DATETIME NOT NULL"
                ")"
            ))


def _get_version(engine: Engine) -> int:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT MAX(version) FROM _schema_version")
        ).fetchone()
        return row[0] if row and row[0] is not None else 0


def _set_version(engine: Engine, version: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO _schema_version (version, applied_at) VALUES (:v, :t)"),
            {"v": version, "t": datetime.now().isoformat()},
        )


def _has_column(engine: Engine, table: str, column: str) -> bool:
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def _migrate_v1(engine: Engine) -> None:
    """Add user_id columns to existing tables for multi-user isolation."""
    tables_needing_user_id = [
        "analysis_history",
        "conversation_messages",
        "backtest_results",
        "backtest_summaries",
        "llm_usage",
    ]
    with engine.begin() as conn:
        for table in tables_needing_user_id:
            if not _has_column(engine, table, "user_id"):
                conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(32)"
                ))
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id ON {table} (user_id)"
                ))
