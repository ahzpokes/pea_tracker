import yfinance as yf
import logging

logger = logging.getLogger(__name__)

def _extract_from_info(info: dict) -> dict:
    """Extrait les champs utiles depuis yfinance .info."""
    isin = info.get("isin")
    symbol = info.get("symbol")
    name = info.get("longName") or info.get("shortName") or info.get("name") or symbol
    exchange = info.get("exchange") or info.get("fullExchangeName")
    currency = info.get("currency") or "EUR"
    region = info.get("region") or info.get("country") or info.get("market")

    return {
        "isin": isin,
        "yahoo_symbol": symbol,
        "name": name,
        "exchange": exchange,
        "currency": currency,
        "region": region
    }

def _is_likely_isin(query: str) -> bool:
    """Un ISIN fait 12 caractères alphanumériques sans point."""
    if len(query) == 12 and query.isalnum():
        return True
    return False

def _find_ticker_by_isin(isin: str) -> str | None:
    """Utilise l'API de recherche Yahoo pour retrouver le ticker."""
    try:
        # Utiliser yfinance Search (si disponible)
        search = yf.Search(isin)
        # Attendre un peu car la recherche est asynchrone dans yfinance
        results = search.quotes
        if results and len(results) > 0:
            # Le premier résultat est généralement le bon
            return results[0].get("symbol")
    except Exception as e:
        logger.warning(f"yfinance Search failed for ISIN {isin}: {e}")

    # Fallback : API HTTP Yahoo Finance
    try:
        import requests
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": isin, "quotes_count": 1, "news_count": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.ok:
            data = response.json()
            quotes = data.get("quotes", [])
            if quotes:
                return quotes[0].get("symbol")
    except Exception as e:
        logger.warning(f"HTTP search failed for ISIN {isin}: {e}")
    return None

def lookup_instrument(query: str) -> dict:
    """Recherche les métadonnées d'un instrument à partir d'un ISIN ou ticker."""
    query = query.strip().upper()
    if not query:
        raise ValueError("Requête vide.")

    ticker = query
    original_isin = None

    if _is_likely_isin(query):
        # Chercher le ticker Yahoo correspondant
        found_ticker = _find_ticker_by_isin(query)
        if not found_ticker:
            raise ValueError("Impossible de trouver un ticker Yahoo pour cet ISIN.")
        ticker = found_ticker
        original_isin = query
    else:
        # Supposons que c'est un ticker Yahoo
        pass

    # Récupérer les infos via yfinance
    try:
        yticker = yf.Ticker(ticker)
        info = yticker.info
        if not info:
            raise ValueError("Aucune information retournée par Yahoo Finance.")
        data = _extract_from_info(info)
        # Si l'ISIN a été fourni, on le garde
        if original_isin:
            data["isin"] = original_isin
        return data
    except Exception as e:
        raise ValueError(f"Erreur yfinance pour {ticker}: {e}")