from typing import Any


SYSTEM_ALIASES = {
    "Parashari": {"Parashari", "Parashari/Vimshottari"},
    "Vimshottari": {"Parashari/Vimshottari"},
    "Jaimini": {"Jaimini"},
    "Yogini": {"Yogini"},
    "Divisional": {"Divisional", "Varga / Divisional"},
    "Transit": {"Transit"},
}


def _strength(score: int | float | None, fallback: str = "medium") -> str:
    if score is None:
        return fallback
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    if score > 0:
        return "low"
    return "weak"


def _direction(status: str | None = None, score: int | float | None = None, polarities: list[str] | None = None) -> str:
    polarities = polarities or []
    if "negative" in polarities and "positive" in polarities:
        return "mixed"
    if "negative" in polarities:
        return "negative"
    if "mixed" in polarities:
        return "mixed"
    if "positive" in polarities:
        return "positive"
    if status == "supports":
        return "positive"
    if status == "mixed":
        return "mixed"
    if score is not None and score >= 60:
        return "positive"
    if score is not None and score > 0:
        return "mixed"
    return "unavailable"


def _rule_ids_for_system(triggered_rules: list[dict[str, Any]], system_key: str) -> list[str]:
    aliases = SYSTEM_ALIASES.get(system_key, {system_key})
    ids = []
    for rule in triggered_rules:
        if rule.get("system") in aliases and rule.get("rule_id"):
            ids.append(rule["rule_id"])
    return ids[:12]


def _polarities_for_system(triggered_rules: list[dict[str, Any]], system_key: str) -> list[str]:
    aliases = SYSTEM_ALIASES.get(system_key, {system_key})
    return [
        rule.get("polarity", "mixed")
        for rule in triggered_rules
        if rule.get("system") in aliases
    ]


def _first_findings(system_payload: dict[str, Any], limit: int = 3) -> list[str]:
    findings = []
    for item in system_payload.get("findings", [])[:limit]:
        text = item.get("finding") or item.get("factor")
        if text:
            findings.append(text)
    return findings


def _ledger_item(
    evidence: dict[str, Any],
    system_key: str,
    payload: dict[str, Any],
    claim: str,
    score: int | float | None = None,
) -> dict[str, Any]:
    triggered_rules = evidence.get("triggered_rules", [])
    polarities = _polarities_for_system(triggered_rules, system_key)
    score = payload.get("score", score)
    direction = _direction(payload.get("status"), score, polarities)
    return {
        "system": system_key,
        "claim": claim,
        "direction": direction,
        "strength": _strength(score),
        "score": score or 0,
        "status": payload.get("status", "not_confirmed"),
        "supporting_rule_ids": _rule_ids_for_system(triggered_rules, system_key),
        "findings": _first_findings(payload),
        "available": bool(payload),
    }


def build_evidence_ledger(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    parashari = evidence.get("parashari", {})
    vimshottari = evidence.get("parashari_vimshottari", {})
    jaimini = evidence.get("jaimini", {})
    yogini = evidence.get("yogini", {})
    varga = evidence.get("varga", {})
    transits = evidence.get("transits", {})

    ledger = [
        _ledger_item(evidence, "Parashari", parashari, "D1 Parashari factors have been calculated for the question category."),
        _ledger_item(evidence, "Vimshottari", vimshottari, "Current Vimshottari dasha and antardasha have been checked against topic houses."),
        _ledger_item(evidence, "Jaimini", jaimini, "Jaimini karakas, Arudha/Karakamsha, and Chara Dasha factors have been checked."),
        _ledger_item(evidence, "Yogini", yogini, "Yogini major and sub-period lord relevance has been checked."),
        _ledger_item(evidence, "Divisional", varga, "Relevant divisional chart confirmation has been checked."),
    ]

    transit_score = transits.get("priority_score") or transits.get("score") or 0
    transit_payload = {
        "status": "supports" if transit_score >= 60 else "mixed" if transits else "not_confirmed",
        "score": transit_score,
        "findings": transits.get("findings", []),
    }
    ledger.append(_ledger_item(evidence, "Transit", transit_payload, "Transit and future timing windows have been scanned.", transit_score))
    return ledger
