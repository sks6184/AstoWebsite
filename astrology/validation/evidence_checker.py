import re

from chat.prediction_context import CATEGORY_RULES
from astrology.rules.dasha_scoring import dasha_polarity_summary


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

# Terms the LLM might use to reference each divisional chart
_CHART_MENTION_ALIASES: dict[str, list[str]] = {
    "d1":  ["d1", "lagna chart", "birth chart", "rashi chart"],
    "d2":  ["d2", "hora"],
    "d3":  ["d3", "drekkana"],
    "d4":  ["d4", "chaturthamsha"],
    "d7":  ["d7", "saptamsha"],
    "d9":  ["d9", "navamsha"],
    "d10": ["d10", "dashamsha"],
    "d12": ["d12", "dwadashamsha"],
    "d16": ["d16", "shodashamsha"],
    "d20": ["d20"],
    "d24": ["d24", "siddhamsha"],
    "d27": ["d27"],
    "d30": ["d30", "trimsamsha"],
    "d40": ["d40"],
    "d45": ["d45"],
    "d60": ["d60", "shashtiamsha"],
}


def _question_text(evidence: dict) -> str:
    return (evidence.get("question") or {}).get("text", "").lower()


def _charts_with_triggered_rules(evidence: dict) -> set[str]:
    """Return lowercase chart keys that have at least one triggered rule in the evidence."""
    charts = set()
    for rule in evidence.get("triggered_rules", []):
        chart = (rule.get("chart") or "").lower()
        if chart:
            charts.add(chart)
    return charts


def _has_dasha_context(lowered: str) -> bool:
    return any(term in lowered for term in ["dasha", "mahadasha", "antardasha", "vimshottari"])


def _dasha_polarity_claim_issues(answer: str, evidence: dict) -> list[str]:
    lowered = answer.lower()
    if not _has_dasha_context(lowered):
        return []

    positive_claim = bool(
        re.search(
            r"\b(?:dasha|mahadasha|antardasha|vimshottari)\b[^.]{0,90}\b(?:favo[u]?rable|auspicious|positive|supportive|supports)\b",
            lowered,
        )
        or re.search(
            r"\b(?:favo[u]?rable|auspicious|positive|supportive)\b[^.]{0,90}\b(?:dasha|mahadasha|antardasha|vimshottari)\b",
            lowered,
        )
    )
    pressure_claim = bool(
        re.search(
            r"\b(?:dasha|mahadasha|antardasha|vimshottari)\b[^.]{0,90}\b(?:unfavo[u]?rable|negative|difficult|weak|pressure|challenging)\b",
            lowered,
        )
        or re.search(
            r"\b(?:unfavo[u]?rable|negative|difficult|weak|challenging)\b[^.]{0,90}\b(?:dasha|mahadasha|antardasha|vimshottari)\b",
            lowered,
        )
    )
    if not positive_claim and not pressure_claim:
        return []

    summary = dasha_polarity_summary(evidence)
    issues = []
    if positive_claim and not summary["has_positive"]:
        issues.append(
            "Answer calls Vimshottari/Mahadasha/Antardasha favorable or supportive, "
            "but no positive triggered Vimshottari rule supports that dasha polarity."
        )
    if pressure_claim and not summary["has_pressure"]:
        issues.append(
            "Answer calls Vimshottari/Mahadasha/Antardasha unfavorable, difficult, weak, or challenging, "
            "but no mixed/negative triggered Vimshottari rule supports that dasha polarity."
        )
    return issues


