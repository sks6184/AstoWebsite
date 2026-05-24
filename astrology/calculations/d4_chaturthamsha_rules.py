"""D4-specific rules from the Chaturthamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Chaturthamsha D4 (pp. 92–105).

SET 1 (Jupiter — natural happiness karaka in D4):
  D4-S1-JU-DUSTHANA           Jupiter in dusthana (6/8/12) in D4 — despair for wealth
  D4-S1-JU-LAGNA              Jupiter in D4 Lagna — strong happiness promise
  D4-S1-JU-ASPECTS-LAGNA      Jupiter in 5/7/9 → aspects D4 Lagna — happiness assured
  D4-S1-JU-4TH                Jupiter in 4th house D4 — comforts of life supported
  D4-S1-JU-ANGLE-TRINE        Jupiter in angle/trine D4 — generally strong for happiness

SET 2 (Mars — natural fixed-assets karaka in D4):
  D4-S2-MA-10TH               Mars in 10th house D4 — best placement for land/buildings
  D4-S2-MA-EXALTED            Mars exalted (Capricorn) in D4 — exceptional property karaka
  D4-S2-MA-OWN                Mars in own sign (Aries/Scorpio) in D4 — stable property karaka
  D4-S2-MA-ANGLE-TRINE        Mars in angle/trine D4 — supports property acquisition
  D4-S2-MA-DEBILITATED        Mars debilitated (Cancer) in D4 — no permanent residence
  D4-S2-MA-DUSTHANA           Mars in dusthana D4 — poor fixed-asset outcomes

SET 3 (4th lord strength and special house placements in D4):
  D4-S3-4TH-LORD-UPACHAYA     4th lord in upachaya (3/6/10/11) — many properties
  D4-S3-4TH-LORD-TRIK         4th lord in trik or debilitated — loss of property
  D4-S3-4TH-LORD-8TH          4th lord in 8th from Lagna — permanent home issues
  D4-S3-12TH-IN-4TH-{X}      12th lord in 4th house — lives in someone else's house
  D4-S3-LL-4TH-WELL-PLACED    Lagna lord and 4th lord mutually strong — happiness with home

SET 4 (Sign modality — movable/fixed in 4th house of D4):
  D4-S4-MOVABLE-BOTH          Movable sign in 4th AND 4th lord in movable sign — no permanent home
  D4-S4-FIXED-BOTH            Fixed sign in 4th AND 4th lord in fixed sign — permanent stable home

SET 5 (Settlement abroad / displacement indicators in D4):
  D4-S5-9TH-LORD-8TH          9th lord in 8th — strong displacement / foreign settlement
  D4-S5-9TH-LORD-TRIK-6-12   9th lord in 6th or 12th — change of residence within country
  D4-S5-11TH-4TH-LINK        11th lord afflicting 4th house/lord — displacement from home
  D4-S5-4TH-AFFLICTED-KETU   Ketu in 4th house D4 — loss from natural calamity
  D4-S5-4TH-MALEFIC          Malefics occupying 4th house D4 — displacement from birthplace
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Chaturthamsha D4"
_SOURCE_PAGE = "92"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
UPACHAYA = frozenset({3, 6, 10, 11})
MALEFICS = frozenset({"Su", "Ma", "Sa", "Ra", "Ke"})
MOVABLE_SIGNS = frozenset({1, 4, 7, 10})
FIXED_SIGNS = frozenset({2, 5, 8, 11})


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
        "system": "D4/ChaturthamshRules",
        "chart": "D4",
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
        "source_file": "d4_chaturthamsha_rules.py",
    }


def _get_d4_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d4", {})


def _build_lord_maps(d4_chart: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    """Return (house→lord_code, lord_code→placed_house) for all 12 houses."""
    all_pl = d4_chart.get("all_lord_placements", {})
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


def _house4_sign(d4_chart: dict[str, Any]) -> int | None:
    """Derive the sign_number occupying house 4 from D4 lagna sign."""
    lagna_sign = d4_chart.get("lagna", {}).get("sign_number")
    if not lagna_sign:
        return None
    return ((int(lagna_sign) - 1 + 3) % 12) + 1


# ── Set 1: Jupiter (natural happiness karaka) in D4 ──────────────────────────

def _d4_s1_jupiter(d4_chart: dict[str, Any]) -> list[dict]:
    """Jupiter's placement in D4 — primary happiness and wealth karaka signal."""
    ju = d4_chart.get("planet_lookup", {}).get("Ju", {})
    if not ju:
        return []

    house = ju.get("house")
    dignity = ju.get("dignity", "")
    triggered = []

    if house in DUSTHANA:
        triggered.append(_rule(
            "D4-S1-JU-DUSTHANA",
            f"Jupiter in dusthana (house {house}) in D4 — happiness karaka obstructed",
            "Jupiter in a dusthana (6, 8, or 12) in the D4 chart indicates despair and obstacles "
            "in acquiring material happiness. As the primary significator of happiness in D4, "
            "its placement here undermines property comforts, wealth satisfaction, and overall "
            "contentment during Jupiter's dasha periods.",
            "negative", 5,
            {"overall": -4, "property": -5, "career": -2},
            confidence="high",
        ))

    if house == 1:
        triggered.append(_rule(
            "D4-S1-JU-LAGNA",
            "Jupiter in D4 Lagna — strongest happiness karaka placement",
            "Jupiter occupying the D4 ascendant is the most powerful placement for happiness and "
            "property. It promises comforts from multiple sources, spiritual happiness, and strong "
            "destiny linked to real estate and fixed assets. The native derives lasting joy.",
            "positive", 6,
            {"overall": 5, "property": 6, "career": 3},
            confidence="high",
        ))
    elif house in {5, 7, 9}:
        triggered.append(_rule(
            "D4-S1-JU-ASPECTS-LAGNA",
            f"Jupiter in house {house} in D4 — aspects D4 Lagna, promising happiness",
            "Jupiter casting its full aspect on the D4 ascendant (from the 5th, 7th, or 9th house) "
            "is a strong promise of happiness and contentment. The Lagna receives Jupiter's "
            "benefic gaze, blessing the chart with the potential for property acquisition, "
            "comforts, and wealth satisfaction.",
            "positive", 5,
            {"overall": 4, "property": 5, "career": 2},
            confidence="high",
        ))

    if house == 4:
        triggered.append(_rule(
            "D4-S1-JU-4TH",
            "Jupiter in 4th house of D4 — comforts of life strongly supported",
            "Jupiter in the 4th house of D4 directly blesses the house of happiness and fixed "
            "assets. Comforts of life, including property, vehicles, and domestic peace, are "
            "well-supported. Particularly auspicious when Jupiter is also a trine lord.",
            "positive", 5,
            {"overall": 4, "property": 5, "career": 2},
            confidence="medium",
        ))
    elif house in ANGLE_OR_TRINE and house not in {1, 4}:
        triggered.append(_rule(
            "D4-S1-JU-ANGLE-TRINE",
            f"Jupiter in angle/trine (house {house}) in D4 — happiness karaka well-placed",
            "Jupiter in an angular or trine position in D4 gives the natural happiness significator "
            "visibility and strength. Property and material comforts are generally available and "
            "the native maintains a positive outlook toward wealth.",
            "positive", 4,
            {"overall": 3, "property": 4, "career": 2},
            confidence="medium",
        ))

    return triggered


