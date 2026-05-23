from typing import Any

from charts.vedic_utils import (
    DUSTHANA_HOUSES,
    KENDRA_HOUSES,
    PLANET_NAMES,
    SIGN_NAMES,
    TRIKONA_HOUSES,
    get_house_lord,
    get_owned_houses,
    get_planet,
    get_planet_dignity,
    house_distance,
)


CATEGORY_CONFIG = {
    "career": {
        "houses": [2, 6, 10, 11],
        "primary_houses": [10],
        "support_houses": [2, 6, 11],
        "scores": {"authority": 3, "income": 2, "delay": -1},
    },
    "business": {
        "houses": [2, 7, 10, 11],
        "primary_houses": [7, 10],
        "support_houses": [2, 11],
        "scores": {"business": 3, "partnership": 2},
    },
    "money": {
        "houses": [2, 5, 9, 11],
        "primary_houses": [2, 11],
        "support_houses": [5, 9],
        "scores": {"income": 3},
    },
    "marriage": {
        "houses": [2, 7, 8, 11],
        "primary_houses": [7],
        "support_houses": [2, 11],
        "scores": {"partnership": 3},
    },
    "children": {
        "houses": [2, 5, 9, 11],
        "primary_houses": [5],
        "support_houses": [2, 9, 11],
        "scores": {"children": 3},
    },
    "education": {
        "houses": [4, 5, 9, 11],
        "primary_houses": [4, 5],
        "support_houses": [9, 11],
        "scores": {"education": 3},
    },
    "property": {
        "houses": [4, 9, 11, 12],
        "primary_houses": [4],
        "support_houses": [9, 11],
        "scores": {"property": 3},
    },
    "family": {
        "houses": [1, 4, 9, 12],
        "primary_houses": [4, 9],
        "support_houses": [1, 12],
        "scores": {"family": 3},
    },
    "health": {
        "houses": [1, 6, 8, 12],
        "primary_houses": [1, 6],
        "support_houses": [8, 12],
        "scores": {"risk": 3},
    },
}

DHANA_HOUSES = {2, 5, 9, 11}


def _compact_planet(chart_data: dict[str, Any], planet_code: str) -> dict[str, Any]:
    planet = get_planet(chart_data, planet_code, "d1")
    if not planet:
        return {"code": planet_code, "name": PLANET_NAMES.get(planet_code, planet_code)}
    return {
        "code": planet_code,
        "name": PLANET_NAMES.get(planet_code, planet_code),
        "house": planet.get("house"),
        "sign": planet.get("sign"),
        "sign_number": planet.get("sign_number"),
        "dignity": get_planet_dignity(chart_data, planet_code, "d1"),
        "owned_houses": get_owned_houses(chart_data, planet_code),
    }


def _lord_factor(chart_data: dict[str, Any], house_number: int) -> dict[str, Any]:
    lord = get_house_lord(chart_data, house_number)
    planet = _compact_planet(chart_data, lord) if lord else {}
    placed_house = planet.get("house")
    dignity = planet.get("dignity", "unknown")
    return {
        "house": house_number,
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "placed_house": placed_house,
        "placed_sign": planet.get("sign"),
        "placed_sign_number": planet.get("sign_number"),
        "dignity": dignity,
        "is_strong": dignity in {"exalted", "own_sign"},
        "is_weak": dignity == "debilitated",
        "in_kendra": placed_house in KENDRA_HOUSES,
        "in_trikona": placed_house in TRIKONA_HOUSES,
        "in_dusthana": placed_house in DUSTHANA_HOUSES,
        "planet": planet,
    }


