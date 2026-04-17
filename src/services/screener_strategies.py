"""
Preset stock screening strategies.

Each strategy function takes a DataFrame with columns
[date, open, high, low, close, volume] sorted by date ascending
(at least 60 rows) and returns True if the stock matches.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _ma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def trend_breakout(df: pd.DataFrame) -> bool:
    """
    Trend Breakout — capture breakout signals.
    Conditions:
      1. Today's close > MA20, yesterday's close <= MA20
      2. Volume ratio > 1.5 (today's volume / 5-day avg volume)
      3. 5-day price gain < 10%
    """
    if len(df) < 25:
        return False
    close = df["close"]
    volume = df["volume"]
    ma20 = _ma(close, 20)

    today = close.iloc[-1]
    yesterday = close.iloc[-2]
    ma20_today = ma20.iloc[-1]
    ma20_yesterday = ma20.iloc[-2]

    if pd.isna(ma20_today) or pd.isna(ma20_yesterday):
        return False

    # Condition 1: breakout
    if not (today > ma20_today and yesterday <= ma20_yesterday):
        return False

    # Condition 2: volume ratio > 1.5
    vol_5d_avg = volume.iloc[-6:-1].mean()
    if vol_5d_avg <= 0:
        return False
    volume_ratio = volume.iloc[-1] / vol_5d_avg
    if volume_ratio < 1.5:
        return False

    # Condition 3: 5-day gain < 10%
    close_5d_ago = close.iloc[-6]
    if close_5d_ago <= 0:
        return False
    pct_5d = (today - close_5d_ago) / close_5d_ago
    if pct_5d >= 0.10:
        return False

    return True


def oversold_bounce(df: pd.DataFrame) -> bool:
    """
    Oversold Bounce — bottom-fishing candidates.
    Conditions:
      1. 20-day decline > 15%
      2. RSI14 < 30
      3. At least 1 green candle or doji in last 3 days
    """
    if len(df) < 25:
        return False
    close = df["close"]

    # Condition 1: 20-day decline
    close_20d_ago = close.iloc[-21] if len(df) > 20 else close.iloc[0]
    if close_20d_ago <= 0:
        return False
    pct_20d = (close.iloc[-1] - close_20d_ago) / close_20d_ago
    if pct_20d > -0.15:
        return False

    # Condition 2: RSI < 30
    rsi_series = _rsi(close, 14)
    rsi_today = rsi_series.iloc[-1]
    if pd.isna(rsi_today) or rsi_today >= 30:
        return False

    # Condition 3: at least one green / doji in last 3 days
    last3 = df.iloc[-3:]
    has_green_or_doji = any(
        row["close"] >= row["open"] for _, row in last3.iterrows()
    )
    if not has_green_or_doji:
        return False

    return True


def volume_surge(df: pd.DataFrame) -> bool:
    """
    Volume Surge — strong momentum tracking.
    Conditions:
      1. 3 consecutive days of increasing volume
      2. Close > MA5 > MA10
    """
    if len(df) < 15:
        return False
    close = df["close"]
    volume = df["volume"]
    ma5 = _ma(close, 5)
    ma10 = _ma(close, 10)

    # Condition 1: volume[-1] > volume[-2] > volume[-3]
    v1, v2, v3 = volume.iloc[-1], volume.iloc[-2], volume.iloc[-3]
    if not (v1 > v2 > v3):
        return False

    # Condition 2: close > MA5 > MA10
    today_close = close.iloc[-1]
    ma5_today = ma5.iloc[-1]
    ma10_today = ma10.iloc[-1]
    if pd.isna(ma5_today) or pd.isna(ma10_today):
        return False
    if not (today_close > ma5_today > ma10_today):
        return False

    return True


def ma_bullish(df: pd.DataFrame) -> bool:
    """
    MA Bullish Alignment — trend confirmation.
    Conditions:
      1. MA5 > MA10 > MA20 > MA60
      2. Volume activity filter: today's volume >= 5-day avg
    """
    if len(df) < 65:
        return False
    close = df["close"]
    volume = df["volume"]
    ma5 = _ma(close, 5).iloc[-1]
    ma10 = _ma(close, 10).iloc[-1]
    ma20 = _ma(close, 20).iloc[-1]
    ma60 = _ma(close, 60).iloc[-1]

    if any(pd.isna(v) for v in [ma5, ma10, ma20, ma60]):
        return False

    # Condition 1: MA alignment
    if not (ma5 > ma10 > ma20 > ma60):
        return False

    # Condition 2: volume activity filter
    vol_5d_avg = volume.iloc[-6:-1].mean()
    if vol_5d_avg <= 0:
        return False
    volume_ratio = volume.iloc[-1] / vol_5d_avg
    if volume_ratio < 1.0:
        return False

    return True


@dataclass
class StrategyDef:
    id: str
    name: str
    func: Callable[[pd.DataFrame], bool]
    description: str
    icon: str


STRATEGIES: Dict[str, StrategyDef] = {
    "trend_breakout": StrategyDef(
        id="trend_breakout",
        name="趋势突破",
        func=trend_breakout,
        description="突破MA20+放量，捕捉启动信号",
        icon="📈",
    ),
    "oversold_bounce": StrategyDef(
        id="oversold_bounce",
        name="超跌反弹",
        func=oversold_bounce,
        description="20日跌>15%+RSI低，抄底候选",
        icon="📉",
    ),
    "volume_surge": StrategyDef(
        id="volume_surge",
        name="放量上攻",
        func=volume_surge,
        description="连续3日放量递增，强势股追踪",
        icon="🔥",
    ),
    "ma_bullish": StrategyDef(
        id="ma_bullish",
        name="均线多头",
        func=ma_bullish,
        description="MA5>10>20>60，趋势确认",
        icon="⛳",
    ),
}
