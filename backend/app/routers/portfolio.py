from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Holding, User
from ..portfolio import build_portfolio
from ..prices import get_quote
from ..schemas import HoldingIn, PortfolioOut

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOut)
def get_portfolio(user: User = Depends(current_user)):
    return build_portfolio(user)


@router.get("/lookup/{ticker}")
def lookup(ticker: str, user: User = Depends(current_user)):
    """Validate a ticker before adding it, and return its name/price."""
    q = get_quote(ticker)
    if q is None:
        raise HTTPException(404, f"No price found for {ticker.upper()} on Yahoo Finance")
    return {"ticker": q.symbol, "name": q.name, "price": round(q.price, 4), "currency": q.currency}


@router.post("/holdings", response_model=PortfolioOut, status_code=201)
def add_holding(body: HoldingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.holdings.append(Holding(
        ticker=body.ticker.strip().upper(), quantity=body.quantity, avg_buy_price=body.avg_buy_price,
    ))
    db.commit()
    return build_portfolio(user)


@router.put("/holdings/{holding_id}", response_model=PortfolioOut)
def update_holding(holding_id: int, body: HoldingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = next((h for h in user.holdings if h.id == holding_id), None)
    if h is None:
        raise HTTPException(404, "Holding not found")
    h.ticker, h.quantity, h.avg_buy_price = body.ticker.strip().upper(), body.quantity, body.avg_buy_price
    db.commit()
    return build_portfolio(user)


@router.delete("/holdings/{holding_id}", response_model=PortfolioOut)
def delete_holding(holding_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    h = next((h for h in user.holdings if h.id == holding_id), None)
    if h is None:
        raise HTTPException(404, "Holding not found")
    user.holdings.remove(h)
    db.commit()
    return build_portfolio(user)
