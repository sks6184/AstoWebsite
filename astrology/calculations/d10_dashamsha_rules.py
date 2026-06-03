"""D10-specific rules from the Dashamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Dashamsha D10 (pp. 157–169).

SET 1 (Dashamsha Deity — career nature from D1 Lagna/10th lord dashamsha):
  D10-S1-LAGNA-DEITY-{name}        D1 Lagna in deity's dashamsha — basic career nature
  D10-S1-10TH-LORD-DEITY-{name}    D1 10th lord in deity's dashamsha — career approach

SET 2 (Core Examination Pillars):
  D10-S2-D1-LL-STRONG-IN-D10       D1 Lagna lord strong/angle in D10 — dedicated, right path
  D10-S2-D1-LL-WEAK-IN-D10         D1 Lagna lord weak/dusthana in D10 — no growth
  D10-S2-D1-10L-STRONG-IN-D10      D1 10th lord strong in D10 — smooth career
  D10-S2-D10-LAGNA-STRONG          Benefic in/aspecting D10 Lagna — career foundation solid
  D10-S2-D10-LAGNA-WEAK            Malefic(s) only in/aspecting D10 Lagna — career instability
  D10-S2-10TH-6-8-12               D10 10th lord related to 6/8/12 — sudden career changes
  D10-S2-SUN-ANGLE                 Sun in angle D10 — high-status government/authority career
  D10-S2-SUN-DUSTHANA              Sun in 6/8/12 D10 — problems from govt, indecisive
  D10-S2-SATURN-STRONG             Saturn well-placed D10 — subordinate support, political/mining
  D10-S2-SATURN-WEAK               Saturn badly placed/malefic D10 — problems from subordinates
  D10-S2-MOON-10TH-STRONG          Moon + 10th from Moon well-placed — zeal and jest for work
  D10-S2-MOON-10TH-WEAK            Moon + 10th from Moon weak — inferiority complex at work

SET 3 (Dasha Timing Signatures — structural planet house triggers):
  D10-S3-3RD-HOUSE-PLANETS         Planets in 3rd D10 → their dasha = retirement trigger
  D10-S3-AFFLICTED-3RD-5TH        Lagna+10th afflicted + planet in 3rd/5th → 3rd/5th dasha = career crisis
  D10-S3-6TH-TRANSFER              Planet in 6th D10 → its dasha = welcome transfer
  D10-S3-8TH-FORCED-TRANSFER       Planet in 8th D10 → its dasha = forced/unwanted transfer
  D10-S3-12TH-ROUTINE-CHANGE       Planet in 12th D10 → its dasha = routine job change
  D10-S3-RAHU-LAGNA                Rahu in D10 Lagna — many career ups and downs

SET 4 (10th Lord in Houses 6–12 — houses 1–5 are in divisional_rules.yaml):
  D10-S4-10TH-LORD-6TH             10th lord in 6th — service/servitude, luck-dependent
  D10-S4-10TH-LORD-7TH             10th lord in 7th — strong business/partnership career
  D10-S4-10TH-LORD-8TH             10th lord in 8th — challenges, uncertain career
  D10-S4-10TH-LORD-9TH             10th lord in 9th — Rajyoga, high position by luck
  D10-S4-10TH-LORD-10TH            10th lord in 10th — distinction, honour, fame
  D10-S4-10TH-LORD-11TH            10th lord in 11th — fortunate, multiple professions
  D10-S4-10TH-LORD-12TH            10th lord in 12th — foreign/hospital/jail-related career

SET 5 (Planet Placement Strength in D10):
  D10-S5-ANGLE-BEST                10th house strongest, then 7th, 4th, 1st for career results
  D10-S5-TRINE-OBSTACLE            5th/9th house planets — 8th/12th from 10th, career obstacle
  D10-S5-TRIK-CONNECTED-RELIEF     Trik planet linked to Lagna/10th lord — initial struggle then relief
  D10-S5-DEBILITATED-LATE-RISE     Debilitated planet(s) in D10 — humble start but rise later
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Dashamsha D10"
_SOURCE_PAGE = "157"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
UPACHAYA = frozenset({3, 6, 10, 11})
BENEFICS = frozenset({"Ju", "Ve", "Mo", "Me"})
MALEFICS = frozenset({"Su", "Ma", "Sa", "Ra", "Ke"})

# Deity number → (name, direction, ruling_planet, career_theme)
# Ruling planet is "4th_lord" / "10th_lord" for Brahma/Ananta (dynamic per chart)
_DEITY_INFO: dict[int, tuple[str, str, str, str]] = {
    1: ("Indra",   "East",       "Su", "government, authority, administration, head of department"),
    2: ("Agni",    "South East", "Ve", "fire-related professions, police, army, energy, prosperity"),
    3: ("Yama",    "South",      "Ma", "law, judiciary, bureaucracy, administration, engineering"),
    4: ("Rakshash","South West", "Ra", "mystery work, dealing with law-breakers, instinct-driven professions"),
    5: ("Varun",   "West",       "Sa", "water/shipping/fishery/medicine, foreign travel, depth of thought"),
    6: ("Vayu",    "North West", "Mo", "writing, teaching, thinking, intelligent changeable professions"),
    7: ("Kubera",  "North",      "Me", "finance, tax, chartered accounting, money-making intelligence"),
    8: ("Ishan",   "North East", "Ju", "priesthood, consultancy, teaching, banking, self-realised work"),
    9: ("Brahma",  "Downward",   "4th_lord", "wisdom, foundational creativity, inner contentment"),
    10: ("Ananta", "Upward",     "10th_lord", "worldwide fame, Vishnu-like far-reaching influence"),
}


def _pname(code: str) -> str:
    return PLANET_NAMES.get(code, code)


def _rule(
    rule_id: str,
    reason: str,
    interpretation: str,
    polarity: str,
    weight: int,
    outcomes: dict[str, Any],
    confidence: str = "medium",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "system": "D10/DashamshRules",
        "chart": "D10",
        "dasha": "",
        "category": "general",
        "reason": reason,
        "match_reasons": [reason],
        "interpretation": interpretation,
        "outcomes": outcomes,
        "weight": weight,
        "polarity": polarity,
        "confidence": confidence,
        "source_book": _SOURCE_BOOK,
        "source_chapter": _SOURCE_CHAPTER,
        "source_page": _SOURCE_PAGE,
        "source_file": "d10_dashamsha_rules.py",
    }


def _get_d10_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d10", {})


def _get_d1_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d1", {})


def _build_lord_maps(chart: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    all_pl = chart.get("all_lord_placements", {})
    h2l: dict[int, str] = {}
    l2p: dict[str, int] = {}
    for h in range(1, 13):
        pl = all_pl.get(f"{h}_lord", {})
        lord = pl.get("lord")
        placed = pl.get("placed_house")
        if lord:
            h2l[h] = lord
            if placed:
                l2p[lord] = placed
    return h2l, l2p


def _planets_in_house(chart: dict[str, Any], house: int) -> list[str]:
    return [p["code"] for p in chart.get("planets", []) if p.get("house") == house and p.get("code")]


def _deity_number(sign_number: int, degree: float) -> int:
    """Compute dashamsha deity number (1–10) from sign number and degree within sign."""
    part = min(int(degree / 3), 9) + 1  # 1–10
    if sign_number % 2 == 1:  # odd sign → direct order
        return part
    else:                       # even sign → reversed order
        return 11 - part


# ── Set 1: Dashamsha Deity System ────────────────────────────────────────────

def _d10_s1_deity(d10_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Compute deity from D1 Lagna and D1 10th lord degree — reveals career nature and approach."""
    if not d1_chart:
        return []

    triggered = []
    h2l_d10, _ = _build_lord_maps(d10_chart)
    h2l_d1, _ = _build_lord_maps(d1_chart)

    def _deity_rule(planet_data: dict, role: str, rule_prefix: str) -> dict | None:
        sign_num = planet_data.get("sign_number")
        degree = planet_data.get("degree")
        if sign_num is None or degree is None:
            return None
        try:
            deity_num = _deity_number(int(sign_num), float(degree))
        except (ValueError, TypeError):
            return None

        name, direction, ruling_planet_key, career_theme = _DEITY_INFO[deity_num]
        rule_id = f"{rule_prefix}-{name.upper()}"

        if ruling_planet_key == "4th_lord":
            ruling_planet = h2l_d10.get(4)
            rp_label = f"{_pname(ruling_planet)} (4th lord of D10)" if ruling_planet else "4th lord of D10"
        elif ruling_planet_key == "10th_lord":
            ruling_planet = h2l_d10.get(10)
            rp_label = f"{_pname(ruling_planet)} (10th lord of D10)" if ruling_planet else "10th lord of D10"
        else:
            ruling_planet = ruling_planet_key
            rp_label = _pname(ruling_planet)

        interp = (
            f"The {role} falls in the {name} dashamsha ({direction} direction). "
            f"{name} governs: {career_theme}. "
            f"The ruling planet {rp_label} should be well placed in D10 to fulfil this career potential. "
            f"The lord of the ruling direction embodies the professional archetype — "
            f"its D10 strength or weakness directly colours the quality of the native's work life."
        )
        return _rule(
            rule_id,
            f"{role} in {name} dashamsha ({direction}) — career theme: {career_theme}",
            interp,
            "neutral", 3,
            {"overall": 2, "career": 3},
            confidence="high",
        )

    # D1 Lagna deity
    d1_lagna = d1_chart.get("lagna", {})
    if d1_lagna:
        r = _deity_rule(d1_lagna, "D1 Lagna", "D10-S1-LAGNA-DEITY")
        if r:
            triggered.append(r)

    # D1 10th lord deity
    lord_10_d1 = h2l_d1.get(10)
    if lord_10_d1:
        d1_10l_data = d1_chart.get("planet_lookup", {}).get(lord_10_d1, {})
        if d1_10l_data:
            r = _deity_rule(d1_10l_data, f"D1 10th lord {_pname(lord_10_d1)}", "D10-S1-10TH-LORD-DEITY")
            if r:
                triggered.append(r)

    return triggered


