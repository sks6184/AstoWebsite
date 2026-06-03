from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from .ashtakavarga import build_ashtakavarga
from .jaimini import build_chara_dasha
from .yogas import detect_yogas
from astrology.constants import (
    NAKSHATRAS,
    SIGN_LORDS,
    SIGNS,
)
from astrology.calculations.vimshottari import build_vimshottari_dasha
from astrology.calculations.yogini import build_yogini_periods


JAIMINI_KARAKAS = [
    "Atmakaraka",
    "Amatyakaraka",
    "Bhratrukaraka",
    "Matrukaraka",
    "Putrakaraka",
    "Gnatikaraka",
    "Darakaraka",
]

PLANETS = [
    ("Sun", "Su", swe.SUN),
    ("Moon", "Mo", swe.MOON),
    ("Mars", "Ma", swe.MARS),
    ("Mercury", "Me", swe.MERCURY),
    ("Jupiter", "Ju", swe.JUPITER),
    ("Venus", "Ve", swe.VENUS),
    ("Saturn", "Sa", swe.SATURN),
    ("Rahu", "Ra", swe.TRUE_NODE),
]

HOUSE_POSITIONS = {
    1: {"sign": {"x": 50, "y": 31}, "planets": {"x": 50, "y": 24}},
    2: {"sign": {"x": 31, "y": 23}, "planets": {"x": 34, "y": 14}},
    3: {"sign": {"x": 24, "y": 34}, "planets": {"x": 10, "y": 30}},
    4: {"sign": {"x": 36, "y": 47}, "planets": {"x": 25, "y": 44}},
    5: {"sign": {"x": 24, "y": 70}, "planets": {"x": 10, "y": 70}},
    6: {"sign": {"x": 31, "y": 80}, "planets": {"x": 36, "y": 91}},
    7: {"sign": {"x": 50, "y": 69}, "planets": {"x": 50, "y": 80}},
    8: {"sign": {"x": 69, "y": 80}, "planets": {"x": 64, "y": 91}},
    9: {"sign": {"x": 76, "y": 70}, "planets": {"x": 90, "y": 70}},
    10: {"sign": {"x": 64, "y": 47}, "planets": {"x": 75, "y": 44}},
    11: {"sign": {"x": 76, "y": 34}, "planets": {"x": 88, "y": 34}},
    12: {"sign": {"x": 69, "y": 23}, "planets": {"x": 66, "y": 14}},
}


def _local_datetime_to_utc(birth_date, birth_time, timezone_name):
    try:
        tzinfo = ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        tzinfo = ZoneInfo("UTC")

    local_dt = datetime.combine(birth_date, birth_time).replace(tzinfo=tzinfo)
    return local_dt.astimezone(ZoneInfo("UTC"))


