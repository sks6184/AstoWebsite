from typing import Any

from charts.vedic_utils import (
    KENDRA_HOUSES,
    PLANET_NAMES,
    SIGN_NAMES,
    TRIKONA_HOUSES,
    get_house_lord,
    get_house_sign,
    get_planet,
    get_planets,
    get_planets_in_sign,
    house_distance,
    normalize_sign_number,
    sign_distance,
)


MOVABLE_SIGNS = {1, 4, 7, 10}
FIXED_SIGNS = {2, 5, 8, 11}
DUAL_SIGNS = {3, 6, 9, 12}
RAJAYOGA_KARAKAS = {"Atmakaraka", "Amatyakaraka", "Putrakaraka", "Darakaraka"}


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
        "arudha_lagna": arudha,
        "upapada_lagna": padas["upapada_lagna"],
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
        ("Putrakaraka-Darakaraka", "Putrakaraka", "Darakaraka"),
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
                    "score": 6,
                }
            )
    return yogas


def build_ak_dasha_caution(chart_data: dict[str, Any], current_major: dict[str, Any], current_subperiod: dict[str, Any]) -> dict[str, Any]:
    ak = _karaka_planet(chart_data, "Atmakaraka")
    ak_sign = ak.get("sign_number")
    major_sign = current_major.get("sign_number")
    sub_sign = current_subperiod.get("sign_number")
    major_related = bool(ak_sign and major_sign and (major_sign == ak_sign or signs_have_jaimini_aspect(major_sign, ak_sign)))
    subperiod_related = bool(ak_sign and sub_sign and (sub_sign == ak_sign or signs_have_jaimini_aspect(sub_sign, ak_sign)))
    return {
        "atmakaraka": _compact_planet(ak) if ak else {},
        "major_related_to_ak": major_related,
        "subperiod_related_to_ak": subperiod_related,
        "active": major_related or subperiod_related,
        "finding": "Current Chara Dasha sign is related to Atmakaraka by sign placement or Jaimini aspect."
        if major_related or subperiod_related
        else "",
        "caution": "Book notes caution in dasha periods of Atmakaraka or signs aspected by Atmakaraka.",
    }


def build_sagittarius_dasha_caution(current_major: dict[str, Any], current_subperiod: dict[str, Any]) -> dict[str, Any]:
    major_active = current_major.get("sign_number") == 9
    subperiod_active = current_subperiod.get("sign_number") == 9
    return {
        "active": major_active or subperiod_active,
        "major_active": major_active,
        "subperiod_active": subperiod_active,
        "finding": "Sagittarius Chara Dasha or subperiod is active." if major_active or subperiod_active else "",
        "caution": "Book examples flag Sagittarius dasha as a period requiring careful judgment rather than automatic positive reading.",
    }


def _relative_house_sign(base_sign: int | None, house_number: int) -> int | None:
    if not base_sign:
        return None
    return normalize_sign_number(base_sign + house_number - 1)


def _dasha_sign_as_lagna_period(chart_data: dict[str, Any], period: dict[str, Any], category_houses: list[int], label: str) -> dict[str, Any]:
    sign_number = period.get("sign_number")
    ascendant_sign = chart_data.get("ascendant", {}).get("sign_number")
    relevant_house_activations = []
    for house_number in category_houses:
        house_sign = _relative_house_sign(sign_number, house_number)
        occupants = [_compact_planet(planet) for planet in get_planets_in_sign(chart_data, house_sign, "d1")]
        influencers = _planets_influencing_sign(chart_data, house_sign)
        if occupants or influencers:
            relevant_house_activations.append(
                {
                    "house_from_dasha_sign": house_number,
                    "sign_number": house_sign,
                    "sign": SIGN_NAMES.get(house_sign),
                    "occupants": occupants,
                    "influencing_planets": influencers,
                    "karaka_influencers": [
                        planet for planet in occupants + influencers if planet.get("karaka") in RAJAYOGA_KARAKAS
                    ],
                }
            )
    tenth_sign = _relative_house_sign(sign_number, 10)
    return {
        "label": label,
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "house_from_birth_lagna": sign_distance(ascendant_sign, sign_number),
        "tenth_from_dasha_sign": {
            "sign_number": tenth_sign,
            "sign": SIGN_NAMES.get(tenth_sign),
            "occupants": [_compact_planet(planet) for planet in get_planets_in_sign(chart_data, tenth_sign, "d1")],
            "influencing_planets": _planets_influencing_sign(chart_data, tenth_sign),
        },
        "relevant_house_activations": relevant_house_activations,
        "relevant_activation_count": len(relevant_house_activations),
        "method_note": "For Chara Dasha judgment, the running rashi is treated as a temporary lagna and relevant houses are examined from it.",
    }


def build_dasha_sign_as_lagna(
    chart_data: dict[str, Any],
    current_major: dict[str, Any],
    current_subperiod: dict[str, Any],
    category_houses: list[int],
) -> dict[str, Any]:
    major = _dasha_sign_as_lagna_period(chart_data, current_major or {}, category_houses, "mahadasha")
    subperiod = _dasha_sign_as_lagna_period(chart_data, current_subperiod or {}, category_houses, "antardasha")
    return {
        "mahadasha": major,
        "antardasha": subperiod,
        "combined_relevant_activation_count": major.get("relevant_activation_count", 0) + subperiod.get("relevant_activation_count", 0),
    }


def build_enhanced_jaimini_facts(
    chart_data: dict[str, Any],
    category: str,
    category_houses: list[int],
    current_major: dict[str, Any] | None = None,
    current_subperiod: dict[str, Any] | None = None,
) -> dict[str, Any]:
    karaka_data = build_karakas(chart_data)
    karakas = karaka_data["karakas"]
    arudha = build_arudha_factors(chart_data, category_houses)
    yogas = build_jaimini_yogas(chart_data)
    navamsha_yogas = build_navamsha_jaimini_yogas(chart_data)
    karakamsha = build_karakamsha(chart_data)
    ak_amk_relation = build_ak_amk_relation(chart_data)
    ak_caution = build_ak_dasha_caution(chart_data, current_major or {}, current_subperiod or {})
    sagittarius_caution = build_sagittarius_dasha_caution(current_major or {}, current_subperiod or {})
    dasha_sign_as_lagna = build_dasha_sign_as_lagna(chart_data, current_major or {}, current_subperiod or {}, category_houses)
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
    score = min(100, sum(item["score"] for item in findings))
    return {
        "calculation_status": "active",
        "method_source": "Predicting through Jaimini's Chara Dasha",
        "karaka_method": karaka_data,
        "karakamsha": karakamsha,
        "padas": {
            "arudha_lagna": arudha.get("arudha_lagna", {}),
            "upapada_lagna": arudha.get("upapada_lagna", {}),
        },
        "arudha_factors": arudha,
        "dasha_sign_as_lagna": dasha_sign_as_lagna,
        "jaimini_yogas": yogas,
        "navamsha_jaimini_yogas": navamsha_yogas,
        "ak_amk_relation": ak_amk_relation,
        "atmakaraka_dasha_caution": ak_caution,
        "sagittarius_dasha_caution": sagittarius_caution,
        "enhanced_findings": findings,
        "enhanced_score": score,
        "enhanced_status": "supports" if score >= 45 else "mixed" if score else "not_confirmed",
    }