# ── Set 2: Mars (natural fixed-assets karaka) in D4 ──────────────────────────

def _d4_s2_mars(d4_chart: dict[str, Any]) -> list[dict]:
    """Mars placement and dignity in D4 — primary fixed-assets and land karaka."""
    ma = d4_chart.get("planet_lookup", {}).get("Ma", {})
    if not ma:
        return []

    house = ma.get("house")
    dignity = ma.get("dignity", "")
    triggered = []

    if dignity == "exalted":
        triggered.append(_rule(
            "D4-S2-MA-EXALTED",
            f"Mars exalted in D4 (house {house}) — exceptional fixed-assets karaka strength",
            "Exalted Mars in D4 is the strongest signal for owning immovable property. Mars as "
            "the natural significator of land and built properties at peak strength ensures the "
            "native can acquire substantial real estate. Particularly strong when also in an "
            "angular or trine house.",
            "positive", 6,
            {"overall": 5, "property": 6, "career": 2},
            confidence="high",
        ))
    elif dignity == "own_sign":
        triggered.append(_rule(
            "D4-S2-MA-OWN",
            f"Mars in own sign in D4 (house {house}) — stable property karaka",
            "Mars in its own sign (Aries or Scorpio) in D4 provides reliable support for property "
            "acquisition. The fixed-assets karaka is at comfortable strength, enabling steady "
            "accumulation of land and built properties.",
            "positive", 4,
            {"overall": 3, "property": 4, "career": 2},
            confidence="high",
        ))
    elif dignity == "debilitated":
        triggered.append(_rule(
            "D4-S2-MA-DEBILITATED",
            f"Mars debilitated in D4 (house {house}) — no permanent residence indicated",
            "Debilitated Mars in D4 significantly weakens the fixed-assets karaka. The native "
            "struggles to acquire or retain immovable property. Combined with a movable sign in "
            "the 4th house, this often indicates constant movement and no stable home.",
            "negative", 5,
            {"overall": -4, "property": -5, "career": -2},
            confidence="high",
        ))

    if house == 10:
        triggered.append(_rule(
            "D4-S2-MA-10TH",
            "Mars in 10th house of D4 — best placement for granting fixed assets",
            "Mars in the 10th house of D4 is described as the single best placement for "
            "owning land and buildings. Strong Mars in the 10th of the property chart is a "
            "near-certain indicator of substantial immovable property acquisition.",
            "positive", 6,
            {"overall": 5, "property": 6, "career": 3},
            confidence="high",
        ))
    elif house in ANGLE_OR_TRINE and house != 10:
        triggered.append(_rule(
            "D4-S2-MA-ANGLE-TRINE",
            f"Mars in angle/trine (house {house}) in D4 — property acquisition supported",
            "Mars placed in an angular or trine house of D4 gives the fixed-assets karaka "
            "directional or fortune-based strength. Property acquisition is actively supported "
            "during Mars dasha periods.",
            "positive", 4,
            {"overall": 3, "property": 4, "career": 2},
            confidence="medium",
        ))
    elif house in DUSTHANA:
        triggered.append(_rule(
            "D4-S2-MA-DUSTHANA",
            f"Mars in dusthana (house {house}) in D4 — poor fixed-asset outcomes",
            "Mars in a dusthana (6, 8, or 12) in D4 weakens its ability to confer property "
            "and built assets. The native may face obstacles in property acquisition, disputes "
            "over land, or losses of fixed assets during Mars periods.",
            "negative", 4,
            {"overall": -3, "property": -4, "career": -2},
            confidence="medium",
        ))

    return triggered


