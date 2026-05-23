_RELOCATION_QUESTION_MARKERS = frozenset({
    "return to", "return back", "return home", "go back", "go home", "move back",
    "come back", "coming back", "homeland", "hometown", "native place", "native country",
    "native land", "repatriate", "repatriation", "back to india", "back to home",
    "settle back", "shift back",
})

_PERMANENT_MARKERS = frozenset({
    "forever", "for good", "permanently", "permanent return", "permanent settlement",
    "permanently settle", "never come back", "settle permanently", "settle for good",
})


def _question_text(evidence: dict) -> str:
    return (evidence.get("question") or {}).get("text", "").lower()


def check_evidence(answer: str, evidence: dict) -> list[str]:
    issues = []
    lowered = answer.lower()
    score_words = ["score", "confidence", "medium", "high", "low"]

    if not any(word in lowered for word in score_words):
        issues.append("Answer does not discuss scores or confidence.")
    if evidence.get("question", {}).get("category") == "career" and "d10" not in lowered:
        issues.append("Career answer does not mention D10 evidence.")
    if evidence.get("parashari_vimshottari", {}).get("current_mahadasha") and not all(
        word in lowered for word in ["mahadasha", "antardasha"]
    ):
        issues.append("Answer does not name Vimshottari Mahadasha and Antardasha evidence.")
    if evidence.get("jaimini", {}).get("calculation_status") == "active" and "jaimini" not in lowered:
        issues.append("Answer ignores available Jaimini facts.")
    if evidence.get("jaimini", {}).get("calculation_status") == "active" and not any(
        word in lowered for word in ["chara", "atmakaraka", "amatyakaraka", "arudha", "karakamsha", "upapada"]
    ):
        issues.append("Answer mentions Jaimini but not specific Jaimini factors.")
    if evidence.get("yogini", {}).get("calculation_status") == "active" and "yogini" not in lowered:
        issues.append("Answer ignores available Yogini facts.")
    if evidence.get("yogini", {}).get("calculation_status") == "active" and not any(
        word in lowered for word in ["sub-period", "sub period", "lord"]
    ):
        issues.append("Answer mentions Yogini but not its period/lord details.")
    remedy_context = evidence.get("remedy_context", {})
    if remedy_context.get("remedies"):
        if "no deterministic remedy was calculated" in lowered:
            issues.append("Answer says no remedy was calculated even though deterministic remedy_context is present.")
        if "beej" not in lowered or "mantra" not in lowered:
            issues.append("Remedy section does not include the deterministic Beej mantra guidance.")
    timing_question = any(
        phrase in evidence.get("question", {}).get("text", "").lower()
        for phrase in ["when", "promotion", "promoted", "job change", "job switch", "switch job"]
    )
    if timing_question and evidence.get("transits", {}).get("future_timing", {}).get("scan_months") == 60:
        if "**" not in answer:
            issues.append("Timing answer should bold important timing windows.")
    if "dasha" not in lowered:
        issues.append("Answer does not mention dasha timing.")

    # ── Relocation / return-to-homeland rules ──────────────────────────────────
    q_text = _question_text(evidence)
    is_relocation = any(marker in q_text for marker in _RELOCATION_QUESTION_MARKERS)
    is_permanent = any(marker in q_text for marker in _PERMANENT_MARKERS)

    if is_relocation or evidence.get("question", {}).get("category") == "foreign_travel":
        if not any(h in lowered for h in ["4th house", "4th lord", "fourth house", "fourth lord"]):
            issues.append(
                "Relocation/return answer must discuss the 4th house (homeland/roots) — it is missing."
            )
        if not any(h in lowered for h in ["12th house", "12th lord", "twelfth house", "twelfth lord"]):
            issues.append(
                "Relocation/return answer must discuss the 12th house (foreign settlement) — it is missing."
            )
        if "d4" not in lowered and "chaturthamsha" not in lowered:
            issues.append(
                "Relocation answer should reference D4 (Chaturthamsha) for residence/property confirmation."
            )
        if not any(p in lowered for p in ["rahu", "ketu"]):
            issues.append(
                "Relocation answer should discuss Rahu/Ketu axis — Rahu pulls toward foreign, Ketu toward homeland."
            )

    if is_permanent and not any(
        phrase in lowered
        for phrase in [
            "temporary", "permanent", "short-term", "long-term",
            "settle permanently", "permanent return", "temporary visit",
        ]
    ):
        issues.append(
            "Question asks about 'forever'/'permanently' but answer does not distinguish "
            "temporary return from permanent resettlement."
        )

    return issues
