import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

from charts.jaimini_confirmation import build_jaimini_confirmation
from charts.remedies import remedies_for_dasha
from charts.transit_priority import build_transit_priority_context
from charts.vedic_utils import PLANET_IDS, get_planets, parse_iso_date, transit_context_for_lord

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
            "stay",
            "stay here",
            "long time",
            "settle",
            "settlement",
            "immigration",
            "migration",
            "migrate",
            "relocation",
            "move abroad",
            "move overseas",
            "overseas",
            "residence",
            "resident",
            "permanent resident",
            "permanent residency",
            "work permit",
            "citizenship",
            "country",
        ],
        "houses": [3, 4, 7, 9, 10, 12],
        "divisional_charts": ["d1", "d4", "d9", "d10"],
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


def _answer_contract(question, category):
    lowered = question.lower().strip()
    binary_markers = [
        "will ",
        "can ",
        "should ",
        "would ",
        "is ",
        "are ",
        "am ",
        "do ",
        "does ",
        "did ",
        "possible",
        "yes or no",
        "?",
    ]
    direct_answer_required = any(marker in f" {lowered}" for marker in binary_markers)
    return {
        "category": category,
        "direct_answer_required": direct_answer_required,
        "binary_answer_options": [
            "Likely yes",
            "Likely no",
            "Mixed, leaning yes",
            "Mixed, leaning no",
        ],
        "confidence_options": ["High", "Medium", "Low"],
        "visible_answer_style": "natural_question_aware_prose",
        "avoid_visible_headings": ["Short Answer", "Confidence", "Astrological Reason"],
        "allowed_supporting_headings": ["Timing", "Why this is indicated", "Remedy", "Practical guidance"],
        "instruction": (
            "Start with a natural sentence that reuses the user's subject and gives the outcome probability. "
            "For yes/no or stay/move/job/marriage questions, choose one binary_answer_option internally, "
            "but do not print the option as a label. Convert it into human wording such as "
            "'Your stay in the foreign country is likely to continue, though...' "
            "Do not use AI-looking headings like Short Answer or Confidence."
        ),
    }


def _prediction_horizon(question):
    lowered = question.lower()
    if any(marker in lowered for marker in ["weekly", "this week", "next week", "7 days", "next 7 days"]):
        return "weekly"
    return "monthly"


def _add_months(value, months):
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, 28)
    return value.replace(year=year, month=month, day=day)


def _time_scope(question, target_date):
    lowered = question.lower()
    explicit_year = re.search(r"\b(20\d{2})\b", lowered)
    if explicit_year:
        year = int(explicit_year.group(1))
        return {
            "phrase": explicit_year.group(1),
            "start": date(year, 1, 1),
            "end": date(year, 12, 31),
            "months": None,
            "is_default": False,
            "instruction": f"Only consider dates from 01-Jan-{year} to 31-Dec-{year}.",
        }
    if "this year" in lowered or "current year" in lowered:
        return {
            "phrase": "this year",
            "start": target_date,
            "end": date(target_date.year, 12, 31),
            "months": None,
            "is_default": False,
            "instruction": f"Only consider the remaining current year: {target_date.isoformat()} to {target_date.year}-12-31.",
        }
    if "next year" in lowered:
        year = target_date.year + 1
        return {
            "phrase": "next year",
            "start": date(year, 1, 1),
            "end": date(year, 12, 31),
            "months": None,
            "is_default": False,
            "instruction": f"Only consider next calendar year: 01-Jan-{year} to 31-Dec-{year}.",
        }
    if "next 12 months" in lowered or "coming 12 months" in lowered:
        return {
            "phrase": "next 12 months",
            "start": target_date,
            "end": _add_months(target_date, 12),
            "months": 12,
            "is_default": False,
            "instruction": "Only consider the next 12 months from current_date.",
        }
    if "this month" in lowered or "current month" in lowered:
        return {
            "phrase": "this month",
            "start": target_date,
            "end": date(target_date.year, target_date.month, 28),
            "months": None,
            "is_default": False,
            "instruction": "Only consider the current calendar month.",
        }
    return {
        "phrase": "default_next_5_years",
        "start": target_date,
        "end": _add_months(target_date, 60),
        "months": 60,
        "is_default": True,
        "instruction": "No explicit time phrase was found; scan the next 5 years using dasha, transit, and Jaimini confirmation.",
    }


