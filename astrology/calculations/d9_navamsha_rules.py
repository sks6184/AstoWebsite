"""D9-specific rules from the Navamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Navamsha D9 (pp. 121–145).

SET 1 (Vargottam — planet in same sign in D1 and D9):
  D9-S1-VARGOTTAM-LAGNA        D1 and D9 Lagna in same sign — exceptionally strong self
  D9-S1-VARGOTTAM-VENUS        Venus vargottam — marriage karaka at peak strength
  D9-S1-VARGOTTAM-7TH-LORD     7th lord vargottam — strong marriage promise
  D9-S1-VARGOTTAM-{P}          Any key planet vargottam — gives name, fame, and D9 result

SET 2 (D9 Dignity — confirms or overrides D1 dignity):
  D9-S2-EXALTED-{P}            Planet exalted in D9 — strengthens even if debilitated in D1
  D9-S2-DEBILITATED-{P}        Planet debilitated in D9 — weakens even if exalted in D1
  D9-S2-VENUS-EXALTED          Venus exalted in D9 — peak marriage karaka
  D9-S2-VENUS-DEBILITATED      Venus debilitated in D9 — strained marriage karaka

SET 3 (Nadi Method 1 — Nidhanamsha):
  D9-S3-NIDHANAMSHA-{P}        D9 planet sign maps to D1 8th house — very inauspicious for that planet

SET 4 (Marriage promise from D9 Lagna):
  D9-S4-LAGNA-BENEFIC          Benefic in D9 Lagna — marriage assured
  D9-S4-JU-ASPECTS-LAGNA       Jupiter in 5/7/9 aspects D9 Lagna — strong marriage promise
  D9-S4-LAGNA-MALEFIC-ONLY     Only malefics in/aspecting D9 Lagna, no benefic — marriage problematic
  D9-S4-D1-7TH-LORD-DUSTHANA   D1 7th lord in D9 dusthana — marriage difficult or delayed
  D9-S4-7TH-8TH-LORD-LINK      8th lord influencing 7th house in D9 — separation/divorce potential

SET 5 (7th house and Venus in D9):
  D9-S5-7TH-LORD-ANGLE-TRINE   D9 7th lord in angle/trine — good spouse, strong marriage
  D9-S5-7TH-LORD-DUSTHANA      D9 7th lord in dusthana — difficult spouse or marital strain
  D9-S5-7TH-LORD-UPACHAYA      D9 7th lord in upachaya — higher-status spouse or multiple relationships
  D9-S5-VENUS-ANGLE-TRINE      Venus in angle/trine of D9 — auspicious for marriage
  D9-S5-VENUS-DUSTHANA         Venus in dusthana of D9 — strained marital happiness
  D9-S5-8TH-IN-7TH             8th lord in D9 7th — marital disruption/divorce risk

SET 6 (Multiple marriages and marital denial):
  D9-S6-LL-STRONG-REMARRIAGE   D9 Lagna lord in kendra/trikona/11th with own/exalted/retrograde — remarriage
  D9-S6-7TH-MALEFIC-ONLY       Only malefics in D9 7th, no benefic — difficult marriage or denial
  D9-S6-MULTI-UPACHAYA         2nd, 7th, 12th lords all in upachaya in D9 — multiple marriages
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Navamsha D9"
_SOURCE_PAGE = "121"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
UPACHAYA = frozenset({3, 6, 10, 11})
BENEFICS = frozenset({"Ju", "Ve", "Mo", "Me"})
MALEFICS = frozenset({"Su", "Ma", "Sa", "Ra", "Ke"})


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
        "system": "D9/NavamshaRules",
        "chart": "D9",
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
        "source_file": "d9_navamsha_rules.py",
    }


def _get_d9_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d9", {})


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


def _lords_related(
    code_a: str, house_a: int, placed_a: int | None,
    code_b: str, house_b: int, placed_b: int | None,
) -> bool:
    if code_a == code_b or placed_a is None or placed_b is None:
        return False
    return placed_a == placed_b or placed_a == house_b or placed_b == house_a


def _planets_in_house(chart: dict[str, Any], house: int) -> list[str]:
    return [p["code"] for p in chart.get("planets", []) if p.get("house") == house and p.get("code")]


# ── Set 1: Vargottam ─────────────────────────────────────────────────────────

def _d9_s1_vargottam(d9_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Planets in same sign in D1 and D9 — at their strongest, give name and fame."""
    if not d1_chart:
        return []

    d1_lookup = d1_chart.get("planet_lookup", {})
    d9_lookup = d9_chart.get("planet_lookup", {})
    triggered = []

    d1_lagna = d1_chart.get("lagna", {})
    d9_lagna = d9_chart.get("lagna", {})
    if d1_lagna.get("sign_number") and d1_lagna.get("sign_number") == d9_lagna.get("sign_number"):
        sign = d9_lagna.get("sign", f"sign {d9_lagna.get('sign_number')}")
        triggered.append(_rule(
            "D9-S1-VARGOTTAM-LAGNA",
            f"D1 and D9 Lagna both in {sign} — vargottam ascendant, exceptionally strong self",
            "When the Lagna (ascendant) occupies the same sign in both the birth chart (D1) "
            "and the Navamsha (D9), the native is vargottam in the most literal sense. This "
            "bestows exceptional strength of body, mind, and character. The native enjoys "
            "name, fame, and longevity. The entire chart is strengthened, as a vargottam "
            "Lagna lord gives results of highest quality throughout life.",
            "positive", 7,
            {"overall": 6, "marriage": 4, "career": 4},
            confidence="high",
        ))

    key_planets = {
        "Ve": ("Venus", "marriage karaka", {"overall": 5, "marriage": 6, "career": 1}),
        "Ju": ("Jupiter", "wisdom and dharma karaka", {"overall": 4, "marriage": 4, "career": 3}),
        "Mo": ("Moon", "mind and emotional karaka", {"overall": 4, "marriage": 3, "career": 2}),
        "Su": ("Sun", "soul and authority karaka", {"overall": 4, "marriage": 2, "career": 4}),
        "Me": ("Mercury", "intelligence karaka", {"overall": 3, "marriage": 2, "career": 3}),
        "Ma": ("Mars", "strength and property karaka", {"overall": 3, "marriage": 2, "career": 3}),
        "Sa": ("Saturn", "longevity and karma karaka", {"overall": 3, "marriage": 2, "career": 3}),
    }

    h2l_d1, _ = _build_lord_maps(d1_chart)
    seventh_lord_d1 = h2l_d1.get(7)

    for code, (name, role, outcomes) in key_planets.items():
        d1_p = d1_lookup.get(code, {})
        d9_p = d9_lookup.get(code, {})
        if not d1_p or not d9_p:
            continue
        d1_sign = d1_p.get("sign_number")
        d9_sign = d9_p.get("sign_number")
        if not d1_sign or d1_sign != d9_sign:
            continue

        sign_name = d9_p.get("sign", f"sign {d9_sign}")

        if code == "Ve":
            triggered.append(_rule(
                "D9-S1-VARGOTTAM-VENUS",
                f"Venus vargottam in {sign_name} — marriage karaka at its peak strength",
                "Vargottam Venus — occupying the same sign in D1 and D9 — is one of the most "
                "powerful blessings for marriage. The natural significator of love, beauty, and "
                "partnership operates at full force. This native enjoys a beautiful spouse, "
                "marital happiness, and refined pleasures throughout life. Name and fame through "
                "partnerships and artistic pursuits are also indicated.",
                "positive", 7,
                outcomes,
                confidence="high",
            ))
        elif code == seventh_lord_d1 and code != "Ve":
            triggered.append(_rule(
                "D9-S1-VARGOTTAM-7TH-LORD",
                f"D1 7th lord {_pname(code)} vargottam in {sign_name} — strong marriage promise",
                f"The 7th lord ({_pname(code)}) of the birth chart occupies the same sign in "
                "both D1 and D9, making it vargottam. This significantly strengthens the promise "
                "of marriage and the quality of the spouse. A vargottam 7th lord gives results "
                "of the 7th house — marriage, partnership, and public dealings — at their "
                "fullest potential. The spouse brings name and stability.",
                "positive", 6,
                outcomes,
                confidence="high",
            ))
        else:
            triggered.append(_rule(
                f"D9-S1-VARGOTTAM-{code}",
                f"{name} vargottam in {sign_name} — {role} at peak strength",
                f"Vargottam {name} (same sign in D1 and D9) operates at its highest strength. "
                f"A vargottam planet gives the best results of both its natal house and its "
                f"significations. The native gains recognition and {role.split(' karaka')[0]}-related "
                "blessings that persist through dashas of this planet. Name and fame come through "
                f"the domain of {name}.",
                "positive", 5,
                outcomes,
                confidence="medium",
            ))

    return triggered


