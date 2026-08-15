from datetime import date, timedelta
from sqlalchemy.orm import Session
from ... import models


def get_closes(db: Session, instrument_id: int, end_date: date = None):
    query = db.query(models.DailyPrice).filter(
        models.DailyPrice.instrument_id == instrument_id
    )
    if end_date:
        query = query.filter(models.DailyPrice.price_date <= end_date)
    prices = query.order_by(models.DailyPrice.price_date).all()
    closes = [p.close for p in prices]
    dates = [p.price_date for p in prices]
    return closes, dates


def performance_over_period(closes: list[float], dates: list[date], period_days: int):
    if len(closes) < 2:
        return None
    target_date = dates[-1] - timedelta(days=period_days)
    idx = None
    for i, d in enumerate(dates):
        if d >= target_date:
            idx = i
            break
    if idx is None:
        idx = 0
    if idx >= len(closes) - 1:
        return None
    start_close = closes[idx]
    end_close = closes[-1]
    return (end_close / start_close) - 1


def compute_performance_metrics(db: Session, instrument_id: int) -> dict:
    closes, dates = get_closes(db, instrument_id)
    if not closes:
        return {
            "last_close": None,
            "sma200": None,
            "above_sma200": None,
            "perf_1m": None,
            "perf_3m": None,
            "perf_6m": None,
            "perf_12m": None,
            "total_points": 0
        }

    last_close = closes[-1]

    if len(closes) >= 200:
        sma200 = sum(closes[-200:]) / 200
    else:
        sma200 = None

    above_sma200 = (last_close > sma200) if sma200 is not None else None

    perf_1m = performance_over_period(closes, dates, 30)
    perf_3m = performance_over_period(closes, dates, 90)
    perf_6m = performance_over_period(closes, dates, 180)
    perf_12m = performance_over_period(closes, dates, 365)

    return {
        "last_close": last_close,
        "sma200": sma200,
        "above_sma200": above_sma200,
        "perf_1m": perf_1m,
        "perf_3m": perf_3m,
        "perf_6m": perf_6m,
        "perf_12m": perf_12m,
        "total_points": len(closes)
    }