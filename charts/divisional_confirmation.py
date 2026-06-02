"""Timing-oriented divisional-chart confirmation from Yogini Dasha Chapter 5."""
from typing import Any

from .vedic_utils import (
    DUSTHANA_HOUSES,
    PLANET_NAMES,
    SIGN_LORDS,
    get_house_lord as get_d1_house_lord,
    get_planet,
    get_planet_dignity,
)


CHAPTER_FIVE_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 5: Interpretation of Divisional Charts",
    "printed_pages": "46-49",
    "pdf_pages": "54-57",
}

_CATEGORY_VARGA: dict[str, str] = {
    "job": "d10",
    "career": "d10",
    "business": "d10",
    "money": "d2",
    "marriage": "d9",
    "children": "d7",
    "health": "d30",
    "education": "d24",
    "property": "d4",
    "family": "d12",
    "foreign_travel": "d9",
    "spirituality": "d20",
    "general": "d9",
}
_CATEGORY_KARAKAS: dict[str, list[str]] = {
    "job": ["Sa", "Me"],
    "career": ["Su"],
    "business": ["Me"],
    "money": ["Ju"],
    "marriage": ["Ve"],
    "children": ["Ju"],
    "health": ["Su", "Ma"],
    "education": ["Me", "Ju"],
    "property": ["Ma"],
    "family": ["Mo", "Su"],
    "foreign_travel": ["Ra", "Sa"],
    "spirituality": ["Ju", "Ke"],
}


def _house_sign(chart_data: dict[str, Any], chart_key: str, house_number: int) -> int | None:
    for house in chart_data.get(chart_key, {}).get("houses", []):
        if house.get("number") == house_number:
            return house.get("sign_number")
    ascendant = get_planet(chart_data, "Asc", chart_key)
    asc_sign = ascendant.get("sign_number")
    return ((asc_sign + house_number - 2) % 12) + 1 if asc_sign else None


def _add_factor(factors: list[dict[str, Any]], code: str, score: int, reason: str) -> None:
    factors.append({"code": code, "score": score, "reason": reason})


