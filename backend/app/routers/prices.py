from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from typing import List
from ..services.prices.update_service import update_all_prices
from ..services.prices.yfinance_service import YFinancePriceService

from ..database import get_db
from .. import models, schemas
from ..services.prices.csv_import_service import import_csv_for_instrument

router = APIRouter(prefix="/prices", tags=["Prices"])


@router.post("/import-csv", response_model=schemas.PriceImportResult)
async def import_csv(
    instrument_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    instrument = db.get(models.Instrument, instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument introuvable.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier CSV vide.")

    try:
        result = import_csv_for_instrument(db, instrument_id, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result


@router.get("/status")
def prices_status(db: Session = Depends(get_db)):
    total_prices = db.query(func.count(models.DailyPrice.id)).scalar()
    last_date = db.query(func.max(models.DailyPrice.price_date)).scalar()
    total_instruments = db.query(func.count(models.Instrument.id)).scalar()
    return {
        "total_prices": total_prices,
        "total_instruments": total_instruments,
        "last_price_date": last_date.isoformat() if last_date else None
    }
    

@router.post("/update", response_model=List[schemas.PriceUpdateResult])
def update_prices(
    request: schemas.PriceUpdateRequest,
    db: Session = Depends(get_db)
):
    if request.instrument_id:
        instrument = db.get(models.Instrument, request.instrument_id)
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument introuvable.")
        service = YFinancePriceService(instrument.yahoo_symbol)
        try:
            result = service.update_database(instrument.id, request.force_full)
            return [{
                "instrument_id": instrument.id,
                "name": instrument.name,
                "yahoo_symbol": instrument.yahoo_symbol,
                "inserted": result.get("inserted", 0),
                "updated": result.get("updated", 0),
                "total": result.get("total", 0),
                "status": "success",
                "message": "OK"
            }]
        except Exception as e:
            return [{
                "instrument_id": instrument.id,
                "name": instrument.name,
                "yahoo_symbol": instrument.yahoo_symbol,
                "inserted": 0,
                "updated": 0,
                "total": 0,
                "status": "error",
                "message": str(e)
            }]
    else:
        return update_all_prices(db, request.force_full)