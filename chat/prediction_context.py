import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

from charts.jaimini_confirmation import build_jaimini_confirmation
from charts.remedies import remedies_for_dasha
from charts.transit_priority import build_transit_priority_context
from charts.vedic_utils import (
    PLANET_IDS, PLANET_NAMES, SIGN_NAMES,
    get_house_lord, get_house_lord_planet,
    get_planet, get_planet_dignity, get_planets, get_sarvashtakavarga_points,
    parse_iso_date, transit_context_for_lord,
)

CATEGORY_RULES = {
    "job": {
        "keywords": [
            "job",
            "work",
            "employment",
            "employed",
            "unemployed",
            "hire",
            "hired",
            "hiring",
            "interview",
            "resignation",
            "transfer",
            "fired",
            "layoff",
            "retrenchment",
            "job change",
            "job switch",
            "switch job",
            "change job",
            "find work",
            "get work",
            "find a job",
            "get a job",
            "joining",
            "onboarding",
        ],
        "houses": [6, 2, 10, 11],  # 6th-led: service/employment, then income, career context, gains
        "divisional_charts": ["d1", "d10"],
        "natural_karakas": ["Sa", "Me"],  # Saturn=service/labour, Mercury=profession/intellect
    },
    "career": {
        "keywords": [
            "career",
            "profession",
            "professional",
            "promotion",
            "promoted",
            "authority",
            "leadership",
            "income",
        ],
        "houses": [10, 2, 6, 11],  # 10th-led: karma/authority, then income, service context, gains
        "divisional_charts": ["d1", "d10"],
        "natural_karakas": ["Su", "Me", "Sa"],  # Sun=authority, Mercury=trade/profession, Saturn=service
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
        "natural_karakas": ["Ve", "Ju"],  # Venus=spouse/love, Jupiter=wisdom/partner
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
        "natural_karakas": ["Ju", "Ve"],  # Jupiter=wealth/abundance, Venus=luxury/comforts
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
        "natural_karakas": ["Su", "Ma"],  # Sun=vitality/constitution, Mars=energy/accidents
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
        "natural_karakas": ["Me", "Ju"],  # Mercury=intellect/learning, Jupiter=higher wisdom
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
        "natural_karakas": ["Ju"],  # Jupiter=primary karaka for children/progeny
    },
    "property": {
        "keywords": [
            "property",
            "home",
            "house",
            "land",
            "real estate",
            "vehicle",
            "buy",
            "purchase",
            "apartment",
            "flat",
            "plot",
            "comfort",
            "residence",
        ],
        "houses": [2, 4, 6, 9, 11, 12],  # 2=assets/savings, 4=home/property, 6=loan/EMI, 9=fortune, 11=gains, 12=foreign property
        "divisional_charts": ["d1", "d4", "d16"],
        "natural_karakas": ["Ma", "Mo", "Ve"],  # Mars=land/real estate, Moon=home/domestic comfort, Venus=vehicles/comforts
    },
    "family": {
        "keywords": [
            "family",
            "parents",
            "parent",
            "father",
            "mother",
            "sibling",
            "siblings",
            "brother",
            "sister",
            "lineage",
            "ancestry",
            "grandparents",
            "relationship with",
        ],
        "houses": [1, 3, 4, 9, 12],
        "divisional_charts": ["d1", "d3", "d12"],
        "natural_karakas": ["Mo", "Su"],  # Moon=mother/family, Sun=father/lineage
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
        "natural_karakas": ["Ra", "Sa"],  # Rahu=foreign/unfamiliar, Saturn=long-distance/hardship
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
        "natural_karakas": ["Sa", "Ma"],  # Saturn=litigation/enemies, Mars=conflicts/accidents
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
        "natural_karakas": ["Ju", "Ke"],  # Jupiter=dharma/wisdom, Ketu=moksha/liberation
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


def build_natural_karaka_assessment(chart_data: dict, category: str) -> dict:
    """
    Assess the strength and D1/primary-D-chart position of the natural significator
    (naisargika karaka) planets for this question category.
    Surfaces Mars for property, Venus/Jupiter for marriage, etc.
    """
    rules = CATEGORY_RULES.get(category, {})
    karaka_codes = rules.get("natural_karakas", [])
    if not karaka_codes:
        return {}

    div_charts = rules.get("divisional_charts", ["d1"])
    primary_d = div_charts[1] if len(div_charts) > 1 else "d1"
    category_houses = rules.get("houses", [])

    assessments = []
    for code in karaka_codes:
        d1_p = get_planet(chart_data, code, "d1")
        if not d1_p:
            continue
        house = d1_p.get("house")
        sign_num = d1_p.get("sign_number")
        dignity = get_planet_dignity(chart_data, code)
        sav = get_sarvashtakavarga_points(chart_data, house) if house else 0

        primary_d_house = None
        primary_d_sign = None
        if primary_d != "d1":
            d_p = get_planet(chart_data, code, primary_d)
            if d_p:
                primary_d_house = d_p.get("house")
                primary_d_sign = SIGN_NAMES.get(d_p.get("sign_number"))

        assessments.append({
            "planet": code,
            "planet_name": PLANET_NAMES.get(code, code),
            "d1_house": house,
            "d1_sign": SIGN_NAMES.get(sign_num) if sign_num else None,
            "dignity": dignity,
            "natal_house_sav": sav,
            "sav_strong": sav > 28,
            "in_category_house": house in category_houses,
            f"{primary_d}_house": primary_d_house,
            f"{primary_d}_sign": primary_d_sign,
        })

    return {
        "category": category,
        "primary_divisional_chart": primary_d.upper(),
        "natural_karakas": assessments,
        "note": (
            "Natural significators (naisargika karakas) for this category. "
            "Their dignity, house position, and SAV in both D1 and the primary divisional chart "
            "indicate how strongly the chart supports the topic."
        ),
    }


_KNOWN_LOCATIONS = {
    # South / Southeast Asia
    "india", "malaysia", "singapore", "indonesia", "thailand", "philippines",
    "vietnam", "myanmar", "bangladesh", "sri lanka", "nepal", "pakistan",
    # Middle East
    "uae", "dubai", "abu dhabi", "qatar", "bahrain", "kuwait", "oman",
    "saudi arabia", "saudi", "riyadh",
    # East Asia
    "china", "japan", "south korea", "korea", "hong kong", "taiwan",
    # Oceania
    "australia", "new zealand",
    # Europe
    "uk", "united kingdom", "england", "london", "germany", "france",
    "netherlands", "canada", "ireland", "switzerland",
    # Americas
    "usa", "united states", "america", "us", "new york", "california",
    "canada",
    # Generic homeland
    "hometown", "native place", "home country", "home town",
}

_DIGNITY_SCORE = {
    "exalted": 4,
    "own_sign": 3,
    "ordinary": 1,
    "debilitated": -2,
    "unknown": 0,
}

_GOOD_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
_BAD_HOUSES = {6, 8, 12}


def _score_house_axis(chart_data: dict, house_num: int) -> tuple[int, list[str]]:
    """Score the overall strength of a house axis (D1 lord + SAV + D4 lord)."""
    score = 0
    reasons = []

    lord_code = get_house_lord(chart_data, house_num)
    if not lord_code:
        return score, reasons

    # D1 lord dignity
    dignity = get_planet_dignity(chart_data, lord_code)
    d_score = _DIGNITY_SCORE.get(dignity, 0)
    score += d_score
    if d_score >= 3:
        reasons.append(f"{PLANET_NAMES.get(lord_code, lord_code)} ({house_num}th lord) is {dignity.replace('_', ' ')}")
    elif d_score < 0:
        reasons.append(f"{PLANET_NAMES.get(lord_code, lord_code)} ({house_num}th lord) is debilitated — weakened")

    # D1 lord placement quality
    lord_planet = get_house_lord_planet(chart_data, house_num, "d1")
    lord_house = lord_planet.get("house") if lord_planet else None
    if lord_house in _GOOD_HOUSES:
        score += 2
        reasons.append(f"{PLANET_NAMES.get(lord_code, lord_code)} placed in house {lord_house} (beneficial)")
    elif lord_house in _BAD_HOUSES:
        score -= 1
        reasons.append(f"{PLANET_NAMES.get(lord_code, lord_code)} placed in house {lord_house} (challenging)")

    # House SAV
    sav = get_sarvashtakavarga_points(chart_data, house_num)
    if sav > 28:
        score += 3
        reasons.append(f"House {house_num} SAV {sav} — strong delivery capacity")
    elif sav >= 25:
        score += 1
        reasons.append(f"House {house_num} SAV {sav} — moderate")
    elif sav > 0 and sav < 22:
        score -= 1
        reasons.append(f"House {house_num} SAV {sav} — below average")

    # D4 lord placement (same lord code, check in d4)
    d4_lord = get_house_lord_planet(chart_data, house_num, "d4")
    if d4_lord:
        d4_house = d4_lord.get("house")
        if d4_house in _GOOD_HOUSES:
            score += 2
            reasons.append(f"D4: {house_num}th lord in house {d4_house} — confirms {house_num}th house promise")
        elif d4_house in _BAD_HOUSES:
            score -= 1
            reasons.append(f"D4: {house_num}th lord in house {d4_house} — D4 weakens promise")

    return score, reasons


def _detect_two_locations(question: str) -> list[str]:
    """Return up to two location names found in the question text."""
    lowered = question.lower()
    found = []
    for loc in sorted(_KNOWN_LOCATIONS, key=len, reverse=True):
        if loc in lowered and loc not in found:
            found.append(loc)
            if len(found) == 2:
                break
    return found


def build_location_verdict(question: str, chart_data: dict, jaimini_data: dict | None = None) -> dict:
    """
    When a property question names two countries/cities, score 4th house (homeland)
    vs 12th house (foreign) axis strength and return an explicit location verdict.

    Returns {} if fewer than two locations are detected in the question.
    """
    locations = _detect_two_locations(question)
    if len(locations) < 2:
        return {}

    homeland_score, homeland_reasons = _score_house_axis(chart_data, 4)
    foreign_score, foreign_reasons = _score_house_axis(chart_data, 12)

    # Rahu pulls toward foreign, Ketu pulls toward homeland
    rahu = get_planet(chart_data, "Ra", "d1")
    ketu = get_planet(chart_data, "Ke", "d1")
    rahu_house = rahu.get("house") if rahu else None
    ketu_house = ketu.get("house") if ketu else None

    if rahu_house in {1, 9, 12}:
        foreign_score += 2
        foreign_reasons.append(f"Rahu in house {rahu_house} — strong foreign pull")
    elif rahu_house == 4:
        homeland_score -= 1
        foreign_score += 1
        foreign_reasons.append("Rahu in 4th — foreign element invades homeland house")

    if ketu_house == 12:
        homeland_score += 2
        homeland_reasons.append("Ketu in 12th — separating from foreign settlement, homeland favored")
    elif ketu_house == 4:
        foreign_score += 1
        homeland_score -= 1
        homeland_reasons.append("Ketu in 4th — some detachment from homeland anchor")

    # Jaimini active Chara dasha house confirmation
    if jaimini_data:
        active_chara = jaimini_data.get("active_chara_dasha", {})
        md_house = (active_chara.get("mahadasha") or {}).get("house_from_lagna")
        ad_house = (active_chara.get("antardasha") or {}).get("house_from_lagna")
        for h in (md_house, ad_house):
            if h == 4:
                homeland_score += 3
                homeland_reasons.append(f"Jaimini Chara Dasha active in 4th house sign — homeland strongly activated")
            elif h == 12:
                foreign_score += 3
                foreign_reasons.append(f"Jaimini Chara Dasha active in 12th house sign — foreign activation confirmed")
            elif h == 9:
                foreign_score += 1
                foreign_reasons.append(f"Jaimini Chara in 9th house — long-distance/fortune angle active")

    gap = homeland_score - foreign_score
    if gap >= 4:
        lean = "homeland"
        confidence = "strong"
    elif gap >= 2:
        lean = "homeland"
        confidence = "moderate"
    elif gap <= -4:
        lean = "foreign"
        confidence = "strong"
    elif gap <= -2:
        lean = "foreign"
        confidence = "moderate"
    else:
        lean = "balanced"
        confidence = "low"

    return {
        "detected_locations": locations,
        "homeland_score": homeland_score,
        "foreign_score": foreign_score,
        "verdict_lean": lean,
        "confidence": confidence,
        "homeland_reasons": homeland_reasons,
        "foreign_reasons": foreign_reasons,
        "note": (
            "4th house = homeland/native land. 12th house = foreign/abroad. "
            "Higher score indicates which axis the chart favors. "
            "LLM must give an explicit location probability lean using these scores."
        ),
    }


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
    # Lookback / retrospective phrases
    "look back", "looking back", "would have", "when did i", "when was i",
    "in the past", "past years", "years ago", "years back",
    "previously", "retrospect", "tell what time i would",
    "what time i would", "when would i have", "when i would have",
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

    # Past intent: detect "last N years" / "past N years" lookback patterns
    if intent == "past":
        lookback_match = re.search(r"\b(?:last|past)\s+(\d+)\s+years?\b", lowered)
        if lookback_match:
            n_years = int(lookback_match.group(1))
            start = date(target_date.year - n_years, target_date.month, 1)
            return _scope(
                f"last {n_years} years",
                start,
                target_date,
                n_years * 12,
                False,
                (
                    f"Retrospective question: scan {start.isoformat()} to {target_date.isoformat()}. "
                    "Use retrospective language — describe what the chart showed during those past periods. "
                    "Identify which dasha periods were active and what they indicated for the topic."
                ),
            )
        # Past intent without explicit year count → scan last 5 years
        start = _add_months(target_date, -60)
        return _scope(
            "past_5_years",
            start,
            target_date,
            60,
            False,
            (
                f"Retrospective question: scan {start.isoformat()} to {target_date.isoformat()}. "
                "Use retrospective language — describe what the chart showed in those past periods."
            ),
        )

    # General intent: delegate to existing relative/year detection
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
