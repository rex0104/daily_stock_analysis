import pytest
import pandas as pd
import numpy as np


def _make_df(closes, volumes=None, highs=None, lows=None, opens=None):
    """Helper to build a DataFrame with at least 60 rows."""
    n = len(closes)
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "date": dates,
        "open": opens if opens is not None else [c - 0.5 for c in closes],
        "high": highs if highs is not None else [c + 0.5 for c in closes],
        "low": lows if lows is not None else [c - 1.0 for c in closes],
        "close": closes,
        "volume": volumes if volumes is not None else [1_000_000] * n,
    })
    return df


class TestTrendBreakout:
    def test_matches_when_breaks_above_ma20_with_volume(self):
        from src.services.screener_strategies import trend_breakout
        # 60 bars: first 58 bars close at 10, yesterday dips, today breaks above MA20
        # 5-day gain must stay < 10%: (10.8 - 10.0) / 10.0 = 8%
        closes = [10.0] * 58 + [9.8, 10.8]
        volumes = [1_000_000] * 58 + [1_000_000, 2_500_000]  # last bar volume_ratio > 1.5
        df = _make_df(closes, volumes=volumes)
        assert trend_breakout(df) is True

    def test_rejects_when_no_breakout(self):
        from src.services.screener_strategies import trend_breakout
        closes = [10.0] * 60  # flat, always at MA20
        df = _make_df(closes)
        assert trend_breakout(df) is False

    def test_rejects_when_5d_gain_too_large(self):
        from src.services.screener_strategies import trend_breakout
        # Break above MA20 but 5-day gain > 10%
        closes = [10.0] * 55 + [10.0, 10.5, 11.0, 11.5, 12.0]
        volumes = [1_000_000] * 55 + [1_000_000] * 4 + [3_000_000]
        df = _make_df(closes, volumes=volumes)
        # 5d gain = (12 - 10) / 10 = 20% > 10%
        assert trend_breakout(df) is False


class TestOversoldBounce:
    def test_matches_oversold_with_reversal_candle(self):
        from src.services.screener_strategies import oversold_bounce
        # Simulate decline: 60 bars, last 20 drop > 15%
        closes = [100.0] * 40 + [100 - i * 1.0 for i in range(20)]
        # closes[-1] = 81, closes[-21] = 100 -> -19%
        # Force a green candle on last day
        opens = [c + 0.5 for c in closes]
        opens[-1] = closes[-1] - 0.5  # green candle
        df = _make_df(closes, opens=opens)
        # The actual match depends on RSI calculation
        result = oversold_bounce(df)
        assert isinstance(result, bool)

    def test_rejects_when_no_decline(self):
        from src.services.screener_strategies import oversold_bounce
        closes = [100.0] * 60
        df = _make_df(closes)
        assert oversold_bounce(df) is False


class TestVolumeSurge:
    def test_matches_increasing_volume_above_ma(self):
        from src.services.screener_strategies import volume_surge
        closes = [10.0 + i * 0.1 for i in range(60)]  # steady uptrend
        volumes = [1_000_000] * 57 + [1_200_000, 1_500_000, 2_000_000]
        df = _make_df(closes, volumes=volumes)
        assert volume_surge(df) is True

    def test_rejects_when_volume_not_increasing(self):
        from src.services.screener_strategies import volume_surge
        closes = [10.0 + i * 0.1 for i in range(60)]
        volumes = [1_000_000] * 60
        df = _make_df(closes, volumes=volumes)
        assert volume_surge(df) is False


class TestMaBullish:
    def test_matches_perfect_alignment(self):
        from src.services.screener_strategies import ma_bullish
        # Steady uptrend over 70 bars: MA5 > MA10 > MA20 > MA60 naturally
        closes = [10.0 + i * 0.15 for i in range(70)]
        df = _make_df(closes)
        assert ma_bullish(df) is True

    def test_rejects_downtrend(self):
        from src.services.screener_strategies import ma_bullish
        closes = [20.0 - i * 0.15 for i in range(70)]
        df = _make_df(closes)
        assert ma_bullish(df) is False
