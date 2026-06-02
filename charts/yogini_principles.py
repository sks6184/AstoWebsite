"""
Contextual Yogini-lord assessment from Chapters 3 and 4.

The chapter does not assign a fixed good or bad nature to each Yogini. It
instructs the reader to judge the active planetary lord through its chart
condition, relevant houses, natal promises, and divisional-chart support.
"""
from typing import Any

from .vedic_utils import (
    BENEFIC_PLANETS,
    DUSTHANA_HOUSES,
    MALEFIC_PLANETS,
    PLANET_NAMES,
    SIGN_LORDS,
    aspected_houses,
    get_house_lord,
    get_owned_houses,
    get_planet,
    get_planet_dignity,
    get_planets,
)


SOURCE_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 3: The Basic Principles",
    "printed_pages": "22-29",
    "pdf_pages": "30-37",
}
CHAPTER_FOUR_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 4: Interpretation of a Horoscope",
    "printed_pages": "30-45",
    "pdf_pages": "38-53",
}

_CATEGORY_PRIMARY_VARGA: dict[str, str] = {
    "job": "d10",
    "career": "d10",
    "business": "d10",
    "money": "d2",
    "marriage": "d9",
    "children": "d7",
    "health": "d9",
    "education": "d24",
    "spirituality": "d20",
    "property": "d4",
    "foreign_travel": "d9",
    "general": "d9",
}

_DIRECTIONALLY_STRONG_HOUSES = {
    "Me": 1,
    "Ju": 1,
    "Mo": 4,
    "Ve": 4,
    "Sa": 7,
    "Su": 10,
    "Ma": 10,
}
_DIRECTIONALLY_WEAK_HOUSES = {
    "Me": 7,
    "Ju": 7,
    "Mo": 10,
    "Ve": 10,
    "Sa": 1,
    "Su": 4,
    "Ma": 4,
}
_BENEFIC_LORDSHIP_HOUSES = {1, 4, 5, 7, 9, 10}
_RAJA_KENDRAS = {1, 4, 7, 10}
_RAJA_TRIKONAS = {1, 5, 9}
_DHANA_HOUSES = {2, 5, 9, 11}
_CATEGORY_KARAKAS: dict[str, set[str]] = {
    "job": {"Sa", "Me"},
    "career": {"Su", "Me", "Sa"},
    "business": {"Me", "Ju", "Ra"},
    "money": {"Ju", "Ve"},
    "marriage": {"Ve", "Ju"},
    "children": {"Ju"},
    "health": {"Su", "Ma"},
    "education": {"Me", "Ju"},
    "property": {"Ma", "Mo", "Ve"},
    "foreign_travel": {"Ra", "Sa"},
    "spirituality": {"Ju", "Ke"},
}


def _planet_in_chart(chart_data: dict[str, Any], chart_key: str, planet_code: str) -> dict[str, Any]:
    return get_planet(chart_data, planet_code, chart_key)


def _add_factor(
    factors: list[dict[str, Any]],
    code: str,
    score: int,
    reason: str,
) -> None:
    factors.append({"code": code, "score": score, "reason": reason})


def _association_factors(
    chart_data: dict[str, Any],
    lord_code: str,
    lord_house: int | None,
) -> list[dict[str, Any]]:
    if not lord_house:
        return []

    factors = []
    for planet in get_planets(chart_data, "d1"):
        code = planet.get("code")
        house = planet.get("house")
        if not code or code == lord_code or not house:
            continue
        is_connected = house == lord_house or lord_house in aspected_houses(code, house)
        if not is_connected:
            continue
        name = PLANET_NAMES.get(code, code)
        if code in BENEFIC_PLANETS:
            _add_factor(factors, "benefic_association", 3, f"{name} supports the Yogini lord by association or aspect.")
        elif code in MALEFIC_PLANETS:
            _add_factor(factors, "malefic_association", -3, f"{name} pressures the Yogini lord by association or aspect.")
    return factors


def _lords_connected(
    chart_data: dict[str, Any],
    first_topic_house: int,
    second_topic_house: int,
    first_lord: str,
    second_lord: str,
) -> bool:
    if not first_lord or not second_lord:
        return False
    if first_lord == second_lord:
        return True
    first = get_planet(chart_data, first_lord, "d1")
    second = get_planet(chart_data, second_lord, "d1")
    first_placed_house = first.get("house")
    second_placed_house = second.get("house")
    if not first_placed_house or not second_placed_house:
        return False
    return (
        first_placed_house == second_placed_house
        or first_placed_house == second_topic_house
        or second_placed_house == first_topic_house
        or second_placed_house in aspected_houses(first_lord, first_placed_house)
        or first_placed_house in aspected_houses(second_lord, second_placed_house)
    )


