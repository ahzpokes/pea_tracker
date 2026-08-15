from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas
from ..services.signals.dual_momentum import calculate_signal, get_latest_signal

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.post("/calculate", response_model=schemas.SignalResponse)
def trigger_calculation(db: Session = Depends(get_db)):
    try:
        signal = calculate_signal(db)
        return signal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul : {str(e)}")


@router.get("", response_model=List[schemas.SignalResponse])
def list_signals(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.MonthlySignal).order_by(
        models.MonthlySignal.signal_date.desc()
    ).limit(limit).all()


@router.get("/latest", response_model=schemas.SignalResponse)
def latest_signal(db: Session = Depends(get_db)):
    signal = get_latest_signal(db)
    if not signal:
        raise HTTPException(status_code=404, detail="Aucun signal calculé.")
    return signal