# ── Set 3: 4th lord strength and special placements ───────────────────────────

def _d4_s3_fourth_lord(d4_chart: dict[str, Any]) -> list[dict]:
    """4th lord placement and special inter-house combinations in D4."""
    h2l, l2p = _build_lord_maps(d4_chart)
    triggered = []

    lord_4 = h2l.get(4)
    placed_4 = l2p.get(lord_4) if lord_4 else None
    dignity_4 = d4_chart.get("all_lord_placements", {}).get("4_lord", {}).get("dignity", "")
    lord_1 = h2l.get(1)
    placed_1 = l2p.get(lord_1) if lord_1 else None
    lord_12 = h2l.get(12)
    placed_12 = l2p.get(lord_12) if lord_12 else None

    if lord_4 and placed_4:
        if placed_4 in UPACHAYA:
            triggered.append(_rule(
                "D4-S3-4TH-LORD-UPACHAYA",
                f"4th lord {_pname(lord_4)} in upachaya house {placed_4} in D4 — many properties",
                "The 4th lord placed in an upachaya house (3, 6, 10, or 11) in D4 indicates "
                "the native acquires multiple properties over time. Upachaya houses grow with "
                "effort and age, so property accumulation builds progressively and substantially.",
                "positive", 5,
                {"overall": 4, "property": 5, "career": 2},
                confidence="medium",
            ))

        if placed_4 in DUSTHANA or dignity_4 == "debilitated":
            reason_parts = []
            if placed_4 in DUSTHANA:
                reason_parts.append(f"placed in trik house {placed_4}")
            if dignity_4 == "debilitated":
                reason_parts.append("debilitated")
            triggered.append(_rule(
                "D4-S3-4TH-LORD-TRIK",
                f"4th lord {_pname(lord_4)} {' and '.join(reason_parts)} in D4 — property loss",
                "The 4th lord badly placed (in a trik house or debilitated) in D4 is a clear "
                "indicator of property loss, difficulty in home ownership, or instability in "
                "fixed assets. Government-related loss is possible if the 10th house is also involved.",
                "negative", 5,
                {"overall": -4, "property": -5, "career": -2},
                confidence="medium",
            ))

        if placed_4 == 8:
            triggered.append(_rule(
                "D4-S3-4TH-LORD-8TH",
                f"4th lord {_pname(lord_4)} in 8th house of D4 — challenges with home/mother",
                "The 4th lord in the 8th from the D4 Lagna indicates disruption to permanent "
                "home and possible strain in the relationship with mother. The 8th placement "
                "creates a trik condition for the 4th lord, undermining stability in property matters.",
                "negative", 4,
                {"overall": -3, "property": -4, "career": -1},
                confidence="medium",
            ))

    if lord_12 and placed_12 == 4:
        triggered.append(_rule(
            f"D4-S3-12TH-IN-4TH-{lord_12}",
            f"12th lord {_pname(lord_12)} in 4th house D4 — lives in someone else's house",
            "The 12th lord placed in the 4th house of D4 is a classic indicator that the "
            "native resides in a rented home or someone else's property. Home ownership is "
            "elusive, and expenses related to residence tend to be high.",
            "negative", 4,
            {"overall": -3, "property": -4, "career": -1},
            confidence="medium",
        ))

    if lord_1 and lord_4 and lord_1 != lord_4 and placed_1 and placed_4:
        if placed_1 in ANGLE_OR_TRINE and placed_4 in ANGLE_OR_TRINE:
            triggered.append(_rule(
                "D4-S3-LL-4TH-WELL-PLACED",
                f"Lagna lord {_pname(lord_1)} and 4th lord {_pname(lord_4)} both in angle/trine D4 — happiness with home",
                "When both the Lagna lord and 4th lord are well-placed in angles or trines in D4, "
                "there is mutual harmony between the self and one's home environment. The native "
                "enjoys stable, comfortable living conditions and a warm relationship with the "
                "mother figure.",
                "positive", 4,
                {"overall": 4, "property": 4, "career": 2},
                confidence="medium",
            ))

    return triggered


