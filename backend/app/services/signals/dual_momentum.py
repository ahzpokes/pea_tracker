import logging
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session
from ... import models
from ..calculations.indicators import sma200

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.05
MAX_PRICE_AGE_DAYS = 7
MAX_DATE_DIFF_DAYS = 3

def _get_threshold(db: Session) -> float:
    setting = db.query(models.Setting).filter_by(setting_key="momentum_threshold").first()
    if setting:
        try:
            return float(setting.setting_value)
        except (ValueError, TypeError):
            pass
    return DEFAULT_THRESHOLD

def _get_closes(db: Session, instrument_id: int) -> list[tuple[date, float]]:
    prices = db.query(models.DailyPrice).filter(
        models.DailyPrice.instrument_id == instrument_id
    ).order_by(models.DailyPrice.price_date).all()
    return [(p.price_date, p.close) for p in prices]

def _momentum_12m(closes: list[tuple[date, float]]) -> tuple[float, date, float, date, float] | None:
    """Calcule le momentum 12 mois (252 séances) et renvoie les détails."""
    if len(closes) < 252:
        return None
    start_idx = -252
    start_date, start_close = closes[start_idx]
    end_date, end_close = closes[-1]
    if start_close == 0:
        return None
    momentum = (end_close / start_close) - 1
    return momentum, start_date, start_close, end_date, end_close

def _sma200(closes: list[tuple[date, float]]) -> float | None:
    if len(closes) < 200:
        return None
    recent_closes = [c for _, c in closes[-200:]]
    return sum(recent_closes) / 200

def _check_freshness(candidates: list[dict]) -> None:
    """Vérifie que les derniers cours sont récents et alignés."""
    if not candidates:
        return
    today = date.today()
    for cand in candidates:
        last_date = cand["last_date"]
        if (today - last_date).days > MAX_PRICE_AGE_DAYS:
            raise ValueError(
                f"Le dernier cours de {cand['instrument'].name} date de {last_date} "
                f"({ (today - last_date).days } jours). Mettez à jour les prix."
            )
    last_dates = [cand["last_date"] for cand in candidates]
    max_diff = max(last_dates) - min(last_dates)
    if max_diff.days > MAX_DATE_DIFF_DAYS:
        raise ValueError(
            f"Les derniers cours des actifs ne sont pas alignés (écart de {max_diff.days} jours)."
        )

def calculate_signal(db: Session) -> models.MonthlySignal:
    instruments = db.query(models.Instrument).filter(
        models.Instrument.is_active.is_(True),
        models.Instrument.is_benchmark.is_(False)
    ).all()

    if not instruments:
        raise ValueError("Aucun ETF actif pour le calcul.")

    candidates = []
    excluded = []
    for inst in instruments:
        closes = _get_closes(db, inst.id)
        if len(closes) < 200:
            excluded.append({"instrument": inst.name, "reason": "moins de 200 séances"})
            continue
        sma = _sma200(closes)
        last_close = closes[-1][1]
        last_date = closes[-1][0]
        above_sma200 = last_close > sma if sma is not None else False
        if not above_sma200:
            excluded.append({"instrument": inst.name, "reason": "sous SMA200"})
            continue

        mom_data = _momentum_12m(closes)
        if mom_data is None:
            excluded.append({"instrument": inst.name, "reason": "moins de 252 séances"})
            continue

        momentum, start_date, start_close, end_date, end_close = mom_data
        candidates.append({
            "instrument": inst,
            "momentum": momentum,
            "sma200": sma,
            "last_close": last_close,
            "last_date": last_date,
            "above_sma200": True,
            "start_date": start_date,
            "start_close": start_close,
            "end_date": end_date,
            "end_close": end_close,
        })

    # Contrôle de fraîcheur sur les candidats
    _check_freshness(candidates)

    if not candidates:
        # Aucun ETF au-dessus de sa SMA200
        signal_type = "CASH"
        selected_instrument_id = None
        leader_score = None
        second_score = None
        score_gap = None
        leader_close = None
        leader_sma200 = None
        leader_above_sma200 = None
        calc_details = {
            "excluded": excluded,
            "message": "Aucun ETF au-dessus de sa SMA200"
        }
    else:
        candidates.sort(key=lambda x: x["momentum"], reverse=True)
        leader = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None

        leader_score = leader["momentum"]
        second_score = second["momentum"] if second else None
        score_gap = leader_score - second_score if second_score is not None else None
        threshold = _get_threshold(db)

        last_signal = db.query(models.MonthlySignal).order_by(
            models.MonthlySignal.signal_date.desc(),
            models.MonthlySignal.id.desc()
        ).first()
        previous_instrument_id = last_signal.selected_instrument_id if last_signal else None

        if previous_instrument_id is None:
            # Pas de position précédente, on adopte le leader
            signal_type = "ROTATE_TO_LEADER"
            selected_instrument_id = leader["instrument"].id
        elif previous_instrument_id == leader["instrument"].id:
            signal_type = "HOLD_LEADER"
            selected_instrument_id = leader["instrument"].id
        else:
            # Position différente, vérifier l'écart
            if score_gap is not None and score_gap < threshold:
                # Avantage insuffisant, on garde la position actuelle
                signal_type = "HOLD_CURRENT"
                selected_instrument_id = previous_instrument_id
                # On stocke quand même les métriques du leader théorique
            else:
                signal_type = "ROTATE_TO_LEADER"
                selected_instrument_id = leader["instrument"].id

        calc_details = {
            "leader_name": leader["instrument"].name,
            "leader_symbol": leader["instrument"].yahoo_symbol,
            "leader_momentum": leader["momentum"],
            "leader_start_date": leader["start_date"].isoformat(),
            "leader_start_close": leader["start_close"],
            "leader_end_date": leader["end_date"].isoformat(),
            "leader_end_close": leader["end_close"],
            "second_name": second["instrument"].name if second else None,
            "candidates_count": len(candidates),
            "excluded": excluded,
            "threshold_used": threshold,
            "selected_instrument_id": selected_instrument_id,
            "selected_is_leader": selected_instrument_id == leader["instrument"].id,
            "position_was_none": previous_instrument_id is None
        }

    signal = models.MonthlySignal(
        signal_date=date.today(),
        selected_instrument_id=selected_instrument_id,
        previous_instrument_id=previous_instrument_id,
        signal_type=signal_type,
        leader_score=leader_score,
        second_score=second_score,
        score_gap=score_gap,
        leader_close=leader["last_close"] if candidates else None,
        leader_sma200=leader["sma200"] if candidates else None,
        leader_above_sma200=leader["above_sma200"] if candidates else None,
        threshold_used=_get_threshold(db),
        calculation_details_json=calc_details,
        created_at=datetime.now(timezone.utc)
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal

def get_latest_signal(db: Session) -> models.MonthlySignal | None:
    return db.query(models.MonthlySignal).order_by(
        models.MonthlySignal.signal_date.desc(),
        models.MonthlySignal.id.desc()
    ).first()