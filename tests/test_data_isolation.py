# -*- coding: utf-8 -*-
"""
Tests for user_id data isolation across storage models.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.storage import Base, AnalysisHistory, ConversationMessage
from src.migration import ensure_schema_current


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    return engine


def test_analysis_history_filtered_by_user_id():
    engine = _make_engine()
    sf = sessionmaker(bind=engine)

    with sf() as s:
        s.add(AnalysisHistory(query_id="q1", code="600519", user_id="userA"))
        s.add(AnalysisHistory(query_id="q2", code="000001", user_id="userB"))
        s.commit()

    with sf() as s:
        rows = s.query(AnalysisHistory).filter_by(user_id="userA").all()
        assert len(rows) == 1
        assert rows[0].code == "600519"


def test_conversation_filtered_by_user_id():
    engine = _make_engine()
    sf = sessionmaker(bind=engine)

    with sf() as s:
        s.add(ConversationMessage(session_id="s1", role="user", content="hi", user_id="userA"))
        s.add(ConversationMessage(session_id="s2", role="user", content="hello", user_id="userB"))
        s.commit()

    with sf() as s:
        rows = s.query(ConversationMessage).filter_by(user_id="userA").all()
        assert len(rows) == 1
        assert rows[0].session_id == "s1"


def test_analysis_history_no_user_id_returns_all():
    """When user_id filter is None, all records should be returned."""
    engine = _make_engine()
    sf = sessionmaker(bind=engine)

    with sf() as s:
        s.add(AnalysisHistory(query_id="q1", code="600519", user_id="userA"))
        s.add(AnalysisHistory(query_id="q2", code="000001", user_id="userB"))
        s.add(AnalysisHistory(query_id="q3", code="000002", user_id=None))
        s.commit()

    with sf() as s:
        # No filter => all records
        rows = s.query(AnalysisHistory).all()
        assert len(rows) == 3


def test_conversation_no_user_id_returns_all():
    """When user_id filter is None, all records should be returned."""
    engine = _make_engine()
    sf = sessionmaker(bind=engine)

    with sf() as s:
        s.add(ConversationMessage(session_id="s1", role="user", content="hi", user_id="userA"))
        s.add(ConversationMessage(session_id="s2", role="user", content="hello", user_id=None))
        s.commit()

    with sf() as s:
        rows = s.query(ConversationMessage).all()
        assert len(rows) == 2