# ── Set 2: D9 Dignity ─────────────────────────────────────────────────────────

def _d9_s2_dignity(d9_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """D9 dignity overrides or confirms D1 dignity — the Navamsha is the fruit of the D1."""
    d9_lookup = d9_chart.get("planet_lookup", {})
    d1_lookup = d1_chart.get("planet_lookup", {}) if d1_chart else {}
    triggered = []

    for code, d9_p in d9_lookup.items():
        if not code or code == "Asc":
            continue
        d9_dignity = d9_p.get("dignity", "")
        d1_dignity = d1_lookup.get(code, {}).get("dignity", "")
        house = d9_p.get("house")
        sign = d9_p.get("sign", "")
        pname = _pname(code)

        if d9_dignity == "exalted":
            if code == "Ve":
                triggered.append(_rule(
                    "D9-S2-VENUS-EXALTED",
                    f"Venus exalted in D9 (house {house}, {sign}) — peak marriage karaka strength",
                    "Venus exalted in the Navamsha is one of the finest indicators for marriage. "
                    "The natural significator of love and beauty is at its maximum dignity in the "
                    "D9 chart — the chart of marriage itself. Even if Venus is challenged in D1, "
                    "the exaltation in D9 assures that marital happiness is ultimately fulfilled. "
                    "The spouse is likely to be beautiful, refined, and a genuine source of joy.",
                    "positive", 7,
                    {"overall": 5, "marriage": 7, "career": 2},
                    confidence="high",
                ))
            elif d1_dignity == "debilitated":
                triggered.append(_rule(
                    f"D9-S2-EXALTED-{code}",
                    f"{pname} debilitated in D1 but exalted in D9 — Navamsha cancels debilitation",
                    f"{pname} is debilitated in the birth chart, ordinarily a weakness. However, "
                    f"exaltation in the Navamsha (D9) substantially mitigates this: the Navamsha "
                    "is the fruit of the D1, and a planet exalted in D9 ultimately gives good "
                    "results even when it struggled in D1. The native gains through patience — "
                    f"{pname}'s results improve markedly over the life span.",
                    "positive", 6,
                    {"overall": 5, "marriage": 3, "career": 3},
                    confidence="high",
                ))
            else:
                triggered.append(_rule(
                    f"D9-S2-EXALTED-{code}",
                    f"{pname} exalted in D9 (house {house}) — D9 confirms and amplifies strength",
                    f"Exalted {pname} in the Navamsha confirms and amplifies the planet's strength "
                    "established in the birth chart. A planet exalted in both D1 and D9 is at its "
                    "most powerful — giving the fullest results of its significations. The native "
                    f"enjoys peak benefits from {pname}'s dasha and related life areas.",
                    "positive", 5,
                    {"overall": 4, "marriage": 3, "career": 3},
                    confidence="medium",
                ))

        elif d9_dignity == "debilitated":
            if code == "Ve":
                triggered.append(_rule(
                    "D9-S2-VENUS-DEBILITATED",
                    f"Venus debilitated in D9 (house {house}, {sign}) — strained marriage karaka",
                    "Venus debilitated in the Navamsha significantly strains the natural significator "
                    "of marriage within the D9 — the chart specifically governing the quality of "
                    "marriage. Even if Venus appears strong in D1, debilitation in D9 indicates "
                    "that the fruits of marital relationships carry suffering, disappointment, or "
                    "disharmony. The native must work hard to sustain marital happiness.",
                    "negative", 7,
                    {"overall": -4, "marriage": -7, "career": -2},
                    confidence="high",
                ))
            elif d1_dignity == "exalted":
                triggered.append(_rule(
                    f"D9-S2-DEBILITATED-{code}",
                    f"{pname} exalted in D1 but debilitated in D9 — Navamsha denies full results",
                    f"{pname} is exalted in the birth chart — a seeming strength — but debilitation "
                    "in the Navamsha means the promised results do not fully materialize. The D9 "
                    "represents the final fruit; a planet debilitated there ultimately yields "
                    "disappointing outcomes despite an initially promising appearance. The native "
                    f"may see initial gain in {pname}'s areas followed by loss or frustration.",
                    "negative", 6,
                    {"overall": -4, "marriage": -3, "career": -3},
                    confidence="high",
                ))
            else:
                triggered.append(_rule(
                    f"D9-S2-DEBILITATED-{code}",
                    f"{pname} debilitated in D9 (house {house}) — Navamsha weakens the planet",
                    f"Debilitated {pname} in the Navamsha diminishes the planet's capacity to "
                    "deliver its promised results. The D9 is the divisional of dharma and "
                    "strength confirmation — debilitation here indicates the planet's D1 "
                    "placement lacks the strength to fully manifest its potential.",
                    "negative", 4,
                    {"overall": -3, "marriage": -2, "career": -2},
                    confidence="medium",
                ))

    return triggered


# ── Set 3: Nadi Method 1 — Nidhanamsha ───────────────────────────────────────

def _d9_s3_nidhanamsha(d9_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Nadi Method 1: D9 planet sign maps to D1 8th house → Nidhanamsha — very inauspicious."""
    if not d1_chart:
        return []

    d1_lagna = d1_chart.get("lagna", {})
    d1_lagna_sign = d1_lagna.get("sign_number")
    if not d1_lagna_sign:
        return []

    d9_lookup = d9_chart.get("planet_lookup", {})
    d1_lookup = d1_chart.get("planet_lookup", {})
    triggered = []

    # Key planets to check for Nidhanamsha
    key_planets = {"Ve", "Ju", "Mo", "Su", "Me", "Ma", "Sa", "Ra", "Ke"}
    for code in key_planets:
        d9_p = d9_lookup.get(code, {})
        if not d9_p:
            continue
        d9_sign = d9_p.get("sign_number")
        if not d9_sign:
            continue
        # Which D1 house holds this D9 sign?
        d1_house_of_d9_sign = ((int(d9_sign) - int(d1_lagna_sign)) % 12) + 1
        if d1_house_of_d9_sign != 8:
            continue

        pname = _pname(code)
        d9_sign_name = d9_p.get("sign", f"sign {d9_sign}")
        d9_house = d9_p.get("house")
        d1_dignity = d1_lookup.get(code, {}).get("dignity", "unknown")

        triggered.append(_rule(
            f"D9-S3-NIDHANAMSHA-{code}",
            f"{pname} in Nidhanamsha — D9 sign ({d9_sign_name}) falls in D1 8th house",
            f"{pname} occupies {d9_sign_name} in D9 (house {d9_house}), and that sign corresponds "
            f"to the 8th house of the D1 chart. By Nadi Method 1, this makes {pname} a "
            "Nidhanamsha planet — occupying the most inauspicious division relative to the "
            "birth chart. The 8th house in D1 governs obstacles, death, and hidden karmas. "
            f"A Nidhanamsha {pname} gives its results with great difficulty, suffering, or "
            "delay; the native faces karmic obstruction in the domain signified by this planet. "
            "This is especially significant if the planet is also a dasha lord or house lord.",
            "negative", 5,
            {"overall": -4, "marriage": -3 if code in {"Ve", "Ju"} else -1, "career": -3},
            confidence="medium",
        ))

    return triggered


# ── Set 4: Marriage promise from D9 Lagna ────────────────────────────────────

def _d9_s4_marriage_promise(d9_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """D9 Lagna and 7th house of D1 placed in D9 — primary marriage promise indicators."""
    lagna_occupants = _planets_in_house(d9_chart, 1)
    h2l_d9, l2p_d9 = _build_lord_maps(d9_chart)
    triggered = []

    # Benefic or Jupiter aspecting D9 Lagna → marriage assured
    ju = d9_chart.get("planet_lookup", {}).get("Ju", {})
    ju_house = ju.get("house")
    if ju_house in {5, 7, 9} or ju_house == 1:
        triggered.append(_rule(
            "D9-S4-JU-ASPECTS-LAGNA",
            f"Jupiter in house {ju_house} of D9 — aspects/occupies D9 Lagna, marriage strongly promised",
            "Jupiter aspecting (from 5th, 7th, or 9th) or occupying the D9 Lagna is one of the "
            "most reliable indicators of marriage. Jupiter's full aspect on the ascendant of the "
            "Navamsha — the chart of marriage itself — assures that the native will marry and "
            "that the marriage will have dharmic support. The spouse is likely to be wise, "
            "educated, and dharmic.",
            "positive", 6,
            {"overall": 5, "marriage": 6, "career": 1},
            confidence="high",
        ))

    benefic_in_lagna = [c for c in lagna_occupants if c in BENEFICS]
    malefic_in_lagna = [c for c in lagna_occupants if c in MALEFICS]

    if benefic_in_lagna:
        names = [_pname(c) for c in benefic_in_lagna]
        triggered.append(_rule(
            "D9-S4-LAGNA-BENEFIC",
            f"Benefic(s) {', '.join(names)} in D9 Lagna — marriage assured",
            f"Benefic planet(s) ({', '.join(names)}) in the D9 ascendant strengthens the "
            "chart of marriage at its root. A benefic Lagna in Navamsha is a clear indication "
            "that the native will marry and that the marriage carries benefit. The native "
            "enters marriage with dharmic merit and the relationship brings growth.",
            "positive", 5,
            {"overall": 4, "marriage": 5, "career": 1},
            confidence="medium",
        ))

    if malefic_in_lagna and not benefic_in_lagna and ju_house not in {1, 5, 7, 9}:
        names = [_pname(c) for c in malefic_in_lagna]
        triggered.append(_rule(
            "D9-S4-LAGNA-MALEFIC-ONLY",
            f"Malefic(s) {', '.join(names)} in D9 Lagna with no benefic — marriage problematic",
            f"Only malefic planets ({', '.join(names)}) occupy the D9 Lagna with no benefic "
            "aspect or Jupiter's support. This weakens the ascendant of the Navamsha — the "
            "foundation of the marriage chart. The native faces delays, obstacles, or "
            "dissatisfaction in marriage, and the relationship may carry suffering or strain.",
            "negative", 5,
            {"overall": -3, "marriage": -5, "career": -1},
            confidence="medium",
        ))

    # D1 7th lord placed in D9 dusthana
    if d1_chart:
        h2l_d1, _ = _build_lord_maps(d1_chart)
        seventh_lord_d1 = h2l_d1.get(7)
        if seventh_lord_d1:
            d9_placement = d9_chart.get("planet_lookup", {}).get(seventh_lord_d1, {})
            d9_house = d9_placement.get("house")
            if d9_house in DUSTHANA:
                triggered.append(_rule(
                    "D9-S4-D1-7TH-LORD-DUSTHANA",
                    f"D1 7th lord {_pname(seventh_lord_d1)} in D9 dusthana (house {d9_house}) — marriage difficult or delayed",
                    f"The 7th lord of the birth chart ({_pname(seventh_lord_d1)}) placed in "
                    f"a dusthana (house {d9_house}) of the Navamsha is a significant concern "
                    "for marriage. The lord of the house of marriage in D1 is weakened within "
                    "the D9 itself — the chart governing the quality of marriage. This indicates "
                    "that marriage is difficult, delayed, or brings significant challenges, "
                    "particularly during the 7th lord's dasha.",
                    "negative", 6,
                    {"overall": -4, "marriage": -6, "career": -1},
                    confidence="high",
                ))
            elif d9_house in ANGLE_OR_TRINE:
                triggered.append(_rule(
                    "D9-S4-D1-7TH-LORD-WELL-PLACED",
                    f"D1 7th lord {_pname(seventh_lord_d1)} in D9 angle/trine (house {d9_house}) — marriage well supported",
                    f"The 7th lord of the birth chart ({_pname(seventh_lord_d1)}) is well-placed "
                    f"in an angular or trine house of the Navamsha (house {d9_house}). This "
                    "cross-chart confirmation strengthens the promise of marriage. The D1 marriage "
                    "significator is supported by the D9 chart, indicating that marital "
                    "relationships are ultimately fulfilling and dharmic.",
                    "positive", 5,
                    {"overall": 4, "marriage": 5, "career": 1},
                    confidence="high",
                ))

    # 8th lord influencing 7th house in D9
    lord_8 = h2l_d9.get(8)
    placed_8 = l2p_d9.get(lord_8) if lord_8 else None
    occupants_7 = _planets_in_house(d9_chart, 7)
    lord_7 = h2l_d9.get(7)
    placed_7 = l2p_d9.get(lord_7) if lord_7 else None

    if lord_8 and (placed_8 == 7 or (lord_8 in occupants_7 and lord_8 != lord_7)):
        triggered.append(_rule(
            "D9-S4-7TH-8TH-LORD-LINK",
            f"8th lord {_pname(lord_8)} in D9 7th house — separation or divorce potential",
            f"The 8th lord ({_pname(lord_8)}) placed in the 7th house of the Navamsha introduces "
            "the energy of disruption, loss, and transformation into the house of marriage within "
            "the D9 chart. This is a classical indicator of marital separation, divorce, or the "
            "death of a spouse. The native may experience a major turning point in marriage "
            "during the dasha of the 8th lord or 7th lord.",
            "negative", 5,
            {"overall": -3, "marriage": -5, "career": -1},
            confidence="medium",
        ))

    return triggered


# ── Set 5: 7th house and Venus in D9 ─────────────────────────────────────────

def _d9_s5_seventh_venus(d9_chart: dict[str, Any]) -> list[dict]:
    """7th lord and Venus placement in D9 — quality of spouse and marriage."""
    h2l, l2p = _build_lord_maps(d9_chart)
    triggered = []

    lord_7 = h2l.get(7)
    placed_7 = l2p.get(lord_7) if lord_7 else None

    if lord_7 and placed_7:
        if placed_7 in ANGLE_OR_TRINE:
            triggered.append(_rule(
                "D9-S5-7TH-LORD-ANGLE-TRINE",
                f"D9 7th lord {_pname(lord_7)} in angle/trine (house {placed_7}) — good spouse, strong marriage",
                "The 7th lord well-placed in an angular or trine house of the Navamsha confirms "
                "a good marriage and a quality spouse. In the chart of marriage (D9), the 7th "
                "lord in such a position indicates that the native marries someone of character, "
                "and the marriage is fulfilling and long-lasting.",
                "positive", 5,
                {"overall": 4, "marriage": 5, "career": 1},
                confidence="medium",
            ))
        elif placed_7 in DUSTHANA:
            triggered.append(_rule(
                "D9-S5-7TH-LORD-DUSTHANA",
                f"D9 7th lord {_pname(lord_7)} in dusthana (house {placed_7}) — difficult spouse or marital strain",
                "The 7th lord of the Navamsha placed in a dusthana (6, 8, or 12) indicates "
                "strain in marriage. Within the D9 — the chart dedicated to marriage — this "
                "weakens the primary indicator of the spouse. The native may attract a difficult "
                "partner, face conflict in marriage, or experience separation at some point.",
                "negative", 5,
                {"overall": -3, "marriage": -5, "career": -1},
                confidence="medium",
            ))
        elif placed_7 in UPACHAYA:
            triggered.append(_rule(
                "D9-S5-7TH-LORD-UPACHAYA",
                f"D9 7th lord {_pname(lord_7)} in upachaya (house {placed_7}) — higher-status spouse",
                "The 7th lord in an upachaya house (3, 6, 10, 11) of D9 indicates the spouse "
                "comes from a higher social or economic background than expected, or that the "
                "native benefits materially from the marriage. In some interpretations, upachaya "
                "placement of the 7th lord also indicates the native's marriage improves "
                "progressively over time, or suggests more than one significant relationship.",
                "positive", 3,
                {"overall": 3, "marriage": 3, "career": 2},
                confidence="low",
            ))

    # Venus in D9
    ve = d9_chart.get("planet_lookup", {}).get("Ve", {})
    if ve:
        ve_house = ve.get("house")
        ve_dignity = ve.get("dignity", "")
        if ve_house in ANGLE_OR_TRINE and ve_dignity != "debilitated":
            triggered.append(_rule(
                "D9-S5-VENUS-ANGLE-TRINE",
                f"Venus in angle/trine (house {ve_house}) of D9 — auspicious for marriage",
                "Venus in an angular or trine house of the Navamsha positions the natural "
                "significator of love and marriage in a place of strength within the chart "
                "of marriage itself. This is auspicious — the native enjoys marital happiness, "
                "a beautiful or charming spouse, and pleasures of married life.",
                "positive", 5,
                {"overall": 4, "marriage": 5, "career": 1},
                confidence="medium",
            ))
        elif ve_house in DUSTHANA and ve_dignity != "exalted":
            triggered.append(_rule(
                "D9-S5-VENUS-DUSTHANA",
                f"Venus in dusthana (house {ve_house}) of D9 — strained marital happiness",
                "Venus placed in a dusthana (6, 8, or 12) of the Navamsha places the natural "
                "karaka for marriage in a challenging position within the D9. This strains the "
                "native's capacity for marital happiness — the spouse may be difficult, "
                "marriage brings suffering, or Venus dasha brings disappointment in love.",
                "negative", 5,
                {"overall": -3, "marriage": -5, "career": -1},
                confidence="medium",
            ))

    # 8th lord in 7th of D9
    lord_8 = h2l.get(8)
    placed_8 = l2p.get(lord_8) if lord_8 else None
    if lord_8 and placed_8 == 7 and lord_8 != lord_7:
        triggered.append(_rule(
            "D9-S5-8TH-IN-7TH",
            f"D9 8th lord {_pname(lord_8)} in 7th house — marital disruption or divorce risk",
            f"The 8th lord ({_pname(lord_8)}) placed in the 7th house of the Navamsha is a "
            "strong indicator of disruption to marriage. The 8th house governs obstacles, "
            "sudden events, longevity, and endings — its lord in the house of partnership "
            "within D9 brings these energies directly to bear on marriage. Separation, "
            "divorce, or the loss of a spouse are possible outcomes depending on dasha.",
            "negative", 5,
            {"overall": -3, "marriage": -5, "career": -1},
            confidence="medium",
        ))

    return triggered


# ── Set 6: Multiple marriages and marital denial ──────────────────────────────

def _d9_s6_multiple_marriages(d9_chart: dict[str, Any]) -> list[dict]:
    """Combinations in D9 for multiple marriages, denial, or remarriage."""
    h2l, l2p = _build_lord_maps(d9_chart)
    triggered = []

    lord_1 = h2l.get(1)
    placed_1 = l2p.get(lord_1) if lord_1 else None
    lord_7 = h2l.get(7)
    placed_7 = l2p.get(lord_7) if lord_7 else None
    lord_2 = h2l.get(2)
    placed_2 = l2p.get(lord_2) if lord_2 else None
    lord_12 = h2l.get(12)
    placed_12 = l2p.get(lord_12) if lord_12 else None

    # D9 Lagna lord exalted/own/retrograde AND in kendra/trikona/11th → remarriage combination
    if lord_1 and placed_1:
        ll1_data = d9_chart.get("planet_lookup", {}).get(lord_1, {})
        ll1_dignity = ll1_data.get("dignity", "")
        ll1_retrograde = ll1_data.get("retrograde", False)
        strong_ll = ll1_dignity in {"exalted", "own_sign"} or ll1_retrograde
        in_beneficial = placed_1 in ANGLE_OR_TRINE or placed_1 == 11

        if strong_ll and in_beneficial:
            quality = "exalted" if ll1_dignity == "exalted" else ("own sign" if ll1_dignity == "own_sign" else "retrograde")
            triggered.append(_rule(
                "D9-S6-LL-STRONG-REMARRIAGE",
                f"D9 Lagna lord {_pname(lord_1)} {quality} in house {placed_1} — remarriage or strong second relationship",
                f"The D9 Lagna lord ({_pname(lord_1)}) is {quality} and placed in a powerful "
                f"house ({placed_1}) of the Navamsha. When the Lagna lord is strong and in a "
                "kendra, trikona, or 11th house of D9, classical texts indicate the possibility "
                "of multiple marriages or a strong second relationship. The native has the inner "
                "strength and karma to sustain partnership, even through disruption.",
                "positive", 4,
                {"overall": 3, "marriage": 4, "career": 1},
                confidence="low",
            ))

    # Only malefics in 7th, no benefic → denial or difficulty
    occupants_7 = _planets_in_house(d9_chart, 7)
    malefics_7 = [c for c in occupants_7 if c in MALEFICS]
    benefics_7 = [c for c in occupants_7 if c in BENEFICS]
    ju_house = d9_chart.get("planet_lookup", {}).get("Ju", {}).get("house")

    if malefics_7 and not benefics_7 and ju_house != 5:
        names = [_pname(c) for c in malefics_7]
        triggered.append(_rule(
            "D9-S6-7TH-MALEFIC-ONLY",
            f"Only malefic(s) {', '.join(names)} in D9 7th house, no benefic — difficult marriage or denial",
            f"The D9 7th house contains only malefic planets ({', '.join(names)}) with no "
            "benefic presence or Jupiter's protective aspect. In the Navamsha — the chart "
            "of marriage — a malefic-only 7th house is a strong indicator of difficulty "
            "in marriage, marital suffering, or complete denial of marriage in rare cases. "
            "The spouse or the institution of marriage brings hardship.",
            "negative", 5,
            {"overall": -3, "marriage": -5, "career": -1},
            confidence="medium",
        ))

    # 2nd + 7th + 12th lords all in upachaya → multiple marriages
    lords_in_upachaya = [
        (lord_2, placed_2, "2nd"),
        (lord_7, placed_7, "7th"),
        (lord_12, placed_12, "12th"),
    ]
    all_upachaya = all(
        lord and placed and placed in UPACHAYA
        for lord, placed, _ in lords_in_upachaya
    )
    if all_upachaya:
        triggered.append(_rule(
            "D9-S6-MULTI-UPACHAYA",
            "D9 2nd, 7th, and 12th lords all in upachaya — multiple marriages indicated",
            "When the 2nd lord (family/household), 7th lord (spouse), and 12th lord "
            "(pleasures/bed comforts) are all placed in upachaya houses (3, 6, 10, 11) of "
            "the Navamsha, classical texts indicate more than one marriage. Upachaya houses "
            "grow over time and multiply — this triplicate combination in D9 suggests the "
            "native's married life involves more than one significant partner.",
            "negative", 4,
            {"overall": -1, "marriage": -3, "career": 0},
            confidence="low",
        ))

    return triggered


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d9_navamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d9_chart = _get_d9_chart(chart_facts)
    if not d9_chart:
        return []
    d1_chart = _get_d1_chart(chart_facts)
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d9_s1_vargottam(d9_chart, d1_chart))
    triggered.extend(_d9_s2_dignity(d9_chart, d1_chart))
    triggered.extend(_d9_s3_nidhanamsha(d9_chart, d1_chart))
    triggered.extend(_d9_s4_marriage_promise(d9_chart, d1_chart))
    triggered.extend(_d9_s5_seventh_venus(d9_chart))
    triggered.extend(_d9_s6_multiple_marriages(d9_chart))
    return triggered
