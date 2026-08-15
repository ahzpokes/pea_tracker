import hashlib
import json
import os
import logging
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from ... import models
from .base import AICommentaryProvider
from .local_commentary import LocalCommentaryProvider

logger = logging.getLogger(__name__)


def _get_next_month_first_day(today: date) -> date:
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _build_data_from_signal(signal: models.MonthlySignal, db: Session) -> dict:
    leader = None
    if signal.selected_instrument_id:
        inst = db.get(models.Instrument, signal.selected_instrument_id)
        if inst:
            leader = {"name": inst.name, "yahoo_symbol": inst.yahoo_symbol}

    # Pour HOLD_CURRENT, le leader théorique est dans calculation_details_json
    details = signal.calculation_details_json or {}
    if signal.signal_type == "HOLD_CURRENT":
        # On privilégie le leader théorique pour le commentaire
        leader_name = details.get("leader_name", leader.get("name") if leader else "Leader")
        leader_symbol = details.get("leader_symbol", leader.get("yahoo_symbol") if leader else "")
    else:
        leader_name = leader.get("name") if leader else details.get("leader_name", "Leader")
        leader_symbol = leader.get("yahoo_symbol") if leader else details.get("leader_symbol", "")

    return {
        "signal_type": signal.signal_type,
        "signal_date": signal.signal_date.isoformat(),
        "leader_name": leader_name,
        "leader_symbol": leader_symbol,
        "leader_score": signal.leader_score,
        "second_score": signal.second_score,
        "score_gap": signal.score_gap,
        "leader_above_sma200": signal.leader_above_sma200,
        "leader_close": signal.leader_close,
        "leader_sma200": signal.leader_sma200,
        "threshold_used": signal.threshold_used,
        "next_control_date": _get_next_month_first_day(date.today()).isoformat()
    }


def _get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(models.Setting).filter_by(setting_key=key).first()
    if setting:
        return setting.setting_value
    return os.getenv(key, default)


def _get_provider(db: Session) -> AICommentaryProvider:
    provider_name = _get_setting(db, "AI_PROVIDER", "local").lower()
    if provider_name == "gemini":
        api_key = _get_setting(db, "GEMINI_API_KEY", "")
        model = _get_setting(db, "AI_MODEL", "gemini-2.0-flash")  # modèle à jour
        if api_key:
            from .gemini_provider import GeminiProvider
            return GeminiProvider(api_key, model)
    elif provider_name == "nvidia":
        api_key = _get_setting(db, "NVIDIA_API_KEY", "")
        model = _get_setting(db, "AI_MODEL", "meta/llama-3.1-8b-instruct")
        if api_key:
            from .nvidia_provider import NvidiaProvider
            return NvidiaProvider(api_key, model)
    return LocalCommentaryProvider()


def _hash_prompt(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_commentary(db: Session, force: bool = False) -> models.AICommentary:
    signal = db.query(models.MonthlySignal).order_by(
        models.MonthlySignal.signal_date.desc(),
        models.MonthlySignal.id.desc()
    ).first()
    if not signal:
        raise ValueError("Aucun signal calculé. Calculez d'abord un signal Dual Momentum.")

    data = _build_data_from_signal(signal, db)
    prompt_hash = _hash_prompt(data)
    provider_name = _get_setting(db, "AI_PROVIDER", "local").lower()
    model_name = _get_setting(db, "AI_MODEL", "local")

    if not force:
        cached = db.query(models.AICommentary).filter_by(
            monthly_signal_id=signal.id,
            prompt_hash=prompt_hash,
            provider=provider_name
        ).order_by(models.AICommentary.created_at.desc()).first()
        if cached:
            return cached

    provider = _get_provider(db)
    try:
        result = provider.generate(data)
        if result is None:
            raise ValueError("Le provider a retourné None au lieu d'un dictionnaire.")
        required = ["summary", "decision_explained", "risk_note"]
        for key in required:
            if key not in result:
                raise ValueError(f"Clé manquante dans la réponse du provider : {key}")
        tone = result.get("tone", "pedagogical")
        commentary = models.AICommentary(
            monthly_signal_id=signal.id,
            provider=provider_name,
            model_name=model_name,
            prompt_hash=prompt_hash,
            summary=result["summary"],
            decision_explained=result["decision_explained"],
            risk_note=result.get("risk_note"),
            raw_json=result,
            created_at=datetime.now(timezone.utc)
        )
        db.add(commentary)
        db.commit()
        db.refresh(commentary)
        return commentary
    except Exception as e:
        logger.warning(f"Provider {provider_name} a échoué : {e}. Fallback vers local.")
        local_provider = LocalCommentaryProvider()
        result = local_provider.generate(data)
        commentary = models.AICommentary(
            monthly_signal_id=signal.id,
            provider="local",
            model_name="local",
            prompt_hash=prompt_hash,
            summary=result["summary"],
            decision_explained=result["decision_explained"],
            risk_note=result.get("risk_note"),
            raw_json=result,
            created_at=datetime.now(timezone.utc)
        )
        db.add(commentary)
        db.commit()
        db.refresh(commentary)
        return commentary


def get_latest_commentary(db: Session) -> models.AICommentary | None:
    return db.query(models.AICommentary).order_by(
        models.AICommentary.created_at.desc()
    ).first()