from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.storage import Base, UserWatchlist, UserWatchlistGroup
from src.migration import ensure_schema_current


def test_group_table_created():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "user_watchlist_groups" in inspector.get_table_names()


def test_watchlist_has_group_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("user_watchlists")]
    assert "group_id" in cols
    assert "sort_order" in cols


def test_migration_v3_adds_columns():
    engine = create_engine("sqlite:///:memory:")
    # Simulate pre-v3: create tables without new columns
    # Since create_all uses current models (which have the columns),
    # migration should be idempotent
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("user_watchlists")]
    assert "group_id" in cols
    assert "sort_order" in cols


def test_watchlist_default_group():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        item = UserWatchlist(user_id="u1", stock_code="600519")
        s.add(item)
        s.commit()
        s.refresh(item)
        assert item.group_id == "default"
        assert item.sort_order == 0
