from abc import ABC, abstractmethod

class AICommentaryProvider(ABC):
    @abstractmethod
    def generate(self, data: dict) -> dict:
        """Retourne un dict avec summary, decision_explained, risk_note, tone."""
        raise NotImplementedError