def _sign_index(longitude):
    return int(longitude // 30)


def _format_dms(degrees):
    whole_degrees = int(degrees)
    minutes_float = (degrees - whole_degrees) * 60
    minutes = int(minutes_float)
    seconds = int(round((minutes_float - minutes) * 60))

    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        whole_degrees += 1

    return f"{whole_degrees:02d}-{minutes:02d}-{seconds:02d}"


def _format_date(value):
    return value.strftime("%d-%b-%Y")


def _nakshatra_details(longitude):
    nakshatra_span = 360 / 27
    pada_span = nakshatra_span / 4
    index = int(longitude // nakshatra_span)
    degrees_in_nakshatra = longitude % nakshatra_span
    pada = int(degrees_in_nakshatra // pada_span) + 1
    name, lord = NAKSHATRAS[index]
    return {"name": name, "lord": lord, "pada": pada}


def _planet_row(name, code, longitude, speed, asc_sign_index):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    house = ((sign_index - asc_sign_index) % 12) + 1
    nakshatra = _nakshatra_details(longitude)
    retrograde = speed < 0

    return {
        "name": name,
        "code": code,
        "longitude": round(longitude, 6),
        "degree": _format_dms(sign_degree),
        "sign": SIGNS[sign_index],
        "sign_lord": SIGN_LORDS[SIGNS[sign_index]],
        "sign_number": sign_index + 1,
        "house": house,
        "nakshatra": nakshatra["name"],
        "nakshatra_lord": nakshatra["lord"],
        "pada": nakshatra["pada"],
        "motion": "R" if retrograde else "D",
        "retrograde": retrograde,
    }


def _varga_longitude(longitude, division, start_sign_index):
    sign_degree = longitude % 30
    part_size = 30 / division
    part = int(sign_degree // part_size)
    varga_sign_index = (start_sign_index + part) % 12
    varga_degree = (sign_degree % part_size) * division
    return varga_sign_index * 30 + varga_degree


def _hora_longitude(longitude):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    is_odd_sign = (sign_index + 1) % 2 == 1
    if is_odd_sign:
        hora_sign_index = 4 if sign_degree < 15 else 3
    else:
        hora_sign_index = 3 if sign_degree < 15 else 4
    hora_degree = (sign_degree % 15) * 2
    return hora_sign_index * 30 + hora_degree


def _saptamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    is_odd_sign = (sign_index + 1) % 2 == 1
    start_sign_index = sign_index if is_odd_sign else (sign_index + 6) % 12
    return _varga_longitude(longitude, 7, start_sign_index)


def _drekkana_longitude(longitude):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    part = int(sign_degree // 10)
    drekkana_sign_index = (sign_index + part * 4) % 12
    drekkana_degree = (sign_degree % 10) * 3
    return drekkana_sign_index * 30 + drekkana_degree


def _chaturthamsha_longitude(longitude):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    quarter = int(sign_degree // 7.5)
    chaturthamsha_sign_index = (sign_index + (quarter * 3)) % 12
    chaturthamsha_degree = (sign_degree % 7.5) * 4
    return chaturthamsha_sign_index * 30 + chaturthamsha_degree


def _navamsha_longitude(longitude):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    navamsha_part = int(sign_degree // (30 / 9))

    if sign_index in [0, 3, 6, 9]:
        navamsha_sign_index = (sign_index + navamsha_part) % 12
    elif sign_index in [1, 4, 7, 10]:
        navamsha_sign_index = (sign_index + 8 + navamsha_part) % 12
    else:
        navamsha_sign_index = (sign_index + 4 + navamsha_part) % 12

    navamsha_degree = (sign_degree % (30 / 9)) * 9
    return navamsha_sign_index * 30 + navamsha_degree


def _dasamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    dasamsa_part = int(sign_degree // 3)

    if (sign_index + 1) % 2 == 1:
        dasamsa_sign_index = (sign_index + dasamsa_part) % 12
    else:
        dasamsa_sign_index = (sign_index + 8 + dasamsa_part) % 12

    dasamsa_degree = (sign_degree % 3) * 10
    return dasamsa_sign_index * 30 + dasamsa_degree


def _dwadasamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    return _varga_longitude(longitude, 12, sign_index)


def _shodashamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    if sign_index in [0, 3, 6, 9]:
        start_sign_index = 0
    elif sign_index in [1, 4, 7, 10]:
        start_sign_index = 4
    else:
        start_sign_index = 8
    return _varga_longitude(longitude, 16, start_sign_index)


def _vimshamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    if sign_index in [0, 3, 6, 9]:
        start_sign_index = 0
    elif sign_index in [1, 4, 7, 10]:
        start_sign_index = 8
    else:
        start_sign_index = 4
    return _varga_longitude(longitude, 20, start_sign_index)


def _chaturvimshamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    is_odd_sign = (sign_index + 1) % 2 == 1
    start_sign_index = 4 if is_odd_sign else 3
    return _varga_longitude(longitude, 24, start_sign_index)


def _saptavimshamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    if sign_index in [0, 4, 8]:
        start_sign_index = 0
    elif sign_index in [1, 5, 9]:
        start_sign_index = 3
    elif sign_index in [2, 6, 10]:
        start_sign_index = 6
    else:
        start_sign_index = 9
    return _varga_longitude(longitude, 27, start_sign_index)


def _trimsamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    sign_degree = longitude % 30
    is_odd_sign = (sign_index + 1) % 2 == 1

    if is_odd_sign:
        ranges = [
            (5, 0),
            (10, 10),
            (18, 8),
            (25, 2),
            (30, 6),
        ]
    else:
        ranges = [
            (5, 1),
            (12, 5),
            (20, 11),
            (25, 9),
            (30, 7),
        ]

    previous_limit = 0
    for limit, trimsamsa_sign_index in ranges:
        if sign_degree < limit:
            span = limit - previous_limit
            degree = ((sign_degree - previous_limit) / span) * 30
            return trimsamsa_sign_index * 30 + degree
        previous_limit = limit
    return ranges[-1][1] * 30


def _khavedamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    is_odd_sign = (sign_index + 1) % 2 == 1
    start_sign_index = 0 if is_odd_sign else 6
    return _varga_longitude(longitude, 40, start_sign_index)


def _akshavedamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    if sign_index in [0, 3, 6, 9]:
        start_sign_index = 0
    elif sign_index in [1, 4, 7, 10]:
        start_sign_index = 4
    else:
        start_sign_index = 8
    return _varga_longitude(longitude, 45, start_sign_index)


def _shashtiamsa_longitude(longitude):
    sign_index = _sign_index(longitude)
    return _varga_longitude(longitude, 60, sign_index)


def _build_divisional_chart(asc_longitude, planets, longitude_func):
    asc_longitude = longitude_func(asc_longitude)
    asc_sign_index = _sign_index(asc_longitude)
    ascendant = _planet_row("Ascendant", "Asc", asc_longitude, 0, asc_sign_index)
    varga_planets = [
        _planet_row(planet["name"], planet["code"], longitude_func(planet["longitude"]), 0, asc_sign_index)
        for planet in planets
    ]
    houses = _build_houses(asc_sign_index, varga_planets)
    return {"houses": houses, "planets": [ascendant] + varga_planets}


def _build_houses(asc_sign_index, planets):
    houses = []
    for house_number in range(1, 13):
        sign_index = (asc_sign_index + house_number - 1) % 12
        occupants = [planet for planet in planets if planet["house"] == house_number]
        houses.append(
            {
                "number": house_number,
                "sign": SIGNS[sign_index],
                "sign_number": sign_index + 1,
                "position": HOUSE_POSITIONS[house_number],
                "occupants": occupants,
            }
        )
    return houses


def _assign_jaimini_karakas(planets):
    candidates = [planet for planet in planets if planet["code"] not in {"Ra", "Ke"}]
    ordered = sorted(candidates, key=lambda planet: planet["longitude"] % 30, reverse=True)
    for karaka, planet in zip(JAIMINI_KARAKAS, ordered):
        planet["jaimini_karaka"] = karaka
    for planet in planets:
        planet.setdefault("jaimini_karaka", "")
    return planets


def build_vedic_chart(name, birth_date, birth_time, birth_place, latitude, longitude, timezone):
    if latitude is None or longitude is None:
        return {
            "name": name,
            "birth_date": birth_date.isoformat(),
            "birth_time": birth_time.isoformat(),
            "birth_place": birth_place,
            "timezone": timezone,
            "system": "vedic_lahiri",
            "calculation_error": "Latitude and longitude are required for chart calculation.",
        }

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    utc_dt = _local_datetime_to_utc(birth_date, birth_time, timezone)
    jd_ut = swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600,
    )
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    _, ascmc = swe.houses_ex(jd_ut, float(latitude), float(longitude), b"P", swe.FLG_SIDEREAL)
    asc_longitude = ascmc[0] % 360
    asc_sign_index = _sign_index(asc_longitude)

    ascendant = _planet_row("Ascendant", "Asc", asc_longitude, 0, asc_sign_index)
    planets = []
    for planet_name, planet_code, planet_id in PLANETS:
        values, _ = swe.calc_ut(jd_ut, planet_id, flags)
        planets.append(_planet_row(planet_name, planet_code, values[0] % 360, values[3], asc_sign_index))

    rahu = next(planet for planet in planets if planet["code"] == "Ra")
    ketu_longitude = (rahu["longitude"] + 180) % 360
    planets.append(_planet_row("Ketu", "Ke", ketu_longitude, rahu.get("speed", 0), asc_sign_index))
    planets = _assign_jaimini_karakas(planets)

    houses = _build_houses(asc_sign_index, planets)
    d3 = _build_divisional_chart(asc_longitude, planets, _drekkana_longitude)
    d2 = _build_divisional_chart(asc_longitude, planets, _hora_longitude)
    d4 = _build_divisional_chart(asc_longitude, planets, _chaturthamsha_longitude)
    d7 = _build_divisional_chart(asc_longitude, planets, _saptamsa_longitude)
    d9 = _build_divisional_chart(asc_longitude, planets, _navamsha_longitude)
    d10 = _build_divisional_chart(asc_longitude, planets, _dasamsa_longitude)
    d12 = _build_divisional_chart(asc_longitude, planets, _dwadasamsa_longitude)
    d16 = _build_divisional_chart(asc_longitude, planets, _shodashamsa_longitude)
    d20 = _build_divisional_chart(asc_longitude, planets, _vimshamsa_longitude)
    d24 = _build_divisional_chart(asc_longitude, planets, _chaturvimshamsa_longitude)
    d27 = _build_divisional_chart(asc_longitude, planets, _saptavimshamsa_longitude)
    d30 = _build_divisional_chart(asc_longitude, planets, _trimsamsa_longitude)
    d40 = _build_divisional_chart(asc_longitude, planets, _khavedamsa_longitude)
    d45 = _build_divisional_chart(asc_longitude, planets, _akshavedamsa_longitude)
    d60 = _build_divisional_chart(asc_longitude, planets, _shashtiamsa_longitude)

    moon = next(planet for planet in planets if planet["code"] == "Mo")
    vimshottari = build_vimshottari_dasha(birth_date, moon["longitude"])

    chart_data = {
        "name": name,
        "birth_date": birth_date.isoformat(),
        "birth_time": birth_time.isoformat(),
        "birth_place": birth_place,
        "latitude": str(latitude),
        "longitude": str(longitude),
        "timezone": timezone,
        "system": "vedic_lahiri",
        "ayanamsa": "Lahiri",
        "chart_template": "north_indian_clear_sign_positions_v10_shodashvarga",
        "julian_day_ut": jd_ut,
        "ascendant": ascendant,
        "d1": {"houses": houses, "planets": [ascendant] + planets},
        "d2": d2,
        "d3": d3,
        "d4": d4,
        "d7": d7,
        "d9": d9,
        "d10": d10,
        "d12": d12,
        "d16": d16,
        "d20": d20,
        "d24": d24,
        "d27": d27,
        "d30": d30,
        "d40": d40,
        "d45": d45,
        "d60": d60,
        "ashtakavarga": build_ashtakavarga(ascendant, planets),
        "jaimini": {"chara_dasha": build_chara_dasha(birth_date, ascendant, planets)},
        "dashas": {"vimshottari": vimshottari},
    }
    chart_data["dashas"]["yogini"] = build_yogini_periods(chart_data)
    chart_data["yogas"] = detect_yogas(chart_data)
    return chart_data


def build_placeholder_chart(name, birth_date, birth_time, birth_place):
    return {
        "name": name,
        "birth_date": birth_date.isoformat(),
        "birth_time": birth_time.isoformat(),
        "birth_place": birth_place,
        "system": "vedic_lahiri_placeholder",
        "note": "Save this chart again with coordinates to calculate D1 and dashas.",
    }