def check_evidence(answer: str, evidence: dict) -> list[str]:
    issues = []
    lowered = answer.lower()
    score_words = [
        "score", "confidence", "medium", "high", "low",
        "strong", "strongly", "clearly", "moderate", "weak", "limited",
        "favorable", "unfavorable", "mixed", "partial", "uncertain",
        "supported", "confirmed", "alignment", "leans",
    ]

    if not any(word in lowered for word in score_words):
        issues.append("Answer does not discuss the strength or quality of astrological indicators.")

    # ── Auto-validate every non-D1 divisional chart required for this category ──
    category = (evidence.get("question") or {}).get("category", "")
    category_charts = CATEGORY_RULES.get(category, {}).get("divisional_charts", [])
    triggered_charts = _charts_with_triggered_rules(evidence)

    for chart in category_charts:
        if chart == "d1":
            continue  # D1 is always implied; skip
        aliases = _CHART_MENTION_ALIASES.get(chart, [chart])
        if any(alias in lowered for alias in aliases):
            continue  # chart is already mentioned — pass
        if chart in triggered_charts:
            # Rules fired for this chart but the answer doesn't mention it — hard failure
            issues.append(
                f"Answer does not mention {chart.upper()} chart evidence — "
                f"it is a required divisional chart for this {category} question and rules were triggered."
            )
        else:
            # No rules fired but chart is still required for this category — soft failure
            issues.append(
                f"Answer does not mention {chart.upper()} ({_CHART_MENTION_ALIASES.get(chart, [chart])[0]}) — "
                f"it is a required divisional chart for {category} questions. "
                f"If data is unavailable, state that explicitly."
            )

    if evidence.get("parashari_vimshottari", {}).get("current_mahadasha") and not all(
        word in lowered for word in ["mahadasha", "antardasha"]
    ):
        issues.append("Answer does not name Vimshottari Mahadasha and Antardasha evidence.")

    # Use data-presence checks — calculation_status is stripped from the compact evidence payload
    windows = (evidence.get("transits") or {}).get("future_timing", {}).get("windows", [])
    jaimini_present = (
        any(w.get("jaimini_active_sign") for w in windows)
        or bool((evidence.get("jaimini") or {}).get("active_chara_dasha"))
    )
    yogini_present = (
        any(w.get("yogini_name") for w in windows)
        or bool((evidence.get("yogini") or {}).get("current_yogini"))
    )
    if jaimini_present and not any(w in lowered for w in ["jaimini", "chara"]):
        issues.append(
            "Answer ignores available Jaimini/Chara Dasha data — must name the active Chara sign and its house from Lagna."
        )
    if jaimini_present and any(w in lowered for w in ["jaimini", "chara"]) and not any(
        word in lowered for word in ["chara", "atmakaraka", "amatyakaraka", "karakamsha"]
    ):
        issues.append("Answer mentions Jaimini but not specific Jaimini factors (Chara sign, Atmakaraka, etc.).")
    if yogini_present and "yogini" not in lowered:
        issues.append("Answer ignores available Yogini data — must name the active Yogini and sub-Yogini.")

    remedy_context = evidence.get("remedy_context", {})
    if remedy_context.get("remedies"):
        if "no deterministic remedy was calculated" in lowered:
            issues.append("Answer says no remedy was calculated even though deterministic remedy_context is present.")
        if "beej" not in lowered or "mantra" not in lowered:
            issues.append("Remedy section does not include the deterministic Beej mantra guidance.")

    timing_question = any(
        phrase in (evidence.get("question") or {}).get("text", "").lower()
        for phrase in ["when", "promotion", "promoted", "job change", "job switch", "switch job"]
    )
    if timing_question and evidence.get("transits", {}).get("future_timing", {}).get("scan_months") == 60:
        if "**" not in answer:
            issues.append("Timing answer should bold important timing windows.")

    if "dasha" not in lowered:
        issues.append("Answer does not mention dasha timing.")

    issues.extend(_dasha_polarity_claim_issues(answer, evidence))

    # ── Relocation / return-to-homeland rules ──────────────────────────────────
    q_text = _question_text(evidence)
    is_relocation = any(marker in q_text for marker in _RELOCATION_QUESTION_MARKERS)
    is_permanent = any(marker in q_text for marker in _PERMANENT_MARKERS)

    if is_relocation or category == "foreign_travel":
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