# ── Set 2: Core Examination Pillars ──────────────────────────────────────────

def _d10_s2_core_pillars(d10_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """D1 Lagna lord and 10th lord in D10, D10 Lagna quality, Sun, Saturn, Moon."""
    triggered = []
    h2l_d1, _ = _build_lord_maps(d1_chart)
    h2l_d10, l2p_d10 = _build_lord_maps(d10_chart)
    d10_lookup = d10_chart.get("planet_lookup", {})

    # ── D1 Lagna lord in D10 ─────────────────────────────────────────────
    ll_d1 = h2l_d1.get(1)
    if ll_d1:
        ll_in_d10 = d10_lookup.get(ll_d1, {})
        ll_house = ll_in_d10.get("house")
        ll_dignity = ll_in_d10.get("dignity", "")
        if ll_house:
            if ll_dignity in {"exalted", "own_sign"} or ll_house in ANGLES:
                triggered.append(_rule(
                    "D10-S2-D1-LL-STRONG-IN-D10",
                    f"D1 Lagna lord {_pname(ll_d1)} strong in D10 (house {ll_house}, {ll_dignity or 'angle'}) — dedicated and on right professional path",
                    f"The D1 Lagna lord ({_pname(ll_d1)}) is well placed in D10, indicating the native "
                    "is dedicated to their work and will commit to no mean action. They follow the right "
                    "professional path with focus and commitment. A strong D1 Lagna lord in D10 is one "
                    "of the clearest indicators of professional integrity and career resilience.",
                    "positive", 6,
                    {"overall": 4, "career": 6},
                    confidence="high",
                ))
            elif ll_house in DUSTHANA or ll_dignity == "debilitated":
                triggered.append(_rule(
                    "D10-S2-D1-LL-WEAK-IN-D10",
                    f"D1 Lagna lord {_pname(ll_d1)} weak in D10 (house {ll_house}, {ll_dignity or 'dusthana'}) — career growth obstructed",
                    f"The D1 Lagna lord ({_pname(ll_d1)}) is badly placed or aspected in D10, indicating "
                    "the native faces no growth and constant career problems. A weak Lagna lord in D10 "
                    "undermines professional dedication and places the native on a difficult path with "
                    "recurring obstacles.",
                    "negative", 5,
                    {"overall": -4, "career": -5},
                    confidence="high",
                ))

    # ── D1 10th lord in D10 ──────────────────────────────────────────────
    lord_10_d1 = h2l_d1.get(10)
    if lord_10_d1:
        l10_in_d10 = d10_lookup.get(lord_10_d1, {})
        l10_house = l10_in_d10.get("house")
        l10_dignity = l10_in_d10.get("dignity", "")
        if l10_house:
            if l10_dignity in {"exalted", "own_sign"} or l10_house in ANGLES:
                triggered.append(_rule(
                    "D10-S2-D1-10L-STRONG-IN-D10",
                    f"D1 10th lord {_pname(lord_10_d1)} strong in D10 (house {l10_house}) — smooth career without obstructions",
                    f"The D1 10th lord ({_pname(lord_10_d1)}) is strong and well associated in D10, "
                    "indicating a smooth career without obstructions. The native has many sources of "
                    "income and enjoys good status in society. Multiple avenues of career success "
                    "remain open throughout life.",
                    "positive", 7,
                    {"overall": 5, "career": 7},
                    confidence="high",
                ))

    # ── D10 Lagna quality ────────────────────────────────────────────────
    d10_lagna = d10_chart.get("lagna", {})
    d10_lagna_sign = d10_lagna.get("sign_number")
    planets_in_lagna = _planets_in_house(d10_chart, 1) if d10_lagna_sign else []

    benefics_in_lagna = [p for p in planets_in_lagna if p in BENEFICS]
    malefics_in_lagna = [p for p in planets_in_lagna if p in MALEFICS]

    # Jupiter aspect to Lagna (from 5, 7, 9 relative to Lagna = houses 5, 7, 9)
    ju_data = d10_lookup.get("Ju", {})
    ju_house = ju_data.get("house")
    ju_aspects_lagna = ju_house in {5, 7, 9}

    if benefics_in_lagna or ju_aspects_lagna:
        codes = benefics_in_lagna or ["Ju (aspects)"]
        triggered.append(_rule(
            "D10-S2-D10-LAGNA-STRONG",
            f"Benefic {'in' if benefics_in_lagna else 'aspecting'} D10 Lagna — solid career foundation",
            "A strong D10 Lagna is a prerequisite for having a stable profession or vocation. "
            "With benefic influence, the Lagna is not disturbed by minor career problems and "
            "the native maintains professional standing through difficulty. The career foundation "
            "is firm, allowing the person to build on setbacks rather than be undone by them.",
            "positive", 5,
            {"overall": 4, "career": 5},
            confidence="medium",
        ))
    elif malefics_in_lagna and not benefics_in_lagna and not ju_aspects_lagna:
        triggered.append(_rule(
            "D10-S2-D10-LAGNA-WEAK",
            f"Malefic(s) {', '.join(_pname(p) for p in malefics_in_lagna)} in D10 Lagna, no benefic — career instability",
            "A weak D10 Lagna with only malefic influence and no benefic protection undermines "
            "the professional foundation. The native's career identity is fragile and vulnerable "
            "to disruption. Even small problems feel serious and the person may struggle to "
            "establish a consistent professional vocation.",
            "negative", 5,
            {"overall": -3, "career": -5},
            confidence="medium",
        ))

    # ── 10th house/lord of D10 linked to 6/8/12 ─────────────────────────
    lord_10_d10 = h2l_d10.get(10)
    placed_10_d10 = l2p_d10.get(lord_10_d10) if lord_10_d10 else None
    planets_in_10th = _planets_in_house(d10_chart, 10)
    if placed_10_d10 in DUSTHANA:
        triggered.append(_rule(
            "D10-S2-10TH-6-8-12",
            f"D10 10th lord {_pname(lord_10_d10)} in house {placed_10_d10} — sudden career changes/problems",
            f"The 10th lord of D10 ({_pname(lord_10_d10)}) placed in house {placed_10_d10} (a dusthana) "
            "connects career significators with the houses of obstruction. Relation of the 10th "
            "house/lord with 6th, 8th, or 12th gives problems and sudden changes in profession. "
            "Career disruptions, forced transitions, or hidden issues in the work sphere are indicated.",
            "negative", 5,
            {"overall": -3, "career": -5},
            confidence="high",
        ))

    # ── Sun in D10 ───────────────────────────────────────────────────────
    su = d10_lookup.get("Su", {})
    su_house = su.get("house")
    if su_house:
        if su_house in ANGLES:
            triggered.append(_rule(
                "D10-S2-SUN-ANGLE",
                f"Sun in angle (house {su_house}) of D10 — high-status government/authority career",
                "A strong Sun in an angular house (1st, 4th, 7th, or 10th) of D10 gives a "
                "high-status government job with high income. It provides administrative power, "
                "far-sightedness, and steady career rise. The native earns authority and recognition "
                "through their work. Angles are the most powerful positions in D10, and Sun in an "
                "angle is one of the clearest indicators of government or authority-linked success.",
                "positive", 6,
                {"overall": 4, "career": 6},
                confidence="high",
            ))
        elif su_house in DUSTHANA:
            triggered.append(_rule(
                "D10-S2-SUN-DUSTHANA",
                f"Sun in dusthana (house {su_house}) of D10 — problems from government, indecisive",
                f"A weak Sun placed in house {su_house} (a dusthana — 6th, 8th, or 12th) of D10 "
                "is not welcome and gives problems from government and authority. The native may "
                "become indecisive in career choices, face obstacles in obtaining recognition, and "
                "struggle with authority figures at the workplace.",
                "negative", 5,
                {"overall": -3, "career": -5},
                confidence="high",
            ))

    # ── Saturn in D10 ────────────────────────────────────────────────────
    sa = d10_lookup.get("Sa", {})
    sa_house = sa.get("house")
    sa_dignity = sa.get("dignity", "")
    if sa_house:
        if sa_dignity in {"exalted", "own_sign"} or sa_house in ANGLES:
            triggered.append(_rule(
                "D10-S2-SATURN-STRONG",
                f"Saturn well-placed in D10 (house {sa_house}, {sa_dignity or 'angle'}) — subordinate support, political/mining career",
                "A strong Saturn in D10 promises support from subordinates and workers, making "
                "the native an effective team leader. Political career is also supported by a "
                "good Saturn. Other Saturn-ruled fields — underground mining, steel, construction, "
                "and organised labour — also prosper. The native earns through disciplined effort.",
                "positive", 5,
                {"overall": 4, "career": 5},
                confidence="high",
            ))
        elif sa_house in DUSTHANA or sa_dignity == "debilitated":
            triggered.append(_rule(
                "D10-S2-SATURN-WEAK",
                f"Saturn badly placed in D10 (house {sa_house}, {sa_dignity or 'dusthana'}) — problems from subordinates",
                "A badly placed or malefic Saturn in D10 invites problems from subordinates and "
                "workers. The native faces insubordination, sabotage from those below in the "
                "hierarchy, or difficulty managing teams. Political and labour-related fields also "
                "carry greater risk of disruption.",
                "negative", 4,
                {"overall": -3, "career": -4},
                confidence="medium",
            ))

    # ── Moon and 10th lord from Moon ─────────────────────────────────────
    mo = d10_lookup.get("Mo", {})
    mo_house = mo.get("house")
    if mo_house:
        moon_10th_house = ((mo_house - 1 + 9) % 12) + 1  # 10th from Moon
        lord_moon_10th = h2l_d10.get(moon_10th_house)
        moon_10th_dignity = l2p_d10.get(lord_moon_10th) if lord_moon_10th else None
        moon_10th_lord_data = d10_lookup.get(lord_moon_10th, {}) if lord_moon_10th else {}
        moon_10th_lord_placed = moon_10th_lord_data.get("house")
        moon_10th_lord_dign = moon_10th_lord_data.get("dignity", "")

        moon_strong = mo_house in ANGLE_OR_TRINE
        moon_10th_strong = moon_10th_lord_placed in ANGLE_OR_TRINE if moon_10th_lord_placed else False
        moon_10th_dign_strong = moon_10th_lord_dign in {"exalted", "own_sign"}

        if moon_strong and (moon_10th_strong or moon_10th_dign_strong):
            triggered.append(_rule(
                "D10-S2-MOON-10TH-STRONG",
                f"Moon (house {mo_house}) and 10th from Moon (house {moon_10th_house}) lord {_pname(lord_moon_10th) if lord_moon_10th else '?'} both well-placed — zeal and jest for work",
                "Moon and the 10th lord from Moon in D10 govern the mental attitude toward karma "
                "(professional actions). When both are strong, the native has genuine enthusiasm, "
                "zeal, and joy for their work. This gives emotional fulfilment from one's profession "
                "and a strong inner drive to perform.",
                "positive", 4,
                {"overall": 3, "career": 4},
                confidence="medium",
            ))
        elif not moon_strong and not moon_10th_strong and not moon_10th_dign_strong:
            triggered.append(_rule(
                "D10-S2-MOON-10TH-WEAK",
                f"Moon (house {mo_house}) and 10th from Moon lord both weak in D10 — inferiority complex",
                "Moon and the 10th lord from Moon in D10 govern the mental attitude toward work. "
                "When both are weak, the native develops an inferiority complex about their "
                "professional abilities. Lack of confidence, fear of judgment, and emotional "
                "dissatisfaction with work are the recurring themes.",
                "negative", 4,
                {"overall": -3, "career": -4},
                confidence="medium",
            ))

    return triggered


# ── Set 3: Dasha Timing Signatures ───────────────────────────────────────────

def _d10_s3_dasha_timing(d10_chart: dict[str, Any]) -> list[dict]:
    """Structural house-based dasha timing triggers in D10."""
    triggered = []
    h2l_d10, l2p_d10 = _build_lord_maps(d10_chart)
    d10_lookup = d10_chart.get("planet_lookup", {})

    # Check whether Lagna and 10th are afflicted (for 3rd/5th dasha crisis rule)
    lagna_occupants = _planets_in_house(d10_chart, 1)
    tenth_occupants = _planets_in_house(d10_chart, 10)
    lord_10_d10 = h2l_d10.get(10)
    placed_10_d10 = l2p_d10.get(lord_10_d10) if lord_10_d10 else None

    lagna_afflicted = any(p in MALEFICS for p in lagna_occupants) and not any(p in BENEFICS for p in lagna_occupants)
    tenth_afflicted = any(p in MALEFICS for p in tenth_occupants) or placed_10_d10 in DUSTHANA

    # ── 3rd house planets → retirement trigger ───────────────────────────
    planets_3rd = _planets_in_house(d10_chart, 3)
    if planets_3rd:
        names = ", ".join(_pname(p) for p in planets_3rd)
        triggered.append(_rule(
            "D10-S3-3RD-HOUSE-PLANETS",
            f"Planets {names} in 3rd house of D10 — their dasha periods trigger retirement/exit from service",
            f"Dasha of a planet related to the third house gives retirement from service. "
            f"{names} in the 3rd house of D10 marks their mahadasha or antardasha as a potential "
            "timing window for retirement, exit from current employment, or a decisive transition "
            "away from active professional life. The 3rd lord is the most critical of these.",
            "negative", 4,
            {"overall": -2, "career": -4},
            confidence="medium",
        ))

    # ── 3rd/5th afflicted with afflicted Lagna/10th → career crisis ─────
    planets_5th = _planets_in_house(d10_chart, 5)
    if lagna_afflicted and tenth_afflicted and (planets_3rd or planets_5th):
        crisis_planets = planets_3rd + planets_5th
        names = ", ".join(_pname(p) for p in crisis_planets)
        triggered.append(_rule(
            "D10-S3-AFFLICTED-3RD-5TH",
            f"Lagna and 10th house afflicted; planets {names} in 3rd/5th — their dasha = serious career crisis",
            "When both the D10 Lagna/Lagna lord and the 10th house/10th lord are afflicted, "
            "the dashas of planets in the 3rd and/or 5th house deliver serious professional "
            "problems. This is one of the more severe career crisis indicators — the affliction "
            "of the professional pillars combined with 3rd/5th dasha timing creates a period "
            "of grave career difficulty.",
            "negative", 6,
            {"overall": -4, "career": -6},
            confidence="medium",
        ))

    # ── 6th house planets → welcome transfer ────────────────────────────
    planets_6th = _planets_in_house(d10_chart, 6)
    if planets_6th:
        names = ", ".join(_pname(p) for p in planets_6th)
        triggered.append(_rule(
            "D10-S3-6TH-TRANSFER",
            f"Planets {names} in 6th house of D10 — their dasha = welcome transfer or change",
            f"Dasha related to the 6th house of D10 gives a change or transfer in service. "
            f"With {names} in the 6th, their dasha periods are timing windows for a welcome "
            "job change or transfer — one that the native accepts positively and that often "
            "improves conditions.",
            "neutral", 3,
            {"overall": 1, "career": 2},
            confidence="medium",
        ))

    # ── 8th house planets → forced/unwanted transfer ─────────────────────
    planets_8th = _planets_in_house(d10_chart, 8)
    if planets_8th:
        names = ", ".join(_pname(p) for p in planets_8th)
        triggered.append(_rule(
            "D10-S3-8TH-FORCED-TRANSFER",
            f"Planets {names} in 8th house of D10 — their dasha = forced/unwanted transfer",
            f"The 8th house in D10 represents hidden activities, underhand dealings, and the end of "
            f"career phases. With {names} in the 8th, their dasha periods trigger forced or "
            "unwelcome job changes — transfers the native has no choice but to accept, often "
            "accompanied by disruption, hidden challenges, or a difficult adjustment.",
            "negative", 4,
            {"overall": -2, "career": -3},
            confidence="medium",
        ))

    # ── 12th house planets → routine change ─────────────────────────────
    planets_12th = _planets_in_house(d10_chart, 12)
    if planets_12th:
        names = ", ".join(_pname(p) for p in planets_12th)
        triggered.append(_rule(
            "D10-S3-12TH-ROUTINE-CHANGE",
            f"Planets {names} in 12th house of D10 — their dasha = routine job change",
            f"The 12th house of D10 governs the end of career phases, charities in profession, "
            f"and secret activities against the career. With {names} in the 12th, their dasha "
            "periods trigger routine job changes — transitions that are expected, part of the "
            "natural career cycle, neither particularly welcome nor forced.",
            "neutral", 3,
            {"overall": -1, "career": -2},
            confidence="medium",
        ))

    # ── Rahu in D10 Lagna ────────────────────────────────────────────────
    if "Ra" in lagna_occupants:
        triggered.append(_rule(
            "D10-S3-RAHU-LAGNA",
            "Rahu in D10 Lagna — many career ups and downs",
            "Rahu in the D10 Lagna gives many ups and downs in career throughout life. The native "
            "experiences sudden rises and unexpected falls in professional status. Rahu brings an "
            "unusual or unconventional career path, often with foreign connections or non-traditional "
            "fields. The career is never dull but is difficult to stabilise.",
            "negative", 5,
            {"overall": -2, "career": -4},
            confidence="high",
        ))

    return triggered


# ── Set 4: 10th Lord in Houses 6–12 ──────────────────────────────────────────

def _d10_s4_tenth_lord_houses(d10_chart: dict[str, Any]) -> list[dict]:
    """10th lord placement in houses 6–12 (houses 1–5 are covered by divisional_rules.yaml)."""
    triggered = []
    h2l_d10, l2p_d10 = _build_lord_maps(d10_chart)
    lord_10 = h2l_d10.get(10)
    if not lord_10:
        return []
    placed = l2p_d10.get(lord_10)
    if not placed or placed < 6:
        return []

    placements = {
        6: (
            "D10-S4-10TH-LORD-6TH",
            f"D10 10th lord {_pname(lord_10)} in 6th — service/servitude, luck-dependent career",
            f"The 10th lord {_pname(lord_10)} in the 6th house of D10 places career under the domain "
            "of service and servitude. The person depends heavily on luck for furthering their career. "
            "The 6th relates to problems of society — disease, debt, and enemies — and the native "
            "earns their living working with or around these fields (medical, legal, social services).",
            "negative", 4,
            {"overall": -2, "career": -3},
        ),
        7: (
            "D10-S4-10TH-LORD-7TH",
            f"D10 10th lord {_pname(lord_10)} in 7th — strong business skills, partnership-based career",
            f"The 10th lord {_pname(lord_10)} in the 7th house of D10 gives strong business skills "
            "and emphasises partnership and corporate structures as important earning vehicles. "
            "Partnership with foreigners, international trade, and travel as part of profession "
            "are indicated. The native is best suited to collaborative, client-facing work.",
            "positive", 5,
            {"overall": 3, "career": 5},
        ),
        8: (
            "D10-S4-10TH-LORD-8TH",
            f"D10 10th lord {_pname(lord_10)} in 8th — challenges and uncertain career",
            f"The 10th lord {_pname(lord_10)} in the 8th house creates an uncertain and challenging "
            "career. If the D10 Lagna is strong, one can achieve great positions through considerable "
            "struggle. With benefic association, high positions come quickly. Without Lagna strength, "
            "the career remains unstable, subject to hidden disruptions and sudden reversals.",
            "negative", 5,
            {"overall": -3, "career": -5},
        ),
        9: (
            "D10-S4-10TH-LORD-9TH",
            f"D10 10th lord {_pname(lord_10)} in 9th — Rajyoga, high position by luck",
            f"The 10th lord {_pname(lord_10)} in the 9th house of D10 is a powerful Rajyoga. "
            "The native attains high position by sheer luck and divine grace. The career frequently "
            "changes and the native is often in a transferable job. The 9th lord connection "
            "indicates a preceptor or guide whose support shapes the professional rise.",
            "positive", 6,
            {"overall": 5, "career": 6},
        ),
        10: (
            "D10-S4-10TH-LORD-10TH",
            f"D10 10th lord {_pname(lord_10)} in 10th — distinction, honour, and fame",
            f"The 10th lord {_pname(lord_10)} in its own house (10th) of D10 gives distinction in "
            "work, honour, and fame. The native gets recognition for their professional achievements. "
            "When afflicted, the fame may come for the wrong reasons or through controversy. "
            "This is among the strongest placements for professional achievement.",
            "positive", 7,
            {"overall": 5, "career": 7},
        ),
        11: (
            "D10-S4-10TH-LORD-11TH",
            f"D10 10th lord {_pname(lord_10)} in 11th — fortunate, multiple professions",
            f"The 10th lord {_pname(lord_10)} in the 11th house of D10 makes the native fortunate "
            "in all undertakings. Success comes with least effort. The native often has more than "
            "one profession simultaneously and employs many others. Gains flow easily and the "
            "professional path is marked by good fortune.",
            "positive", 6,
            {"overall": 4, "career": 6},
        ),
        12: (
            "D10-S4-10TH-LORD-12TH",
            f"D10 10th lord {_pname(lord_10)} in 12th — foreign or hospital/jail-related career",
            f"The 10th lord {_pname(lord_10)} in the 12th house of D10 gives a foreign-related "
            "profession or work in hospitals, jails, or secluded places. The career is hidden from "
            "public view or involves behind-the-scenes service. Association with the 12th lord "
            "increases the probability of an unsuccessful career unless foreign connection redeems it.",
            "negative", 4,
            {"overall": -2, "career": -3},
        ),
    }

    if placed in placements:
        rule_id, reason, interp, polarity, weight, outcomes = placements[placed]
        triggered.append(_rule(rule_id, reason, interp, polarity, weight, outcomes, confidence="high"))

    return triggered


# ── Set 5: Planet Placement Strength in D10 ──────────────────────────────────

def _d10_s5_planet_strength(d10_chart: dict[str, Any]) -> list[dict]:
    """Angle strength ordering, trine obstacles, trik with/without connection, debilitated planets."""
    triggered = []
    h2l_d10, l2p_d10 = _build_lord_maps(d10_chart)
    d10_lookup = d10_chart.get("planet_lookup", {})

    # ── Planets in 10th (strongest angle) ───────────────────────────────
    planets_10th = _planets_in_house(d10_chart, 10)
    if planets_10th:
        names = ", ".join(_pname(p) for p in planets_10th)
        triggered.append(_rule(
            "D10-S5-ANGLE-BEST",
            f"Planets {names} in 10th house (strongest D10 angle) — most powerful career delivery",
            "Planets in angles are the most powerful for delivering career results in D10. "
            f"The order of angular strength is 10th > 7th > 4th > 1st. {names} in the 10th "
            "is the peak position for career fulfilment. Even malefics are not bad for career "
            "when placed in angles — they deliver with effort and grit.",
            "positive", 5,
            {"overall": 3, "career": 5},
            confidence="high",
        ))

    # ── Planets in 5th/9th (trines = 8th/12th from 10th) ────────────────
    trine_obstacle_planets = _planets_in_house(d10_chart, 5) + _planets_in_house(d10_chart, 9)
    if trine_obstacle_planets:
        names = ", ".join(_pname(p) for p in trine_obstacle_planets)
        triggered.append(_rule(
            "D10-S5-TRINE-OBSTACLE",
            f"Planets {names} in 5th/9th D10 — obstacles and changes from career house perspective",
            "Planets in trine houses (5th and 9th) of D10 are auspicious in general, but the "
            "5th and 9th are the 8th and 12th from the 10th house. As such, they bring obstacles "
            "and career changes more so when these planets are afflicted. Their dasha periods "
            "tend to introduce disruptions to the career main axis even while promising intelligence "
            "or fortune in other life areas.",
            "negative", 3,
            {"overall": 1, "career": -3},
            confidence="medium",
        ))

    # ── Planets in trik (6/8/12) connected to Lagna/10th lord ───────────
    lord_1_d10 = h2l_d10.get(1)
    lord_10_d10 = h2l_d10.get(10)
    placed_ll = l2p_d10.get(lord_1_d10) if lord_1_d10 else None
    placed_10l = l2p_d10.get(lord_10_d10) if lord_10_d10 else None

    for house in (6, 8, 12):
        trik_planets = _planets_in_house(d10_chart, house)
        for p in trik_planets:
            p_house = d10_lookup.get(p, {}).get("house")
            # Connected = conjunct with lagna lord or 10th lord, or placed in lagna lord's/10th lord's house
            connected = (
                (placed_ll is not None and p_house == placed_ll) or
                (placed_10l is not None and p_house == placed_10l) or
                p in (lord_1_d10, lord_10_d10)
            )
            if connected:
                triggered.append(_rule(
                    f"D10-S5-TRIK-CONNECTED-RELIEF-{p}",
                    f"{_pname(p)} in trik (house {house}) D10 but connected to Lagna/10th lord — initial trouble then relief",
                    f"{_pname(p)} is in a trik house (house {house}) of D10, which generally shows "
                    "difficulty, struggle, and obstacles. However, its connection with the Lagna lord "
                    "or 10th lord means the initial career problems give way to relief. The native "
                    "works through difficulties with support from their core professional pillars.",
                    "neutral", 3,
                    {"overall": 1, "career": 2},
                    confidence="medium",
                ))

    # ── Debilitated planets in D10 → humble start, rise later ───────────
    debilitated = [
        p for p, data in d10_lookup.items()
        if data.get("dignity") == "debilitated" and p not in ("Ra", "Ke")
    ]
    if debilitated:
        names = ", ".join(_pname(p) for p in debilitated)
        triggered.append(_rule(
            "D10-S5-DEBILITATED-LATE-RISE",
            f"Debilitated planet(s) {names} in D10 — tough profession with humble beginning, rise later",
            f"Do not be afraid of debilitated planets ({names}) in D10. They give a tough profession "
            "with a small and humble beginning, but the native rises high later in life. Debilitation "
            "cancellation (neechabhanga) strengthens this rise. Example: Mohammad Ali — debilitated "
            "planets in D10 with later-life greatness is a classic signature of this pattern.",
            "neutral", 3,
            {"overall": 2, "career": 2},
            confidence="medium",
        ))

    return triggered


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d10_dashamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d10_chart = _get_d10_chart(chart_facts)
    if not d10_chart:
        return []
    d1_chart = _get_d1_chart(chart_facts)
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d10_s1_deity(d10_chart, d1_chart))
    triggered.extend(_d10_s2_core_pillars(d10_chart, d1_chart))
    triggered.extend(_d10_s3_dasha_timing(d10_chart))
    triggered.extend(_d10_s4_tenth_lord_houses(d10_chart))
    triggered.extend(_d10_s5_planet_strength(d10_chart))
    return triggered