def _lords_related(chart_data: dict[str, Any], first_house: int, second_house: int) -> dict[str, Any]:
    first_lord = get_house_lord(chart_data, first_house)
    second_lord = get_house_lord(chart_data, second_house)
    first = get_planet(chart_data, first_lord, "d1") if first_lord else {}
    second = get_planet(chart_data, second_lord, "d1") if second_lord else {}
    same_lord = bool(first_lord and first_lord == second_lord)
    conjunct = bool(first and second and first.get("house") == second.get("house"))
    first_in_second = first.get("house") == second_house
    second_in_first = second.get("house") == first_house
    exchange = first_in_second and second_in_first and not same_lord
    distance = house_distance(first.get("house"), second.get("house")) if first and second else None
    return {
        "houses": [first_house, second_house],
        "first_house": first_house,
        "second_house": second_house,
        "first_lord": first_lord,
        "second_lord": second_lord,
        "first_lord_name": PLANET_NAMES.get(first_lord, first_lord),
        "second_lord_name": PLANET_NAMES.get(second_lord, second_lord),
        "same_lord": same_lord,
        "conjunct": conjunct,
        "exchange": exchange,
        "first_lord_in_second_house": first_in_second,
        "second_lord_in_first_house": second_in_first,
        "distance": distance,
        "kendra_relation": distance in KENDRA_HOUSES,
        "trikona_relation": distance in TRIKONA_HOUSES,
        "related": same_lord or conjunct or exchange or first_in_second or second_in_first,
    }


def _relationship_finding(label: str, relation: dict[str, Any], impact: str, score: int) -> dict[str, Any]:
    return {
        "factor": label,
        "finding": (
            f"{relation.get('first_lord_name')} ({relation.get('first_house')} lord) "
            f"and {relation.get('second_lord_name')} ({relation.get('second_house')} lord) are related."
        ),
        "impact": impact,
        "score": score,
        "relation": relation,
    }


