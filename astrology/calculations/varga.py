from typing import Any

from charts.vedic_utils import PLANET_NAMES, SIGN_LORDS, SIGN_NAMES, get_planet_dignity


CAREER_HOUSES = {2, 6, 10, 11}
BUSINESS_HOUSES = {2, 7, 10, 11}
SUPPORTED_VARGAS = ["d1", "d2", "d3", "d4", "d7", "d9", "d10", "d12", "d16", "d20", "d24", "d27", "d30", "d40", "d45", "d60"]
VARGA_PURPOSES = {
    "d1": "Basic chart and overall life context.",
    "d2": "Wealth, family resources, and speech.",
    "d3": "Coborns, courage, effort, communication, and vitality of initiative.",
    "d4": "Home, immovable property, comforts, and destiny related to residence.",
    "d7": "Children, grandchildren, creativity, and fulfilment.",
    "d9": "Strength confirmation, spouse, dharma, marriage, and partnership.",
    "d10": "Profession, status, career rise/fall, promotion, demotion, and work.",
    "d12": "Parents, lineage, ancestry, and prenatal influences.",
    "d16": "Movable assets, vehicles, comforts, and general happiness.",
    "d20": "Spiritual practice, worship, and devotional results.",
    "d24": "Education, learning, academic achievements, and knowledge.",
    "d27": "Physical, mental, and spiritual strength or weakness.",
    "d30": "Miseries, evils, misfortune, disease, and conflict.",
    "d40": "General auspicious effects.",
    "d45": "Character and conduct.",
    "d60": "All effects; deep benefic/malefic karma, only with reliable birth time.",
}


def get_varga_lagna(chart_data: dict[str, Any], chart_key: str) -> dict[str, Any]:
    return next(
        (
            planet
            for planet in chart_data.get(chart_key, {}).get("planets", [])
            if planet.get("code") == "Asc"
        ),
        {},
    )


def get_planets_in_chart(chart_data: dict[str, Any], chart_key: str, include_ascendant: bool = False) -> list[dict[str, Any]]:
    planets = chart_data.get(chart_key, {}).get("planets", [])
    if include_ascendant:
        return planets
    return [planet for planet in planets if planet.get("code") != "Asc"]


def get_planet_in_varga(chart_data: dict[str, Any], chart_key: str, planet_code: str) -> dict[str, Any]:
    return next(
        (
            planet
            for planet in get_planets_in_chart(chart_data, chart_key, include_ascendant=True)
            if planet.get("code") == planet_code
        ),
        {},
    )


def get_varga_house(chart_data: dict[str, Any], chart_key: str, house_number: int) -> dict[str, Any]:
    return next(
        (
            house
            for house in chart_data.get(chart_key, {}).get("houses", [])
            if house.get("number") == house_number
        ),
        {},
    )


def get_planets_in_house(chart_data: dict[str, Any], chart_key: str, house_number: int) -> list[dict[str, Any]]:
    return [
        planet
        for planet in get_planets_in_chart(chart_data, chart_key)
        if planet.get("house") == house_number
    ]


def get_house_lord(chart_data: dict[str, Any], chart_key: str, house_number: int) -> str | None:
    house = get_varga_house(chart_data, chart_key, house_number)
    sign_number = house.get("sign_number")
    return SIGN_LORDS.get(sign_number) if sign_number else None


def get_lord_placement(chart_data: dict[str, Any], chart_key: str, house_number: int) -> dict[str, Any]:
    lord = get_house_lord(chart_data, chart_key, house_number)
    planet = get_planet_in_varga(chart_data, chart_key, lord) if lord else {}
    if not planet:
        return {"house": house_number, "lord": lord, "planet": {}}
    return {
        "house": house_number,
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "placed_house": planet.get("house"),
        "placed_sign": planet.get("sign"),
        "placed_sign_number": planet.get("sign_number"),
        "dignity": get_planet_dignity(chart_data, lord, chart_key),
        "planet": _compact_planet(chart_data, chart_key, planet),
    }


def _compact_planet(chart_data: dict[str, Any], chart_key: str, planet: dict[str, Any]) -> dict[str, Any]:
    code = planet.get("code")
    return {
        "code": code,
        "name": planet.get("name") or PLANET_NAMES.get(code, code),
        "house": planet.get("house"),
        "sign": planet.get("sign"),
        "sign_number": planet.get("sign_number"),
        "degree": planet.get("degree"),
        "nakshatra": planet.get("nakshatra"),
        "nakshatra_lord": planet.get("nakshatra_lord"),
        "motion": planet.get("motion"),
        "retrograde": planet.get("retrograde"),
        "jaimini_karaka": planet.get("jaimini_karaka", ""),
        "dignity": get_planet_dignity(chart_data, code, chart_key) if code and code != "Asc" else "not_applicable",
    }


def _house_summary(chart_data: dict[str, Any], chart_key: str, house_number: int) -> dict[str, Any]:
    house = get_varga_house(chart_data, chart_key, house_number)
    return {
        "house": house_number,
        "sign": house.get("sign"),
        "sign_number": house.get("sign_number"),
        "sign_lord": get_house_lord(chart_data, chart_key, house_number),
        "occupants": [
            _compact_planet(chart_data, chart_key, planet)
            for planet in get_planets_in_house(chart_data, chart_key, house_number)
        ],
        "lord_placement": get_lord_placement(chart_data, chart_key, house_number),
    }


