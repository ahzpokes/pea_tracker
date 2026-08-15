from sqlalchemy.orm import Session
from ... import models
from .yfinance_service import YFinancePriceService
import logging

logger = logging.getLogger(__name__)


def update_all_prices(db: Session, force_full: bool = False) -> list[dict]:
    """Met à jour tous les instruments actifs via yfinance."""
    instruments = db.query(models.Instrument).filter(
        models.Instrument.is_active.is_(True)
    ).all()

    results = []
    for instrument in instruments:
        try:
            service = YFinancePriceService(instrument.yahoo_symbol)
            result = service.update_database(instrument.id, force_full)
            results.append({
                "instrument_id": instrument.id,
                "name": instrument.name,
                "yahoo_symbol": instrument.yahoo_symbol,
                "inserted": result.get("inserted", 0),
                "updated": result.get("updated", 0),
                "total": result.get("total", 0),
                "status": "success",
                "message": "OK"
            })
        except Exception as e:
            results.append({
                "instrument_id": instrument.id,
                "name": instrument.name,
                "yahoo_symbol": instrument.yahoo_symbol,
                "inserted": 0,
                "updated": 0,
                "total": 0,
                "status": "error",
                "message": str(e)
            })
    return results