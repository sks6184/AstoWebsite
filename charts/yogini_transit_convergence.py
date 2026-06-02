"""Conservative transit-trigger confirmation from Yogini Dasha Chapter 11."""
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .vedic_utils import PLANET_NAMES, aspected_houses, get_planet, sign_distance, transit_context_for_lord


CHAPTER_ELEVEN_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 11: Composite Approach of Vedic Astrology",
    "printed_pages": "130-182",
    "pdf_pages": "138-190",
}


def evaluate_transit_convergence(
    chart_data: dict[str, Any],
    category_houses: list[int],
    target_date: Any,
) -> dict[str, Any]:
    """Check slow transit triggers and expose fast planets only as timing refiners."""
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo("UTC")).replace(hour=12)
    moon_sign = get_planet(chart_data, "Mo", "d1").get("sign_number")
    triggers = []
    score = 0
    slow_support = False

    for planet_code in ["Ju", "Sa", "Ma", "Su", "Mo"]:
        transit = transit_context_for_lord(chart_data, planet_code, target_dt)
        house = transit.get("transit_house_from_lagna")
        aspects = sorted(set(aspected_houses(planet_code, house)) & set(category_houses))
        direct = house in category_houses
        connected = direct or bool(aspects)
        moon_house = sign_distance(moon_sign, transit.get("transit_sign_number"))
        contribution = 0
        role = "timing_refiner"
        if planet_code in {"Ju", "Sa"} and connected:
            contribution = 5
            role = "slow_trigger"
            slow_support = True
        elif planet_code == "Ma" and connected:
            contribution = 3 if slow_support else 1
            role = "execution_trigger"
        elif planet_code in {"Su", "Mo"} and connected:
            contribution = 1
        score += contribution
        triggers.append(
            {
                "planet": planet_code,
                "planet_name": PLANET_NAMES.get(planet_code, planet_code),
                "role": role,
                "transit_house_from_lagna": house,
                "transit_house_from_moon": moon_house,
                "relevant_house_placement": direct,
                "relevant_house_aspects": aspects,
                "connected_to_topic": connected,
                "score": contribution,
            }
        )

    return {
        "calculation_status": "active",
        "score": min(score, 15),
        "status": "supports" if score >= 8 else "mixed" if score else "not_confirmed",
        "triggers": triggers,
        "instruction": "Use transits as confirmation and timing refinement, not as the sole prediction basis.",
        "deferred_unscored_rules": [
            "pre_ingress_effects",
            "body_part_health_predictions",
            "dasha_start_transit_snapshot",
            "moon_lagna_vedha_ranking",
            "jupiter_trine_natal_or_navamsha_lord",
        ],
        "source_reference": CHAPTER_ELEVEN_REFERENCE,
    }
