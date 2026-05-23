from datetime import datetime

import swisseph as swe


PLANET_IDS = {
    "Su": swe.SUN,
    "Mo": swe.MOON,
    "Ma": swe.MARS,
    "Me": swe.MERCURY,
    "Ju": swe.JUPITER,
    "Ve": swe.VENUS,
    "Sa": swe.SATURN,
    "Ra": swe.TRUE_NODE,
}

PLANET_NAMES = {
    "Su": "Sun",
    "Mo": "Moon",
    "Ma": "Mars",
    "Me": "Mercury",
    "Ju": "Jupiter",
    "Ve": "Venus",
    "Sa": "Saturn",
    "Ra": "Rahu",
    "Ke": "Ketu",
}

SIGN_NAMES = {
    1: "Aries",
    2: "Taurus",
    3: "Gemini",
    4: "Cancer",
    5: "Leo",
    6: "Virgo",
    7: "Libra",
    8: "Scorpio",
    9: "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

SIGN_LORDS = {
    1: "Ma",
    2: "Ve",
    3: "Me",
    4: "Mo",
    5: "Su",
    6: "Me",
    7: "Ve",
    8: "Ma",
    9: "Ju",
    10: "Sa",
    11: "Sa",
    12: "Ju",
}

OWN_SIGNS = {
    "Su": {5},
    "Mo": {4},
    "Ma": {1, 8},
    "Me": {3, 6},
    "Ju": {9, 12},
    "Ve": {2, 7},
    "Sa": {10, 11},
}

EXALTATION_SIGNS = {
    "Su": 1,
    "Mo": 2,
    "Ma": 10,
    "Me": 6,
    "Ju": 4,
    "Ve": 12,
    "Sa": 7,
    "Ra": 2,
    "Ke": 8,
}

DEBILITATION_SIGNS = {
    "Su": 7,
    "Mo": 8,
    "Ma": 4,
    "Me": 12,
    "Ju": 10,
    "Ve": 6,
    "Sa": 1,
    "Ra": 8,
    "Ke": 2,
}

KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}
BENEFIC_PLANETS = {"Ju", "Ve", "Me", "Mo"}
MALEFIC_PLANETS = {"Su", "Ma", "Sa", "Ra", "Ke"}

# Vedic special aspects (offsets in houses from planet's house, 1-indexed).
# All planets have 7th aspect. Jupiter adds 5th+9th, Saturn adds 3rd+10th, Mars adds 4th+8th.
# Rahu/Ketu: 7th only (tradition varies; we use conservative 7th-only).
PLANET_ASPECTS = {
    "Su": [7],
    "Mo": [7],
    "Ma": [4, 7, 8],
    "Me": [7],
    "Ju": [5, 7, 9],
    "Ve": [7],
    "Sa": [3, 7, 10],
    "Ra": [7],
    "Ke": [7],
}


def aspected_houses(planet_code, from_house):
    """Return list of houses aspected by planet_code when placed in from_house."""
    if not from_house:
        return []
    offsets = PLANET_ASPECTS.get(planet_code, [7])
    return [((int(from_house) + offset - 2) % 12) + 1 for offset in offsets]


def natal_planet_aspects_on_house(chart_data, house_number):
    """
    Return list of (planet_code, planet_name) tuples whose natal position aspects house_number.
    Used to detect inbound natal aspects — e.g. natal Jupiter in 3rd aspects house 7 (3+4=7).
    """
    from_chart = chart_data.get("d1", {}).get("planets", [])
    aspecting = []
    for p in from_chart:
        code = p.get("code")
        natal_house = p.get("house")
        if not code or not natal_house or code == "Asc":
            continue
        if house_number in aspected_houses(code, natal_house):
            aspecting.append((code, PLANET_NAMES.get(code, code)))
    return aspecting


