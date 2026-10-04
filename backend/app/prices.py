"""Price, FX and volatility data from Yahoo Finance (via yfinance), with a short in-memory cache."""

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from .config import BASE_CURRENCY

log = logging.getLogger(__name__)
_TTL = 300  # seconds
_cache: dict[str, tuple[float, "Quote | None"]] = {}


@dataclass
class Quote:
    symbol: str
    name: str | None
    price: float  # in the quote currency
    prev_close: float | None
    currency: str
    instrument_type: str  # EQUITY, ETF, MUTUALFUND, INDEX, CURRENCY...
    closes: pd.Series  # ~1y of daily closes, used for volatility


def _fetch(symbol: str) -> Quote | None:
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y", auto_adjust=True)
        closes = hist["Close"].dropna() if not hist.empty else pd.Series(dtype=float)
        if closes.empty:
            return None
        meta = t.history_metadata or {}
        currency = meta.get("currency") or "USD"
        price = float(meta.get("regularMarketPrice") or closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) > 1 else None
        name = meta.get("longName") or meta.get("shortName")
        kind = meta.get("instrumentType") or "EQUITY"
        # London quotes are in pence
        if currency == "GBp":
            currency, price, closes = "GBP", price / 100, closes / 100
            prev = prev / 100 if prev else None
        return Quote(symbol, name, price, prev, currency, kind, closes)
    except Exception as e:  # network errors, unknown tickers, Yahoo rate limits
        log.warning("price fetch failed for %s: %s", symbol, e)
        return None


def get_quote(symbol: str) -> Quote | None:
    symbol = symbol.upper()
    hit = _cache.get(symbol)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    q = _fetch(symbol)
    _cache[symbol] = (time.time(), q)
    return q


def get_quotes(symbols: list[str]) -> dict[str, Quote | None]:
    unique = sorted({s.upper() for s in symbols})
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(unique, pool.map(get_quote, unique)))


def fx_rate(currency: str) -> float | None:
    """Units of BASE_CURRENCY per one unit of `currency`."""
    if currency == BASE_CURRENCY:
        return 1.0
    q = get_quote(f"{currency}{BASE_CURRENCY}=X")
    return q.price if q else None


def annual_volatility(weights: dict[str, float], quotes: dict[str, Quote | None]) -> float | None:
    """Annualised volatility of the weighted portfolio, from aligned daily returns."""
    series = {s: quotes[s].closes for s in weights if quotes.get(s) is not None}
    if not series:
        return None
    df = pd.DataFrame(series)
    df.index = pd.to_datetime(df.index).date  # align across exchanges/timezones
    df = df.groupby(level=0).last().ffill().dropna()
    returns = df.pct_change().dropna()
    if len(returns) < 20:
        return None
    w = pd.Series({s: weights[s] for s in returns.columns})
    w = w / w.sum()
    vol = float(math.sqrt(w @ returns.cov() @ w) * math.sqrt(252))
    return vol if math.isfinite(vol) else None
