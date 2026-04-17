import pytest
from unittest.mock import patch, AsyncMock
import pandas as pd


def _make_sample_df(code="600519", bullish=True):
    """Build a sample 60-day DataFrame."""
    n = 60
    if bullish:
        closes = [10.0 + i * 0.15 for i in range(n)]
    else:
        closes = [10.0] * n
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=n, freq="B"),
        "open": [c - 0.3 for c in closes],
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
    })


class TestScreenerService:
    @pytest.mark.asyncio
    async def test_scan_yields_candidates_event(self):
        from src.services.screener_service import ScreenerService

        svc = ScreenerService.__new__(ScreenerService)

        # Mock stock list
        stock_list = pd.DataFrame({
            "code": ["600519", "000001"],
            "name": ["贵州茅台", "平安银行"],
        })

        # Mock data fetch: first stock matches, second doesn't
        async def mock_fetch(code):
            if code == "600519":
                return _make_sample_df(code, bullish=True)
            return _make_sample_df(code, bullish=False)

        # Use ma_bullish strategy (matches steady uptrend)
        events = []
        with patch.object(svc, '_get_stock_list', return_value=stock_list), \
             patch.object(svc, '_fetch_kline', side_effect=mock_fetch), \
             patch.object(svc, '_generate_summary', new_callable=AsyncMock, return_value="AI 摘要"):
            async for event in svc.scan("ma_bullish"):
                events.append(event)

        event_types = [e["type"] for e in events]
        assert "candidates" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_scan_unknown_strategy_yields_error(self):
        from src.services.screener_service import ScreenerService

        svc = ScreenerService()
        events = []
        async for event in svc.scan("nonexistent_strategy"):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "Unknown strategy" in events[0]["data"]["message"]

    @pytest.mark.asyncio
    async def test_scan_empty_stock_list_yields_error(self):
        from src.services.screener_service import ScreenerService

        svc = ScreenerService.__new__(ScreenerService)
        events = []
        with patch.object(svc, '_get_stock_list', return_value=pd.DataFrame()):
            async for event in svc.scan("trend_breakout"):
                events.append(event)

        event_types = [e["type"] for e in events]
        assert "error" in event_types
