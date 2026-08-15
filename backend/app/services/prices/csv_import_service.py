import io
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from ... import models


def _safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value):
    try:
        if pd.isna(value):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def import_csv_for_instrument(db: Session, instrument_id: int, content: bytes):
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise ValueError(f"CSV invalide : {exc}")

    df.columns = [str(col).strip().lower() for col in df.columns]

    date_col = next((col for col in df.columns if "date" in col), None)
    close_col = next((col for col in df.columns if col == "close"), None)

    if not date_col:
        raise ValueError("La colonne 'Date' est introuvable dans le CSV.")
    if not close_col:
        raise ValueError("La colonne 'Close' est introuvable dans le CSV.")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[close_col] = pd.to_numeric(df[close_col], errors="coerce")

    df = df.dropna(subset=[date_col, close_col])
    if df.empty:
        raise ValueError("Aucune ligne valide après lecture des dates et clôtures.")
    if (df[close_col] <= 0).any():
        raise ValueError("Tous les prix Close doivent être strictement positifs.")

    open_col = next((col for col in df.columns if col == "open"), None)
    high_col = next((col for col in df.columns if col == "high"), None)
    low_col = next((col for col in df.columns if col == "low"), None)
    volume_col = next((col for col in df.columns if col == "volume"), None)

    inserted = 0
    updated = 0

    for _, row in df.iterrows():
        price_date = row[date_col].date()
        close = _safe_float(row[close_col])

        existing = db.query(models.DailyPrice).filter_by(
            instrument_id=instrument_id,
            price_date=price_date
        ).first()

        if existing:
            existing.open = _safe_float(row[open_col]) if open_col else None
            existing.high = _safe_float(row[high_col]) if high_col else None
            existing.low = _safe_float(row[low_col]) if low_col else None
            existing.close = close
            existing.volume = _safe_int(row[volume_col]) if volume_col else None
            existing.source = "csv_manual"
            updated += 1
        else:
            db.add(models.DailyPrice(
                instrument_id=instrument_id,
                price_date=price_date,
                open=_safe_float(row[open_col]) if open_col else None,
                high=_safe_float(row[high_col]) if high_col else None,
                low=_safe_float(row[low_col]) if low_col else None,
                close=close,
                volume=_safe_int(row[volume_col]) if volume_col else None,
                source="csv_manual"
            ))
            inserted += 1

    db.commit()
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}