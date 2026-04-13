import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage import Base
from src.services.user_service import UserService


@pytest.fixture
def svc():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return UserService(session_factory)


def test_register_creates_user(svc):
    user = svc.register("alice@test.com", "secret123")
    assert user["email"] == "alice@test.com"
    assert user["nickname"] == "alice"
    assert len(user["id"]) == 32


def test_register_duplicate_email_fails(svc):
    svc.register("bob@test.com", "pass1234")
    with pytest.raises(ValueError, match="already registered"):
        svc.register("bob@test.com", "pass5678")


def test_register_short_password_fails(svc):
    with pytest.raises(ValueError, match="at least 6"):
        svc.register("short@test.com", "12345")


def test_login_success(svc):
    svc.register("carol@test.com", "mypassword")
    user = svc.login("carol@test.com", "mypassword")
    assert user["email"] == "carol@test.com"


def test_login_wrong_password(svc):
    svc.register("dave@test.com", "correct")
    assert svc.login("dave@test.com", "wrong") is None


def test_login_unknown_email(svc):
    assert svc.login("nobody@test.com", "pass") is None


def test_change_password(svc):
    svc.register("eve@test.com", "oldpass1")
    user = svc.login("eve@test.com", "oldpass1")
    svc.change_password(user["id"], "oldpass1", "newpass1")
    assert svc.login("eve@test.com", "newpass1") is not None
    assert svc.login("eve@test.com", "oldpass1") is None


def test_change_password_wrong_current(svc):
    svc.register("frank@test.com", "correct1")
    user = svc.login("frank@test.com", "correct1")
    with pytest.raises(ValueError, match="incorrect"):
        svc.change_password(user["id"], "wrong", "newpass1")


def test_is_first_user(svc):
    assert svc.has_users() is False
    svc.register("first@test.com", "pass1234")
    assert svc.has_users() is True


def test_get_user_by_id(svc):
    created = svc.register("get@test.com", "pass1234")
    user = svc.get_user(created["id"])
    assert user["email"] == "get@test.com"