# ── Set 4: Sign modality in D4's 4th house ───────────────────────────────────

def _d4_s4_modality(d4_chart: dict[str, Any]) -> list[dict]:
    """Movable vs. fixed sign in D4's 4th house combined with 4th lord sign."""
    h4_sign = _house4_sign(d4_chart)
    if not h4_sign:
        return []

    h2l, l2p = _build_lord_maps(d4_chart)
    lord_4 = h2l.get(4)
    lord_4_sign = d4_chart.get("all_lord_placements", {}).get("4_lord", {}).get("placed_sign_number")
    triggered = []

    if h4_sign in MOVABLE_SIGNS and lord_4_sign and int(lord_4_sign) in MOVABLE_SIGNS:
        triggered.append(_rule(
            "D4-S4-MOVABLE-BOTH",
            f"Movable sign in D4 4th house (sign {h4_sign}) and 4th lord {_pname(lord_4) if lord_4 else '?'} also in movable sign ({lord_4_sign}) — no permanent home",
            "When both the 4th house of D4 and the 4th lord are in movable (chara) signs, "
            "the native has no permanent or stable residence. Constant movement, frequent "
            "relocations, and inability to settle in one place characterise the life.",
            "negative", 5,
            {"overall": -3, "property": -5, "career": -1},
            confidence="medium",
        ))

    if h4_sign in FIXED_SIGNS and lord_4_sign and int(lord_4_sign) in FIXED_SIGNS:
        triggered.append(_rule(
            "D4-S4-FIXED-BOTH",
            f"Fixed sign in D4 4th house (sign {h4_sign}) and 4th lord {_pname(lord_4) if lord_4 else '?'} also in fixed sign ({lord_4_sign}) — permanent stable home",
            "A fixed (sthira) sign in D4's 4th house combined with the 4th lord also in a "
            "fixed sign gives the native a stable, permanent home. The property is retained "
            "through life and the native enjoys long-term comfort in one residence.",
            "positive", 4,
            {"overall": 3, "property": 4, "career": 1},
            confidence="medium",
        ))

    return triggered


# ── Set 5: Settlement abroad and displacement indicators ─────────────────────

