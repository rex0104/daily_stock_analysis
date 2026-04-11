import uuid
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.storage import Base, User, UserWatchlist, SharedReport


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)


def test_users_table_created():
    engine, _ = _make_db()
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()


def test_watchlists_table_created():
    engine, _ = _make_db()
    inspector = inspect(engine)
    assert "user_watchlists" in inspector.get_table_names()


def test_shared_reports_table_created():
    engine, _ = _make_db()
    inspector = inspect(engine)
    assert "shared_reports" in inspector.get_table_names()


def test_create_and_read_user():
    engine, Session = _make_db()
    user_id = uuid.uuid4().hex
    with Session() as session:
        user = User(
            id=user_id,
            email="test@example.com",
            nickname="test",
            password_hash="fakehash",
            password_salt="fakesalt",
        )
        session.add(user)
        session.commit()
    with Session() as session:
        u = session.query(User).filter_by(id=user_id).one()
        assert u.email == "test@example.com"
        assert u.nickname == "test"
        assert u.created_at is not None


def test_email_unique_constraint():
    engine, Session = _make_db()
    import pytest
    from sqlalchemy.exc import IntegrityError
    with Session() as session:
        session.add(User(id=uuid.uuid4().hex, email="dup@test.com",
                         nickname="a", password_hash="h", password_salt="s"))
        session.commit()
    with Session() as session:
        session.add(User(id=uuid.uuid4().hex, email="dup@test.com",
                         nickname="b", password_hash="h", password_salt="s"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_watchlist_unique_constraint():
    engine, Session = _make_db()
    import pytest
    from sqlalchemy.exc import IntegrityError
    with Session() as session:
        session.add(UserWatchlist(user_id="u1", stock_code="600519", stock_name="test"))
        session.commit()
    with Session() as session:
        session.add(UserWatchlist(user_id="u1", stock_code="600519", stock_name="test2"))
        with pytest.raises(IntegrityError):
            session.commit()
