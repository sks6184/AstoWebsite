"""D7-specific rules from the Saptamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Saptamsha D7 (pp. 106–120).

SET 1 (D7 Lagna strength — promise of children):
  D7-S1-JU-ASPECTS-LAGNA      Jupiter in 5/7/9 → aspects D7 Lagna — strong promise
  D7-S1-LAGNA-BENEFIC         Benefic occupies D7 Lagna — children promised
  D7-S1-LAGNA-MALEFIC-ONLY    Malefics only in/aspecting Lagna, no benefic — problematic

SET 2 (Jupiter — natural children karaka in D7):
  D7-S2-JU-EXALTED            Jupiter exalted in D7 — peak children karaka strength
  D7-S2-JU-OWN               Jupiter in own sign in D7 — stable children karaka
  D7-S2-JU-ANGLE-TRINE       Jupiter in angle/trine — powerfully placed for progeny
  D7-S2-JU-DUSTHANA          Jupiter in dusthana (6/8/12) — progeny karaka obstructed
  D7-S2-JU-DEBILITATED       Jupiter debilitated — weakened children karaka

SET 3 (5th house and lord — Poorva Punya / first child):
  D7-S3-5TH-LORD-ANGLE-TRINE  5th lord in angle/trine — children and Poorva Punya strong
  D7-S3-5TH-LORD-DUSTHANA     5th lord in dusthana — challenges with first child/progeny
  D7-S3-KETU-5TH              Ketu in 5th house D7 — sorrow related to eldest child
  D7-S3-8TH-LORD-IN-5TH-{X}  8th lord in 5th house D7 — malefic affliction of progeny house
  D7-S3-ADOPTION-TRINE-AFFLICTED  Saturn/Mars aspecting both 5th and 9th — adoption combination

SET 4 (Cross-chart D1 → D7):
  D7-S4-D1-LL-DUSTHANA-{X}   D1 Lagna lord in 6/8/12 of D7 — strained relation with children

SET 5 (Special combinations in D7):
  D7-S5-9TH-RELATED-8TH      9th lord related to 8th house D7 — adoption indicator
  D7-S5-RAJYOGA-{X}-{Y}      Angle + trine lords related — intelligent/highly placed children
  D7-S5-DHANA-YOGA-{X}-{Y}   2nd+11th or 9th+2nd related — many children
  D7-S5-8TH-MALEFIC           Malefics in 8th D7 — past karma obstructing progeny
  D7-S5-LL-BENEFIC-LINK       D7 Lagna lord aspected/conjunct Moon or benefics — famous/energetic
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Saptamsha D7"
_SOURCE_PAGE = "106"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
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
        "system": "D7/SaptamshaRules",
        "chart": "D7",
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
        "source_file": "d7_saptamsha_rules.py",
    }


def _get_d7_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d7", {})


def _get_d1_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d1", {})


def _build_lord_maps(d7_chart: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    """Return (house→lord_code, lord_code→placed_house) for all 12 houses."""
    all_pl = d7_chart.get("all_lord_placements", {})
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
    """True if two lords are related: conjunct, or one placed in the other's natal house."""
    if code_a == code_b or placed_a is None or placed_b is None:
        return False
    return (
        placed_a == placed_b or
        placed_a == house_b or
        placed_b == house_a
    )


def _planets_in_house(d7_chart: dict[str, Any], house: int) -> list[str]:
    return [p["code"] for p in d7_chart.get("planets", []) if p.get("house") == house and p.get("code")]


def _jupiter_aspects_lagna(d7_chart: dict[str, Any]) -> bool:
    """Jupiter in houses 5, 7, or 9 aspects the Lagna (house 1) with full aspect."""
    ju = d7_chart.get("planet_lookup", {}).get("Ju", {})
    return ju.get("house") in {5, 7, 9}


# ── Set 1: D7 Lagna strength ──────────────────────────────────────────────────