def evaluate_divisional_confirmation(
    chart_data: dict[str, Any],
    category: str,
    category_houses: list[int],
    active_lords: list[str],
) -> dict[str, Any]:
    """Confirm active planetary-dasha lords through the category's primary varga."""
    chart_key = _CATEGORY_VARGA.get(category, "d9")
    if chart_key not in chart_data:
        return {
            "calculation_status": "unavailable",
            "primary_varga": chart_key,
            "score": 0,
            "status": "not_confirmed",
            "factors": [],
            "source_reference": CHAPTER_FIVE_REFERENCE,
        }

    factors: list[dict[str, Any]] = []
    ascendant = get_planet(chart_data, "Asc", chart_key)
    lagna_lord = SIGN_LORDS.get(ascendant.get("sign_number"))
    lagna_lord_planet = get_planet(chart_data, lagna_lord, chart_key) if lagna_lord else {}
    lagna_lord_house = lagna_lord_planet.get("house")
    lagna_lord_dignity = get_planet_dignity(chart_data, lagna_lord, chart_key) if lagna_lord else "unknown"

    if lagna_lord_house in {1, 4, 5, 7, 9, 10} or lagna_lord_dignity in {"exalted", "own_sign"}:
        _add_factor(factors, "varga_lagna_lord_support", 5, f"{chart_key.upper()} Lagna lord is well placed.")
    elif lagna_lord_house in DUSTHANA_HOUSES or lagna_lord_dignity == "debilitated":
        _add_factor(factors, "varga_lagna_lord_pressure", -5, f"{chart_key.upper()} Lagna lord is pressured.")

    relevant_lords = []
    for house_number in category_houses:
        house_lord = SIGN_LORDS.get(_house_sign(chart_data, chart_key, house_number))
        if not house_lord:
            continue
        relevant_lords.append(house_lord)
        planet = get_planet(chart_data, house_lord, chart_key)
        placed_house = planet.get("house")
        dignity = get_planet_dignity(chart_data, house_lord, chart_key)
        if placed_house in {1, 4, 5, 7, 9, 10, 11} or dignity in {"exalted", "own_sign"}:
            _add_factor(factors, "relevant_varga_house_lord_support", 3, f"{chart_key.upper()} {house_number}th lord is supported.")
        elif placed_house in DUSTHANA_HOUSES or dignity == "debilitated":
            _add_factor(factors, "relevant_varga_house_lord_pressure", -3, f"{chart_key.upper()} {house_number}th lord is pressured.")

        d1_lord = get_d1_house_lord(chart_data, house_number)
        d1_lord_planet = get_planet(chart_data, d1_lord, chart_key) if d1_lord else {}
        d1_lord_house = d1_lord_planet.get("house")
        d1_lord_dignity = get_planet_dignity(chart_data, d1_lord, chart_key) if d1_lord else "unknown"
        d1_lord_name = PLANET_NAMES.get(d1_lord, d1_lord)
        if d1_lord_house in {1, 4, 5, 7, 9, 10, 11} or d1_lord_dignity in {"exalted", "own_sign"}:
            _add_factor(
                factors,
                "d1_topic_lord_supported_in_varga",
                3,
                f"D1 {house_number}th lord {d1_lord_name} is supported in {chart_key.upper()}.",
            )
        elif d1_lord_house in DUSTHANA_HOUSES or d1_lord_dignity == "debilitated":
            _add_factor(
                factors,
                "d1_topic_lord_pressured_in_varga",
                -3,
                f"D1 {house_number}th lord {d1_lord_name} is pressured in {chart_key.upper()}.",
            )

    for lord in dict.fromkeys(active_lords):
        if not lord:
            continue
        planet = get_planet(chart_data, lord, chart_key)
        house = planet.get("house")
        dignity = get_planet_dignity(chart_data, lord, chart_key)
        name = PLANET_NAMES.get(lord, lord)
        if house in category_houses:
            _add_factor(factors, "active_lord_in_varga_topic_house", 6, f"{name} is in {chart_key.upper()} topic house {house}.")
        elif house in DUSTHANA_HOUSES:
            _add_factor(factors, "active_lord_in_varga_dusthana", -5, f"{name} is in {chart_key.upper()} dusthana house {house}.")
        if dignity in {"exalted", "own_sign"}:
            _add_factor(factors, "active_lord_varga_dignity", 4, f"{name} has {dignity} dignity in {chart_key.upper()}.")
        elif dignity == "debilitated":
            _add_factor(factors, "active_lord_varga_debilitated", -4, f"{name} is debilitated in {chart_key.upper()}.")

    for karaka in _CATEGORY_KARAKAS.get(category, []):
        planet = get_planet(chart_data, karaka, chart_key)
        house = planet.get("house")
        dignity = get_planet_dignity(chart_data, karaka, chart_key)
        name = PLANET_NAMES.get(karaka, karaka)
        if house in {1, 4, 5, 7, 9, 10} or dignity in {"exalted", "own_sign"}:
            _add_factor(factors, "varga_karaka_support", 3, f"{name}, the {category} karaka, is supported in {chart_key.upper()}.")
        elif house in DUSTHANA_HOUSES or dignity == "debilitated":
            _add_factor(factors, "varga_karaka_pressure", -3, f"{name}, the {category} karaka, is pressured in {chart_key.upper()}.")

    score = sum(factor["score"] for factor in factors)
    return {
        "calculation_status": "active",
        "primary_varga": chart_key,
        "lagna_lord": lagna_lord,
        "lagna_lord_name": PLANET_NAMES.get(lagna_lord, lagna_lord),
        "lagna_lord_house": lagna_lord_house,
        "relevant_house_lords": sorted(set(relevant_lords)),
        "active_lords": list(dict.fromkeys(lord for lord in active_lords if lord)),
        "score": score,
        "status": "supports" if score >= 8 else "mixed" if score > 0 else "pressured" if score < 0 else "not_confirmed",
        "factors": factors,
        "source_reference": CHAPTER_FIVE_REFERENCE,
    }
