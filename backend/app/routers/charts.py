from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.calculations.chart_data import get_performance_chart_data

router = APIRouter(tags=["Charts"])

@router.get("/charts/performance")
def performance_chart(
    period: str = Query("12M", pattern="^(1M|3M|6M|12M|Max)$"),
    instrument_ids: str = Query(..., description="Comma-separated instrument IDs"),
    db: Session = Depends(get_db)
):
    ids = [int(i.strip()) for i in instrument_ids.split(",") if i.strip()]
    if not ids:
        return {"period": period, "labels": [], "series": [], "annotations": []}
    return get_performance_chart_data(db, period, ids)