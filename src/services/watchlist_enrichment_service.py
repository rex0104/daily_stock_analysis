"""Watchlist enrichment — aggregates price, analysis, sparkline, position data."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy.orm import sessionmaker

from src.storage import (
    AnalysisHistory,
    PortfolioAccount,
    PortfolioPosition,
    StockDaily,
    UserWatchlist,
    UserWatchlistGroup,
)

logger = logging.getLogger(__name__)

_SPARKLINE_DAYS = 30
_HISTORY_LIMIT = 5


def _detect_market(code: str) -> str:
    if code.lower().startswith("hk"):
        return "hk"
    if code.isdigit() and len(code) == 6:
        return "cn"
    return "us"


class WatchlistEnrichmentService:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def get_enriched(self, user_id: str) -> Dict[str, Any]:
        """Return the full enriched watchlist grouped by category."""
        with self._sf() as session:
            # 1. Fetch watchlist items
            wl_items: List[UserWatchlist] = (
                session.query(UserWatchlist)
                .filter(UserWatchlist.user_id == user_id)
                .order_by(UserWatchlist.sort_order)
                .all()
            )
            if not wl_items:
                return {"groups": []}

            codes = [item.stock_code for item in wl_items]

            # 2. Fetch custom groups
            groups_rows: List[UserWatchlistGroup] = (
                session.query(UserWatchlistGroup)
                .filter(UserWatchlistGroup.user_id == user_id)
                .order_by(UserWatchlistGroup.sort_order)
                .all()
            )
            group_meta: Dict[str, Dict[str, Any]] = {
                "default": {"group_id": "default", "group_name": "默认", "sort_order": 0},
            }
            for g in groups_rows:
                group_meta[g.id] = {
                    "group_id": g.id,
                    "group_name": g.name,
                    "sort_order": g.sort_order,
                }

            # 3. Batch fetch stock_daily (last N rows per stock, ordered by date desc)
            price_map = self._fetch_prices(session, codes)

            # 4. Batch fetch analysis_history (last 5 per stock for this user)
            analysis_map = self._fetch_analyses(session, user_id, codes)

            # 5. Batch fetch portfolio_positions
            position_map = self._fetch_positions(session, user_id, codes)

            # 6. Assemble items into groups
            grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for item in wl_items:
                code = item.stock_code
                gid = item.group_id or "default"

                # Ensure the group exists in metadata (defensive)
                if gid not in group_meta:
                    group_meta[gid] = {
                        "group_id": gid,
                        "group_name": gid,
                        "sort_order": 999,
                    }

                price_info = price_map.get(code)
                analysis_rows = analysis_map.get(code, [])
                position_info = position_map.get(code)

                latest_analysis = None
                if analysis_rows:
                    a = analysis_rows[0]
                    latest_analysis = {
                        "sentiment_score": a.sentiment_score,
                        "operation_advice": a.operation_advice,
                        "analysis_summary": a.analysis_summary,
                        "analyzed_at": a.created_at.isoformat() if a.created_at else None,
                    }

                history_timeline = [
                    {
                        "date": a.created_at.strftime("%Y-%m-%d") if a.created_at else None,
                        "sentiment_score": a.sentiment_score,
                        "operation_advice": a.operation_advice,
                        "analysis_summary": a.analysis_summary,
                    }
                    for a in analysis_rows
                ]

                grouped[gid].append({
                    "stock_code": code,
                    "stock_name": item.stock_name,
                    "group_id": gid,
                    "sort_order": item.sort_order,
                    "market": _detect_market(code),
                    "price": price_info,
                    "analysis": latest_analysis,
                    "position": position_info,
                    "sparkline": price_map.get(code, {}).get("_sparkline", []) if price_info else [],
                    "history_timeline": history_timeline,
                })

            # Build ordered groups list
            result_groups = []
            for gid, meta in sorted(group_meta.items(), key=lambda x: x[1]["sort_order"]):
                items = grouped.get(gid, [])
                if not items:
                    continue
                result_groups.append({
                    "group_id": meta["group_id"],
                    "group_name": meta["group_name"],
                    "sort_order": meta["sort_order"],
                    "items": sorted(items, key=lambda x: x["sort_order"]),
                })

            return {"groups": result_groups}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_prices(session, codes: List[str]) -> Dict[str, Any]:
        """Fetch last N daily rows per stock; return map with price + sparkline."""
        rows = (
            session.query(StockDaily.code, StockDaily.date, StockDaily.close, StockDaily.pct_chg)
            .filter(StockDaily.code.in_(codes))
            .order_by(StockDaily.code, StockDaily.date.desc())
            .all()
        )

        by_code: Dict[str, list] = defaultdict(list)
        for row in rows:
            if len(by_code[row.code]) < _SPARKLINE_DAYS:
                by_code[row.code].append(row)

        result: Dict[str, Any] = {}
        for code, code_rows in by_code.items():
            # code_rows are desc by date; reverse for chronological sparkline
            code_rows.reverse()
            latest = code_rows[-1]  # most recent
            result[code] = {
                "close": latest.close,
                "pct_chg": latest.pct_chg,
                "_sparkline": [r.close for r in code_rows],
            }
        return result

    @staticmethod
    def _fetch_analyses(session, user_id: str, codes: List[str]) -> Dict[str, list]:
        """Fetch last N analysis rows per stock for this user."""
        rows = (
            session.query(AnalysisHistory)
            .filter(
                AnalysisHistory.user_id == user_id,
                AnalysisHistory.code.in_(codes),
            )
            .order_by(AnalysisHistory.code, AnalysisHistory.created_at.desc())
            .all()
        )

        by_code: Dict[str, list] = defaultdict(list)
        for row in rows:
            if len(by_code[row.code]) < _HISTORY_LIMIT:
                by_code[row.code].append(row)
        return dict(by_code)

    @staticmethod
    def _fetch_positions(session, user_id: str, codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch active portfolio positions for the user's accounts."""
        positions = (
            session.query(PortfolioPosition)
            .join(PortfolioAccount, PortfolioPosition.account_id == PortfolioAccount.id)
            .filter(
                PortfolioAccount.owner_id == user_id,
                PortfolioPosition.symbol.in_(codes),
                PortfolioPosition.quantity > 0,
            )
            .all()
        )

        # Aggregate across accounts if the same stock is held in multiple
        agg: Dict[str, Dict[str, float]] = {}
        for p in positions:
            sym = p.symbol
            if sym not in agg:
                agg[sym] = {
                    "quantity": 0.0,
                    "total_cost": 0.0,
                    "market_value": 0.0,
                    "unrealized_pnl": 0.0,
                }
            agg[sym]["quantity"] += p.quantity
            agg[sym]["total_cost"] += p.total_cost
            agg[sym]["market_value"] += p.market_value_base
            agg[sym]["unrealized_pnl"] += p.unrealized_pnl_base

        result: Dict[str, Dict[str, Any]] = {}
        for sym, data in agg.items():
            qty = data["quantity"]
            avg_cost = data["total_cost"] / qty if qty else 0.0
            pnl_pct = (data["unrealized_pnl"] / data["total_cost"] * 100) if data["total_cost"] else 0.0
            result[sym] = {
                "quantity": qty,
                "avg_cost": round(avg_cost, 4),
                "market_value": round(data["market_value"], 2),
                "unrealized_pnl": round(data["unrealized_pnl"], 2),
                "pnl_pct": round(pnl_pct, 2),
            }
        return result
