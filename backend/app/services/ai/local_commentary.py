from .base import AICommentaryProvider


class LocalCommentaryProvider(AICommentaryProvider):
    """Génère un commentaire déterministe à partir des données chiffrées."""

    def generate(self, data: dict) -> dict:
        leader_name = data.get("leader_name", "Leader")
        leader_score = data.get("leader_score")
        second_name = data.get("second_name")
        score_gap = data.get("score_gap")
        signal_type = data.get("signal_type", "UNKNOWN")
        threshold = data.get("threshold_used", 0.05)

        leader_pct = f"{leader_score:.2%}" if leader_score is not None else "—"
        gap_pct = f"{score_gap:.2%}" if score_gap is not None else "—"
        threshold_pct = f"{threshold:.2%}"

        summary = f"Signal actuel : {signal_type}"

        if signal_type == "CASH":
            decision_explained = (
                f"L'ETF leader {leader_name} affiche un momentum de {leader_pct}, "
                "mais il se situe sous sa moyenne mobile SMA200. "
                "La stratégie Dual Momentum impose de rester en liquidités (CASH) "
                "tant qu'aucun actif de l'univers ne dépasse sa SMA200."
            )
        elif signal_type == "ROTATE_TO_LEADER":
            decision_explained = (
                f"Le leader actuel est {leader_name} avec un momentum de {leader_pct}. "
                f"Son écart avec le second ({second_name or 'N/A'}) est de {gap_pct}, "
                f"supérieur au seuil de bascule de {threshold_pct}. "
                "Il est au-dessus de sa SMA200, ce qui déclenche une rotation vers cet actif."
            )
        elif signal_type == "HOLD_LEADER":
            decision_explained = (
                f"La position actuelle est maintenue sur {leader_name}. "
                f"Momentum : {leader_pct}. "
                f"Écart avec le second : {gap_pct}. "
                "Le filtre SMA200 est respecté et aucun avantage suffisant ne justifie une rotation."
            )
        elif signal_type == "HOLD_CURRENT":
            decision_explained = (
                f"Le leader théorique est {leader_name} avec un momentum de {leader_pct}, "
                f"mais son avance sur le second ({second_name or 'N/A'}) est de {gap_pct}, "
                f"inférieure au seuil de bascule de {threshold_pct}. "
                "La position actuelle est donc conservée pour éviter une rotation excessive."
            )
        else:
            decision_explained = (
                f"Signal inconnu : {signal_type}. "
                "Veuillez consulter les détails du calcul."
            )

        risk_note = (
            "Les données proviennent de Yahoo Finance et peuvent présenter des erreurs. "
            "La stratégie Dual Momentum reste systématique : elle n'offre aucune garantie de performance future."
        )

        return {
            "summary": summary,
            "decision_explained": decision_explained,
            "risk_note": risk_note,
            "tone": "pedagogical"
        }