"""
Yogini Dasha alignment check for timing windows.

Reads from pre-computed chart_data["dashas"]["yogini"] (built by astro_engine).
Pattern mirrors jaimini_confirmation.py — called per timing window at midpoint date.
"""
from datetime import datetime
from typing import Any

from .divisional_confirmation import CHAPTER_FIVE_REFERENCE, evaluate_divisional_confirmation
from .planetary_dasha_principles import CHAPTER_SIX_REFERENCE, evaluate_planetary_dasha_pair
from .vedic_utils import PLANET_NAMES
from .yogini_baselines import CHAPTER_SEVEN_REFERENCE, evaluate_yogini_baseline
from .yogini_principles import CHAPTER_FOUR_REFERENCE, SOURCE_REFERENCE, evaluate_yogini_lord
from .yogini_snapshot import CHAPTER_EIGHT_REFERENCE, build_yogini_snapshot_checklist


def _parse_date(value: str) -> Any:
    return datetime.fromisoformat(value).date()


def _current_period(periods: list[dict], target_date: Any) -> dict:
    for period in periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start <= target_date <= end:
            return period
    return periods[-1] if periods else {}


def build_yogini_alignment(
    chart_data: dict,
    category: str,
    category_houses: list[int],
    target_date: Any,
) -> dict:
    """
    Returns which Yogini major and sub-period are active at target_date and
    whether their contextual lord, divisional, and pair factors support the category.

    Called once per timing window at the window midpoint.
    """
    yogini_data = chart_data.get("dashas", {}).get("yogini", {})
    if not yogini_data or yogini_data.get("calculation_status") != "active":
        return {
            "calculation_status": "unavailable",
            "yogini": None,
            "sub_yogini": None,
            "score": 0,
            "status": "not_confirmed",
            "reasons": ["Yogini Dasha not available in chart data."],
        }

    major = _current_period(yogini_data.get("periods", []), target_date)
    sub = _current_period(major.get("subperiods", []), target_date)

    major_yogini = major.get("yogini")
    sub_yogini = sub.get("yogini")
    major_lord = major.get("lord")
    sub_lord = sub.get("lord")

    score = 0
    reasons = []

    major_assessment = evaluate_yogini_lord(chart_data, major_lord, category, category_houses)
    sub_assessment = evaluate_yogini_lord(chart_data, sub_lord, category, category_houses) if sub_lord else {}
    score += major_assessment.get("score", 0)
    reasons.extend(factor["reason"] for factor in major_assessment.get("factors", []))

    if sub_lord and sub_lord != major_lord:
        score += sub_assessment.get("score", 0) // 2
        reasons.extend(factor["reason"] for factor in sub_assessment.get("factors", []))

    pair_assessment = evaluate_planetary_dasha_pair(chart_data, major_lord, sub_lord, category_houses)
    divisional_confirmation = evaluate_divisional_confirmation(
        chart_data, category, category_houses, [major_lord, sub_lord]
    )
    classical_baseline = evaluate_yogini_baseline(major_yogini, sub_yogini)
    snapshot_checklist = build_yogini_snapshot_checklist(
        major_yogini, sub_yogini, major_assessment, sub_assessment
    )
    score += pair_assessment.get("score", 0)
    score += divisional_confirmation.get("score", 0) // 2
    score += classical_baseline.get("score", 0)
    reasons.extend(pair_assessment.get("reasons", []))
    reasons.extend(factor["reason"] for factor in divisional_confirmation.get("factors", []))

    score = min(100, max(0, score))
    status = "supports" if score >= 20 else "mixed" if score >= 8 else "not_confirmed"

    return {
        "calculation_status": "active",
        "yogini": major_yogini,
        "sub_yogini": sub_yogini,
        "major_lord": major_lord,
        "major_lord_name": PLANET_NAMES.get(major_lord, major_lord) if major_lord else None,
        "sub_lord": sub_lord,
        "sub_lord_name": PLANET_NAMES.get(sub_lord, sub_lord) if sub_lord else None,
        "major_period_start": major.get("start"),
        "major_period_end": major.get("end"),
        "major_lord_quality": major_assessment.get("quality", "weak"),
        "sub_lord_quality": sub_assessment.get("quality", "weak"),
        "major_lord_assessment": major_assessment,
        "sub_lord_assessment": sub_assessment,
        "pair_assessment": pair_assessment,
        "divisional_confirmation": divisional_confirmation,
        "classical_baseline": classical_baseline,
        "snapshot_checklist": snapshot_checklist,
        "source_reference": SOURCE_REFERENCE,
        "source_references": [
            SOURCE_REFERENCE,
            CHAPTER_FOUR_REFERENCE,
            CHAPTER_FIVE_REFERENCE,
            CHAPTER_SIX_REFERENCE,
            CHAPTER_SEVEN_REFERENCE,
            CHAPTER_EIGHT_REFERENCE,
        ],
        "score": score,
        "status": status,
        "reasons": reasons[:5],
    }
