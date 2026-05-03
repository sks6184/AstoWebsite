from datetime import datetime
from zoneinfo import ZoneInfo

import swisseph as swe
from django.utils import timezone


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

CATEGORY_RULES = {
    "career": {
        "keywords": [
            "job",
            "career",
            "profession",
            "work",
            "promotion",
            "business",
            "income",
            "transfer",
            "resignation",
            "startup",
            "client",
            "contract",
            "website",
            "launch",
            "launching",
            "venture",
            "entrepreneur",
        ],
        "houses": [2, 6, 7, 10, 11],
        "divisional_charts": ["d1", "d10"],
    },
    "marriage": {
        "keywords": [
            "marriage",
            "spouse",
            "relationship",
            "partner",
            "love",
            "wedding",
            "engagement",
            "divorce",
            "separation",
        ],
        "houses": [2, 7, 8, 11],
        "divisional_charts": ["d1", "d9"],
    },
    "money": {
        "keywords": [
            "money",
            "wealth",
            "finance",
            "salary",
            "income",
            "debt",
            "loan",
            "investment",
            "inheritance",
            "profit",
            "loss",
        ],
        "houses": [2, 6, 8, 9, 11],
        "divisional_charts": ["d1", "d2"],
    },
    "health": {
        "keywords": [
            "health",
            "disease",
            "illness",
            "recovery",
            "hospital",
            "hospitalised",
            "hospitalized",
            "surgery",
            "accident",
            "medical",
            "sick",
            "injury",
        ],
        "houses": [1, 6, 8, 12],
        "divisional_charts": ["d1", "d30"],
    },
    "education": {
        "keywords": [
            "education",
            "study",
            "college",
            "exam",
            "selection",
            "academic",
            "university",
            "school",
            "test",
            "higher studies",
        ],
        "houses": [4, 5, 9, 11],
        "divisional_charts": ["d1", "d24"],
    },
    "children": {
        "keywords": [
            "child",
            "children",
            "pregnancy",
            "baby",
            "son",
            "daughter",
            "childbirth",
            "conception",
            "offspring",
            "fertility",
        ],
        "houses": [2, 5, 9, 11],
        "divisional_charts": ["d1", "d7"],
    },
    "foreign_travel": {
        "keywords": [
            "foreign",
            "visa",
            "abroad",
            "travel",
            "settlement",
            "immigration",
            "relocation",
            "overseas",
            "citizenship",
        ],
        "houses": [3, 7, 9, 12],
        "divisional_charts": ["d1"],
    },
    "legal_and_enemies": {
        "keywords": [
            "court",
            "case",
            "legal",
            "lawsuit",
            "dispute",
            "litigation",
            "enemy",
            "police",
            "jail",
        ],
        "houses": [6, 8, 12],
        "divisional_charts": ["d1", "d30"],
    },
    "spirituality": {
        "keywords": [
            "spiritual",
            "meditation",
            "moksha",
            "occult",
            "enlightenment",
            "guru",
            "sadhana",
            "astrology",
        ],
        "houses": [4, 8, 9, 12],
        "divisional_charts": ["d1", "d9", "d20"],
    },
}


def classify_question(question):
    lowered = question.lower()
    for category, rules in CATEGORY_RULES.items():
        if any(keyword in lowered for keyword in rules["keywords"]):
            return category
    return "general"


def _parse_date(value):
    return datetime.fromisoformat(value).date()


def _current_period(periods, target_date):
    for period in periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start <= target_date <= end:
            return period
    return periods[0] if periods else {}


def _current_chara_context(chart_data, target_date):
    chara = chart_data.get("jaimini", {}).get("chara_dasha", {})
    major = _current_period(chara.get("periods", []), target_date)
    subperiod = _current_period(major.get("subperiods", []), target_date)
    return {
        "system": chara.get("system"),
        "order_direction": chara.get("order_direction"),
        "mahadasha": major,
        "antardasha": subperiod,
    }


def _planet_by_code(chart_data, code):
    for planet in chart_data.get("d1", {}).get("planets", []):
        if planet.get("code") == code:
            return planet
    return {}


def _owned_houses(chart_data, planet_code):
    asc_sign_number = chart_data.get("ascendant", {}).get("sign_number")
    if not asc_sign_number:
        return []
    return [
        ((sign_number - asc_sign_number) % 12) + 1
        for sign_number, owner_code in SIGN_LORDS.items()
        if owner_code == planet_code
    ]


def _transit_longitude(planet_code, target_dt):
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