def _d7_s1_lagna(d7_chart: dict[str, Any]) -> list[dict]:
    """Lagna strength in D7 — primary indicator of whether children are promised."""
    lagna_occupants = _planets_in_house(d7_chart, 1)
    triggered = []

    ju_house = d7_chart.get("planet_lookup", {}).get("Ju", {}).get("house")
    if ju_house in {5, 7, 9}:
        triggered.append(_rule(
            "D7-S1-JU-ASPECTS-LAGNA",
            f"Jupiter in house {ju_house} of D7 — aspects D7 Lagna, strong promise of children",
            "Jupiter casting its full aspect on the D7 Lagna is a powerful indicator that the "
            "native will have children. As the natural karaka for progeny, Jupiter's aspect on "
            "the Lagna of the Saptamsha chart is one of the clearest blessings for childbirth "
            "and the wellbeing of progeny.",
            "positive", 6,
            {"overall": 5, "children": 6, "career": 1},
            confidence="high",
        ))
    elif ju_house == 1:
        triggered.append(_rule(
            "D7-S1-JU-ASPECTS-LAGNA",
            "Jupiter in D7 Lagna — occupies and strengthens the progeny ascendant",
            "Jupiter occupying the D7 Lagna directly blesses the chart of children. This is "
            "among the strongest placements for progeny — the natural significator of children "
            "sits in the house of overall promise, assuring the birth of children and their "
            "general wellbeing.",
            "positive", 6,
            {"overall": 5, "children": 6, "career": 1},
            confidence="high",
        ))

    benefic_in_lagna = [c for c in lagna_occupants if c in BENEFICS]
    malefic_in_lagna = [c for c in lagna_occupants if c in MALEFICS]

    if benefic_in_lagna:
        names = [_pname(c) for c in benefic_in_lagna]
        triggered.append(_rule(
            "D7-S1-LAGNA-BENEFIC",
            f"Benefic(s) {', '.join(names)} in D7 Lagna — children promised",
            f"A benefic planet ({', '.join(names)}) occupying the D7 ascendant strengthens the "
            "Lagna of the Saptamsha chart. A strong Lagna is the primary condition for the "
            "promise of children — the native is likely to have progeny and enjoy a positive "
            "relationship with them.",
            "positive", 5,
            {"overall": 4, "children": 5, "career": 1},
            confidence="medium",
        ))

    if malefic_in_lagna and not benefic_in_lagna and ju_house not in {1, 5, 7, 9}:
        names = [_pname(c) for c in malefic_in_lagna]
        triggered.append(_rule(
            "D7-S1-LAGNA-MALEFIC-ONLY",
            f"Malefic(s) {', '.join(names)} in D7 Lagna with no benefic aspect — problematic progeny",
            f"Malefic planet(s) ({', '.join(names)}) occupy the D7 Lagna with no benefic "
            "aspect or Jupiter's influence. This weakens the promise of children and can "
            "indicate delays, health issues in progeny, or a strained relationship with children. "
            "The Lagna of D7 requires benefic influence to fully promise progeny.",
            "negative", 5,
            {"overall": -3, "children": -5, "career": -1},
            confidence="medium",
        ))

    return triggered


# ── Set 2: Jupiter (natural children karaka) in D7 ───────────────────────────

