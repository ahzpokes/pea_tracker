def sma200(closes: list[float]) -> float | None:
    if len(closes) < 200:
        return None
    return sum(closes[-200:]) / 200