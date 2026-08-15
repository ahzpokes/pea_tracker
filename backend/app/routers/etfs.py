from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..services.calculations.performance import compute_performance_metrics
from ..services.prices.yfinance_service import YFinancePriceService
from ..services.instruments.lookup_service import lookup_instrument

router = APIRouter(tags=["ETFs"])

@router.post("/etfs/lookup", response_model=schemas.LookupResponse)
def lookup_etf(payload: schemas.LookupRequest):
    try:
        data = lookup_instrument(payload.query)
        return {"message": "OK", **data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {e}")

@router.get("/etfs", response_model=List[schemas.InstrumentResponse])
def list_etfs(include_inactive: bool = True, db: Session = Depends(get_db)):
    query = db.query(models.Instrument)
    if not include_inactive:
        query = query.filter(models.Instrument.is_active.is_(True))
    return query.order_by(
        models.Instrument.is_benchmark.desc(),
        models.Instrument.name.asc()
    ).all()


@router.post("/etfs", response_model=schemas.InstrumentResponse, status_code=201)
def create_etf(payload: schemas.InstrumentCreate, db: Session = Depends(get_db)):
    if db.query(models.Instrument).filter(models.Instrument.isin == payload.isin).first():
        raise HTTPException(status_code=409, detail="Cet ISIN existe déjà.")
    if db.query(models.Instrument).filter(
        models.Instrument.yahoo_symbol == payload.yahoo_symbol
    ).first():
        raise HTTPException(status_code=409, detail="Ce ticker Yahoo existe déjà.")

    instrument = models.Instrument(**payload.model_dump())
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    return instrument


@router.get("/etfs/{etf_id}", response_model=schemas.InstrumentResponse)
def get_etf(etf_id: int, db: Session = Depends(get_db)):
    instrument = db.get(models.Instrument, etf_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument introuvable.")
    return instrument


@router.patch("/etfs/{etf_id}", response_model=schemas.InstrumentResponse)
def update_etf(
    etf_id: int,
    payload: schemas.InstrumentUpdate,
    db: Session = Depends(get_db)
):
    instrument = db.get(models.Instrument, etf_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument introuvable.")

    data = payload.model_dump(exclude_unset=True)

    if "isin" in data:
        existing = db.query(models.Instrument).filter(
            models.Instrument.isin == data["isin"],
            models.Instrument.id != etf_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Cet ISIN est déjà utilisé.")

    if "yahoo_symbol" in data:
        existing = db.query(models.Instrument).filter(
            models.Instrument.yahoo_symbol == data["yahoo_symbol"],
            models.Instrument.id != etf_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Ce ticker Yahoo est déjà utilisé.")

    for key, value in data.items():
        setattr(instrument, key, value)

    db.commit()
    db.refresh(instrument)
    return instrument


@router.delete("/etfs/{etf_id}", status_code=204)
def delete_etf(etf_id: int, db: Session = Depends(get_db)):
    instrument = db.get(models.Instrument, etf_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument introuvable.")
    db.delete(instrument)
    db.commit()
    return Response(status_code=204)


@router.get("/etfs/{etf_id}/performance", response_model=schemas.PerformanceResponse)
def get_etf_performance(etf_id: int, db: Session = Depends(get_db)):
    instrument = db.get(models.Instrument, etf_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument introuvable.")
    metrics = compute_performance_metrics(db, etf_id)
    metrics["instrument_id"] = etf_id
    return metrics


@router.post("/etfs/{etf_id}/test-ticker")
def test_ticker(etf_id: int, db: Session = Depends(get_db)):
    instrument = db.get(models.Instrument, etf_id)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument introuvable.")
    try:
        service = YFinancePriceService(instrument.yahoo_symbol)
        end = date.today()
        start = end - timedelta(days=30)
        records = service.fetch_prices(start, end)
        if records:
            return {
                "status": "ok",
                "message": f"Données disponibles : {len(records)} points depuis le {records[0]['price_date']}.",
                "sample": records[-1]
            }
        else:
            return {"status": "error", "message": "Aucune donnée retournée."}
    except Exception as e:
        return {"status": "error", "message": f"Erreur : {str(e)}"}