def _d7_s2_jupiter(d7_chart: dict[str, Any]) -> list[dict]:
    """Jupiter's placement and dignity in D7 — primary children karaka signal."""
    ju = d7_chart.get("planet_lookup", {}).get("Ju", {})
    if not ju:
        return []

    house = ju.get("house")
    dignity = ju.get("dignity", "")
    triggered = []

    if dignity == "exalted":
        triggered.append(_rule(
            "D7-S2-JU-EXALTED",
            f"Jupiter exalted in D7 (house {house}) — peak children karaka strength",
            "Exalted Jupiter in D7 is the strongest possible signal for progeny. The natural "
            "significator of children at its highest strength in the Saptamsha chart assures "
            "children of high quality — well-placed, intelligent, and successful. The native's "
            "Poorva Punya is exceptionally strong.",
            "positive", 6,
            {"overall": 5, "children": 6, "career": 2},
            confidence="high",
        ))
    elif dignity == "own_sign":
        triggered.append(_rule(
            "D7-S2-JU-OWN",
            f"Jupiter in own sign in D7 (house {house}) — stable children karaka",
            "Jupiter in its own sign (Sagittarius or Pisces) in D7 provides reliable support "
            "for progeny. Children are generally healthy and the relationship with them is warm "
            "and consistent. The native's Poorva Punya is intact.",
            "positive", 4,
            {"overall": 3, "children": 4, "career": 1},
            confidence="high",
        ))
    elif dignity == "debilitated":
        triggered.append(_rule(
            "D7-S2-JU-DEBILITATED",
            f"Jupiter debilitated in D7 (house {house}) — weakened children karaka",
            "Debilitated Jupiter in D7 significantly weakens the natural significator of "
            "children. Progeny-related results are delayed, diminished, or troubled. The "
            "native's Poorva Punya may be depleted and childbirth faces obstacles unless "
            "neechabhanga applies.",
            "negative", 5,
            {"overall": -4, "children": -5, "career": -1},
            confidence="high",
        ))

    if house in ANGLES and dignity != "debilitated":
        triggered.append(_rule(
            "D7-S2-JU-ANGLE-TRINE",
            f"Jupiter in angle (house {house}) in D7 — children karaka powerfully placed",
            "Angular Jupiter in D7 gives the natural karaka for children direct visibility "
            "and strength in the Saptamsha chart. The native is likely to have children and "
            "the progeny will be well-positioned in life. Rajyoga potential is present.",
            "positive", 5,
            {"overall": 4, "children": 5, "career": 2},
            confidence="medium",
        ))
    elif house in TRINES and house != 1 and dignity != "debilitated":
        triggered.append(_rule(
            "D7-S2-JU-ANGLE-TRINE",
            f"Jupiter in trine (house {house}) in D7 — children karaka fortunately placed",
            "Jupiter in a trikona of D7 connects the children karaka with fortune and Poorva "
            "Punya. Progeny comes through blessings of past karma and children tend to be "
            "virtuous and blessed.",
            "positive", 4,
            {"overall": 3, "children": 4, "career": 1},
            confidence="medium",
        ))
    elif house in DUSTHANA:
        triggered.append(_rule(
            "D7-S2-JU-DUSTHANA",
            f"Jupiter in dusthana (house {house}) in D7 — children karaka obstructed",
            "Jupiter in a dusthana (6, 8, or 12) of D7 places the natural karaka for children "
            "in a difficult position. Progeny-related results are inconsistent — delays, health "
            "concerns in children, or emotional distance from progeny during Jupiter's dasha.",
            "negative", 4,
            {"overall": -3, "children": -4, "career": -1},
            confidence="medium",
        ))

    return triggered


# ── Set 3: 5th house and lord in D7 ──────────────────────────────────────────