def build_parashari_facts(
    chart_data: dict[str, Any],
    category: str = "general",
    category_houses: list[int] | None = None,
    vimshottari_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = CATEGORY_CONFIG.get(category, {})
    category_houses = category_houses or config.get("houses", [2, 6, 10, 11])
    primary_houses = config.get("primary_houses", category_houses[:1])
    support_houses = config.get("support_houses", [house for house in category_houses if house not in primary_houses])
    houses_to_assess = sorted(set([1, *category_houses, *primary_houses, *support_houses, 5, 9, 10]))
    lord_factors = {f"{house}_lord": _lord_factor(chart_data, house) for house in houses_to_assess}
    findings = []

    for house in primary_houses:
        factor = lord_factors.get(f"{house}_lord", {})
        if factor.get("is_strong"):
            findings.append(
                {
                    "factor": f"{house}th lord strength",
                    "finding": f"{factor.get('lord_name')} as {house} lord is strong in D1.",
                    "impact": "Primary house lord has strength to deliver topic results.",
                    "score": 8,
                }
            )
        if factor.get("in_dusthana"):
            findings.append(
                {
                    "factor": f"{house}th lord dusthana pressure",
                    "finding": f"{factor.get('lord_name')} as {house} lord is placed in house {factor.get('placed_house')}.",
                    "impact": "Topic results may come with delay, pressure, dispute, loss, or transformation.",
                    "score": -5,
                }
            )

    rajayoga_factors = []
    for kendra in sorted(KENDRA_HOUSES):
        for trikona in sorted(TRIKONA_HOUSES - {1}):
            relation = _lords_related(chart_data, kendra, trikona)
            if relation["related"]:
                rajayoga_factors.append(relation)
                findings.append(
                    _relationship_finding(
                        "Kendra-Trikona Rajayoga factor",
                        relation,
                        "Kendra and trikona lord connection supports status, capability, and rise when timing agrees.",
                        8,
                    )
                )

    dharma_karma_relation = _lords_related(chart_data, 9, 10)
    if dharma_karma_relation["related"]:
        findings.append(
            _relationship_finding(
                "Dharma-Karma relation",
                dharma_karma_relation,
                "Ninth and tenth lord relation supports career direction, guidance, and professional rise.",
                9,
            )
        )

    dhana_yoga_factors = []
    for first_house in sorted(DHANA_HOUSES):
        for second_house in sorted(DHANA_HOUSES):
            if first_house >= second_house:
                continue
            relation = _lords_related(chart_data, first_house, second_house)
            if relation["related"]:
                dhana_yoga_factors.append(relation)
                findings.append(
                    _relationship_finding(
                        "Dhana yoga factor",
                        relation,
                        "Wealth-house lord connection supports income, gains, or resources when timing agrees.",
                        7,
                    )
                )

    category_lord_relations = []
    for primary in primary_houses:
        for support in support_houses:
            relation = _lords_related(chart_data, primary, support)
            if relation["related"]:
                category_lord_relations.append(relation)
                findings.append(
                    _relationship_finding(
                        "Category lord relation",
                        relation,
                        "Primary topic lord connects with a supporting house for the question category.",
                        7,
                    )
                )

    dusthana_pressure_factors = []
    for house in category_houses:
        factor = lord_factors.get(f"{house}_lord", {})
        if factor.get("in_dusthana"):
            dusthana_pressure_factors.append(factor)

    dasha_activation = build_dasha_activation(
        vimshottari_facts or {},
        rajayoga_factors,
        dhana_yoga_factors,
        category_lord_relations,
        dusthana_pressure_factors,
    )
    if dasha_activation.get("activates_raja_yoga"):
        findings.append(
            {
                "factor": "Vimshottari activates Rajayoga",
                "finding": "Active dasha lord participates in a calculated kendra-trikona relation.",
                "impact": "Timing is more capable of delivering rise/status results.",
                "score": 9,
            }
        )
    if dasha_activation.get("activates_dhana_yoga"):
        findings.append(
            {
                "factor": "Vimshottari activates Dhana yoga",
                "finding": "Active dasha lord participates in a calculated wealth-house relation.",
                "impact": "Timing is more capable of delivering income or gains.",
                "score": 8,
            }
        )
    if dasha_activation.get("activates_dusthana_pressure"):
        findings.append(
            {
                "factor": "Vimshottari activates dusthana pressure",
                "finding": "Active dasha lord participates in a dusthana-pressured category factor.",
                "impact": "Results may come with pressure, delay, or risk.",
                "score": -5,
            }
        )

    score = max(0, min(100, sum(item.get("score", 0) for item in findings) * 3))
    return {
        "system": "Parashari",
        "category": category,
        "category_houses": category_houses,
        "primary_houses": primary_houses,
        "support_houses": support_houses,
        "lord_factors": lord_factors,
        "rajayoga_factors": rajayoga_factors,
        "dhana_yoga_factors": dhana_yoga_factors,
        "dharma_karma_relation": dharma_karma_relation,
        "category_lord_relations": category_lord_relations,
        "dusthana_pressure_factors": dusthana_pressure_factors,
        "dasha_activation": dasha_activation,
        "findings": findings,
        "score": score,
        "status": "supports" if score >= 60 else "mixed" if findings else "not_confirmed",
        "method_source": "Phal Dipika / Brihat Parashar Hora Shastra",
        "calculation_status": "active",
    }


def build_dasha_activation(
    vimshottari_facts: dict[str, Any],
    rajayoga_factors: list[dict[str, Any]],
    dhana_yoga_factors: list[dict[str, Any]],
    category_lord_relations: list[dict[str, Any]],
    dusthana_pressure_factors: list[dict[str, Any]],
) -> dict[str, Any]:
    active_lords = {
        lord.get("code")
        for lord in vimshottari_facts.get("dasha_lord_facts", [])
        if lord.get("code")
    }

    def relation_activated(relation: dict[str, Any]) -> bool:
        return relation.get("first_lord") in active_lords or relation.get("second_lord") in active_lords

    active_raja = [relation for relation in rajayoga_factors if relation_activated(relation)]
    active_dhana = [relation for relation in dhana_yoga_factors if relation_activated(relation)]
    active_category = [relation for relation in category_lord_relations if relation_activated(relation)]
    active_dusthana = [
        factor
        for factor in dusthana_pressure_factors
        if factor.get("lord") in active_lords
    ]
    return {
        "active_lords": sorted(active_lords),
        "active_lord_names": [PLANET_NAMES.get(lord, lord) for lord in sorted(active_lords)],
        "activates_raja_yoga": bool(active_raja),
        "activates_dhana_yoga": bool(active_dhana),
        "activates_category_lord_relation": bool(active_category),
        "activates_dusthana_pressure": bool(active_dusthana),
        "raja_yoga_relations": active_raja,
        "dhana_yoga_relations": active_dhana,
        "category_lord_relations": active_category,
        "dusthana_pressure_factors": active_dusthana,
    }
