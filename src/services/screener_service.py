"""
Stock screening service.

Orchestrates: stock list -> kline fetch -> strategy filter -> LLM summaries.
All results streamed via async generator for SSE consumption.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, Dict, Any, Optional, List

import pandas as pd

from src.services.screener_strategies import STRATEGIES

logger = logging.getLogger(__name__)

# Concurrency limits
_DATA_FETCH_SEMAPHORE = 20
_LLM_SUMMARY_SEMAPHORE = 5
_THREAD_POOL = ThreadPoolExecutor(max_workers=10)


class ScreenerService:
    """On-demand stock screener with SSE-friendly async generator output."""

    async def scan(self, strategy_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run a screening scan and yield SSE events.

        Events:
          {"type": "progress", "data": {"phase": "...", ...}}
          {"type": "candidates", "data": [candidate, ...]}
          {"type": "summary", "data": {"code": "...", "summary": "..."}}
          {"type": "done", "data": {"total_scanned": N, "matched": M}}
          {"type": "error", "data": {"message": "..."}}
        """
        strategy = STRATEGIES.get(strategy_id)
        if not strategy:
            yield {"type": "error", "data": {"message": f"Unknown strategy: {strategy_id}"}}
            return

        # Phase 1: get stock list
        yield {"type": "progress", "data": {"phase": "fetching_list"}}
        stock_list = self._get_stock_list()
        if stock_list is None or stock_list.empty:
            yield {"type": "error", "data": {"message": "Failed to fetch stock list"}}
            return

        total = len(stock_list)
        yield {"type": "progress", "data": {"phase": "scanning", "total": total}}

        # Phase 2: fetch kline + run strategy filter
        sem = asyncio.Semaphore(_DATA_FETCH_SEMAPHORE)
        candidates: List[Dict[str, Any]] = []

        async def process_stock(code: str, name: str):
            async with sem:
                try:
                    df = await self._fetch_kline(code)
                    if df is None or len(df) < 20:
                        return None
                    if strategy.func(df):
                        return self._build_candidate(code, name, df)
                except Exception as e:
                    logger.debug(f"Skip {code}: {e}")
                    return None

        tasks = [
            process_stock(row["code"], row["name"])
            for _, row in stock_list.iterrows()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, dict):
                candidates.append(r)

        # Sort by volume_ratio descending
        candidates.sort(key=lambda c: c.get("volume_ratio", 0), reverse=True)

        yield {"type": "candidates", "data": candidates}

        # Phase 3: LLM summaries
        if candidates:
            llm_sem = asyncio.Semaphore(_LLM_SUMMARY_SEMAPHORE)

            async def summarize(candidate: Dict[str, Any]):
                async with llm_sem:
                    try:
                        summary = await self._generate_summary(
                            candidate["code"],
                            candidate["name"],
                            strategy.name,
                            candidate,
                        )
                        return {"code": candidate["code"], "summary": summary}
                    except Exception as e:
                        logger.warning(f"Summary failed for {candidate['code']}: {e}")
                        return {"code": candidate["code"], "summary": "摘要生成失败"}

            summary_tasks = [summarize(c) for c in candidates]
            for coro in asyncio.as_completed(summary_tasks):
                result = await coro
                yield {"type": "summary", "data": result}

        yield {"type": "done", "data": {"total_scanned": total, "matched": len(candidates)}}

    def _get_stock_list(self) -> Optional[pd.DataFrame]:
        """Get all A-share stock list via available fetchers."""
        try:
            from data_provider.base import DataFetcherManager
            manager = DataFetcherManager()
            for fetcher in manager._get_fetchers_snapshot():
                if hasattr(fetcher, "get_stock_list"):
                    df = fetcher.get_stock_list()
                    if df is not None and not df.empty:
                        # Filter out ST stocks
                        mask = ~df["name"].str.contains("ST", case=False, na=False)
                        return df[mask].reset_index(drop=True)
            logger.warning("No fetcher provides get_stock_list")
            return None
        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return None

    async def _fetch_kline(self, code: str) -> Optional[pd.DataFrame]:
        """Fetch 60-day daily kline data in a thread."""
        loop = asyncio.get_event_loop()
        try:
            def _fetch():
                from data_provider.base import DataFetcherManager
                manager = DataFetcherManager()
                return manager.get_daily_data(code, days=90)
            return await loop.run_in_executor(_THREAD_POOL, _fetch)
        except Exception as e:
            logger.debug(f"Kline fetch failed for {code}: {e}")
            return None

    def _build_candidate(self, code: str, name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Build a candidate dict from matched stock data."""
        close = df["close"]
        volume = df["volume"]
        today_close = close.iloc[-1]
        prev_close = close.iloc[-2] if len(close) > 1 else today_close

        vol_5d_avg = volume.iloc[-6:-1].mean() if len(volume) > 5 else volume.mean()
        volume_ratio = round(volume.iloc[-1] / vol_5d_avg, 2) if vol_5d_avg > 0 else 0

        close_5d_ago = close.iloc[-6] if len(close) > 5 else close.iloc[0]
        pct_5d = round((today_close - close_5d_ago) / close_5d_ago * 100, 2) if close_5d_ago > 0 else 0

        change_pct = round((today_close - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0

        return {
            "code": code,
            "name": name,
            "price": round(today_close, 2),
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "pct_5d": pct_5d,
        }

    async def _generate_summary(
        self, code: str, name: str, strategy_name: str, candidate: Dict[str, Any]
    ) -> str:
        """Generate a 1-2 sentence AI summary for a candidate stock."""
        loop = asyncio.get_event_loop()

        def _call_llm():
            from src.agent.llm_adapter import LLMToolAdapter
            adapter = LLMToolAdapter()
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一位股票分析师。请用1-2句话简要点评以下股票，"
                        "基于其命中的筛选策略和近期行情数据。"
                        "要求：说明技术面关键信号 + 一个值得关注的点位或风险。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"股票：{name}（{code}）\n"
                        f"命中策略：{strategy_name}\n"
                        f"当前价：{candidate['price']}  涨跌幅：{candidate['change_pct']}%  "
                        f"量比：{candidate['volume_ratio']}  5日涨幅：{candidate['pct_5d']}%"
                    ),
                },
            ]
            response = adapter.call_text(messages, max_tokens=200, timeout=30.0)
            return response.content.strip() if response.content else "摘要生成失败"

        return await loop.run_in_executor(_THREAD_POOL, _call_llm)
