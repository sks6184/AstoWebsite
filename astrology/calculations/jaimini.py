from typing import Any

from charts.vedic_utils import (
    BENEFIC_PLANETS,
    DUSTHANA_HOUSES,
    KENDRA_HOUSES,
    MALEFIC_PLANETS,
    PLANET_NAMES,
    SIGN_LORDS,
    SIGN_NAMES,
    TRIKONA_HOUSES,
    get_house_lord,
    get_house_sign,
    get_owned_houses,
    get_planet,
    get_planet_dignity,
    get_planets,
    get_planets_in_sign,
    house_distance,
    normalize_sign_number,
    sign_distance,
)


MOVABLE_SIGNS = {1, 4, 7, 10}
FIXED_SIGNS = {2, 5, 8, 11}
DUAL_SIGNS = {3, 6, 9, 12}
JAIMINI_BENEFICS = {"Ju", "Ve"}
JAIMINI_MALEFICS = {"Su", "Ma", "Sa", "Ra", "Ke"}
KARAKA_LABELS_BY_CATEGORY = {
    "career": {"Amatyakaraka"},
    "job": {"Amatyakaraka"},
    "education": {"Putrakaraka"},
    "marriage": {"Darakaraka"},
    "children": {"Putrakaraka"},
    "health": {"Gnatikaraka"},
}
STHIRA_KARAKAS_BY_HOUSE = {
    1: "Su",
    2: "Ju",
    3: "Ma",
    4: "Mo",
    5: "Ju",
    6: "Ma",
    7: "Ve",
    8: "Sa",
    9: "Ju",
    10: "Me",
    11: "Ju",
    12: "Sa",
}
STARTER_RAJAYOGA_PAIRS = {
    "Atmakaraka-Amatyakaraka",
    "Atmakaraka-Putrakaraka",
    "Atmakaraka-fifth lord",
    "Atmakaraka-Darakaraka",
    "Amatyakaraka-Putrakaraka",
    "Amatyakaraka-fifth lord",
    "Amatyakaraka-Darakaraka",
    "Putrakaraka-fifth lord",
    "Putrakaraka-Darakaraka",
    "fifth lord-Darakaraka",
}


def jaimini_aspected_signs(sign_number: int | None) -> list[int]:
    sign_number = normalize_sign_number(sign_number)
    if not sign_number:
        return []
    if sign_number in MOVABLE_SIGNS:
        adjacent_fixed = normalize_sign_number(sign_number + 1)
        return sorted(FIXED_SIGNS - {adjacent_fixed})
    if sign_number in FIXED_SIGNS:
        adjacent_movable = normalize_sign_number(sign_number - 1)
        return sorted(MOVABLE_SIGNS - {adjacent_movable})
    if sign_number in DUAL_SIGNS:
        return sorted(DUAL_SIGNS - {sign_number})
    return []


def signs_aspecting(sign_number: int | None) -> list[int]:
    sign_number = normalize_sign_number(sign_number)
    if not sign_number:
        return []
    return [
        candidate
        for candidate in range(1, 13)
        if sign_number in jaimini_aspected_signs(candidate)
    ]


def signs_have_jaimini_aspect(first_sign: int | None, second_sign: int | None) -> bool:
    return normalize_sign_number(second_sign) in jaimini_aspected_signs(first_sign)


def _compact_planet(planet: dict[str, Any]) -> dict[str, Any]:
    code = planet.get("code")
    return {
        "code": code,
        "name": planet.get("name") or PLANET_NAMES.get(code, code),
        "karaka": planet.get("jaimini_karaka", ""),
        "house": planet.get("house"),
        "sign": planet.get("sign"),
        "sign_number": planet.get("sign_number"),
        "degree": planet.get("degree"),
    }


def _karaka_planet(chart_data: dict[str, Any], karaka: str) -> dict[str, Any]:
    return next(
        (
            planet
            for planet in get_planets(chart_data, "d1")
            if planet.get("jaimini_karaka") == karaka
        ),
        {},
    )


def build_karakas(chart_data: dict[str, Any]) -> dict[str, Any]:
    karakas = {}
    for planet in get_planets(chart_data, "d1"):
        karaka = planet.get("jaimini_karaka")
        if karaka:
            key = karaka[:1].lower() + karaka[1:]
            karakas[key] = _compact_planet(planet)
    return {
        "uses_seven_karakas": True,
        "nodes_excluded": True,
        "karakas": karakas,
        "sthira_karakas": {
            str(house): {
                "house": house,
                "planet": code,
                "planet_name": PLANET_NAMES.get(code, code),
            }
            for house, code in STHIRA_KARAKAS_BY_HOUSE.items()
        },
        "sthira_karakas_scoring_status": "unscored_reference_only",
    }


def build_karakamsha(chart_data: dict[str, Any]) -> dict[str, Any]:
    atmakaraka = _karaka_planet(chart_data, "Atmakaraka")
    if not atmakaraka:
        return {}
    d9_ak = get_planet(chart_data, atmakaraka.get("code"), "d9")
    sign_number = d9_ak.get("sign_number")
    tenth_from_karakamsha = normalize_sign_number(sign_number + 9) if sign_number else None
    fifth_from_karakamsha = normalize_sign_number(sign_number + 4) if sign_number else None
    ninth_from_karakamsha = normalize_sign_number(sign_number + 8) if sign_number else None
    return {
        "source": "Navamsha sign occupied by Atmakaraka",
        "atmakaraka": _compact_planet(atmakaraka),
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "d9_atmakaraka": _compact_planet(d9_ak) if d9_ak else {},
        "tenth_from_karakamsha": {
            "sign_number": tenth_from_karakamsha,
            "sign": SIGN_NAMES.get(tenth_from_karakamsha),
            "d1_house_from_lagna": sign_distance(chart_data.get("ascendant", {}).get("sign_number"), tenth_from_karakamsha),
            "occupants": [_compact_planet(planet) for planet in get_planets_in_sign(chart_data, tenth_from_karakamsha, "d1")],
            "influencing_planets": _planets_influencing_sign(chart_data, tenth_from_karakamsha),
        },
        "fifth_from_karakamsha": {
            "sign_number": fifth_from_karakamsha,
            "sign": SIGN_NAMES.get(fifth_from_karakamsha),
            "occupants": [_compact_planet(planet) for planet in get_planets_in_sign(chart_data, fifth_from_karakamsha, "d1")],
            "influencing_planets": _planets_influencing_sign(chart_data, fifth_from_karakamsha),
        },
        "ninth_from_karakamsha": {
            "sign_number": ninth_from_karakamsha,
            "sign": SIGN_NAMES.get(ninth_from_karakamsha),
            "occupants": [_compact_planet(planet) for planet in get_planets_in_sign(chart_data, ninth_from_karakamsha, "d1")],
            "influencing_planets": _planets_influencing_sign(chart_data, ninth_from_karakamsha),
        },
    }


def _pada_from_house(chart_data: dict[str, Any], house_number: int) -> dict[str, Any]:
    house_sign = get_house_sign(chart_data, house_number)
    lord = get_house_lord(chart_data, house_number)
    lord_planet = get_planet(chart_data, lord, "d1") if lord else {}
    lord_sign = lord_planet.get("sign_number")
    if not house_sign or not lord_sign:
        return {
            "house": house_number,
            "house_sign_number": house_sign,
            "house_sign": SIGN_NAMES.get(house_sign),
            "lord": lord,
            "pada_sign_number": None,
            "pada_sign": None,
        }

    distance = sign_distance(house_sign, lord_sign)
    pada_sign = normalize_sign_number(lord_sign + distance - 1)
    return {
        "house": house_number,
        "house_sign_number": house_sign,
        "house_sign": SIGN_NAMES.get(house_sign),
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "lord_sign_number": lord_sign,
        "lord_sign": SIGN_NAMES.get(lord_sign),
        "distance_from_house_to_lord": distance,
        "pada_sign_number": pada_sign,
        "pada_sign": SIGN_NAMES.get(pada_sign),
        "pada_house_from_lagna": sign_distance(chart_data.get("ascendant", {}).get("sign_number"), pada_sign),
        "method_note": "Count from the house to its lord, then count the same distance from the lord.",
    }


