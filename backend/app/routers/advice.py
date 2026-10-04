from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..advisor import analyse
from ..auth import current_user
from ..config import DISCLAIMER
from ..db import get_db
from ..models import Recommendation, User
from ..portfolio import build_portfolio
from ..prices import get_quotes
from ..schemas import Analysis, AnalysisOut, MarketIndex

router = APIRouter(prefix="/api", tags=["advice"])

MARKET_INDICES = {
    "^FCHI": "CAC 40",
    "^STOXX50E": "Euro Stoxx 50",
    "^GSPC": "S&P 500",
    "EURUSD=X": "EUR / USD",
}


def _out(rec: Recommendation) -> AnalysisOut:
    return AnalysisOut(
        id=rec.id, created_at=rec.created_at, source=rec.source,
        analysis=Analysis.model_validate(rec.payload), disclaimer=DISCLAIMER,
    )


@router.get("/recommendations/latest", response_model=AnalysisOut | None)
def latest(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rec = db.scalar(
        select(Recommendation).where(Recommendation.user_id == user.id)
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc()).limit(1)
    )
    return _out(rec) if rec else None


@router.post("/recommendations", response_model=AnalysisOut, status_code=201)
def generate(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.profile is None:
        raise HTTPException(400, "Complete your risk profile first")
    if not user.holdings:
        raise HTTPException(400, "Add at least one holding first")
    analysis, source = analyse(user, build_portfolio(user))
    rec = Recommendation(user_id=user.id, payload=analysis.model_dump(), source=source)
    db.add(rec)
    db.commit()
    return _out(rec)


@router.get("/market", response_model=list[MarketIndex])
def market(user: User = Depends(current_user)):
    quotes = get_quotes(list(MARKET_INDICES))
    out = []
    for symbol, name in MARKET_INDICES.items():
        q = quotes.get(symbol)
        change = (q.price / q.prev_close - 1) * 100 if q and q.prev_close else None
        out.append(MarketIndex(
            symbol=symbol, name=name,
            price=round(q.price, 4 if symbol.endswith("=X") else 2) if q else None,
            change_pct=round(change, 2) if change is not None else None,
        ))
    return out
