from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..services.signals.dual_momentum import get_latest_signal

from ..database import get_db
from .. import models

router = APIRouter(tags=["Dashboard"])


def _next_month_first_day(today: date) -> date:
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    instruments = db.query(models.Instrument).all()
    active_etfs = [i for i in instruments if i.is_active and not i.is_benchmark]
    benchmarks = [i for i in instruments if i.is_benchmark]

    last_price_date = db.query(func.max(models.DailyPrice.price_date)).scalar()
    latest_signal = get_latest_signal(db)

    if latest_signal:
        signal_info = {
            "type": latest_signal.signal_type,
            "message": f"{latest_signal.signal_type} (leader : {latest_signal.leader_score:.2%})"
        }
    else:
        signal_info = {
            "type": "NOT_CALCULATED",
            "message": "Signal Dual Momentum non calculé"
        }

    return {
        "counts": {
            "total_instruments": len(instruments),
            "active_etfs": len(active_etfs),
            "inactive_etfs": len([i for i in instruments if not i.is_active]),
            "benchmarks": len(benchmarks)
        },
        "last_update": last_price_date.isoformat() if last_price_date else None,
        "next_control_date": _next_month_first_day(date.today()).isoformat(),
        "signal": signal_info
    }