def build_varga_facts(
    chart_data: dict[str, Any],
    category: str = "general",
    chart_keys: list[str] | None = None,
) -> dict[str, Any]:
    chart_keys = chart_keys or SUPPORTED_VARGAS
    relevant_houses = sorted(BUSINESS_HOUSES if category == "business" else CAREER_HOUSES)
    charts = {}

    for chart_key in chart_keys:
        if chart_key not in chart_data:
            continue
        lagna = get_varga_lagna(chart_data, chart_key)
        compact_planets = [
            _compact_planet(chart_data, chart_key, planet)
            for planet in get_planets_in_chart(chart_data, chart_key)
        ]
        charts[chart_key] = {
            "purpose": VARGA_PURPOSES.get(chart_key, ""),
            "lagna": _compact_planet(chart_data, chart_key, lagna) if lagna else {},
            "relevant_houses": [
                _house_summary(chart_data, chart_key, house_number)
                for house_number in relevant_houses
            ],
            "key_lord_placements": {
                f"{house_number}_lord": get_lord_placement(chart_data, chart_key, house_number)
                for house_number in relevant_houses
            },
            "all_lord_placements": {
                f"{house_number}_lord": get_lord_placement(chart_data, chart_key, house_number)
                for house_number in range(1, 13)
            },
            "planets": compact_planets,
            "planet_lookup": {
                planet["code"]: planet
                for planet in compact_planets
                if planet.get("code")
            },
        }

    return {
        "supported_charts": sorted(charts),
        "known_supported_vargas": SUPPORTED_VARGAS,
        "varga_purposes": VARGA_PURPOSES,
        "category": category,
        "relevant_houses": relevant_houses,
        "charts": charts,
        "sign_lords": {str(sign): lord for sign, lord in SIGN_LORDS.items()},
        "sign_names": {str(sign): name for sign, name in SIGN_NAMES.items()},
    }


def build_chart_facts(chart_data: dict[str, Any], category: str = "general") -> dict[str, Any]:
    varga_facts = build_varga_facts(chart_data, category)
    return {
        "system": chart_data.get("system"),
        "ayanamsa": chart_data.get("ayanamsa"),
        "birth_data": {
            "name": chart_data.get("name"),
            "birth_date": chart_data.get("birth_date"),
            "birth_time": chart_data.get("birth_time"),
            "birth_place": chart_data.get("birth_place"),
            "timezone": chart_data.get("timezone"),
        },
        "ascendant": varga_facts.get("charts", {}).get("d1", {}).get("lagna", {}),
        "varga": varga_facts,
    }


def _strength_label(dignity: str) -> str:
    if dignity in {"exalted", "own_sign"}:
        return "strong"
    if dignity == "debilitated":
        return "weak"
    if dignity == "unknown":
        return "unknown"
    return "ordinary"


def _lord_finding(chart_key: str, house_label: str, placement: dict[str, Any], category_houses: list[int]) -> dict[str, Any] | None:
    lord = placement.get("lord")
    if not lord:
        return None
    placed_house = placement.get("placed_house")
    dignity = placement.get("dignity", "unknown")
    score = 0
    impact_parts = []

    if placed_house in category_houses:
        score += 4
        impact_parts.append(f"placed in relevant house {placed_house}")
    if dignity in {"exalted", "own_sign"}:
        score += 4
        impact_parts.append(f"{_strength_label(dignity)} dignity")
    elif dignity == "debilitated":
        score -= 3
        impact_parts.append("debilitated dignity")

    if not impact_parts:
        impact_parts.append("available for judgment but not strongly activated")

    return {
        "factor": f"{chart_key.upper()} {house_label}",
        "planet": placement.get("lord_name") or lord,
        "finding": f"{placement.get('lord_name') or lord} is in {placement.get('placed_sign')} house {placed_house}.",
        "impact": ", ".join(impact_parts),
        "dignity": dignity,
        "placed_house": placed_house,
        "score": score,
    }


def build_varga_assessment(chart_facts: dict[str, Any], category: str = "general") -> dict[str, Any]:
    facts = chart_facts.get("varga", {})
    category_houses = facts.get("relevant_houses", [2, 6, 10, 11])
    d9_findings = []
    d10_findings = []
    cross_chart_confirmations = []

    d9 = facts.get("charts", {}).get("d9", {})
    d10 = facts.get("charts", {}).get("d10", {})

    for house_number in category_houses:
        house_label = f"{house_number}th lord"
        d9_placement = d9.get("key_lord_placements", {}).get(f"{house_number}_lord", {})
        d10_placement = d10.get("key_lord_placements", {}).get(f"{house_number}_lord", {})
        d9_finding = _lord_finding("d9", house_label, d9_placement, category_houses)
        d10_finding = _lord_finding("d10", house_label, d10_placement, category_houses)
        if d9_finding:
            d9_findings.append(d9_finding)
        if d10_finding:
            d10_findings.append(d10_finding)
        if d9_finding and d10_finding and d9_finding["score"] > 0 and d10_finding["score"] > 0:
            cross_chart_confirmations.append(
                {
                    "factor": house_label,
                    "finding": f"D9 and D10 both support the {house_label}.",
                    "impact": "Divisional confirmation improves confidence.",
                    "score": min(d9_finding["score"] + d10_finding["score"], 10),
                }
            )

    score = min(
        100,
        max(
            0,
            sum(item["score"] for item in d9_findings)
            + sum(item["score"] for item in d10_findings)
            + sum(item["score"] for item in cross_chart_confirmations),
        )
        * 4,
    )
    return {
        "system": "Varga / Divisional",
        "category": category,
        "d9_findings": d9_findings,
        "d10_findings": d10_findings,
        "cross_chart_confirmations": cross_chart_confirmations,
        "score": score,
        "status": "supports" if score >= 60 else "mixed" if score else "not_confirmed",
        "facts": facts,
    }