def natal_mutual_aspects(chart_data):
    """
    Find all planet pairs in mutual aspect (parasparika drishti) in the natal D1 chart.
    A mutual aspect exists when planet A aspects B's house AND B aspects A's house.
    Returns list sorted so pairs involving Jupiter or Sun appear first.
    """
    planets = [p for p in get_planets(chart_data, "d1") if p.get("house")]
    pairs = []
    seen = set()

    for i, p1 in enumerate(planets):
        code1 = p1.get("code")
        house1 = p1.get("house")
        if not code1 or not house1:
            continue
        asp1 = set(aspected_houses(code1, house1))

        for p2 in planets[i + 1:]:
            code2 = p2.get("code")
            house2 = p2.get("house")
            if not code2 or not house2 or house1 == house2:
                continue
            asp2 = set(aspected_houses(code2, house2))

            if house2 in asp1 and house1 in asp2:
                key = tuple(sorted([code1, code2]))
                if key in seen:
                    continue
                seen.add(key)

                owned1 = get_owned_houses(chart_data, code1)
                owned2 = get_owned_houses(chart_data, code2)
                linked = sorted(set([house1, house2] + owned1 + owned2))
                involves_karaka = code1 in {"Ju", "Su"} or code2 in {"Ju", "Su"}

                pairs.append({
                    "planet_a": code1,
                    "planet_a_name": PLANET_NAMES.get(code1, code1),
                    "house_a": house1,
                    "owned_houses_a": owned1,
                    "planet_b": code2,
                    "planet_b_name": PLANET_NAMES.get(code2, code2),
                    "house_b": house2,
                    "owned_houses_b": owned2,
                    "linked_houses": linked,
                    "involves_karaka": involves_karaka,
                })

    pairs.sort(key=lambda p: not p["involves_karaka"])
    return pairs


def normalize_sign_number(sign_number):
    if not sign_number:
        return None
    return ((int(sign_number) - 1) % 12) + 1


def house_distance(start_house, target_house):
    if not start_house or not target_house:
        return None
    return ((int(target_house) - int(start_house)) % 12) + 1


def sign_distance(start_sign, target_sign):
    if not start_sign or not target_sign:
        return None
    return ((int(target_sign) - int(start_sign)) % 12) + 1


def house_from_sign(chart_data, sign_number):
    asc_sign_number = chart_data.get("ascendant", {}).get("sign_number")
    if not asc_sign_number or not sign_number:
        return None
    return sign_distance(asc_sign_number, sign_number)


def get_planets(chart_data, chart_key="d1", include_ascendant=False):
    planets = chart_data.get(chart_key, {}).get("planets", [])
    if include_ascendant:
        return planets
    return [planet for planet in planets if planet.get("code") != "Asc"]


def get_planet(chart_data, planet_code, chart_key="d1"):
    for planet in get_planets(chart_data, chart_key, include_ascendant=True):
        if planet.get("code") == planet_code:
            return planet
    return {}


def get_planets_in_house(chart_data, house_number, chart_key="d1"):
    return [
        planet
        for planet in get_planets(chart_data, chart_key)
        if planet.get("house") == house_number
    ]


def get_planets_in_sign(chart_data, sign_number, chart_key="d1"):
    return [
        planet
        for planet in get_planets(chart_data, chart_key)
        if planet.get("sign_number") == sign_number
    ]


def get_house_sign(chart_data, house_number):
    asc_sign_number = chart_data.get("ascendant", {}).get("sign_number")
    if not asc_sign_number or not house_number:
        return None
    return normalize_sign_number(int(asc_sign_number) + int(house_number) - 1)


def get_house_lord(chart_data, house_number):
    sign_number = get_house_sign(chart_data, house_number)
    if not sign_number:
        return None
    return SIGN_LORDS.get(sign_number)


def get_house_lord_planet(chart_data, house_number, chart_key="d1"):
    lord = get_house_lord(chart_data, house_number)
    return get_planet(chart_data, lord, chart_key) if lord else {}


def get_owned_houses(chart_data, planet_code):
    asc_sign_number = chart_data.get("ascendant", {}).get("sign_number")
    if not asc_sign_number:
        return []
    return [
        sign_distance(asc_sign_number, sign_number)
        for sign_number, owner_code in SIGN_LORDS.items()
        if owner_code == planet_code
    ]