def _active_lord_yoga_factors(chart_data: dict[str, Any], lord_code: str) -> list[dict[str, Any]]:
    factors = []
    raja_relations = []
    dhana_relations = []

    for kendra in sorted(_RAJA_KENDRAS):
        for trikona in sorted(_RAJA_TRIKONAS):
            if kendra == trikona:
                continue
            kendra_lord = get_house_lord(chart_data, kendra)
            trikona_lord = get_house_lord(chart_data, trikona)
            if lord_code in {kendra_lord, trikona_lord} and _lords_connected(
                chart_data, kendra, trikona, kendra_lord, trikona_lord
            ):
                raja_relations.append(f"{kendra}/{trikona}")

    for first_house in sorted(_DHANA_HOUSES):
        for second_house in sorted(_DHANA_HOUSES):
            if first_house >= second_house:
                continue
            first_lord = get_house_lord(chart_data, first_house)
            second_lord = get_house_lord(chart_data, second_house)
            if lord_code in {first_lord, second_lord} and _lords_connected(
                chart_data, first_house, second_house, first_lord, second_lord
            ):
                dhana_relations.append(f"{first_house}/{second_house}")

    if raja_relations:
        _add_factor(
            factors,
            "active_lord_raja_yoga",
            6,
            f"{PLANET_NAMES.get(lord_code, lord_code)} activates kendra-trikona relation(s) {sorted(set(raja_relations))}.",
        )
    if dhana_relations:
        _add_factor(
            factors,
            "active_lord_dhana_yoga",
            5,
            f"{PLANET_NAMES.get(lord_code, lord_code)} activates wealth-house relation(s) {sorted(set(dhana_relations))}.",
        )
    return factors


