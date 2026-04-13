import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage import Base, AnalysisHistory
from src.migration import ensure_schema_current
from src.services.share_service import ShareService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        s.add(AnalysisHistory(id=1, query_id="q1", code="600519", name="贵州茅台", user_id="user1"))
        s.commit()
    return sf


@pytest.fixture
def svc(db):
    return ShareService(db)


def test_create_share_link(svc):
    result = svc.create("user1", 1)
    assert "share_token" in result
    assert len(result["share_token"]) > 10


def test_create_share_with_brand(svc):
    result = svc.create("user1", 1, brand_name="MyBrand")
    assert result["brand_name"] == "MyBrand"


def test_duplicate_share_returns_same_token(svc):
    r1 = svc.create("user1", 1)
    r2 = svc.create("user1", 1)
    assert r1["share_token"] == r2["share_token"]


def test_get_shared_report(svc):
    created = svc.create("user1", 1)
    report = svc.get_by_token(created["share_token"])
    assert report is not None
    assert report["stock_code"] == "600519"
    assert report["brand_name"] is not None


def test_get_nonexistent_token(svc):
    assert svc.get_by_token("nonexistent") is None


def test_cannot_share_other_users_report(svc):
    with pytest.raises(ValueError, match="not found"):
        svc.create("user2", 1)


def test_list_my_shares(svc):
    svc.create("user1", 1)
    shares = svc.list_by_user("user1")
    assert len(shares) == 1


def test_revoke_share(svc):
    created = svc.create("user1", 1)
    svc.revoke("user1", created["share_token"])
    assert svc.get_by_token(created["share_token"]) is None