def _parse_date(value):
    return parse_iso_date(value)


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


def _transit_context_for_lord(chart_data, planet_code, target_dt):
    return transit_context_for_lord(chart_data, planet_code, target_dt)


def _compact_chart_context(chart_data, category):
    houses = CATEGORY_RULES.get(category, {}).get("houses", [])
    planets = get_planets(chart_data, "d1", include_ascendant=True)
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


def build_prediction_context(question, chart_data, target_date=None, answer_language="English"):
    from .timing_windows import build_timing_windows

    target_date = target_date or timezone.localdate()
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
    category = classify_question(question)
    horizon = _prediction_horizon(question)
    time_scope = _time_scope(question, target_date)
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    mahadasha = _current_period(vimshottari.get("periods", []), target_date)
    antardasha = _current_period(mahadasha.get("antardashas", []), target_date)

    dasha_lords = [lord for lord in [mahadasha.get("lord"), antardasha.get("lord")] if lord]
    transit_lords = [
        _transit_context_for_lord(chart_data, lord, target_dt)
        for lord in dict.fromkeys(dasha_lords)
        if lord in PLANET_IDS or lord == "Ke"
    ]
    timing_windows = build_timing_windows(
        question,
        chart_data,
        category,
        time_scope["start"],
        months=time_scope.get("months") or 60,
        end_date=time_scope["end"],
    )
    for window in timing_windows:
        active_dasha = window.get("active_dasha", {})
        window["remedies"] = remedies_for_dasha(
            active_dasha.get("mahadasha") or window.get("mahadasha_lord"),
            active_dasha.get("antardasha") or window.get("antardasha_lord"),
            answer_language,
        )

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
            "prediction_horizon": horizon,
            "time_scope": {
                "phrase": time_scope["phrase"],
                "start": time_scope["start"].isoformat(),
                "end": time_scope["end"].isoformat(),
                "is_default": time_scope["is_default"],
                "instruction": time_scope["instruction"],
            },
            "past_periods_are_context_only": True,
            "answer_should_separate_past_current_future": True,
            "never_call_dates_before_current_date_upcoming": True,
            "future_timing_source": "candidate_timing_windows",
        },
        "answer_contract": _answer_contract(question, category),
        "algorithm": {
            "source": "Algo.docx",
            "steps": [
                "Use locally calculated D1 and relevant varga charts, nakshatras, dashas, and ashtakavarga.",
                "Find current Mahadasha and Antardasha.",
                "Calculate transit priority deterministically from Python before LLM interpretation.",
                "For weekly questions, include Moon plus Sun, Mercury, Venus, Mars, Jupiter, Saturn, Rahu, and Ketu.",
                "For monthly questions, exclude Moon and use other planets with Dasha/Antardasha lord priority.",
                "Check Sarvashtakavarga points in the houses those planets transit.",
                "If points are greater than 28, the lord can deliver results of owned and placed houses.",
                "If points are low, treat the transit as frictional or requiring care.",
                "Treat dates before current_date as past context, not prediction.",
            ],
        },
        "dasha": {"mahadasha": mahadasha, "antardasha": antardasha},
        "current_remedies": remedies_for_dasha(mahadasha.get("lord"), antardasha.get("lord"), answer_language),
        "jaimini_cross_check": _current_chara_context(chart_data, target_date),
        "jaimini_confirmation": build_jaimini_confirmation(
            chart_data,
            category,
            CATEGORY_RULES.get(category, {}).get("houses", []),
            target_date,
        ),
        "transit_lords": transit_lords,
        "transit_priority": build_transit_priority_context(
            chart_data,
            CATEGORY_RULES.get(category, {}).get("houses", []),
            target_date,
            mahadasha_lord=mahadasha.get("lord"),
            antardasha_lord=antardasha.get("lord"),
            horizon=horizon,
        ),
        "candidate_timing_windows": timing_windows,
        "chart_summary": _compact_chart_context(chart_data, category),
    }