def build_padas(chart_data: dict[str, Any]) -> dict[str, Any]:
    padas = {str(house): _pada_from_house(chart_data, house) for house in range(1, 13)}
    return {
        "all_padas": padas,
        "arudha_lagna": padas["1"],
        "upapada_lagna": padas["12"],
        "planetary_padas": {
            "calculation_status": "deferred",
            "scoring_status": "unscored_reference_only",
            "reason": "Chapter 7 states that planetary padas should be calculated, but the reviewed pages do not define a sufficiently explicit formula.",
        },
        "exceptions_applied": False,
        "method_note": "All twelve house padas use direct counting. The source instructs readers to ignore the disputed exceptions.",
    }


def _planet_influences_sign(chart_data: dict[str, Any], planet: dict[str, Any], sign_number: int | None) -> bool:
    planet_sign = planet.get("sign_number")
    return planet_sign == sign_number or signs_have_jaimini_aspect(planet_sign, sign_number)


def _planets_influencing_sign(chart_data: dict[str, Any], sign_number: int | None) -> list[dict[str, Any]]:
    return [
        _compact_planet(planet)
        for planet in get_planets(chart_data, "d1")
        if _planet_influences_sign(chart_data, planet, sign_number)
    ]


def _influencing_planets_by_codes(
    chart_data: dict[str, Any],
    sign_number: int | None,
    codes: set[str],
) -> list[dict[str, Any]]:
    return [
        planet
        for planet in _planets_influencing_sign(chart_data, sign_number)
        if planet.get("code") in codes
    ]


def build_karaka_condition_facts(chart_data: dict[str, Any]) -> dict[str, Any]:
    conditions = {}
    for karaka, planet in (
        (planet.get("jaimini_karaka"), planet)
        for planet in get_planets(chart_data, "d1")
        if planet.get("jaimini_karaka")
    ):
        sign_number = planet.get("sign_number")
        planet_code = planet.get("code")
        conditions[karaka] = {
            "planet": _compact_planet(planet),
            "benefic_influences": [
                influence
                for influence in _influencing_planets_by_codes(chart_data, sign_number, JAIMINI_BENEFICS)
                if influence.get("code") != planet_code
            ],
            "malefic_influences": [
                influence
                for influence in _influencing_planets_by_codes(chart_data, sign_number, JAIMINI_MALEFICS)
                if influence.get("code") != planet_code
            ],
            "neutral_or_contextual_planets": [
                influence
                for influence in _planets_influencing_sign(chart_data, sign_number)
                if influence.get("code") != planet_code
                and influence.get("code") not in JAIMINI_BENEFICS | JAIMINI_MALEFICS
            ],
        }
    return {
        "conditions": conditions,
        "scoring_status": "unscored_reference_only",
        "method_note": "Chapter 8 asks whether karakas are afflicted or influenced by benefics. Moon and Mercury remain contextual rather than automatically classified.",
    }


def build_arudha_factors(chart_data: dict[str, Any], category_houses: list[int]) -> dict[str, Any]:
    padas = build_padas(chart_data)
    arudha = padas["arudha_lagna"]
    arudha_sign = arudha.get("pada_sign_number")
    tenth_from_arudha_sign = normalize_sign_number(arudha_sign + 9) if arudha_sign else None
    second_from_arudha_sign = normalize_sign_number(arudha_sign + 1) if arudha_sign else None
    eleventh_from_arudha_sign = normalize_sign_number(arudha_sign + 10) if arudha_sign else None
    tenth_from_arudha_house = sign_distance(chart_data.get("ascendant", {}).get("sign_number"), tenth_from_arudha_sign)
    tenth_influencers = _planets_influencing_sign(chart_data, tenth_from_arudha_sign)
    arudha_influencers = _planets_influencing_sign(chart_data, arudha_sign)
    career_karaka_influence = [
        planet
        for planet in tenth_influencers + arudha_influencers
        if planet.get("karaka") in {"Atmakaraka", "Amatyakaraka"}
    ]
    return {
        "all_padas": padas["all_padas"],
        "arudha_lagna": arudha,
        "upapada_lagna": padas["upapada_lagna"],
        "planetary_padas": padas["planetary_padas"],
        "exceptions_applied": padas["exceptions_applied"],
        "method_note": padas["method_note"],
        "tenth_from_arudha": {
            "sign_number": tenth_from_arudha_sign,
            "sign": SIGN_NAMES.get(tenth_from_arudha_sign),
            "house_from_lagna": tenth_from_arudha_house,
            "is_relevant_to_category": tenth_from_arudha_house in category_houses,
            "occupants": [
                _compact_planet(planet)
                for planet in get_planets_in_sign(chart_data, tenth_from_arudha_sign, "d1")
            ],
            "influencing_planets": tenth_influencers,
        },
        "second_from_arudha": {
            "sign_number": second_from_arudha_sign,
            "sign": SIGN_NAMES.get(second_from_arudha_sign),
            "occupants": [
                _compact_planet(planet)
                for planet in get_planets_in_sign(chart_data, second_from_arudha_sign, "d1")
            ],
            "influencing_planets": _planets_influencing_sign(chart_data, second_from_arudha_sign),
        },
        "eleventh_from_arudha": {
            "sign_number": eleventh_from_arudha_sign,
            "sign": SIGN_NAMES.get(eleventh_from_arudha_sign),
            "occupants": [
                _compact_planet(planet)
                for planet in get_planets_in_sign(chart_data, eleventh_from_arudha_sign, "d1")
            ],
            "influencing_planets": _planets_influencing_sign(chart_data, eleventh_from_arudha_sign),
        },
        "arudha_influencing_planets": arudha_influencers,
        "career_karaka_influence": career_karaka_influence,
    }


def _same_or_aspecting(first: dict[str, Any], second: dict[str, Any]) -> bool:
    first_sign = first.get("sign_number")
    second_sign = second.get("sign_number")
    return bool(first_sign and second_sign and (first_sign == second_sign or signs_have_jaimini_aspect(first_sign, second_sign)))


def _planet_house_distance(first: dict[str, Any], second: dict[str, Any]) -> int | None:
    return house_distance(first.get("house"), second.get("house"))


