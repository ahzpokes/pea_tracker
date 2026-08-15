from datetime import date, timedelta
from sqlalchemy.orm import Session
from ... import models
import pandas as pd

PERIODS = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "12M": 365,
    "Max": None
}


def get_performance_chart_data(db: Session, period: str, instrument_ids: list[int]):
    instruments = db.query(models.Instrument).filter(models.Instrument.id.in_(instrument_ids)).all()
    if not instruments:
        return {"period": period, "labels": [], "series": [], "annotations": []}

    days = PERIODS.get(period, None)
    end_date = date.today()
    start_date = end_date - timedelta(days=days) if days is not None else None

    series_data = []
    all_dates = set()
    for inst in instruments:
        query = db.query(models.DailyPrice).filter(
            models.DailyPrice.instrument_id == inst.id
        )
        if start_date:
            query = query.filter(models.DailyPrice.price_date >= start_date)
        query = query.filter(models.DailyPrice.price_date <= end_date)
        prices = query.order_by(models.DailyPrice.price_date).all()
        if not prices:
            continue
        df = pd.DataFrame([(p.price_date, p.close) for p in prices], columns=["date", "close"])
        df.set_index("date", inplace=True)
        first_close = df["close"].iloc[0]
        if first_close == 0:
            continue
        df["norm"] = df["close"] / first_close * 100
        perf = (df["close"].iloc[-1] / first_close) - 1
        series_data.append({
            "instrument": inst,
            "df": df,
            "performance": perf
        })
        all_dates.update(df.index.tolist())

    if not series_data:
        return {"period": period, "labels": [], "series": [], "annotations": []}

    all_dates = sorted(all_dates)
    labels = [d.isoformat() for d in all_dates]
    series = []
    for item in series_data:
        df = item["df"]
        df_reindexed = df.reindex(all_dates).ffill()  # pas de bfill
        values = [None if pd.isna(x) else round(x, 4) for x in df_reindexed["norm"].tolist()]
        series.append({
            "instrument_id": item["instrument"].id,
            "name": item["instrument"].name,
            "is_benchmark": item["instrument"].is_benchmark,
            "style": "dashed" if item["instrument"].is_benchmark else "solid",
            "values": values,
            "performance_pct": item["performance"]
        })

    # Précharger les instruments pour éviter N+1
    instrument_ids_set = set(instrument_ids)
    instrument_map = {inst.id: inst for inst in db.query(models.Instrument).filter(models.Instrument.id.in_(instrument_ids_set)).all()}

    annotations = []
    signals = db.query(models.MonthlySignal).order_by(models.MonthlySignal.signal_date).all()
    for sig in signals:
        if start_date and sig.signal_date < start_date:
            continue
        if end_date and sig.signal_date > end_date:
            continue
        if sig.signal_type in ["ROTATE_TO_LEADER", "CASH", "HOLD_CURRENT", "HOLD_LEADER"]:
            label = f"{sig.signal_type}"
            if sig.selected_instrument_id and sig.selected_instrument_id in instrument_map:
                inst = instrument_map[sig.selected_instrument_id]
                label += f" : {inst.name}"
            annotations.append({
                "date": sig.signal_date.isoformat(),
                "label": label,
                "signal_type": sig.signal_type
            })

    return {
        "period": period,
        "labels": labels,
        "series": series,
        "annotations": annotations
    }