# tests/test_data_claim.py
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage import Base, AnalysisHistory, ConversationMessage, PortfolioAccount
from src.migration import ensure_schema_current
from src.services.data_claim_service import claim_orphan_data


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    sf = sessionmaker(bind=engine)
    return engine, sf


def test_claim_assigns_user_id_to_orphan_rows(db):
    engine, sf = db
    with sf() as s:
        s.add(AnalysisHistory(query_id="q1", code="600519", user_id=None))
        s.add(AnalysisHistory(query_id="q2", code="000001", user_id="other_user"))
        s.add(ConversationMessage(session_id="s1", role="user", content="hi", user_id=None))
        s.add(PortfolioAccount(id=1, name="test", owner_id=None))
        s.commit()

    claim_orphan_data(sf, "first_user_id")

    with sf() as s:
        rows = s.query(AnalysisHistory).all()
        orphan = [r for r in rows if r.query_id == "q1"][0]
        other = [r for r in rows if r.query_id == "q2"][0]
        assert orphan.user_id == "first_user_id"
        assert other.user_id == "other_user"  # not overwritten

        msgs = s.query(ConversationMessage).all()
        assert msgs[0].user_id == "first_user_id"

        accts = s.query(PortfolioAccount).all()
        assert accts[0].owner_id == "first_user_id"


def test_claim_with_no_orphans(db):
    engine, sf = db
    # Should not error even with empty tables
    claim_orphan_data(sf, "user1")


def test_claim_does_not_overwrite_existing(db):
    engine, sf = db
    with sf() as s:
        s.add(AnalysisHistory(query_id="q1", code="600519", user_id="existing"))
        s.commit()

    claim_orphan_data(sf, "new_user")

    with sf() as s:
        row = s.query(AnalysisHistory).first()
        assert row.user_id == "existing"