def build_jaimini_yogas(chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    planets_by_karaka = {
        planet.get("jaimini_karaka"): planet
        for planet in get_planets(chart_data, "d1")
        if planet.get("jaimini_karaka")
    }
    yogas = []
    ak = planets_by_karaka.get("Atmakaraka", {})
    amk = planets_by_karaka.get("Amatyakaraka", {})
    pk = planets_by_karaka.get("Putrakaraka", {})
    dk = planets_by_karaka.get("Darakaraka", {})
    fifth_lord = get_planet(chart_data, get_house_lord(chart_data, 5), "d1")
    moon = get_planet(chart_data, "Mo", "d1")
    venus = get_planet(chart_data, "Ve", "d1")

    pairs = [
        ("Atmakaraka-Amatyakaraka", ak, amk, "position and authority"),
        ("Atmakaraka-Putrakaraka", ak, pk, "intelligence and merit"),
        ("Atmakaraka-fifth lord", ak, fifth_lord, "personal direction supported by merit and counsel"),
        ("Atmakaraka-Darakaraka", ak, dk, "public interaction and agreements"),
        ("Amatyakaraka-Putrakaraka", amk, pk, "advisory capacity and execution"),
        ("Amatyakaraka-fifth lord", amk, fifth_lord, "professional position supported by intelligence/merit"),
        ("Amatyakaraka-Darakaraka", amk, dk, "clients, partnership, and status"),
        ("Putrakaraka-fifth lord", pk, fifth_lord, "learning, counsel, and merit supporting rise"),
        ("Putrakaraka-Darakaraka", pk, dk, "advisory ability linked with public agreements"),
        ("fifth lord-Darakaraka", fifth_lord, dk, "merit and skill applied through clients or partnerships"),
    ]
    for label, first, second, impact in pairs:
        if first and second and _same_or_aspecting(first, second):
            yogas.append(
                {
                    "name": label,
                    "type": "raja_yoga",
                    "finding": f"{label} are together or in mutual Jaimini aspect.",
                    "impact": impact,
                    "planets": [_compact_planet(first), _compact_planet(second)],
                    "score": 8,
                }
            )

    if moon and venus and _same_or_aspecting(moon, venus):
        yogas.append(
            {
                "name": "Moon-Venus Jaimini Rajayoga",
                "type": "raja_yoga",
                "finding": "Moon and Venus are together or in Jaimini aspect.",
                "impact": "Public appeal, support, or comforts can improve when supported by dasha.",
                "planets": [_compact_planet(moon), _compact_planet(venus)],
                "score": 7,
            }
        )

    if moon:
        moon_aspected_by = [
            _compact_planet(planet)
            for planet in get_planets(chart_data, "d1")
            if planet.get("code") not in {"Asc", "Mo"} and signs_have_jaimini_aspect(planet.get("sign_number"), moon.get("sign_number"))
        ]
        if len(moon_aspected_by) >= 3:
            yogas.append(
                {
                    "name": "Moon aspected by many planets",
                    "type": "raja_yoga",
                    "finding": f"Moon receives Jaimini rashi aspects from {len(moon_aspected_by)} planets.",
                    "impact": "The book treats Moon influenced by many planets as a strong Rajayoga signal for visibility and rise.",
                    "planets": [_compact_planet(moon), *moon_aspected_by],
                    "score": 7,
                }
            )

    if ak and amk:
        distance = _planet_house_distance(ak, amk)
        if distance in KENDRA_HOUSES or distance in TRIKONA_HOUSES or distance == 11:
            yogas.append(
                {
                    "name": "Amatyakaraka supportive from Atmakaraka",
                    "type": "position_giver",
                    "finding": f"Amatyakaraka is {distance} houses from Atmakaraka.",
                    "impact": "Supports professional position with comparatively less struggle when dasha agrees.",
                    "planets": [_compact_planet(ak), _compact_planet(amk)],
                    "score": 8,
                }
            )
    return yogas


def build_ak_amk_relation(chart_data: dict[str, Any]) -> dict[str, Any]:
    d1_ak = _karaka_planet(chart_data, "Atmakaraka")
    d1_amk = _karaka_planet(chart_data, "Amatyakaraka")
    d9_ak = get_planet(chart_data, d1_ak.get("code"), "d9") if d1_ak else {}
    d9_amk = get_planet(chart_data, d1_amk.get("code"), "d9") if d1_amk else {}
    d1_distance = _planet_house_distance(d1_ak, d1_amk) if d1_ak and d1_amk else None
    d9_distance = _planet_house_distance(d9_ak, d9_amk) if d9_ak and d9_amk else None
    struggle_distances = {6, 8, 11}
    supportive_distances = set(KENDRA_HOUSES) | set(TRIKONA_HOUSES) | {11}
    return {
        "d1_distance": d1_distance,
        "d9_distance": d9_distance,
        "d1_supportive": d1_distance in supportive_distances,
        "d9_supportive": d9_distance in supportive_distances,
        "d1_struggle": d1_distance in struggle_distances,
        "d9_struggle": d9_distance in struggle_distances,
        "struggle_active": d1_distance in struggle_distances or d9_distance in struggle_distances,
        "support_active": d1_distance in supportive_distances or d9_distance in supportive_distances,
        "source_note": "Book notes Amatyakaraka in kendra/trikona/11th from Atmakaraka supports position; 6th/8th/11th can bring struggle.",
    }


def build_navamsha_jaimini_yogas(chart_data: dict[str, Any]) -> list[dict[str, Any]]:
    # The karaka labels are assigned from D1 degrees; this checks whether the same karaka planets
    # repeat conjunction/aspect patterns in D9 as a confirmation layer.
    d1_karakas = {
        planet.get("jaimini_karaka"): planet.get("code")
        for planet in get_planets(chart_data, "d1")
        if planet.get("jaimini_karaka")
    }
    d9_by_code = {planet.get("code"): planet for planet in get_planets(chart_data, "d9")}
    yogas = []
    pairs = [
        ("Atmakaraka-Amatyakaraka", "Atmakaraka", "Amatyakaraka"),
        ("Atmakaraka-Putrakaraka", "Atmakaraka", "Putrakaraka"),
        ("Atmakaraka-fifth lord", "Atmakaraka", "fifth_lord"),
        ("Atmakaraka-Darakaraka", "Atmakaraka", "Darakaraka"),
        ("Amatyakaraka-Putrakaraka", "Amatyakaraka", "Putrakaraka"),
        ("Amatyakaraka-fifth lord", "Amatyakaraka", "fifth_lord"),
        ("Amatyakaraka-Darakaraka", "Amatyakaraka", "Darakaraka"),
        ("Putrakaraka-fifth lord", "Putrakaraka", "fifth_lord"),
        ("Putrakaraka-Darakaraka", "Putrakaraka", "Darakaraka"),
        ("fifth lord-Darakaraka", "fifth_lord", "Darakaraka"),
    ]
    fifth_lord_code = get_house_lord(chart_data, 5)
    for label, first_karaka, second_karaka in pairs:
        first_code = fifth_lord_code if first_karaka == "fifth_lord" else d1_karakas.get(first_karaka)
        second_code = fifth_lord_code if second_karaka == "fifth_lord" else d1_karakas.get(second_karaka)
        first = d9_by_code.get(first_code, {})
        second = d9_by_code.get(second_code, {})
        if first and second and _same_or_aspecting(first, second):
            yogas.append(
                {
                    "name": f"D9 {label}",
                    "type": "navamsha_raja_yoga_confirmation",
                    "finding": f"{label} repeats in Navamsha by conjunction or Jaimini aspect.",
                    "impact": "Navamsha confirmation helps filter which Jaimini yogas survive.",
                    "planets": [_compact_planet(first), _compact_planet(second)],
                    "fifth_lord_reference": "d1_fifth_lord_relocated_to_d9"
                    if "fifth_lord" in {first_karaka, second_karaka}
                    else None,
                    "score": 6,
                }
            )

    moon = d9_by_code.get("Mo", {})
    venus = d9_by_code.get("Ve", {})
    if moon and venus and _same_or_aspecting(moon, venus):
        yogas.append(
            {
                "name": "D9 Moon-Venus Jaimini Rajayoga",
                "type": "navamsha_raja_yoga_confirmation",
                "finding": "Moon-Venus Jaimini Rajayoga repeats in Navamsha.",
                "impact": "Navamsha confirmation helps filter which Jaimini yogas survive.",
                "planets": [_compact_planet(moon), _compact_planet(venus)],
                "score": 6,
            }
        )
    if moon:
        moon_aspected_by = [
            _compact_planet(planet)
            for planet in get_planets(chart_data, "d9")
            if planet.get("code") not in {"Asc", "Mo"}
            and signs_have_jaimini_aspect(planet.get("sign_number"), moon.get("sign_number"))
        ]
        if len(moon_aspected_by) >= 3:
            yogas.append(
                {
                    "name": "D9 Moon aspected by many planets",
                    "type": "navamsha_raja_yoga_confirmation",
                    "finding": f"Moon receives Navamsha Jaimini rashi aspects from {len(moon_aspected_by)} planets.",
                    "impact": "Navamsha confirmation helps filter which Jaimini yogas survive.",
                    "planets": [_compact_planet(moon), *moon_aspected_by],
                    "score": 6,
                }
            )
    return yogas


def build_navamsha_fifth_lord_references(chart_data: dict[str, Any]) -> dict[str, Any]:
    d9_ascendant = get_planet(chart_data, "Asc", "d9")
    d9_ascendant_sign = d9_ascendant.get("sign_number")
    d9_fifth_sign = normalize_sign_number(d9_ascendant_sign + 4) if d9_ascendant_sign else None
    d9_fifth_lord_code = SIGN_LORDS.get(d9_fifth_sign)
    d1_fifth_lord_code = get_house_lord(chart_data, 5)
    return {
        "d1_fifth_lord_relocated_to_d9": _compact_planet(get_planet(chart_data, d1_fifth_lord_code, "d9")),
        "d9_lagna_fifth_lord": _compact_planet(get_planet(chart_data, d9_fifth_lord_code, "d9")),
        "d9_lagna_sign_number": d9_ascendant_sign,
        "d9_fifth_sign_number": d9_fifth_sign,
        "scoring_status": "unscored_reference_only",
        "method_note": "The reviewed passage asks for Navamsha confirmation but does not explicitly resolve whether fifth lord means the D1 fifth lord relocated into D9 or the fifth lord from D9 Lagna. Both references are exposed separately.",
    }


def _rajayoga_period_focus(period: dict[str, Any], yogas: list[dict[str, Any]]) -> dict[str, Any]:
    sign_number = period.get("sign_number")
    tenth_sign = _relative_house_sign(sign_number, 10)
    influencing_planets = {}
    for yoga in yogas:
        for planet in yoga.get("planets", []):
            planet_sign = planet.get("sign_number")
            if planet_sign == tenth_sign or signs_have_jaimini_aspect(planet_sign, tenth_sign):
                influencing_planets[planet.get("code")] = planet
    return {
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "tenth_sign_number": tenth_sign,
        "tenth_sign": SIGN_NAMES.get(tenth_sign),
        "surviving_yoga_planets_influencing_tenth": list(influencing_planets.values()),
        "active": bool(influencing_planets),
    }


def build_rajayoga_factors(
    chart_data: dict[str, Any],
    d1_yogas: list[dict[str, Any]],
    d9_yogas: list[dict[str, Any]],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
) -> dict[str, Any]:
    d1_pairs = {
        yoga.get("name"): yoga
        for yoga in d1_yogas
        if yoga.get("name") in STARTER_RAJAYOGA_PAIRS
    }
    d9_pairs = {
        yoga.get("name", "").removeprefix("D9 "): yoga
        for yoga in d9_yogas
        if yoga.get("name", "").removeprefix("D9 ") in STARTER_RAJAYOGA_PAIRS
    }
    surviving_names = sorted(set(d1_pairs) & set(d9_pairs))
    surviving_yogas = [d9_pairs[name] for name in surviving_names]
    d9_ak = get_planet(chart_data, _karaka_planet(chart_data, "Atmakaraka").get("code"), "d9")
    d9_amk = get_planet(chart_data, _karaka_planet(chart_data, "Amatyakaraka").get("code"), "d9")
    ak_amk_distance = sign_distance(d9_ak.get("sign_number"), d9_amk.get("sign_number"))
    supportive_distances = set(KENDRA_HOUSES) | set(TRIKONA_HOUSES) | {11}
    major_focus = _rajayoga_period_focus(current_major, surviving_yogas)
    subperiod_focus = _rajayoga_period_focus(current_subperiod, surviving_yogas)
    return {
        "d1_pair_yogas": list(d1_pairs.values()),
        "d9_pair_yogas": list(d9_pairs.values()),
        "surviving_pair_names": surviving_names,
        "filtered_out_pair_names": sorted(set(d1_pairs) - set(d9_pairs)),
        "d1_pair_count": len(d1_pairs),
        "d9_pair_count": len(d9_pairs),
        "surviving_pair_count": len(surviving_names),
        "navamsha_filtration_status": (
            "none_survive"
            if not surviving_names
            else "all_survive"
            if len(surviving_names) == len(d1_pairs)
            else "partial_survival"
        ),
        "ak_amk_navamsha_relation": {
            "distance": ak_amk_distance,
            "supportive": ak_amk_distance in supportive_distances,
            "one_eleven_relation": ak_amk_distance in {1, 11},
            "amatyakaraka_tenth_from_atmakaraka": ak_amk_distance == 10,
        },
        "timing": {
            "mahadasha": major_focus,
            "antardasha": subperiod_focus,
            "active": major_focus["active"] or subperiod_focus["active"],
        },
        "scoring_note": "Chapter 14 treats D1 Rajayogas as promise, Navamsha survival as filtration, and active Chara focus as timing support. Similar raw yoga lists must not be scored repeatedly.",
        "source_reference": {
            "chapter": "14",
            "pages": "96-104",
        },
    }


def _ak_period_reference(period: dict[str, Any], ak_sign: int | None) -> dict[str, Any]:
    period_sign = period.get("sign_number")
    ak_house_from_period = sign_distance(period_sign, ak_sign)
    contains_ak = bool(period_sign and ak_sign and period_sign == ak_sign)
    aspected_by_ak = bool(period_sign and ak_sign and signs_have_jaimini_aspect(ak_sign, period_sign))
    return {
        "sign_number": period_sign,
        "sign": SIGN_NAMES.get(period_sign),
        "contains_atmakaraka": contains_ak,
        "aspected_by_atmakaraka": aspected_by_ak,
        "related_by_placement_or_aspect": contains_ak or aspected_by_ak,
        "atmakaraka_house_from_period": ak_house_from_period,
        "atmakaraka_in_tenth_from_period": ak_house_from_period == 10,
        "atmakaraka_in_eighth_from_period": ak_house_from_period == 8,
    }


def build_ak_dasha_caution(
    chart_data: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
    karakamsha: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ak = _karaka_planet(chart_data, "Atmakaraka")
    ak_sign = ak.get("sign_number")
    d9_ak = get_planet(chart_data, ak.get("code"), "d9") if ak else {}
    karakamsha = karakamsha or build_karakamsha(chart_data)
    major_reference = _ak_period_reference(current_major, ak_sign)
    subperiod_reference = _ak_period_reference(current_subperiod, ak_sign)
    related_active = major_reference["related_by_placement_or_aspect"] or subperiod_reference["related_by_placement_or_aspect"]
    tenth_house_context_active = major_reference["atmakaraka_in_tenth_from_period"] or subperiod_reference["atmakaraka_in_tenth_from_period"]
    eighth_house_caution_active = major_reference["atmakaraka_in_eighth_from_period"] or subperiod_reference["atmakaraka_in_eighth_from_period"]
    return {
        "atmakaraka": _compact_planet(ak) if ak else {},
        "d1_dignity": get_planet_dignity(chart_data, ak.get("code"), "d1") if ak else "unknown",
        "d9_atmakaraka": _compact_planet(d9_ak) if d9_ak else {},
        "d9_dignity": get_planet_dignity(chart_data, ak.get("code"), "d9") if d9_ak else "unknown",
        "major_period": major_reference,
        "subperiod": subperiod_reference,
        "major_related_to_ak": major_reference["related_by_placement_or_aspect"],
        "subperiod_related_to_ak": subperiod_reference["related_by_placement_or_aspect"],
        "related_active": related_active,
        "tenth_house_context_active": tenth_house_context_active,
        "eighth_house_caution_active": eighth_house_caution_active,
        "atmakaraka_in_sagittarius": ak_sign == 9,
        "karakamsha_in_sagittarius": karakamsha.get("sign_number") == 9,
        "sagittarius_reference_active": ak_sign == 9 or karakamsha.get("sign_number") == 9,
        "active": related_active,
        "finding": (
            "Current Chara Dasha sign is related to Atmakaraka by sign placement or Jaimini aspect."
            if related_active
            else "Atmakaraka is in the eighth house from an active Chara Dasha sign."
            if eighth_house_caution_active
            else ""
        ),
        "caution": "AK-related periods require careful judgment. AK in the eighth from an active period raises caution; AK in the tenth is significant context but does not automatically indicate a fall.",
        "scoring_note": "Chapter 15 rejects automatic fall predictions from Atmakaraka periods. Treat these as caution or context facts and cross-check Vimshottari, Vargas, and other Jaimini factors.",
        "source_reference": {
            "chapter": "15",
            "pages": "105-115",
        },
    }


def build_sagittarius_dasha_caution(
    chart_data: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
    ak_caution: dict[str, Any],
) -> dict[str, Any]:
    major_sign = current_major.get("sign_number")
    subperiod_sign = current_subperiod.get("sign_number")
    subperiod_house_from_major = sign_distance(major_sign, subperiod_sign)
    major_active = major_sign == 9
    subperiod_active = subperiod_sign == 9
    sixth_or_eighth_subperiod_active = subperiod_house_from_major in {6, 8}
    ak_sign = ak_caution.get("atmakaraka", {}).get("sign_number")
    subperiod_aspected_by_ak = bool(
        subperiod_sign
        and ak_sign
        and signs_have_jaimini_aspect(ak_sign, subperiod_sign)
    )
    sixth_house_sign = get_house_sign(chart_data, 6)
    children_sixth_house_period_active = bool(
        sixth_house_sign
        and sixth_house_sign in {major_sign, subperiod_sign}
    )
    return {
        "active": major_active or subperiod_active,
        "major_active": major_active,
        "subperiod_active": subperiod_active,
        "subperiod_house_from_major": subperiod_house_from_major,
        "sixth_or_eighth_subperiod_from_major": {
            "active": sixth_or_eighth_subperiod_active,
            "aspected_by_atmakaraka": sixth_or_eighth_subperiod_active and subperiod_aspected_by_ak,
        },
        "atmakaraka_in_eighth_from_active_period": ak_caution.get("eighth_house_caution_active", False),
        "children_sixth_house_period": {
            "active": children_sixth_house_period_active,
            "sixth_house_sign_number": sixth_house_sign,
            "sixth_house_sign": SIGN_NAMES.get(sixth_house_sign),
        },
        "finding": "Sagittarius Chara Dasha or subperiod is active." if major_active or subperiod_active else "",
        "caution": "Sagittarius periods and sixth/eighth subperiods require careful judgment. The source does not support automatic predictions of accidents, illness, or fall without matching natal and cross-system evidence.",
        "scoring_note": "Chapter 16 caution facts are timing modifiers only. Do not convert them into fatal or event-specific predictions.",
        "source_reference": {
            "chapter": "16",
            "pages": "116-123",
        },
    }


def _relative_house_sign(base_sign: int | None, house_number: int) -> int | None:
    if not base_sign:
        return None
    return normalize_sign_number(base_sign + house_number - 1)


def _dasha_house_snapshot(chart_data: dict[str, Any], base_sign: int | None, house_number: int) -> dict[str, Any]:
    house_sign = _relative_house_sign(base_sign, house_number)
    occupants = [_compact_planet(planet) for planet in get_planets_in_sign(chart_data, house_sign, "d1")]
    influencers = _planets_influencing_sign(chart_data, house_sign)
    karaka_influencers = {
        planet.get("code"): planet
        for planet in occupants + influencers
        if planet.get("karaka")
    }
    return {
        "house_from_dasha_sign": house_number,
        "sign_number": house_sign,
        "sign": SIGN_NAMES.get(house_sign),
        "occupants": occupants,
        "influencing_planets": influencers,
        "karaka_influencers": list(karaka_influencers.values()),
    }


def _dasha_sign_as_lagna_period(
    chart_data: dict[str, Any],
    period: dict[str, Any],
    category: str,
    category_houses: list[int],
    label: str,
) -> dict[str, Any]:
    sign_number = period.get("sign_number")
    ascendant_sign = chart_data.get("ascendant", {}).get("sign_number")
    houses = {
        str(house_number): _dasha_house_snapshot(chart_data, sign_number, house_number)
        for house_number in range(1, 13)
    }
    relevant_house_activations = [
        houses[str(house_number)]
        for house_number in category_houses
        if houses[str(house_number)]["occupants"] or houses[str(house_number)]["influencing_planets"]
    ]
    category_karakas = KARAKA_LABELS_BY_CATEGORY.get(category, set())
    category_karaka_activations = [
        {
            "house_from_dasha_sign": house_number,
            "karakas": [
                planet
                for planet in houses[str(house_number)]["karaka_influencers"]
                if planet.get("karaka") in category_karakas
            ],
        }
        for house_number in category_houses
        if any(
            planet.get("karaka") in category_karakas
            for planet in houses[str(house_number)]["karaka_influencers"]
        )
    ]
    return {
        "label": label,
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "house_from_birth_lagna": sign_distance(ascendant_sign, sign_number),
        "houses_from_dasha_sign": houses,
        "tenth_from_dasha_sign": houses["10"],
        "relevant_house_activations": relevant_house_activations,
        "relevant_activation_count": len(relevant_house_activations),
        "category_karakas": sorted(category_karakas),
        "category_karaka_activations": category_karaka_activations,
        "method_note": "For Chara Dasha judgment, the running rashi is treated as a temporary lagna and relevant houses are examined from it.",
    }


def build_dasha_sign_as_lagna(
    chart_data: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
    category: str,
    category_houses: list[int],
) -> dict[str, Any]:
    major = _dasha_sign_as_lagna_period(chart_data, current_major or {}, category, category_houses, "mahadasha")
    subperiod = _dasha_sign_as_lagna_period(chart_data, current_subperiod or {}, category, category_houses, "antardasha")
    return {
        "mahadasha": major,
        "antardasha": subperiod,
        "combined_relevant_activation_count": major.get("relevant_activation_count", 0) + subperiod.get("relevant_activation_count", 0),
    }


def build_predictive_checklist(
    karaka_data: dict[str, Any],
    karakamsha: dict[str, Any],
    padas: dict[str, Any],
    chara_dasha: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
    dasha_sign_as_lagna: dict[str, Any],
) -> dict[str, Any]:
    return {
        "seven_karakas": karaka_data.get("karakas", {}),
        "karakamsha": karakamsha,
        "arudha_lagna": padas.get("arudha_lagna", {}),
        "upapada_lagna": padas.get("upapada_lagna", {}),
        "dasha_order_direction": chara_dasha.get("order_direction"),
        "current_mahadasha": current_major,
        "current_antardasha": current_subperiod,
        "mahadasha_house_from_birth_lagna": dasha_sign_as_lagna.get("mahadasha", {}).get("house_from_birth_lagna"),
        "antardasha_house_from_birth_lagna": dasha_sign_as_lagna.get("antardasha", {}).get("house_from_birth_lagna"),
        "scoring_status": "unscored_reference_only",
        "method_note": "Chapter 9 checklist: calculate the seven karakas, Karakamsha, Arudha Lagna, Upapada, dasha direction, periods, subperiods, and each active sign's house from birth Lagna before judging an event.",
    }


def _childhood_period_reference(
    period: dict[str, Any],
    gnatikaraka_sign: int | None,
    putrakaraka_sign: int | None,
) -> dict[str, Any]:
    sign_number = period.get("sign_number")
    return {
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "contains_gnatikaraka": bool(sign_number and sign_number == gnatikaraka_sign),
        "receives_gnatikaraka_aspect": bool(
            sign_number
            and gnatikaraka_sign
            and signs_have_jaimini_aspect(gnatikaraka_sign, sign_number)
        ),
        "contains_putrakaraka": bool(sign_number and sign_number == putrakaraka_sign),
    }


def build_childhood_factors(
    chart_data: dict[str, Any],
    karaka_condition_facts: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
) -> dict[str, Any]:
    gnatikaraka = _karaka_planet(chart_data, "Gnatikaraka")
    putrakaraka = _karaka_planet(chart_data, "Putrakaraka")
    gnatikaraka_sign = gnatikaraka.get("sign_number")
    putrakaraka_sign = putrakaraka.get("sign_number")
    gnatikaraka_condition = karaka_condition_facts.get("conditions", {}).get("Gnatikaraka", {})
    malefic_influences = gnatikaraka_condition.get("malefic_influences", [])
    major_period = _childhood_period_reference(current_major, gnatikaraka_sign, putrakaraka_sign)
    subperiod = _childhood_period_reference(current_subperiod, gnatikaraka_sign, putrakaraka_sign)
    pk_gk_same_sign = bool(
        putrakaraka_sign
        and gnatikaraka_sign
        and putrakaraka_sign == gnatikaraka_sign
    )
    active_period_contains_gk = major_period["contains_gnatikaraka"] or subperiod["contains_gnatikaraka"]
    pk_gk_active_period = pk_gk_same_sign and (
        major_period["contains_gnatikaraka"] or subperiod["contains_gnatikaraka"]
    )
    sagittarius_gk_subperiod_caution = bool(
        subperiod.get("sign_number") == 9
        and subperiod["contains_gnatikaraka"]
    )
    return {
        "gnatikaraka": _compact_planet(gnatikaraka) if gnatikaraka else {},
        "putrakaraka": _compact_planet(putrakaraka) if putrakaraka else {},
        "gnatikaraka_condition": gnatikaraka_condition,
        "gnatikaraka_malefic_influence_count": len(malefic_influences),
        "timing": {
            "mahadasha": major_period,
            "antardasha": subperiod,
            "active_period_contains_gnatikaraka": active_period_contains_gk,
        },
        "putrakaraka_gnatikaraka_same_sign": pk_gk_same_sign,
        "putrakaraka_gnatikaraka_active_period": pk_gk_active_period,
        "sagittarius_gnatikaraka_subperiod_caution": sagittarius_gk_subperiod_caution,
        "caution": {
            "active": bool(active_period_contains_gk and malefic_influences),
            "requires_cross_system_confirmation": True,
        },
        "scoring_note": "Chapter 10 childhood factors apply only to child-related questions. Gnatikaraka pressure is a cautious timing signal and must not become an automatic prediction of illness, accident, or harm. Confirm through D1, D7, Vimshottari, and the wider chart.",
        "source_reference": {
            "chapter": "10",
            "pages": "55-62",
        },
    }


def _relationship_reference(label: str, sign_number: int | None) -> dict[str, Any]:
    opposite_sign = normalize_sign_number(sign_number + 6) if sign_number else None
    return {
        "label": label,
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "seventh_sign_number": opposite_sign,
        "seventh_sign": SIGN_NAMES.get(opposite_sign),
    }


def _relationship_period_matches(
    period: dict[str, Any],
    references: dict[str, dict[str, Any]],
    darakaraka: dict[str, Any],
    putrakaraka: dict[str, Any],
) -> dict[str, Any]:
    sign_number = period.get("sign_number")
    matches = []
    for reference_name, reference in references.items():
        if sign_number and sign_number == reference.get("sign_number"):
            matches.append({"reference": reference_name, "relation": "same_sign"})
        if sign_number and sign_number == reference.get("seventh_sign_number"):
            matches.append({"reference": reference_name, "relation": "seventh_from_reference"})

    darakaraka_sign = darakaraka.get("sign_number")
    if sign_number and darakaraka_sign and signs_have_jaimini_aspect(darakaraka_sign, sign_number):
        matches.append({"reference": "darakaraka", "relation": "receives_darakaraka_aspect"})

    putrakaraka_sign = putrakaraka.get("sign_number")
    fifth_from_period = _relative_house_sign(sign_number, 5)
    return {
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "matches": matches,
        "match_count": len(matches),
        "putrakaraka_in_fifth_from_period": bool(
            sign_number and putrakaraka_sign and fifth_from_period == putrakaraka_sign
        ),
        "fifth_from_period_sign_number": fifth_from_period,
        "fifth_from_period_sign": SIGN_NAMES.get(fifth_from_period),
    }


def build_relationship_factors(
    chart_data: dict[str, Any],
    padas: dict[str, Any],
    karaka_condition_facts: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
) -> dict[str, Any]:
    ascendant_sign = chart_data.get("ascendant", {}).get("sign_number")
    darakaraka = _karaka_planet(chart_data, "Darakaraka")
    putrakaraka = _karaka_planet(chart_data, "Putrakaraka")
    darakaraka_sign = darakaraka.get("sign_number")
    d9_darakaraka = get_planet(chart_data, darakaraka.get("code"), "d9") if darakaraka else {}
    d9_ascendant = get_planet(chart_data, "Asc", "d9")
    upapada = padas.get("upapada_lagna", {})
    darapada = padas.get("all_padas", {}).get("7", {})
    rahu = get_planet(chart_data, "Ra", "d1")
    ketu = get_planet(chart_data, "Ke", "d1")
    seventh_lord = get_planet(chart_data, get_house_lord(chart_data, 7), "d1")
    references = {
        "d1_lagna": _relationship_reference("D1 Lagna", ascendant_sign),
        "darakaraka": _relationship_reference("Darakaraka", darakaraka_sign),
        "upapada": _relationship_reference("Upapada", upapada.get("pada_sign_number")),
        "darapada": _relationship_reference("Darapada", darapada.get("pada_sign_number")),
        "darakaraka_navamsha": _relationship_reference("Darakaraka Navamsha", d9_darakaraka.get("sign_number")),
        "d9_lagna": _relationship_reference("D9 Lagna", d9_ascendant.get("sign_number")),
    }
    major_timing = _relationship_period_matches(current_major, references, darakaraka, putrakaraka)
    subperiod_timing = _relationship_period_matches(current_subperiod, references, darakaraka, putrakaraka)
    relationship_signs = {
        sign
        for reference in references.values()
        for sign in (reference.get("sign_number"), reference.get("seventh_sign_number"))
        if sign
    }
    node_influenced_relationship_signs = sorted(
        sign
        for sign in relationship_signs
        if any(
            node.get("sign_number") == sign
            or signs_have_jaimini_aspect(node.get("sign_number"), sign)
            for node in (rahu, ketu)
            if node
        )
    )
    active_sign_pressure = []
    for label, period in (("mahadasha", current_major), ("antardasha", current_subperiod)):
        sign_number = period.get("sign_number")
        house_from_lagna = sign_distance(ascendant_sign, sign_number)
        relations = []
        if house_from_lagna in {6, 12}:
            relations.append(f"{house_from_lagna}_from_d1_lagna")
        for reference_name in ("upapada", "darapada"):
            distance = sign_distance(references[reference_name].get("sign_number"), sign_number)
            if distance in {6, 12}:
                relations.append(f"{distance}_from_{reference_name}")
        if relations:
            active_sign_pressure.append(
                {
                    "period": label,
                    "sign_number": sign_number,
                    "sign": SIGN_NAMES.get(sign_number),
                    "relations": relations,
                }
            )
    darakaraka_condition = karaka_condition_facts.get("conditions", {}).get("Darakaraka", {})
    pressure_facts = {
        "active_sign_pressure": active_sign_pressure,
        "node_influenced_relationship_signs": node_influenced_relationship_signs,
        "seventh_lord_under_node_influence": bool(
            seventh_lord
            and any(
                node.get("sign_number") == seventh_lord.get("sign_number")
                or signs_have_jaimini_aspect(node.get("sign_number"), seventh_lord.get("sign_number"))
                for node in (rahu, ketu)
                if node
            )
        ),
        "darakaraka_malefic_influences": darakaraka_condition.get("malefic_influences", []),
    }
    pressure_facts["pressure_count"] = (
        len(pressure_facts["active_sign_pressure"])
        + len(pressure_facts["node_influenced_relationship_signs"])
        + int(pressure_facts["seventh_lord_under_node_influence"])
        + len(pressure_facts["darakaraka_malefic_influences"])
    )
    return {
        "references": references,
        "darakaraka": _compact_planet(darakaraka) if darakaraka else {},
        "putrakaraka": _compact_planet(putrakaraka) if putrakaraka else {},
        "upapada": upapada,
        "darapada": darapada,
        "darakaraka_navamsha": _compact_planet(d9_darakaraka) if d9_darakaraka else {},
        "d9_lagna": _compact_planet(d9_ascendant) if d9_ascendant else {},
        "rahu_ketu_axis": {
            "rahu": _compact_planet(rahu) if rahu else {},
            "ketu": _compact_planet(ketu) if ketu else {},
            "rahu_aspected_signs": jaimini_aspected_signs(rahu.get("sign_number")) if rahu else [],
            "ketu_aspected_signs": jaimini_aspected_signs(ketu.get("sign_number")) if ketu else [],
        },
        "darakaraka_aspected_signs": jaimini_aspected_signs(darakaraka_sign),
        "timing": {
            "mahadasha": major_timing,
            "antardasha": subperiod_timing,
            "support_count": major_timing["match_count"] + subperiod_timing["match_count"],
        },
        "pressure": pressure_facts,
        "scoring_note": "Relationship timing matches are moderate support only. Pressure facts are caution signals and must not be converted into automatic separation, violence, or death claims.",
        "source_reference": {
            "chapters": "11-12",
            "pages": "64, 73-82",
        },
    }


def _amatyakaraka_period_timing(period: dict[str, Any], amatyakaraka_sign: int | None) -> dict[str, Any]:
    sign_number = period.get("sign_number")
    amatyakaraka_house_from_period = sign_distance(sign_number, amatyakaraka_sign)
    relation = {
        1: "contains_amatyakaraka",
        10: "amatyakaraka_in_tenth_from_period",
        11: "amatyakaraka_in_eleventh_from_period",
    }.get(amatyakaraka_house_from_period)
    return {
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "amatyakaraka_house_from_period": amatyakaraka_house_from_period,
        "relation": relation,
        "supports_professional_rise": bool(relation),
    }


def build_amatyakaraka_factors(
    chart_data: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
) -> dict[str, Any]:
    amatyakaraka = _karaka_planet(chart_data, "Amatyakaraka")
    if not amatyakaraka:
        return {}

    amatyakaraka_code = amatyakaraka.get("code")
    amatyakaraka_sign = amatyakaraka.get("sign_number")
    amatyakaraka_house = amatyakaraka.get("house")
    conjunctions = [
        _compact_planet(planet)
        for planet in get_planets_in_sign(chart_data, amatyakaraka_sign, "d1")
        if planet.get("code") != amatyakaraka_code
    ]
    aspecting_planets = [
        _compact_planet(planet)
        for planet in get_planets(chart_data, "d1")
        if planet.get("code") != amatyakaraka_code
        and planet.get("sign_number") != amatyakaraka_sign
        and signs_have_jaimini_aspect(planet.get("sign_number"), amatyakaraka_sign)
    ]
    sixth_lord_code = get_house_lord(chart_data, 6)
    eighth_lord_code = get_house_lord(chart_data, 8)
    connected_codes = {
        planet.get("code")
        for planet in conjunctions + aspecting_planets
    }
    major_timing = _amatyakaraka_period_timing(current_major, amatyakaraka_sign)
    subperiod_timing = _amatyakaraka_period_timing(current_subperiod, amatyakaraka_sign)
    is_supportive_placement = (
        amatyakaraka_house in KENDRA_HOUSES
        or amatyakaraka_house in TRIKONA_HOUSES
        or amatyakaraka_house == 11
    )
    is_pressure_placement = amatyakaraka_house in DUSTHANA_HOUSES
    benefic_influences = [
        planet
        for planet in conjunctions + aspecting_planets
        if planet.get("code") in BENEFIC_PLANETS
    ]
    malefic_influences = [
        planet
        for planet in conjunctions + aspecting_planets
        if planet.get("code") in MALEFIC_PLANETS
    ]
    sixth_lord_connected = sixth_lord_code in connected_codes
    eighth_lord_connected = eighth_lord_code in connected_codes
    return {
        "planet": {
            **_compact_planet(amatyakaraka),
            "dignity": get_planet_dignity(chart_data, amatyakaraka_code, "d1"),
            "owned_houses": get_owned_houses(chart_data, amatyakaraka_code),
        },
        "placement_from_d1_lagna": {
            "house": amatyakaraka_house,
            "supportive_for_smoother_career": is_supportive_placement,
            "pressure_house": is_pressure_placement,
            "method_note": "Chapter 13 judges Amatyakaraka placement from D1 Lagna, not from Karakamsha, Arudha Lagna, or Moon.",
        },
        "aspecting_planets": aspecting_planets,
        "conjunct_planets": conjunctions,
        "benefic_influences": benefic_influences,
        "malefic_influences": malefic_influences,
        "sixth_lord_connection": {
            "lord": sixth_lord_code,
            "connected": sixth_lord_connected,
        },
        "eighth_lord_connection": {
            "lord": eighth_lord_code,
            "connected": eighth_lord_connected,
        },
        "struggle_capacity_pattern": {
            "active": sixth_lord_connected and not eighth_lord_connected,
            "method_note": "The source treats sixth-lord connection without eighth-lord association as capacity to struggle in favourable periods, not as automatic success.",
        },
        "timing": {
            "mahadasha": major_timing,
            "antardasha": subperiod_timing,
            "support_count": int(major_timing["supports_professional_rise"])
            + int(subperiod_timing["supports_professional_rise"]),
        },
        "important_person_scope": {
            "available": True,
            "scoring_status": "context_only",
            "method_note": "Chapter 13 uses Amatyakaraka as a key reference for important persons and status-oriented questions. Specific outcomes still require question context and corroborating dashas.",
        },
        "caution": {
            "active": bool(is_pressure_placement or malefic_influences),
            "pressure_placement": is_pressure_placement,
            "malefic_influence_count": len(malefic_influences),
            "method_note": "Difficult Amatyakaraka patterns indicate professional friction or image risk. They do not independently justify a prediction of failure, loss of office, illness, or death.",
        },
        "source_reference": {
            "chapter": "13",
            "pages": "83-95",
        },
    }


def build_enhanced_jaimini_facts(
    chart_data: dict[str, Any],
    category: str,
    category_houses: list[int],
    current_major: dict[str, Any] | None = None,
    current_subperiod: dict[str, Any] | None = None,
    chara_dasha: dict[str, Any] | None = None,
) -> dict[str, Any]:
    karaka_data = build_karakas(chart_data)
    karakas = karaka_data["karakas"]
    arudha = build_arudha_factors(chart_data, category_houses)
    yogas = build_jaimini_yogas(chart_data)
    navamsha_yogas = build_navamsha_jaimini_yogas(chart_data)
    rajayoga_factors = build_rajayoga_factors(
        chart_data,
        yogas,
        navamsha_yogas,
        current_major or {},
        current_subperiod or {},
    )
    navamsha_fifth_lord_references = build_navamsha_fifth_lord_references(chart_data)
    karakamsha = build_karakamsha(chart_data)
    karaka_condition_facts = build_karaka_condition_facts(chart_data)
    ak_amk_relation = build_ak_amk_relation(chart_data)
    ak_caution = build_ak_dasha_caution(chart_data, current_major or {}, current_subperiod or {}, karakamsha)
    sagittarius_caution = build_sagittarius_dasha_caution(
        chart_data,
        current_major or {},
        current_subperiod or {},
        ak_caution,
    )
    dasha_sign_as_lagna = build_dasha_sign_as_lagna(
        chart_data,
        current_major or {},
        current_subperiod or {},
        category,
        category_houses,
    )
    predictive_checklist = build_predictive_checklist(
        karaka_data,
        karakamsha,
        arudha,
        chara_dasha or {},
        current_major or {},
        current_subperiod or {},
        dasha_sign_as_lagna,
    )
    relationship_factors = build_relationship_factors(
        chart_data,
        arudha,
        karaka_condition_facts,
        current_major or {},
        current_subperiod or {},
    )
    childhood_factors = build_childhood_factors(
        chart_data,
        karaka_condition_facts,
        current_major or {},
        current_subperiod or {},
    )
    amatyakaraka_factors = build_amatyakaraka_factors(
        chart_data,
        current_major or {},
        current_subperiod or {},
    )
    findings = []

    amk = karakas.get("amatyakaraka", {})
    ak = karakas.get("atmakaraka", {})
    if amk.get("house") in category_houses:
        findings.append(
            {
                "factor": "Amatyakaraka",
                "finding": f"{amk.get('name')} as Amatyakaraka is in relevant house {amk.get('house')}.",
                "impact": "Professional significator directly supports the question category.",
                "score": 14,
            }
        )
    if ak.get("house") in category_houses:
        findings.append(
            {
                "factor": "Atmakaraka",
                "finding": f"{ak.get('name')} as Atmakaraka is in relevant house {ak.get('house')}.",
                "impact": "Personal direction connects with the question category.",
                "score": 10,
            }
        )
    if arudha.get("tenth_from_arudha", {}).get("is_relevant_to_category"):
        findings.append(
            {
                "factor": "10th from Arudha Lagna",
                "finding": "The 10th from Arudha Lagna falls in a relevant house from Lagna.",
                "impact": "Public/professional image is relevant to the question category.",
                "score": 10,
            }
        )
    if arudha.get("career_karaka_influence"):
        findings.append(
            {
                "factor": "Arudha career karaka influence",
                "finding": "Atmakaraka or Amatyakaraka influences Arudha Lagna or the 10th from Arudha.",
                "impact": "Jaimini career indicators repeat through public-image factors.",
                "score": 12,
            }
        )
    if dasha_sign_as_lagna.get("combined_relevant_activation_count", 0) >= 2:
        findings.append(
            {
                "factor": "Chara Dasha sign as Lagna",
                "finding": "The running Chara Dasha signs activate multiple category houses when treated as temporary lagnas.",
                "impact": "This follows the book method of judging the active rashi dasha as a lagna before timing conclusions.",
                "score": 8,
            }
        )
    if karakamsha.get("tenth_from_karakamsha", {}).get("influencing_planets"):
        findings.append(
            {
                "factor": "10th from Karakamsha",
                "finding": "The 10th from Karakamsha receives occupation or Jaimini influence.",
                "impact": "Karakamsha gives a deeper Jaimini reference point for work direction and life path.",
                "score": 6,
            }
        )
    if arudha.get("eleventh_from_arudha", {}).get("occupants") or arudha.get("eleventh_from_arudha", {}).get("influencing_planets"):
        findings.append(
            {
                "factor": "11th from Arudha Lagna",
                "finding": "The 11th from Arudha Lagna is occupied or influenced.",
                "impact": "Arudha-based gains and public-result factors are active.",
                "score": 5,
            }
        )

    findings.extend(
        {
            "factor": yoga["name"],
            "finding": yoga["finding"],
            "impact": yoga["impact"],
            "score": yoga["score"],
        }
        for yoga in yogas + navamsha_yogas
    )
    if ak_caution.get("active"):
        findings.append(
            {
                "factor": "Atmakaraka Chara Dasha caution",
                "finding": ak_caution["finding"],
                "impact": "Use caution and avoid overconfident positive prediction without support from other systems.",
                "score": -4,
            }
        )
    if ak_amk_relation.get("struggle_active"):
        findings.append(
            {
                "factor": "Atmakaraka-Amatyakaraka struggle relation",
                "finding": "Atmakaraka and Amatyakaraka have a struggle distance in D1 or D9.",
                "impact": "Position can come with friction, delay, or extra effort even when other systems support the result.",
                "score": -3,
            }
        )
    if sagittarius_caution.get("active"):
        findings.append(
            {
                "factor": "Sagittarius Chara Dasha caution",
                "finding": sagittarius_caution["finding"],
                "impact": "Use extra caution in timing judgment and verify with Parashari, Varga, Yogini, and transits.",
                "score": -2,
            }
        )
    if sagittarius_caution.get("sixth_or_eighth_subperiod_from_major", {}).get("active"):
        findings.append(
            {
                "factor": "Sixth/eighth Chara subperiod caution",
                "finding": "The active Chara subperiod is sixth or eighth from the major-period sign.",
                "impact": "Use careful timing judgment and require natal and cross-system confirmation before making a strong claim.",
                "score": -2,
            }
        )
    if category == "children" and childhood_factors.get("caution", {}).get("active"):
        findings.append(
            {
                "factor": "Childhood Gnatikaraka caution",
                "finding": "An active Chara period contains Gnatikaraka while Gnatikaraka receives malefic influence.",
                "impact": "Use cautious child-related judgment and require D1, D7, Vimshottari, and wider-chart confirmation.",
                "score": -3,
            }
        )
    score = min(100, sum(item["score"] for item in findings))
    return {
        "calculation_status": "active",
        "method_source": "Predicting through Jaimini's Chara Dasha",
        "karaka_method": karaka_data,
        "karakamsha": karakamsha,
        "padas": {
            "all_padas": arudha.get("all_padas", {}),
            "arudha_lagna": arudha.get("arudha_lagna", {}),
            "upapada_lagna": arudha.get("upapada_lagna", {}),
            "planetary_padas": arudha.get("planetary_padas", {}),
            "exceptions_applied": arudha.get("exceptions_applied"),
            "method_note": arudha.get("method_note"),
        },
        "arudha_factors": arudha,
        "dasha_sign_as_lagna": dasha_sign_as_lagna,
        "predictive_checklist": predictive_checklist,
        "relationship_factors": relationship_factors,
        "childhood_factors": childhood_factors,
        "amatyakaraka_factors": amatyakaraka_factors,
        "jaimini_yogas": yogas,
        "navamsha_jaimini_yogas": navamsha_yogas,
        "rajayoga_factors": rajayoga_factors,
        "navamsha_fifth_lord_references": navamsha_fifth_lord_references,
        "karaka_condition_facts": karaka_condition_facts,
        "ak_amk_relation": ak_amk_relation,
        "atmakaraka_dasha_caution": ak_caution,
        "sagittarius_dasha_caution": sagittarius_caution,
        "enhanced_findings": findings,
        "enhanced_score": score,
        "enhanced_status": "supports" if score >= 45 else "mixed" if score else "not_confirmed",
    }
