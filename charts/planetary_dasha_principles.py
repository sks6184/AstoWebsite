"""Shared planetary-dasha pair assessment from Yogini Dasha Chapter 6."""
from typing import Any

from .vedic_utils import PLANET_NAMES, get_owned_houses, get_planet, house_distance


CHAPTER_SIX_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 6: Interpretation of Vimshottari Dasha",
    "printed_pages": "50-59",
    "pdf_pages": "58-67",
}


def evaluate_planetary_dasha_pair(
    chart_data: dict[str, Any],
    major_lord: str | None,
    subperiod_lord: str | None,
    category_houses: list[int],
) -> dict[str, Any]:
    """Judge a planetary major/subperiod pair by relative placement and topic activation."""
    if not major_lord or not subperiod_lord:
        return {
            "calculation_status": "unavailable",
            "score": 0,
            "status": "not_confirmed",
            "reasons": [],
            "source_reference": CHAPTER_SIX_REFERENCE,
        }

    major = get_planet(chart_data, major_lord, "d1")
    subperiod = get_planet(chart_data, subperiod_lord, "d1")
    major_house = major.get("house")
    subperiod_house = subperiod.get("house")
    distance = house_distance(major_house, subperiod_house)
    reverse_distance = house_distance(subperiod_house, major_house)
    score = 0
    reasons = []

    if distance in {1, 4, 5, 7, 9, 10}:
        score += 8
        reasons.append("Major and subperiod lords are in a kendra or trikona relationship.")
    if {distance, reverse_distance} == {6, 8}:
        score -= 8
        reasons.append("Major and subperiod lords are in a 6/8 relationship.")
    if {distance, reverse_distance} == {2, 12}:
        score -= 6
        reasons.append("Major and subperiod lords are in a 2/12 relationship.")

    activated_topic_houses = sorted(
        set(get_owned_houses(chart_data, subperiod_lord) + ([subperiod_house] if subperiod_house else []))
        & set(category_houses)
    )
    if distance in category_houses:
        score += 6
        reasons.append(f"Subperiod lord is {distance}th from the major-period lord, activating a topic house.")
    if activated_topic_houses:
        score += 5
        reasons.append(f"Subperiod lord connects to relevant D1 house(s) {activated_topic_houses}.")

    return {
        "calculation_status": "active",
        "major_lord": major_lord,
        "major_lord_name": PLANET_NAMES.get(major_lord, major_lord),
        "subperiod_lord": subperiod_lord,
        "subperiod_lord_name": PLANET_NAMES.get(subperiod_lord, subperiod_lord),
        "distance_from_major_to_subperiod": distance,
        "distance_from_subperiod_to_major": reverse_distance,
        "is_kendra_or_trikona": distance in {1, 4, 5, 7, 9, 10},
        "is_six_eight": {distance, reverse_distance} == {6, 8},
        "is_two_twelve": {distance, reverse_distance} == {2, 12},
        "activated_topic_houses": activated_topic_houses,
        "score": score,
        "status": "supports" if score >= 8 else "mixed" if score > 0 else "pressured" if score < 0 else "not_confirmed",
        "reasons": reasons,
        "source_reference": CHAPTER_SIX_REFERENCE,
    }
