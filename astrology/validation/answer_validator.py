import re
from typing import Any

from .genericity_checker import detect_generic_phrases
from .repair_instruction_builder import build_repair_instruction
from .section_checker import is_business_question, is_timing_question, missing_sections


ASTROLOGY_SPELLINGS = {
    "parashri": "Parashari",
    "parasharii": "Parashari",
    "jamini": "Jaimini",
    "sarvashtagwarg": "Sarvashtakavarga",
    "sarvashtakvarga": "Sarvashtakavarga",
    "antardasa": "Antardasha",
    "mahadahsa": "Mahadasha",
    "yogni": "Yogini",
    "muhurtha": "Muhurta",
    "nakshtra": "Nakshatra",
    "titi": "Tithi",
    "lagana": "Lagna",
}


def _question_text(evidence: dict[str, Any]) -> str:
    return evidence.get("question", {}).get("text", "")


def _has_any(lowered: str, terms: list[str]) -> bool:
    return any(term in lowered for term in terms)


def _date_or_window_present(answer: str) -> bool:
    lowered = answer.lower()
    has_year = bool(re.search(r"\b20\d{2}\b", answer))
    has_month = _has_any(
        lowered,
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
    )
    return has_year and (has_month or _has_any(lowered, ["window", "period", "between", "from"]))


def _better_window_present(answer: str) -> bool:
    lowered = answer.lower()
    return _date_or_window_present(answer) and _has_any(lowered, ["better", "recommended", "best", "prefer"])


def _proposed_date_assessed(answer: str) -> bool:
    lowered = answer.lower()
    return _has_any(lowered, ["proposed date", "around", "mixed", "avoid", "not good", "good", "bad", "preliminary"])


def _launch_mode_present(answer: str) -> bool:
    lowered = answer.lower()
    return _has_any(lowered, ["soft launch", "beta", "private testing", "payment launch", "public marketing", "public launch"])


def _start_recommendation_present(answer: str) -> bool:
    lowered = answer.lower()
    return _has_any(
        lowered,
        [
            "can start",
            "start small",
            "soft start",
            "soft launch",
            "do not start",
            "do not use",
            "start quietly",
            "preparation",
            "private testing",
        ],
    )


def _money_outcome_present(answer: str) -> bool:
    lowered = answer.lower()
    return _has_any(lowered, ["money potential", "financial gain", "income", "earning", "profit", "side income", "revenue", "make money"])


def _risk_level_present(answer: str) -> bool:
    lowered = answer.lower()
    return _has_any(lowered, ["risk is", "risk level", "low risk", "medium risk", "high risk", "risk:", "risk remains"])


def _muhurta_basis_present(answer: str) -> bool:
    lowered = answer.lower()
    muhurta_terms = ["tithi", "nakshatra", "yoga", "karana", "weekday", "lagna", "moon strength", "planetary hour"]
    preliminary_phrase = "exact muhurta selection requires"
    return preliminary_phrase in lowered or sum(1 for term in muhurta_terms if term in lowered) >= 3


POSITIVE_TIMING_PHRASES = [
    "recommended date",
    "best date",
    "auspicious date",
    "good time to start",
    "should start on",
]

NEGATIVE_TIMING_PHRASES = [
    "unfavorable",
    "not auspicious",
    "postpone",
    "avoid",
    "high risk",
    "significant hurdles",
    "not recommended",
]

TIMING_CLARIFICATION_PHRASES = [
    "least unfavorable",
    "least difficult",
    "within the checked window",
    "within the searched window",
    "soft launch",
    "testing",
    "preparation",
    "not public launch",
    "not for public launch",
    "postpone public launch",
    "final recommendation is to postpone",
    "overall recommendation: postpone",
]


def _contradictory_timing_issue(answer: str) -> str:
    lowered = answer.lower()
    has_positive = _has_any(lowered, POSITIVE_TIMING_PHRASES)
    has_negative = _has_any(lowered, NEGATIVE_TIMING_PHRASES)
    has_clarification = _has_any(lowered, TIMING_CLARIFICATION_PHRASES)
    if has_positive and has_negative and not has_clarification:
        return (
            "Answer gives both a positive timing recommendation and negative timing judgment "
            "without clarifying whether the date is least unfavorable, soft-launch/testing only, "
            "or still a postpone-public-launch recommendation."
        )
    return ""


