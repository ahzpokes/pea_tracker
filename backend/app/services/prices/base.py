from abc import ABC, abstractmethod
from datetime import date


class PriceProvider(ABC):
    @abstractmethod
    def fetch_prices(self, instrument_id: int, start_date: date, end_date: date) -> list[dict]:
        """Retourne une liste de dicts normalisés."""
        raise NotImplementedError