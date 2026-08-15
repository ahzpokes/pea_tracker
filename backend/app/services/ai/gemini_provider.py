import json
import requests
from .base import AICommentaryProvider

class GeminiProvider(AICommentaryProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    def generate(self, data: dict) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {"Content-Type": "application/json"}
        prompt = self._build_prompt(data)
        body = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        response = requests.post(
            url,
            headers=headers,
            params={"key": self.api_key},
            json=body,
            timeout=15
        )
        if response.status_code != 200:
            raise Exception(f"Gemini API error {response.status_code}: {response.text}")
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json(text)

    def _build_prompt(self, data: dict) -> str:
        return f"""
Tu es un assistant financier pédagogique. Analyse les données calculées suivantes et rédige un commentaire en français.

Données :
{json.dumps(data, ensure_ascii=False, indent=2)}

Réponds UNIQUEMENT avec un JSON valide contenant les clés :
- summary : résumé clair du signal.
- decision_explained : explication de la décision.
- risk_note : point de vigilance.
- tone : doit être "pedagogical".

Aucun calcul supplémentaire n'est autorisé.
"""

    def _parse_json(self, text: str) -> dict:
        # Nettoyer d'éventuels marqueurs Markdown
        text = text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)