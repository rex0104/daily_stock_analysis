import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage import (
    Base, UserWatchlist, UserWatchlistGroup, StockDaily,
    AnalysisHistory, PortfolioAccount, PortfolioPosition,
)
from src.migration import ensure_schema_current
from src.services.watchlist_enrichment_service import WatchlistEnrichmentService
from datetime import date, datetime


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_schema_current(engine)
    sf = sessionmaker(bind=engine)
    # Seed data
    with sf() as s:
        s.add(UserWatchlist(user_id="u1", stock_code="600519", stock_name="贵州茅台"))
        s.add(UserWatchlist(user_id="u1", stock_code="AAPL", stock_name="Apple"))
        s.add(UserWatchlist(user_id="u1", stock_code="hk00700", stock_name="腾讯控股"))
        # Add some daily data for 600519
        for i in range(5):
            s.add(StockDaily(code="600519", date=date(2026, 4, 7 + i),
                             close=1680.0 + i, pct_chg=0.1 * i))
        # Add analysis for 600519
        s.add(AnalysisHistory(code="600519", user_id="u1",
                              sentiment_score=82, operation_advice="持有",
                              analysis_summary="看好",
                              created_at=datetime(2026, 4, 11, 10, 30)))
        # Add portfolio position for 600519
        acct = PortfolioAccount(id=1, owner_id="u1", name="A股账户", market="cn")
        s.add(acct)
        s.flush()
        s.add(PortfolioPosition(
            account_id=1, symbol="600519", market="cn",
            quantity=100, avg_cost=1620.0, total_cost=162000.0,
            last_price=1680.0, market_value_base=168000.0,
            unrealized_pnl_base=6000.0,
        ))
        s.commit()
    return sf


def test_enriched_returns_groups(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    assert "groups" in result
    assert len(result["groups"]) >= 1


def test_enriched_item_has_price(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    assert maotai["price"] is not None
    assert maotai["price"]["close"] > 0


def test_enriched_item_has_sparkline(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    assert len(maotai["sparkline"]) == 5  # we seeded 5 days


def test_enriched_item_has_analysis(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    assert maotai["analysis"]["sentiment_score"] == 82


def test_enriched_no_analysis_is_null(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    aapl = next(i for i in items if i["stock_code"] == "AAPL")
    assert aapl["analysis"] is None


def test_market_detection(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    aapl = next(i for i in items if i["stock_code"] == "AAPL")
    hk = next(i for i in items if i["stock_code"] == "hk00700")
    assert maotai["market"] == "cn"
    assert aapl["market"] == "us"
    assert hk["market"] == "hk"


def test_enriched_item_has_position(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    assert maotai["position"] is not None
    assert maotai["position"]["quantity"] == 100
    assert maotai["position"]["avg_cost"] == 1620.0
    assert maotai["position"]["market_value"] == 168000.0
    assert maotai["position"]["unrealized_pnl"] == 6000.0


def test_enriched_no_position_is_null(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    aapl = next(i for i in items if i["stock_code"] == "AAPL")
    assert aapl["position"] is None


def test_enriched_history_timeline(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    assert len(maotai["history_timeline"]) == 1
    assert maotai["history_timeline"][0]["sentiment_score"] == 82


def test_enriched_empty_watchlist(db):
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("no_such_user")
    assert result["groups"] == []


def test_enriched_with_custom_groups(db):
    """Items assigned to custom groups appear under the correct group."""
    with db() as s:
        s.add(UserWatchlistGroup(id="grp1", user_id="u1", name="重仓", sort_order=1))
        wl = s.query(UserWatchlist).filter_by(user_id="u1", stock_code="AAPL").first()
        wl.group_id = "grp1"
        wl.sort_order = 0
        s.commit()
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    group_names = [g["group_name"] for g in result["groups"]]
    assert "重仓" in group_names
    heavy_group = next(g for g in result["groups"] if g["group_name"] == "重仓")
    codes = [i["stock_code"] for i in heavy_group["items"]]
    assert "AAPL" in codes


def test_sparkline_chronological_order(db):
    """Sparkline should be in chronological (oldest-first) order."""
    svc = WatchlistEnrichmentService(db)
    result = svc.get_enriched("u1")
    items = result["groups"][0]["items"]
    maotai = next(i for i in items if i["stock_code"] == "600519")
    # seeded as 1680, 1681, 1682, 1683, 1684
    assert maotai["sparkline"] == [1680.0, 1681.0, 1682.0, 1683.0, 1684.0]
