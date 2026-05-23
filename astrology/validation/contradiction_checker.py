def _has_mixed_or_negative_rules(evidence: dict) -> bool:
    return any(
        rule.get("polarity") in {"mixed", "negative"}
        for rule in evidence.get("triggered_rules", [])
    )


def check_contradictions(answer: str, evidence: dict) -> list[str]:
    lowered = answer.lower()
    issues = []
    contradiction_payload = evidence.get("contradictions", {})
    if contradiction_payload.get("has_contradictions") and not any(word in lowered for word in ["conflict", "mixed", "however", "contradict", "pressure", "risk", "partial"]):
        issues.append("Answer does not explain cross-system contradictions from the contradiction resolver.")
    for issue in contradiction_payload.get("issues", []):
        systems = set(issue.get("systems", []))
        if {"Vimshottari", "Yogini"}.issubset(systems) and "yogini" not in lowered:
            issues.append("Answer does not mention Yogini when it modifies Vimshottari timing.")
        if {"Jaimini", "Parashari"}.issubset(systems) and "partial" not in lowered and "jaimini" not in lowered:
            issues.append("Answer does not explain partial Jaimini support versus Parashari weakness.")
    if _has_mixed_or_negative_rules(evidence) and not any(word in lowered for word in ["conflict", "mixed", "however", "contradict", "pressure", "risk"]):
        issues.append("Answer ignores mixed/negative triggered rules or contradictory signals.")
    scores = evidence.get("summary_scores", {})
    risk = scores.get("risk_score", 0)
    delay = scores.get("delay_score", 0)
    if (risk >= 40 or delay >= 40) and not any(word in lowered for word in ["risk", "delay", "pressure", "caution"]):
        issues.append("Answer does not disclose significant risk/delay scores.")
    return issues