def _d4_s5_displacement(d4_chart: dict[str, Any]) -> list[dict]:
    """Settlement abroad / displacement indicators in D4 (pp. 102–105)."""
    h2l, l2p = _build_lord_maps(d4_chart)
    triggered = []

    lord_9 = h2l.get(9)
    placed_9 = l2p.get(lord_9) if lord_9 else None
    lord_11 = h2l.get(11)
    placed_11 = l2p.get(lord_11) if lord_11 else None
    lord_4 = h2l.get(4)
    placed_4 = l2p.get(lord_4) if lord_4 else None

    if lord_9 and placed_9 == 8:
        triggered.append(_rule(
            "D4-S5-9TH-LORD-8TH",
            f"9th lord {_pname(lord_9)} in 8th house of D4 — strong displacement / foreign settlement",
            "The 9th lord placed in the 8th house of D4 is described as an almost certain "
            "indicator of displacement from the birthplace. The 9th (foreign lands / fortune) "
            "flowing into the 8th (upheaval / transformation) in the property chart strongly "
            "suggests settling in a foreign country or distant region — like adoption by another land.",
            "negative", 6,
            {"overall": -2, "property": -4, "foreign_travel": 5},
            confidence="high",
        ))
    elif lord_9 and placed_9 in {6, 12}:
        triggered.append(_rule(
            "D4-S5-9TH-LORD-TRIK-6-12",
            f"9th lord {_pname(lord_9)} in house {placed_9} of D4 — change of residence within country",
            "The 9th lord in the 6th or 12th house of D4 indicates the native moves away from "
            "the birthplace — typically to another city or nearby country rather than a full "
            "foreign settlement. The 8th placement is more severe; 6th/12th suggest domestic "
            "or regional relocation.",
            "negative", 4,
            {"overall": -1, "property": -3, "foreign_travel": 3},
            confidence="medium",
        ))

    if lord_11 and placed_4:
        if placed_11 == 4 or placed_11 == placed_4 or placed_4 == 11:
            triggered.append(_rule(
                "D4-S5-11TH-4TH-LINK",
                f"11th lord {_pname(lord_11)} linked to 4th house/lord in D4 — displacement from home",
                "The 11th house is the 8th from the 4th, making the 11th lord a trigger for "
                "upheaval in property and home matters. When the 11th lord is connected to the "
                "4th house or its lord in D4, it creates a condition for the native to leave "
                "their place of birth and settle elsewhere.",
                "negative", 4,
                {"overall": -2, "property": -3, "foreign_travel": 3},
                confidence="medium",
            ))

    planets_in_4 = [
        p for p in d4_chart.get("planets", [])
        if p.get("house") == 4 and p.get("code") in MALEFICS
    ]
    if planets_in_4:
        codes = [_pname(p["code"]) for p in planets_in_4]
        if any(p["code"] == "Ke" for p in planets_in_4):
            triggered.append(_rule(
                "D4-S5-4TH-AFFLICTED-KETU",
                f"Ketu in 4th house of D4 — loss of assets due to natural calamity",
                "Ketu in the 4th house of D4 indicates loss of property through events outside "
                "the native's control — typically natural calamities, sudden accidents, or "
                "unforeseen destruction. The asset loss is abrupt and hard to recover from.",
                "negative", 4,
                {"overall": -3, "property": -4, "career": -1},
                confidence="medium",
            ))
        else:
            triggered.append(_rule(
                "D4-S5-4TH-MALEFIC",
                f"Malefic(s) {', '.join(codes)} in 4th house of D4 — displacement from birthplace",
                "Malefic planets occupying the 4th house of D4 afflict the house of home and "
                "fixed assets. This is a key trigger for the native leaving the birthplace and "
                "settling in another city or country. The more malefics involved, the stronger "
                "the displacement signal.",
                "negative", 4,
                {"overall": -2, "property": -4, "foreign_travel": 3},
                confidence="medium",
            ))

    return triggered


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d4_chaturthamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d4_chart = _get_d4_chart(chart_facts)
    if not d4_chart:
        return []
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d4_s1_jupiter(d4_chart))
    triggered.extend(_d4_s2_mars(d4_chart))
    triggered.extend(_d4_s3_fourth_lord(d4_chart))
    triggered.extend(_d4_s4_modality(d4_chart))
    triggered.extend(_d4_s5_displacement(d4_chart))
    return triggered
