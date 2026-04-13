from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.storage import Base, User
from src.migration import ensure_schema_current


def test_user_has_schedule_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("users")]
    assert "schedule_enabled" in cols
    assert "schedule_time" in cols
    assert "onboarding_completed" in cols


def test_user_schedule_defaults():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        u = User(id="u1", email="t@t.com", nickname="t", password_hash="h", password_salt="s")
        s.add(u)
        s.commit()
        s.refresh(u)
        assert u.schedule_enabled is False
        assert u.schedule_time == "09:15"
        assert u.onboarding_completed is False


def test_migration_v4_idempotent():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    ensure_schema_current(engine)  # second call should not fail