def _dispositor_factors(chart_data: dict[str, Any], lord_code: str, d1_sign: int | None, category_houses: list[int]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dispositor_code = SIGN_LORDS.get(d1_sign)
    if not dispositor_code or dispositor_code == lord_code:
        return {}, []

    dispositor = get_planet(chart_data, dispositor_code, "d1")
    house = dispositor.get("house")
    dignity = get_planet_dignity(chart_data, dispositor_code, "d1")
    owned_houses = get_owned_houses(chart_data, dispositor_code)
    name = PLANET_NAMES.get(dispositor_code, dispositor_code)
    factors = []

    if dignity in {"exalted", "own_sign"}:
        _add_factor(factors, "strong_dispositor", 5, f"Dispositor {name} has {dignity} dignity in D1.")
    elif dignity == "debilitated":
        _add_factor(factors, "weak_dispositor", -5, f"Dispositor {name} is debilitated in D1.")
    if house in category_houses or any(owned in category_houses for owned in owned_houses):
        _add_factor(factors, "category_relevant_dispositor", 5, f"Dispositor {name} connects to the relevant topic houses.")
    if house in DUSTHANA_HOUSES:
        _add_factor(factors, "dispositor_in_dusthana", -4, f"Dispositor {name} is placed in D1 dusthana house {house}.")

    return {
        "code": dispositor_code,
        "name": name,
        "house": house,
        "dignity": dignity,
        "owned_houses": owned_houses,
    }, factors


def evaluate_yogini_lord(
    chart_data: dict[str, Any],
    lord_code: str,
    category: str,
    category_houses: list[int],
) -> dict[str, Any]:
    """Evaluate one Yogini lord using the available Chapter 3 and 4 principles."""
    name = PLANET_NAMES.get(lord_code, lord_code)
    d1 = _planet_in_chart(chart_data, "d1", lord_code)
    d1_house = d1.get("house")
    d1_sign = d1.get("sign_number")
    owned_houses = get_owned_houses(chart_data, lord_code)
    primary_varga = _CATEGORY_PRIMARY_VARGA.get(category, "d9")
    varga = _planet_in_chart(chart_data, primary_varga, lord_code)
    d9 = _planet_in_chart(chart_data, "d9", lord_code)
    factors: list[dict[str, Any]] = []

    dignity = get_planet_dignity(chart_data, lord_code, "d1")
    if dignity == "exalted":
        _add_factor(factors, "d1_exalted", 12, f"{name} is exalted in D1.")
    elif dignity == "own_sign":
        _add_factor(factors, "d1_own_sign", 8, f"{name} is in its own sign in D1.")
    elif dignity == "debilitated":
        _add_factor(factors, "d1_debilitated", -12, f"{name} is debilitated in D1.")

    relevant_owned = sorted(house for house in owned_houses if house in category_houses)
    if relevant_owned:
        _add_factor(factors, "category_house_lord", 12, f"{name} owns relevant house(s) {relevant_owned}.")
    if d1_house in category_houses:
        _add_factor(factors, "category_house_placement", 10, f"{name} is placed in relevant D1 house {d1_house}.")
    aspected_category_houses = sorted(set(aspected_houses(lord_code, d1_house)) & set(category_houses))
    if aspected_category_houses:
        _add_factor(factors, "category_house_aspect", 6, f"{name} aspects relevant D1 house(s) {aspected_category_houses}.")
    if d1_house in DUSTHANA_HOUSES:
        _add_factor(factors, "d1_dusthana_placement", -6, f"{name} is placed in D1 dusthana house {d1_house}.")
    if lord_code in _CATEGORY_KARAKAS.get(category, set()):
        _add_factor(factors, "category_karaka", 4, f"{name} is a natural significator for {category}.")

    benefic_owned = sorted(house for house in owned_houses if house in _BENEFIC_LORDSHIP_HOUSES)
    difficult_owned = sorted(house for house in owned_houses if house in DUSTHANA_HOUSES)
    if benefic_owned:
        _add_factor(factors, "benefic_house_lord", 4, f"{name} owns benefic house(s) {benefic_owned}.")
    if difficult_owned:
        _add_factor(factors, "difficult_house_lord", -4, f"{name} owns difficult house(s) {difficult_owned}.")

    if d1_house == _DIRECTIONALLY_STRONG_HOUSES.get(lord_code):
        _add_factor(factors, "directional_strength", 4, f"{name} has directional strength in D1 house {d1_house}.")
    elif d1_house == _DIRECTIONALLY_WEAK_HOUSES.get(lord_code):
        _add_factor(factors, "directional_weakness", -4, f"{name} is directionally weak in D1 house {d1_house}.")

    if d1_sign and d1_sign == d9.get("sign_number"):
        _add_factor(factors, "vargottama", 6, f"{name} repeats the same sign in D1 and D9 (Vargottama).")

    varga_house = varga.get("house")
    if varga_house in category_houses:
        _add_factor(
            factors,
            "primary_varga_category_house",
            10,
            f"{name} is in {primary_varga.upper()} house {varga_house}, confirming the {category} theme.",
        )
    elif varga_house in {1, 5, 9, 10}:
        _add_factor(factors, "primary_varga_support", 5, f"{name} is well placed in {primary_varga.upper()} house {varga_house}.")
    elif varga_house in DUSTHANA_HOUSES:
        _add_factor(factors, "primary_varga_dusthana", -8, f"{name} is in {primary_varga.upper()} dusthana house {varga_house}.")

    varga_dignity = get_planet_dignity(chart_data, lord_code, primary_varga)
    if varga_dignity in {"exalted", "own_sign"}:
        _add_factor(factors, "primary_varga_strong_dignity", 5, f"{name} has {varga_dignity} dignity in {primary_varga.upper()}.")
    elif varga_dignity == "debilitated":
        _add_factor(factors, "primary_varga_debilitated", -5, f"{name} is debilitated in {primary_varga.upper()}.")

    factors.extend(_association_factors(chart_data, lord_code, d1_house))
    dispositor, dispositor_factors = _dispositor_factors(chart_data, lord_code, d1_sign, category_houses)
    factors.extend(dispositor_factors)
    factors.extend(_active_lord_yoga_factors(chart_data, lord_code))
    score = sum(factor["score"] for factor in factors)
    quality = "supportive" if score >= 16 else "mixed" if score >= 4 else "pressured" if score < 0 else "weak"

    return {
        "lord": lord_code,
        "lord_name": name,
        "score": score,
        "quality": quality,
        "d1_house": d1_house,
        "d1_dignity": dignity,
        "owned_houses": owned_houses,
        "dispositor": dispositor,
        "primary_varga": primary_varga,
        "primary_varga_house": varga_house,
        "primary_varga_dignity": varga_dignity,
        "factors": factors,
        "source_references": [SOURCE_REFERENCE, CHAPTER_FOUR_REFERENCE],
        "deferred_factors": [
            "moolatrikona",
            "friend_or_enemy_sign",
            "combustion",
            "aarohi_or_avarohi",
            "rashi_sandhi_or_gandanta",
            "full_shadabala",
        ],
    }
