from datetime import date, timedelta
import logging
from typing import Optional
import yfinance as yf
import pandas as pd

from .base import PriceProvider
from ... import models
from ...database import SessionLocal

logger = logging.getLogger(__name__)


class YFinancePriceService(PriceProvider):
    """Récupère les prix via yfinance."""

    def __init__(self, ticker: str):
        self.ticker = ticker

    def fetch_prices(self, start_date: date, end_date: date) -> list[dict]:
        """Télécharge les données entre start_date et end_date incluses."""
        data = yf.download(
            self.ticker,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=10
        )

        if data is None or data.empty:
            raise ValueError(f"Aucune donnée retournée pour {self.ticker}")

        # Normaliser les colonnes si MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        records = []
        for index, row in data.iterrows():
            d = index.date() if isinstance(index, pd.Timestamp) else index

            close = self._to_float(row.get("Close"))
            if close is None:
                continue

            records.append({
                "price_date": d,
                "open": self._to_float(row.get("Open")),
                "high": self._to_float(row.get("High")),
                "low": self._to_float(row.get("Low")),
                "close": close,
                "volume": self._to_int(row.get("Volume")),
                "source": "yfinance"
            })
        return records

    def update_database(self, instrument_id: int, force_full: bool = False) -> dict:
        """Met à jour la base pour un instrument donné."""
        db = SessionLocal()
        try:
            instrument = db.get(models.Instrument, instrument_id)
            if not instrument:
                raise ValueError("Instrument introuvable")

            last_price_date = db.query(models.DailyPrice).filter(
                models.DailyPrice.instrument_id == instrument_id
            ).order_by(models.DailyPrice.price_date.desc()).first()

            # Par défaut on récupère 18 mois, sinon depuis la dernière date - 7 jours
            start_date = date.today() - timedelta(days=18*30)
            if last_price_date and not force_full:
                start_date = last_price_date.price_date - timedelta(days=7)

            end_date = date.today()
            records = self.fetch_prices(start_date, end_date)

            if not records:
                return {"inserted": 0, "updated": 0, "total": 0, "message": "Aucune donnée"}

            inserted = 0
            updated = 0
            for rec in records:
                existing = db.query(models.DailyPrice).filter_by(
                    instrument_id=instrument_id,
                    price_date=rec["price_date"]
                ).first()
                if existing:
                    existing.open = rec["open"]
                    existing.high = rec["high"]
                    existing.low = rec["low"]
                    existing.close = rec["close"]
                    existing.volume = rec["volume"]
                    existing.source = "yfinance"
                    updated += 1
                else:
                    db.add(models.DailyPrice(
                        instrument_id=instrument_id,
                        **rec
                    ))
                    inserted += 1

            db.commit()
            return {"inserted": inserted, "updated": updated, "total": inserted + updated}
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {instrument_id}: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    def _to_float(value) -> Optional[float]:
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value) -> Optional[int]:
        try:
            if pd.isna(value):
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None