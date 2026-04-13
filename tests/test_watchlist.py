import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage import Base
from src.services.watchlist_service import WatchlistService


@pytest.fixture
def svc():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return WatchlistService(sessionmaker(bind=engine))


def test_add_and_list(svc):
    svc.add("user1", "600519", "贵州茅台")
    svc.add("user1", "AAPL", "Apple")
    items = svc.list("user1")
    assert len(items) == 2
    codes = [i["stock_code"] for i in items]
    assert "600519" in codes
    assert "AAPL" in codes


def test_add_duplicate_is_idempotent(svc):
    svc.add("user1", "600519", "贵州茅台")
    svc.add("user1", "600519", "贵州茅台")
    assert len(svc.list("user1")) == 1


def test_remove(svc):
    svc.add("user1", "600519")
    svc.remove("user1", "600519")
    assert len(svc.list("user1")) == 0


def test_isolation_between_users(svc):
    svc.add("user1", "600519")
    svc.add("user2", "AAPL")
    assert len(svc.list("user1")) == 1
    assert svc.list("user1")[0]["stock_code"] == "600519"


def test_is_watched(svc):
    svc.add("user1", "600519")
    assert svc.is_watched("user1", "600519") is True
    assert svc.is_watched("user1", "AAPL") is False
