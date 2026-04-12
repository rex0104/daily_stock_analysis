import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage import Base, User, UserWatchlist
from src.migration import ensure_schema_current
from src.services.user_schedule_service import UserScheduleService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        s.add(User(id="u1", email="a@t.com", nickname="a",
                    password_hash="h", password_salt="s"))
        s.commit()
    return sf


@pytest.fixture
def svc(db):
    return UserScheduleService(db)


def test_get_default_schedule(svc):
    result = svc.get_schedule("u1")
    assert result["enabled"] is False
    assert result["time"] == "09:15"


def test_update_schedule(svc):
    result = svc.update_schedule("u1", True, "08:30")
    assert result["enabled"] is True
    assert result["time"] == "08:30"


def test_update_invalid_time(svc):
    with pytest.raises(ValueError, match="HH:MM"):
        svc.update_schedule("u1", True, "25:00")


def test_get_due_users(db):
    svc = UserScheduleService(db)
    svc.update_schedule("u1", True, "09:15")
    with db() as s:
        s.add(UserWatchlist(user_id="u1", stock_code="600519"))
        s.commit()
    due = svc.get_due_users("09:15")
    assert len(due) == 1
    assert due[0]["user_id"] == "u1"
    assert "600519" in due[0]["stock_codes"]


def test_get_due_users_no_match(db):
    svc = UserScheduleService(db)
    svc.update_schedule("u1", True, "09:15")
    due = svc.get_due_users("10:00")
    assert len(due) == 0


def test_get_due_users_disabled(db):
    svc = UserScheduleService(db)
    svc.update_schedule("u1", False, "09:15")
    due = svc.get_due_users("09:15")
    assert len(due) == 0