def _business_evidence_missing(answer: str, evidence: dict[str, Any]) -> list[str]:
    lowered = answer.lower()
    missing = []
    required_terms = {
        "D1 basis": ["d1", "rashi", "lagna"],
        "D9 basis": ["d9", "navamsha"],
        "D10 evidence": ["d10", "dashamsha"],
        "dasha basis": ["dasha", "mahadasha", "antardasha"],
        "Parashari basis": ["parashari", "2nd", "7th", "10th", "11th"],
        "2nd/7th/10th/11th house logic": ["2nd", "7th", "10th", "11th"],
        "Mercury for website/business": ["mercury"],
        "Jupiter for advisory/astrology wisdom": ["jupiter"],
        "Saturn for execution/pressure": ["saturn"],
    }
    if _has_any(_question_text(evidence).lower(), ["website", "online", "technology", "digital"]):
        required_terms["Rahu for online/technology"] = ["rahu"]
    if evidence.get("yogini", {}).get("calculation_status") == "active":
        required_terms["Yogini dasha basis"] = ["yogini"]
    if evidence.get("jaimini", {}).get("calculation_status") == "active":
        required_terms["Jaimini Amatyakaraka/Arudha basis"] = ["jaimini", "amatyakaraka", "arudha"]
    for label, terms in required_terms.items():
        present = all(term in lowered for term in terms) if label == "2nd/7th/10th/11th house logic" else any(term in lowered for term in terms)
        if not present:
            missing.append(label)
    return missing


def _unsupported_claims(answer: str) -> list[str]:
    lowered = answer.lower()
    claims = []
    if "jaimini" in lowered and not _has_any(lowered, ["amatyakaraka", "atmakaraka", "arudha", "karakamsha", "upapada", "chara"]):
        claims.append("Jaimini mentioned without Amatyakaraka, Atmakaraka, Arudha, Karakamsha, Upapada, or Chara Dasha factor.")
    if ("parashari" in lowered or "parāśari" in lowered) and not _has_any(
        lowered,
        ["lord", "lagna", "mahadasha", "antardasha", "dasha"],
    ):
        claims.append("Parashari mentioned without specific house/lord/dasha factors.")
    if _has_any(lowered, ["divisional", "varga"]) and not _has_any(lowered, ["d9", "d10", "d7", "d2", "d4", "d12", "d24", "d30"]):
        claims.append("Divisional charts mentioned without naming a specific varga.")
    if "d10" in lowered and not _has_any(lowered, ["house", "lord", "dashamsha", "planet", "placement"]):
        claims.append("D10 mentioned without an actual D10 fact.")
    if "sarvashtakavarga" in lowered and not _has_any(lowered, ["bindu", "bindus", "point", "points"]):
        claims.append("Sarvashtakavarga mentioned without bindu/point values.")
    if "vimshottari system" in lowered:
        claims.append("Vimshottari called a system; it should be described as a Parashari dasha.")
    if "chara system" in lowered or "chara dasha system" in lowered:
        claims.append("Chara called a system; it should be described as a Jaimini dasha.")
    if _has_any(lowered, ["sun transit is unfavorable", "sun is unfavorable", "sun transit not auspicious"]) and not _has_any(
        lowered,
        ["taurus", "aries", "house", "sarvashtakavarga", "points", "bindu"],
    ):
        claims.append("Sun transit called unfavorable without sign, house, and Sarvashtakavarga evidence.")
    return claims


def _spelling_issues(answer: str) -> list[str]:
    lowered = answer.lower()
    return [f"Possible spelling issue: {wrong} should be {right}." for wrong, right in ASTROLOGY_SPELLINGS.items() if wrong in lowered]


def _quality_issues(answer: str, question: str) -> list[str]:
    lowered = answer.lower()
    issues = []
    if re.search(r"\b(in|for|to|from|with|because|during|regarding|toward|into)\s*[.!?](?:\s|$)", answer, re.IGNORECASE):
        issues.append("Answer appears to contain an incomplete sentence.")
    if "critical time" in lowered and not _has_any(
        lowered,
        [
            "critical time for launch",
            "critical time for testing",
            "critical time for preparation",
            "critical time for decision",
            "critical time for payment",
            "critical time for public release",
        ],
    ):
        issues.append("Vague timing phrase 'critical time' is not explained.")
    raw_score_patterns = [
        r"\b\w+\s+score\s+is\b",
        r"\bsuccess score\b",
        r"\bdelay score\b",
        r"\brisk score\b",
        r"\bscore\s*[:=]\s*\d+",
    ]
    if any(re.search(pattern, lowered) for pattern in raw_score_patterns):
        issues.append("Visible answer exposes raw score language instead of user-facing interpretation.")
    q = question.lower()
    if _has_any(q, ["will it start", "business start", "should i start", "when should i start"]) and not _start_recommendation_present(answer):
        issues.append("Answer does not clearly say start, do not start, or soft start only.")
    if _has_any(q, ["give me money", "make money", "earn", "income", "profit", "financial gain"]) and not _money_outcome_present(answer):
        issues.append("Answer does not clearly discuss financial outcome or money potential.")
    if _has_any(q, ["business", "startup", "website"]) and not _risk_level_present(answer):
        issues.append("Answer does not state practical risk level.")
    return issues