def _transit_context_for_lord(chart_data, planet_code, target_dt):
    longitude = _transit_longitude(planet_code, target_dt)
    sign_number = int(longitude // 30) + 1
    asc_sign_number = chart_data.get("ascendant", {}).get("sign_number", 1)
    house = ((sign_number - asc_sign_number) % 12) + 1
    sav = 0
    for row in chart_data.get("ashtakavarga", {}).get("rows", []):
        if row.get("house") == house:
            sav = row.get("sarva", 0)
            break
    natal_planet = _planet_by_code(chart_data, planet_code)
    return {
        "lord": planet_code,
        "lord_name": PLANET_NAMES.get(planet_code, planet_code),
        "transit_sign_number": sign_number,
        "transit_house_from_lagna": house,
        "sarvashtakavarga_points": sav,
        "ashtakavarga_threshold": 28,
        "can_deliver_owned_or_placed_house_results": sav > 28,
        "natal_placed_house": natal_planet.get("house"),
        "owned_houses": _owned_houses(chart_data, planet_code),
    }


def _compact_chart_context(chart_data, category):
    houses = CATEGORY_RULES.get(category, {}).get("houses", [])
    planets = chart_data.get("d1", {}).get("planets", [])
    requested_divisional_charts = CATEGORY_RULES.get(category, {}).get("divisional_charts", ["d1"])
    relevant_planets = [
        {
            "code": planet.get("code"),
            "name": planet.get("name"),
            "house": planet.get("house"),
            "sign": planet.get("sign"),
            "sign_lord": planet.get("sign_lord"),
            "nakshatra": planet.get("nakshatra"),
            "nakshatra_lord": planet.get("nakshatra_lord"),
            "jaimini_karaka": planet.get("jaimini_karaka"),
        }
        for planet in planets
        if planet.get("house") in houses or category == "general"
    ]
    return {
        "system": chart_data.get("system"),
        "ayanamsa": chart_data.get("ayanamsa"),
        "ascendant": chart_data.get("ascendant"),
        "category_houses": houses,
        "relevant_planets": relevant_planets[:12],
        "requested_divisional_charts": requested_divisional_charts,
        "divisional_chart_summaries": {
            chart_key: {
                "ascendant": (chart_data.get(chart_key, {}).get("planets") or [{}])[0],
                "relevant_planets": [
                    {
                        "code": planet.get("code"),
                        "name": planet.get("name"),
                        "house": planet.get("house"),
                        "sign": planet.get("sign"),
                        "sign_lord": planet.get("sign_lord"),
                    }
                    for planet in chart_data.get(chart_key, {}).get("planets", [])[1:]
                    if planet.get("house") in houses or category == "general"
                ][:12],
            }
            for chart_key in requested_divisional_charts
            if chart_key in chart_data
        },
    }


def build_prediction_context(question, chart_data, target_date=None):
    from .timing_windows import build_timing_windows

    target_date = target_date or timezone.localdate()
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
    category = classify_question(question)
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    mahadasha = _current_period(vimshottari.get("periods", []), target_date)
    antardasha = _current_period(mahadasha.get("antardashas", []), target_date)

    dasha_lords = [lord for lord in [mahadasha.get("lord"), antardasha.get("lord")] if lord]
    transit_lords = [
        _transit_context_for_lord(chart_data, lord, target_dt)
        for lord in dict.fromkeys(dasha_lords)
        if lord in PLANET_IDS or lord == "Ke"
    ]
    timing_windows = build_timing_windows(question, chart_data, category, target_date)

    return {
        "question": question,
        "category": category,
        "calculation_policy": {
            "source_of_truth": "django_swiss_ephemeris_engine",
            "gpt_must_not_recalculate": True,
            "gpt_role": "rag_interpretation_only",
        },
        "temporal_policy": {
            "current_date": target_date.isoformat(),
            "past_periods_are_context_only": True,
            "answer_should_separate_past_current_future": True,
            "never_call_dates_before_current_date_upcoming": True,
            "future_timing_source": "candidate_timing_windows",
        },
        "algorithm": {
            "source": "Algo.docx",
            "steps": [
                "Use locally calculated D1/D9/D10, nakshatras, dashas, and ashtakavarga.",
                "Find current Mahadasha and Antardasha.",
                "Calculate current and monthly future transits of Mahadasha lord and Antardasha lord.",
                "Check Sarvashtakavarga points in the houses those lords transit.",
                "If points are greater than 28, the lord can deliver results of owned and placed houses.",
                "Treat dates before current_date as past context, not prediction.",
            ],
        },
        "dasha": {"mahadasha": mahadasha, "antardasha": antardasha},
        "jaimini_cross_check": _current_chara_context(chart_data, target_date),
        "transit_lords": transit_lords,
        "candidate_timing_windows": timing_windows,
        "chart_summary": _compact_chart_context(chart_data, category),
    }
