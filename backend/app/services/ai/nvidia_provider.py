import json
import requests
from .base import AICommentaryProvider

class NvidiaProvider(AICommentaryProvider):
    def __init__(self, api_key: str, model: str = "meta/llama-3.1-8b-instruct"):
        self.api_key = api_key
        self.model = model

    def generate(self, data: dict) -> dict:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        prompt = self._build_prompt(data)
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        response = requests.post(url, headers=headers, json=body, timeout=15)
        if response.status_code != 200:
            raise Exception(f"NVIDIA API error {response.status_code}: {response.text}")
        result = response.json()
        text = result["choices"][0]["message"]["content"]
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
"""

    def _parse_json(self, text: str) -> dict:
        text = text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)