def are_conjunct(chart_data, first_code, second_code, chart_key="d1"):
    first = get_planet(chart_data, first_code, chart_key)
    second = get_planet(chart_data, second_code, chart_key)
    return bool(first and second and first.get("house") == second.get("house"))


def houses_from_planet(chart_data, from_planet_code, target_planet_code, chart_key="d1"):
    from_planet = get_planet(chart_data, from_planet_code, chart_key)
    target_planet = get_planet(chart_data, target_planet_code, chart_key)
    return house_distance(from_planet.get("house"), target_planet.get("house"))


def is_in_kendra_from_lagna(chart_data, planet_code, chart_key="d1"):
    planet = get_planet(chart_data, planet_code, chart_key)
    return planet.get("house") in KENDRA_HOUSES


def is_in_trikona_from_lagna(chart_data, planet_code, chart_key="d1"):
    planet = get_planet(chart_data, planet_code, chart_key)
    return planet.get("house") in TRIKONA_HOUSES


def is_in_kendra_from_planet(chart_data, from_planet_code, target_planet_code, chart_key="d1"):
    distance = houses_from_planet(chart_data, from_planet_code, target_planet_code, chart_key)
    return distance in KENDRA_HOUSES


def is_own_sign(planet_code, sign_number):
    return normalize_sign_number(sign_number) in OWN_SIGNS.get(planet_code, set())


def is_exalted(planet_code, sign_number):
    return normalize_sign_number(sign_number) == EXALTATION_SIGNS.get(planet_code)


def is_debilitated(planet_code, sign_number):
    return normalize_sign_number(sign_number) == DEBILITATION_SIGNS.get(planet_code)


def get_planet_dignity(chart_data, planet_code, chart_key="d1"):
    planet = get_planet(chart_data, planet_code, chart_key)
    sign_number = planet.get("sign_number")
    if not sign_number:
        return "unknown"
    if is_exalted(planet_code, sign_number):
        return "exalted"
    if is_own_sign(planet_code, sign_number):
        return "own_sign"
    if is_debilitated(planet_code, sign_number):
        return "debilitated"
    return "ordinary"


def get_sarvashtakavarga_points(chart_data, house_number):
    for row in chart_data.get("ashtakavarga", {}).get("rows", []):
        if row.get("house") == house_number:
            return row.get("sarva", 0)
    return 0


def transit_longitude(planet_code, target_dt):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_ut = swe.julday(
        target_dt.year,
        target_dt.month,
        target_dt.day,
        target_dt.hour + target_dt.minute / 60 + target_dt.second / 3600,
    )
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    if planet_code == "Ke":
        rahu_values, _ = swe.calc_ut(jd_ut, swe.TRUE_NODE, flags)
        return (rahu_values[0] + 180) % 360
    values, _ = swe.calc_ut(jd_ut, PLANET_IDS[planet_code], flags)
    return values[0] % 360


def transit_context_for_lord(chart_data, planet_code, target_dt):
    longitude = transit_longitude(planet_code, target_dt)
    sign_number = int(longitude // 30) + 1
    house = house_from_sign(chart_data, sign_number) or 1
    sav = get_sarvashtakavarga_points(chart_data, house)
    natal_planet = get_planet(chart_data, planet_code)
    return {
        "lord": planet_code,
        "lord_name": PLANET_NAMES.get(planet_code, planet_code),
        "transit_longitude": longitude,
        "transit_sign_number": sign_number,
        "transit_sign": SIGN_NAMES.get(sign_number),
        "transit_house_from_lagna": house,
        "sarvashtakavarga_points": sav,
        "ashtakavarga_threshold": 28,
        "can_deliver_owned_or_placed_house_results": sav > 28,
        "natal_placed_house": natal_planet.get("house"),
        "natal_longitude": natal_planet.get("longitude"),
        "owned_houses": get_owned_houses(chart_data, planet_code),
    }


def parse_iso_date(value):
    return datetime.fromisoformat(value).date()
