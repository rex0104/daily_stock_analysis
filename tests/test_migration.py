import os
import tempfile
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from src.storage import Base


def _make_db():
    """Create a fresh in-memory DB with all current tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)


def test_schema_version_table_created():
    engine, Session = _make_db()
    from src.migration import ensure_schema_current
    ensure_schema_current(engine)
    inspector = inspect(engine)
    assert "_schema_version" in inspector.get_table_names()


def test_migration_is_idempotent():
    engine, Session = _make_db()
    from src.migration import ensure_schema_current
    ensure_schema_current(engine)
    ensure_schema_current(engine)  # second call should not fail
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version FROM _schema_version")).fetchall()
    versions = [r[0] for r in rows]
    assert versions.count(1) == 1
