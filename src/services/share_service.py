"""Public report sharing service."""
from __future__ import annotations
import base64
import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import sessionmaker
from src.storage import SharedReport, AnalysisHistory

logger = logging.getLogger(__name__)
DEFAULT_BRAND = "股票智能分析"


def _generate_token() -> str:
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b"=").decode("ascii")


class ShareService:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    def create(self, user_id: str, analysis_history_id: int,
               brand_name: str = None) -> Dict[str, Any]:
        with self._sf() as session:
            record = session.query(AnalysisHistory).filter_by(
                id=analysis_history_id, user_id=user_id).first()
            if not record:
                raise ValueError("Analysis record not found or not owned by user")
            existing = session.query(SharedReport).filter_by(
                analysis_history_id=analysis_history_id, user_id=user_id).first()
            if existing:
                return self._to_dict(existing)
            share = SharedReport(
                share_token=_generate_token(),
                analysis_history_id=analysis_history_id,
                user_id=user_id,
                brand_name=brand_name or DEFAULT_BRAND,
            )
            session.add(share)
            session.commit()
            return self._to_dict(share)

    def get_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        with self._sf() as session:
            share = session.query(SharedReport).filter_by(share_token=token).first()
            if not share:
                return None
            analysis = session.query(AnalysisHistory).filter_by(
                id=share.analysis_history_id).first()
            if not analysis:
                return None
            result = self._to_dict(share)
            result.update({
                "stock_code": analysis.code,
                "stock_name": analysis.name,
                "report_type": analysis.report_type,
                "sentiment_score": analysis.sentiment_score,
                "operation_advice": analysis.operation_advice,
                "trend_prediction": analysis.trend_prediction,
                "analysis_summary": analysis.analysis_summary,
                "ideal_buy": analysis.ideal_buy,
                "secondary_buy": analysis.secondary_buy,
                "stop_loss": analysis.stop_loss,
                "take_profit": analysis.take_profit,
                "analysis_created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            })
            return result

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        with self._sf() as session:
            shares = session.query(SharedReport).filter_by(user_id=user_id)\
                .order_by(SharedReport.created_at.desc()).all()
            return [self._to_dict(s) for s in shares]

    def revoke(self, user_id: str, token: str) -> bool:
        with self._sf() as session:
            share = session.query(SharedReport).filter_by(
                share_token=token, user_id=user_id).first()
            if not share:
                return False
            session.delete(share)
            session.commit()
            return True

    @staticmethod
    def _to_dict(share: SharedReport) -> Dict[str, Any]:
        return {
            "share_token": share.share_token,
            "analysis_history_id": share.analysis_history_id,
            "brand_name": share.brand_name,
            "created_at": share.created_at.isoformat() if share.created_at else None,
        }
