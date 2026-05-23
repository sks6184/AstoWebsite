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
            "married",
            "marry",
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
    "property": {
        "keywords": [
            "property",
            "home",
            "house",
            "land",
            "real estate",
            "vehicle",
            "comfort",
            "residence",
        ],
        "houses": [4, 9, 11, 12],
        "divisional_charts": ["d1", "d4", "d16"],
    },
    "family": {
        "keywords": [
            "family",
            "parents",
            "father",
            "mother",
            "lineage",
            "ancestry",
            "grandparents",
        ],
        "houses": [1, 4, 9, 12],
        "divisional_charts": ["d1", "d12"],
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
            # Return / repatriation keywords
            "return to",
            "return back",
            "return home",
            "go back",
            "go home",
            "move back",
            "move home",
            "come back",
            "coming back",
            "back to india",
            "back to home",
            "back to my country",
            "homeland",
            "hometown",
            "native place",
            "native country",
            "native land",
            "repatriate",
            "repatriation",
            "permanently settle",
            "permanent return",
            "permanent settlement",
            "forever",
            "for good",
            "settle back",
            "shift back",
        ],
        "houses": [3, 4, 7, 9, 12],
        "divisional_charts": ["d1", "d4", "d9"],
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


# Phrases that unambiguously signal foreign_travel/relocation regardless of which
# other category keyword fires first (e.g. "work" → career, "home" → property).
_FOREIGN_TRAVEL_OVERRIDES = frozenset({
    "return to", "return back", "return home",
    "returning to", "returning back", "returning home",
    "go back to", "go home to",
    "move back", "move home", "come back to", "coming back to",
    "back to india", "back to my country", "back to home country",
    "native place", "native country", "native land",
    "homeland", "hometown",
    "repatriate", "repatriation",
    "settle back", "shift back",
    "permanent return", "permanently return", "return permanently",
    "forever in india", "forever back", "return for good",
    "go back for good", "move back for good",
})


def classify_question(question):
    lowered = question.lower()
    # Foreign travel / relocation phrases take priority — they overlap with career
    # ("working abroad") and property ("home") keywords that would otherwise win.
    if any(phrase in lowered for phrase in _FOREIGN_TRAVEL_OVERRIDES):
        return "foreign_travel"
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


# ── Temporal intent classification ───────────────────────────────────────────

_FUTURE_INTENT_PHRASES = frozenset({
    "will i", "when will", "can i", "should i", "when should",
    "is there a chance", "any chance", "chances of", "chance of",
    "do you see", "do u see", "any possibility", "possibility of",
    "when would", "will there be", "when can", "what are my chances",
    "will ever", "will i ever", "is it possible", "could i", "would i",
    "is there hope", "any hope", "shall i", "when shall",
    "will i get", "will i be", "will i return", "will i come back",
    "ever return", "ever come back", "ever move", "any scope",
})

_PAST_INTENT_PHRASES = frozenset({
    "why did", "what happened in", "why was i", "how was my",
    "why i lost", "what went wrong", "why did i fail", "was my",
    "what was my", "how did i", "what caused", "why did i",
    "how was that", "was that period", "was it good",
})


def _temporal_intent(question: str) -> str:
    """Return 'future', 'past', or 'general' based on question phrasing."""
    lowered = question.lower()
    if any(phrase in lowered for phrase in _FUTURE_INTENT_PHRASES):
        return "future"
    if any(phrase in lowered for phrase in _PAST_INTENT_PHRASES):
        return "past"
    return "general"


def detect_question_scope(question: str, target_date: date | None = None) -> dict:
    """
    Detect whether the user has pinned a specific period or wants a forward scan.

    Returns a dict with: start, end, months, phrase, instruction, is_fixed, temporal_intent.
    is_fixed=True  → user named a specific period; analyse only that window.
    is_fixed=False → user wants the best window found within [start, end].

    Temporal intent is classified FIRST so that past reference years ("since 2014",
    "working there from 2018") are not mistaken for target dates when the question
    is clearly future-oriented ("any chance of returning?").
    """
    from calendar import monthrange

    target_date = target_date or date.today()
    lowered = question.lower()
    intent = _temporal_intent(question)

    def _scope(phrase, start, end, months, is_fixed, instruction):
        return {
            "phrase": phrase,
            "start": start,
            "end": end,
            "months": months,
            "is_fixed": is_fixed,
            "temporal_intent": intent,
            "instruction": instruction,
        }

    # Present-tense anchor always wins regardless of intent
    if any(term in lowered for term in {"now", "currently", "today", "right now", "at present", "these days"}):
        end = _add_months(target_date, 3)
        return _scope("now", target_date, end, 3, True,
                      f"Analyse only the current period: {target_date.isoformat()} to {end.isoformat()}.")

    # Month + year: "June 2025", "Sep 2014", etc.
    month_year = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
        r"|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+(20\d{2})\b",
        lowered,
    )
    if month_year:
        _abbr_to_num = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month_num = _abbr_to_num.get(month_year.group(1)[:3])
        year_num = int(month_year.group(2))
        # Future-intent questions must not anchor on past month/year references
        if month_num and (intent != "future" or year_num >= target_date.year):
            last_day = monthrange(year_num, month_num)[1]
            start = date(year_num, month_num, 1)
            end = date(year_num, month_num, last_day)
            phrase = f"{month_year.group(1).capitalize()} {year_num}"
            return _scope(phrase, start, end, None, True,
                          f"Analyse only {phrase}: {start.isoformat()} to {end.isoformat()}.")

    # Future-intent: handle relative phrases, then future-year only, then default forward scan.
    # Never anchor on a past year — "Since 2014", "from 2018", etc. are background context.
    if intent == "future":
        if "next year" in lowered:
            year = target_date.year + 1
            return _scope("next year", date(year, 1, 1), date(year, 12, 31), None, True,
                          f"Only consider next calendar year: 01-Jan-{year} to 31-Dec-{year}.")
        if "this year" in lowered or "current year" in lowered:
            return _scope("this year", target_date, date(target_date.year, 12, 31), None, True,
                          f"Only consider the remaining current year: {target_date.isoformat()} to {target_date.year}-12-31.")
        if "next 12 months" in lowered or "coming 12 months" in lowered:
            end = _add_months(target_date, 12)
            return _scope("next 12 months", target_date, end, 12, False,
                          "Only consider the next 12 months from current_date.")
        if "this month" in lowered or "current month" in lowered:
            end = date(target_date.year, target_date.month, 28)
            return _scope("this month", target_date, end, None, True,
                          "Only consider the current calendar month.")
        # Accept only future year references; ignore past years (context years)
        for m in re.finditer(r"\b(20\d{2})\b", lowered):
            year = int(m.group(1))
            if year >= target_date.year:
                return _scope(str(year), date(year, 1, 1), date(year, 12, 31), None, True,
                              f"Only consider {year}: 01-Jan-{year} to 31-Dec-{year}.")
        # No specific future date found — scan 5 years forward
        end = _add_months(target_date, 60)
        return _scope("default_next_5_years", target_date, end, 60, False,
                      "Future question with no specific target date; scan the next 5 years.")

    # Past or general intent: delegate to existing relative/year detection
    scope = _time_scope(question, target_date)
    scope["is_fixed"] = not scope.get("is_default", True)
    scope["temporal_intent"] = intent
    return scope


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