def _d7_s3_fifth_house(d7_chart: dict[str, Any]) -> list[dict]:
    """5th house analysis in D7 — Poorva Punya, first child, and progeny afflictions."""
    h2l, l2p = _build_lord_maps(d7_chart)
    triggered = []

    lord_5 = h2l.get(5)
    placed_5 = l2p.get(lord_5) if lord_5 else None
    lord_8 = h2l.get(8)
    placed_8 = l2p.get(lord_8) if lord_8 else None
    lord_9 = h2l.get(9)
    placed_9 = l2p.get(lord_9) if lord_9 else None

    occupants_5 = _planets_in_house(d7_chart, 5)
    occupants_9 = _planets_in_house(d7_chart, 9)

    if lord_5 and placed_5:
        if placed_5 in ANGLE_OR_TRINE:
            triggered.append(_rule(
                "D7-S3-5TH-LORD-ANGLE-TRINE",
                f"5th lord {_pname(lord_5)} in angle/trine (house {placed_5}) in D7 — progeny and Poorva Punya strong",
                "The 5th lord well-placed in an angular or trine house of D7 strengthens the "
                "house of Poorva Punya and first child. This is a positive signal for both "
                "the promise of progeny and the quality of children. The native's past-life "
                "merit actively supports childbirth and the wellbeing of offspring.",
                "positive", 5,
                {"overall": 4, "children": 5, "career": 1},
                confidence="medium",
            ))
        elif placed_5 in DUSTHANA:
            triggered.append(_rule(
                "D7-S3-5TH-LORD-DUSTHANA",
                f"5th lord {_pname(lord_5)} in dusthana (house {placed_5}) in D7 — challenges with progeny",
                "The 5th lord placed in a dusthana (6, 8, or 12) of D7 weakens the house of "
                "Poorva Punya and first child. This indicates challenges related to progeny — "
                "delays, health concerns, or emotional difficulty with children. The native's "
                "past-life merit requires effort to activate.",
                "negative", 5,
                {"overall": -3, "children": -5, "career": -1},
                confidence="medium",
            ))

    if "Ke" in occupants_5:
        triggered.append(_rule(
            "D7-S3-KETU-5TH",
            "Ketu in 5th house of D7 — sorrow related to eldest child",
            "Ketu occupying the 5th house of the Saptamsha chart is associated with sorrow "
            "connected to the eldest child. The 5th house in D7 represents the first child "
            "and Poorva Punya; Ketu's separative, shadowy influence here can indicate loss, "
            "premature events, or karmic difficulty with the firstborn.",
            "negative", 5,
            {"overall": -3, "children": -5, "career": -1},
            confidence="medium",
        ))

    if lord_8 and placed_8 == 5 and lord_8 != lord_5:
        triggered.append(_rule(
            f"D7-S3-8TH-LORD-IN-5TH-{lord_8}",
            f"8th lord {_pname(lord_8)} in 5th house of D7 — malefic affliction of progeny house",
            "The 8th lord placed in the 5th house of D7 brings the energy of obstacles, "
            "karmic debt, and longevity concerns into the house of children. This combination "
            "can indicate health issues in children, difficult childbirth, or obstacles "
            "related to the first child's wellbeing.",
            "negative", 4,
            {"overall": -3, "children": -4, "career": -1},
            confidence="medium",
        ))

    sa_ma = {"Sa", "Ma"}
    aspects_5_from = set()
    aspects_9_from = set()
    for p in d7_chart.get("planets", []):
        code = p.get("code")
        h = p.get("house")
        if not code or not h:
            continue
        if code in sa_ma:
            # Saturn and Mars cast full aspect to 3rd, 7th, 10th from self (Saturn also 10th, Mars also 4th, 8th)
            # Simplified: check if 5th or 9th is in their aspect houses
            # Saturn aspects 3rd, 7th, 10th from itself
            # Mars aspects 4th, 7th, 8th from itself
            sat_aspects = {((h + 2) % 12) or 12, ((h + 6) % 12) or 12, ((h + 9) % 12) or 12}
            mar_aspects = {((h + 3) % 12) or 12, ((h + 6) % 12) or 12, ((h + 7) % 12) or 12}
            if code == "Sa":
                if 5 in sat_aspects:
                    aspects_5_from.add(code)
                if 9 in sat_aspects:
                    aspects_9_from.add(code)
            elif code == "Ma":
                if 5 in mar_aspects:
                    aspects_5_from.add(code)
                if 9 in mar_aspects:
                    aspects_9_from.add(code)

    both_afflicted = (aspects_5_from | (sa_ma & set(occupants_5))) and (aspects_9_from | (sa_ma & set(occupants_9)))
    if both_afflicted:
        afflictors = sorted((aspects_5_from | aspects_9_from | (sa_ma & set(occupants_5)) | (sa_ma & set(occupants_9))))
        names = [_pname(c) for c in afflictors]
        triggered.append(_rule(
            "D7-S3-ADOPTION-TRINE-AFFLICTED",
            f"{', '.join(names)} afflict both 5th and 9th houses in D7 — adoption combination",
            f"When malefics ({', '.join(names)}) afflict both the 5th (first child/Poorva Punya) "
            "and 9th (grandchildren/fortune) houses in D7, the trines of the chart are damaged. "
            "This is the classical combination pointing toward adoption rather than biological "
            "children — the own progeny is denied or difficult while the native may nurture "
            "another's child.",
            "negative", 4,
            {"overall": -2, "children": -4, "career": -1},
            confidence="medium",
        ))

    return triggered


# ── Set 4: Cross-chart D1 → D7 ───────────────────────────────────────────────