def validate_astrology_answer(answer: str, evidence: dict[str, Any], pass_threshold: int = 75) -> dict[str, Any]:
    question = _question_text(evidence)
    lowered = (answer or "").lower()
    timing = is_timing_question(question)
    business = is_business_question(question) or evidence.get("question", {}).get("category") == "business"
    issues: list[str] = []
    missing_evidence: list[str] = []
    unsupported_claims = _unsupported_claims(answer)
    generic_hits = detect_generic_phrases(answer)
    spelling = _spelling_issues(answer)
    quality_issues = _quality_issues(answer, question)
    missing = missing_sections(answer, question)
    score = 100

    if not _has_any(lowered[:400], ["yes", "no", "do not", "avoid", "start", "launch", "recommended", "not see", "chance"]):
        score -= 25
        issues.append("Answer does not directly answer the user's question.")

    if timing:
        timing_issue = _contradictory_timing_issue(answer)
        if timing_issue:
            score -= 20
            issues.append(timing_issue)
        if not _better_window_present(answer):
            score -= 20
            issues.append("Timing question has no better alternative date/window.")
        if not _proposed_date_assessed(answer):
            score -= 10
            issues.append("Timing answer does not assess the proposed date as good, bad, or mixed.")
        if not _launch_mode_present(answer):
            score -= 10
            issues.append("Timing/startup answer does not specify launch mode such as soft launch, beta, private testing, payment launch, or public marketing.")
        if not _muhurta_basis_present(answer):
            score -= 10
            missing_evidence.append("muhurta factors or preliminary muhurta warning")

    if business:
        business_missing = _business_evidence_missing(answer, evidence)
        missing_evidence.extend(business_missing)
        if "D10 evidence" in business_missing:
            score -= 15
        if "dasha basis" in business_missing:
            score -= 15
        for item in business_missing:
            if item not in {"D10 evidence", "dasha basis"}:
                score -= 5

    if any("Parashari" in claim for claim in unsupported_claims):
        score -= 10
    if any("Jaimini" in claim for claim in unsupported_claims):
        score -= 10
    if any("Divisional" in claim for claim in unsupported_claims):
        score -= 10
    if any("Sarvashtakavarga" in claim for claim in unsupported_claims):
        score -= 5
    score -= 5 * len(generic_hits)
    score -= 5 * len(spelling)
    score -= 10 * len(quality_issues)

    if not _has_any(lowered, ["confidence", "cautious", "moderate", "high certainty", "low certainty"]):
        score -= 10
        issues.append("Answer does not provide a confidence level.")
    if evidence.get("contradictions", {}).get("has_contradictions") and not _has_any(lowered, ["conflict", "mixed", "contradict", "however"]):
        score -= 10
        issues.append("Answer does not explain contradictions.")

    for section in missing:
        score -= 3
    issues.extend(spelling)
    issues.extend(quality_issues)
    issues.extend(unsupported_claims)
    for item in missing_evidence:
        issues.append(f"Missing evidence: {item}.")
    for phrase in generic_hits:
        if not _has_any(lowered, ["d1", "d9", "d10", "dasha", "bindu", "mahadasha", "antardasha", "arudha", "amatyakaraka"]):
            issues.append(f"Generic phrase without specific evidence: {phrase}.")

    result = {
        "passed": False,
        "score": max(0, score),
        "issues": issues,
        "missing_sections": missing,
        "missing_evidence": missing_evidence,
        "generic_phrases_detected": generic_hits,
        "unsupported_claims": unsupported_claims,
        "repair_instruction": "",
    }
    result["passed"] = result["score"] >= pass_threshold and not unsupported_claims and not missing_evidence and not missing
    if not result["passed"]:
        result["repair_instruction"] = build_repair_instruction(result, evidence)
    return result
