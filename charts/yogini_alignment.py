"""
Yogini Dasha alignment check for timing windows.

Reads from pre-computed chart_data["dashas"]["yogini"] (built by astro_engine).
Pattern mirrors jaimini_confirmation.py — called per timing window at midpoint date.
"""
from datetime import datetime
from typing import Any

from .vedic_utils import PLANET_NAMES, get_owned_houses, get_planet, get_planets


# Classical Yogini nature — determines a base score bonus/penalty.
# Source: Applications of Yogini Dasha (K.N. Rao tradition)
YOGINI_NATURE: dict[str, str] = {
    "Mangala": "auspicious",    # Moon — nurturing, results
    "Pingala": "mixed",         # Sun — authority, visibility, some instability
    "Dhanya": "auspicious",     # Jupiter — expansion, wisdom
    "Bhramari": "challenging",  # Mars — obstacles, delays, conflict
    "Bhadrika": "auspicious",   # Mercury — communication, learning, commerce
    "Ulka": "challenging",      # Saturn — hardship, discipline, delays
    "Siddha": "auspicious",     # Venus — success, completion, relationships
    "Sankata": "challenging",   # Rahu — confusion, sudden changes
}


def _parse_date(value: str) -> Any:
    return datetime.fromisoformat(value).date()


def _current_period(periods: list[dict], target_date: Any) -> dict:
    for period in periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start <= target_date <= end:
            return period
    return periods[-1] if periods else {}


def _lord_d10_house(chart_data: dict, lord_code: str) -> int | None:
    """Find the planet's house number in the pre-computed D10 chart."""
    for planet in get_planets(chart_data, "d10"):
        if planet.get("code") == lord_code:
            return planet.get("house")
    return None


def _lord_category_score(
    chart_data: dict,
    lord_code: str,
    category_houses: list[int],
    category: str,
) -> tuple[int, list[str]]:
    if not lord_code:
        return 0, []

    planet = get_planet(chart_data, lord_code, "d1")
    owned = get_owned_houses(chart_data, lord_code)
    placed = planet.get("house")
    connections = sorted(set(owned + ([placed] if placed else [])))
    category_connected = [h for h in connections if h in category_houses]

    score = 0
    reasons = []

    if category_connected:
        score += 18
        reasons.append(
            f"{PLANET_NAMES.get(lord_code, lord_code)} (Yogini lord) connects to D1 "
            f"category house(s) {category_connected}."
        )

    if category in {"career", "business"}:
        d10_house = _lord_d10_house(chart_data, lord_code)
        if d10_house and d10_house in category_houses:
            score += 10
            reasons.append(
                f"{PLANET_NAMES.get(lord_code, lord_code)} is in D10 house {d10_house}, "
                f"confirming career/business theme in Navamsha-adjacent varga."
            )

    return score, reasons


def build_yogini_alignment(
    chart_data: dict,
    category: str,
    category_houses: list[int],
    target_date: Any,
) -> dict:
    """
    Returns which Yogini major and sub-period are active at target_date,
    how auspicious the Yogini nature is, and whether its lords support the category.

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

    major_nature = YOGINI_NATURE.get(major_yogini, "mixed")
    if major_nature == "auspicious":
        score += 10
        reasons.append(f"{major_yogini} Yogini is classically auspicious.")
    elif major_nature == "challenging":
        score -= 8
        reasons.append(f"{major_yogini} Yogini is classically challenging.")

    major_score, major_reasons = _lord_category_score(
        chart_data, major_lord, category_houses, category
    )
    score += major_score
    reasons.extend(major_reasons)

    if sub_lord and sub_lord != major_lord:
        sub_score, sub_reasons = _lord_category_score(
            chart_data, sub_lord, category_houses, category
        )
        score += sub_score // 2
        reasons.extend(sub_reasons)

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
        "major_nature": major_nature,
        "score": score,
        "status": status,
        "reasons": reasons[:5],
    }