def _d7_s4_cross_chart(d7_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """D1 Lagna lord's placement in D7 — cross-chart relationship with children."""
    if not d1_chart:
        return []

    d1_ll_data = d1_chart.get("all_lord_placements", {}).get("1_lord", {})
    d1_ll = d1_ll_data.get("lord")
    if not d1_ll:
        return []

    d7_placement = d7_chart.get("planet_lookup", {}).get(d1_ll, {})
    d7_house = d7_placement.get("house")
    if not d7_house:
        return []

    triggered = []

    if d7_house in DUSTHANA:
        triggered.append(_rule(
            f"D7-S4-D1-LL-DUSTHANA-{d1_ll}",
            f"D1 Lagna lord {_pname(d1_ll)} in dusthana (house {d7_house}) of D7 — strained relation with children",
            f"The Lagna lord of the birth chart ({_pname(d1_ll)}) placed in a dusthana "
            f"(house {d7_house}) of the Saptamsha chart indicates the native does not enjoy "
            "a good or cordial relationship with their own children. Emotional distance, "
            "misunderstanding, or life circumstances keep parent and child apart. This is "
            "one of the key cross-chart indicators for progeny relations.",
            "negative", 5,
            {"overall": -3, "children": -5, "career": -1},
            confidence="high",
        ))
    elif d7_house in ANGLE_OR_TRINE:
        triggered.append(_rule(
            f"D7-S4-D1-LL-WELL-PLACED-{d1_ll}",
            f"D1 Lagna lord {_pname(d1_ll)} in angle/trine (house {d7_house}) of D7 — good relation with children",
            f"The birth chart's Lagna lord ({_pname(d1_ll)}) placed in an angular or trine "
            "house of D7 indicates the native enjoys a warm and supportive relationship with "
            "their children. The self is well-connected to progeny through the Saptamsha chart.",
            "positive", 4,
            {"overall": 3, "children": 4, "career": 1},
            confidence="high",
        ))

    return triggered


# ── Set 5: Special combinations in D7 ────────────────────────────────────────

def _d7_s5_combinations(d7_chart: dict[str, Any]) -> list[dict]:
    """Special yogas and combinations in D7 — adoption, Rajyoga, Dhana yoga."""
    h2l, l2p = _build_lord_maps(d7_chart)
    triggered = []

    lord_9 = h2l.get(9)
    placed_9 = l2p.get(lord_9) if lord_9 else None
    lord_8 = h2l.get(8)
    placed_8 = l2p.get(lord_8) if lord_8 else None
    lord_2 = h2l.get(2)
    placed_2 = l2p.get(lord_2) if lord_2 else None
    lord_11 = h2l.get(11)
    placed_11 = l2p.get(lord_11) if lord_11 else None
    lord_1 = h2l.get(1)
    placed_1 = l2p.get(lord_1) if lord_1 else None

    # 9th lord related to 8th house → adoption
    if lord_9 and placed_9 and lord_8:
        if placed_9 == 8 or placed_8 == 9 or placed_9 == placed_8:
            triggered.append(_rule(
                "D7-S5-9TH-RELATED-8TH",
                f"9th lord {_pname(lord_9)} related to 8th house in D7 — adoption combination",
                "The 9th lord (grandchildren/fortune of progeny) related to the 8th house "
                "(obstructions, past karma) in D7 is the classical indicator for adoption. "
                "The native's path to children passes through upheaval or karmic debt rather "
                "than natural biological birth — adoption is a likely outcome.",
                "negative", 4,
                {"overall": -1, "children": -3, "career": 0},
                confidence="medium",
            ))

    # Rajyoga: angle lord + trine lord related
    angle_lords = {h2l[h] for h in ANGLES if h in h2l}
    trine_lords = {h2l[h] for h in TRINES if h in h2l}
    rajyoga_found = False
    for al in angle_lords:
        for tl in trine_lords:
            if al == tl:
                continue
            if _lords_related(al, _house_of(h2l, al), l2p.get(al), tl, _house_of(h2l, tl), l2p.get(tl)):
                if not rajyoga_found:
                    triggered.append(_rule(
                        f"D7-S5-RAJYOGA-{al}-{tl}",
                        f"Rajyoga in D7: {_pname(al)} (angle lord) related to {_pname(tl)} (trine lord)",
                        f"A Rajyoga formed by the angle lord {_pname(al)} and trine lord {_pname(tl)} "
                        "in D7 is a powerful indicator. Rajyoga in the Saptamsha gives highly "
                        "placed or exceptionally intelligent children. The native may also be "
                        "very intelligent themselves — the D7 Rajyoga reflects the quality of "
                        "Poorva Punya inherited from past lives.",
                        "positive", 5,
                        {"overall": 4, "children": 5, "career": 2},
                        confidence="medium",
                    ))
                    rajyoga_found = True
                break

    # Dhana yoga: 2nd + 11th related OR 9th + 2nd related
    dhana_found = False
    if lord_2 and lord_11 and lord_2 != lord_11:
        if _lords_related(lord_2, 2, placed_2, lord_11, 11, placed_11):
            triggered.append(_rule(
                f"D7-S5-DHANA-YOGA-{lord_2}-{lord_11}",
                f"Dhana yoga in D7: 2nd lord {_pname(lord_2)} related to 11th lord {_pname(lord_11)} — many children",
                "A Dhana yoga formed by the 2nd and 11th lords in D7 indicates abundance of "
                "progeny. In the Saptamsha context, dhana yoga translates to many children — "
                "the saptamsha wealth is measured in progeny and their prosperity.",
                "positive", 5,
                {"overall": 4, "children": 5, "career": 1},
                confidence="medium",
            ))
            dhana_found = True

    if not dhana_found and lord_9 and lord_2 and lord_9 != lord_2:
        if _lords_related(lord_9, 9, placed_9, lord_2, 2, placed_2):
            triggered.append(_rule(
                f"D7-S5-DHANA-YOGA-{lord_9}-{lord_2}",
                f"Dhana yoga in D7: 9th lord {_pname(lord_9)} related to 2nd lord {_pname(lord_2)} — many children",
                "The 9th lord (fortune/grandchildren) related to the 2nd lord in D7 forms a "
                "dhana yoga for the Saptamsha chart. This indicates multiple children and "
                "fortunate progeny who bring prosperity to the family.",
                "positive", 5,
                {"overall": 4, "children": 5, "career": 1},
                confidence="medium",
            ))

    # Malefics in 8th house D7
    malefics_in_8 = [_pname(c) for c in _planets_in_house(d7_chart, 8) if c in MALEFICS]
    if malefics_in_8:
        triggered.append(_rule(
            "D7-S5-8TH-MALEFIC",
            f"Malefic(s) {', '.join(malefics_in_8)} in 8th house of D7 — past karma obstructing progeny",
            "The 8th house of D7 represents karmas from past lives that obstruct the birth "
            "of progeny. Malefic planets here activate that obstruction — creating delays, "
            "obstacles, or denials related to children. This is the past-life debt dimension "
            "of the Saptamsha chart working against progeny.",
            "negative", 4,
            {"overall": -3, "children": -4, "career": -1},
            confidence="medium",
        ))

    # D7 Lagna lord aspected/conjunct by Moon or benefics
    if lord_1 and placed_1:
        cotenants = _planets_in_house(d7_chart, placed_1)
        benefic_linked = any(c in BENEFICS and c != lord_1 for c in cotenants)
        if not benefic_linked:
            mo = d7_chart.get("planet_lookup", {}).get("Mo", {})
            if mo.get("house") == placed_1:
                benefic_linked = True
        if benefic_linked:
            triggered.append(_rule(
                "D7-S5-LL-BENEFIC-LINK",
                f"D7 Lagna lord {_pname(lord_1)} conjoined with Moon or benefic — energetic children, fame",
                "The D7 Lagna lord associated with Moon or a benefic planet in the Saptamsha "
                "chart (Mansagri combination) gives the native energetic, famous children. "
                "The native themselves will have many friends, energy, and public recognition "
                "connected to their progeny lineage.",
                "positive", 3,
                {"overall": 3, "children": 3, "career": 1},
                confidence="low",
            ))

    return triggered


def _house_of(h2l: dict[int, str], lord_code: str) -> int:
    """Return the house number that a lord rules (reverse lookup)."""
    for h, l in h2l.items():
        if l == lord_code:
            return h
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d7_saptamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d7_chart = _get_d7_chart(chart_facts)
    if not d7_chart:
        return []
    d1_chart = _get_d1_chart(chart_facts)
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d7_s1_lagna(d7_chart))
    triggered.extend(_d7_s2_jupiter(d7_chart))
    triggered.extend(_d7_s3_fifth_house(d7_chart))
    triggered.extend(_d7_s4_cross_chart(d7_chart, d1_chart))
    triggered.extend(_d7_s5_combinations(d7_chart))
    return triggered
