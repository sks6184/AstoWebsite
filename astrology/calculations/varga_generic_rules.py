"""Generic divisional chart rules applicable to all vargas (GDC-01 to GDC-16).

Rules from: Comprehensive Prediction by Divisional Charts — General Rules chapter.
11 fully deterministic rules implemented here. 3 partial rules (combustion,
neechabhanga, mooltrikona) are deferred until supporting data is added to chart_data.

Evaluated rules:
  GDC-01  Key planet placement (D1 lagna lord, div lagna lord, category karaka)
  GDC-02  Exception placements (Mars 6th, Mercury 8th, Venus 12th in D9)
  GDC-03  Double affliction (dusthana in D1 AND dusthana in divisional)
  GDC-06  Kartari on divisional Lagna (subha/papa)
  GDC-07  Vargottam Lagna (same sign as D1)
  GDC-09  Rahu/Ketu or 8th lord in divisional Lagna
  GDC-10  Raj Yoga in divisional (angle+trine lord conjunction or exchange)
  GDC-11  Dhana Yoga in divisional (2nd/11th lord combination)
  GDC-12  Category karaka in dusthana of divisional (Rule 15)
  GDC-13  Key lords in 3rd or 8th — death-like for signification (Rule 16)
  GDC-14  Chart-specific karaka in own divisional Lagna (Rule 17)
  GDC-15  Vargottam planet — same sign in D1 and divisional (Rule 11)
  GDC-16  D1 Lagna lord dignity in D1/D3/D9/D12 (Rule 14)
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES
from chat.prediction_context import CATEGORY_RULES


NATURAL_MALEFICS = frozenset({"Sa", "Ma", "Ra", "Ke"})
NATURAL_BENEFICS = frozenset({"Ju", "Ve", "Me", "Mo"})

ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
DUSTHANA = frozenset({6, 8, 12})
DEATH_HOUSES = frozenset({3, 8})

# Chart-specific natural karakas per divisional (Rule 1 / Rule 17)
CHART_NATURAL_KARAKAS: dict[str, list[str]] = {
    "d2": ["Mo"],
    "d3": ["Ma", "Ju"],
    "d4": ["Ma", "Mo"],
    "d7": ["Ju"],
    "d9": ["Ve"],
    "d10": ["Su", "Me", "Sa"],
    "d12": ["Su", "Mo"],
    "d16": ["Ve"],
    "d20": ["Ju", "Sa"],
    "d24": ["Me", "Ju"],
    "d27": ["Ma", "Sa"],
    "d30": ["Ma"],
    "d40": ["Mo"],
    "d45": ["Su"],
    "d60": ["Sa"],
}

# Karakas whose presence in their own divisional Lagna is specifically bad (Rule 17)
KARAKA_IN_OWN_LAGNA_BAD: dict[str, list[str]] = {
    "d3": ["Ma", "Ju"],
    "d7": ["Ju"],
    "d9": ["Ve"],
    "d12": ["Su", "Mo"],
    "d24": ["Me"],
}

_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "General Rules for All Divisional Charts"


def _get_d1_lagna_lord(chart_facts: dict) -> str | None:
    return (
        chart_facts.get("varga", {})
        .get("charts", {})
        .get("d1", {})
        .get("all_lord_placements", {})
        .get("1_lord", {})
        .get("lord")
    )


def _get_category_karakas(category: str) -> list[str]:
    return CATEGORY_RULES.get(category, {}).get("natural_karakas", [])


def _chart(chart_facts: dict, chart_key: str) -> dict:
    return chart_facts.get("varga", {}).get("charts", {}).get(chart_key, {})


def _planet(chart: dict, code: str) -> dict:
    return chart.get("planet_lookup", {}).get(code, {})


def _lagna_lord(chart: dict) -> dict:
    return chart.get("all_lord_placements", {}).get("1_lord", {})


def _house_lord(chart: dict, house: int) -> dict:
    return chart.get("all_lord_placements", {}).get(f"{house}_lord", {})


def _rule(
    rule_id: str,
    chart_key: str,
    reason: str,
    interpretation: str,
    polarity: str,
    weight: int,
    outcomes: dict,
    confidence: str = "medium",
) -> dict:
    return {
        "rule_id": rule_id,
        "system": "Divisional/Generic",
        "chart": chart_key.upper(),
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
        "source_page": "",
        "source_file": "varga_generic_rules.py",
    }


# ── GDC-01: Key planet placement ────────────────────────────────────────────

def _gdc_01(
    chart_facts: dict,
    chart_keys: list[str],
    d1_lagna_lord: str | None,
    category_karakas: list[str],
) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        def _placement_rules(code: str, label: str, base_weight: int) -> list[dict]:
            results = []
            p = _planet(ch, code)
            house = p.get("house")
            if not house:
                return results
            name = PLANET_NAMES.get(code, code)
            if house in ANGLE_OR_TRINE and house != 1:
                results.append(_rule(
                    f"GDC_01_{label}_{ck.upper()}_ANGLE_TRINE",
                    ck,
                    f"{name} ({label.replace('_', ' ').lower()}) in house {house} (angle/trine) in {ck.upper()}.",
                    f"{name} well placed in angle or trine in {ck.upper()} supports the chart's signification.",
                    "positive", base_weight, {"placement_quality_score": 3},
                ))
            elif house == 1 and label.startswith("KARAKA"):
                results.append(_rule(
                    f"GDC_01_{label}_{ck.upper()}_LAGNA",
                    ck,
                    f"Category karaka {name} is in Lagna (house 1) of {ck.upper()}.",
                    f"A category karaka in the Lagna of {ck.upper()} acts as karaka-in-bhava — classical texts consider this unfavorable for the chart's signification.",
                    "negative", base_weight, {"placement_quality_score": -3},
                ))
            elif house in {2, 11}:
                results.append(_rule(
                    f"GDC_01_{label}_{ck.upper()}_2_11",
                    ck,
                    f"{name} ({label.replace('_', ' ').lower()}) in house {house} in {ck.upper()}.",
                    f"{name} in 2nd or 11th of {ck.upper()} gives moderate support to the chart's signification.",
                    "positive", max(base_weight - 2, 3), {"placement_quality_score": 2},
                ))
            elif house in DUSTHANA:
                results.append(_rule(
                    f"GDC_01_{label}_{ck.upper()}_DUSTHANA",
                    ck,
                    f"{name} ({label.replace('_', ' ').lower()}) in house {house} (dusthana) in {ck.upper()}.",
                    f"{name} in a dusthana of {ck.upper()} weakens delivery — classical texts state this holds even in exaltation.",
                    "negative", base_weight, {"placement_quality_score": -3},
                ))
            return results

        if d1_lagna_lord:
            triggered.extend(_placement_rules(d1_lagna_lord, "D1_LAGNA_LORD", 6))

        div_ll = _lagna_lord(ch)
        ll_code = div_ll.get("lord")
        ll_placed = div_ll.get("placed_house")
        if ll_code and ll_placed:
            ll_name = PLANET_NAMES.get(ll_code, ll_code)
            if ll_placed in ANGLE_OR_TRINE:
                triggered.append(_rule(
                    f"GDC_01_DIV_LL_{ck.upper()}_ANGLE_TRINE",
                    ck,
                    f"{ck.upper()} Lagna lord {ll_name} is in house {ll_placed} (angle/trine).",
                    f"The {ck.upper()} Lagna lord well placed in angle or trine strongly supports the chart's promise.",
                    "positive", 7, {"placement_quality_score": 4},
                ))
            elif ll_placed in {2, 11}:
                triggered.append(_rule(
                    f"GDC_01_DIV_LL_{ck.upper()}_2_11",
                    ck,
                    f"{ck.upper()} Lagna lord {ll_name} is in house {ll_placed}.",
                    f"The {ck.upper()} Lagna lord in 2nd or 11th gives moderate but useful support.",
                    "positive", 5, {"placement_quality_score": 2},
                ))
            elif ll_placed in DUSTHANA:
                triggered.append(_rule(
                    f"GDC_01_DIV_LL_{ck.upper()}_DUSTHANA",
                    ck,
                    f"{ck.upper()} Lagna lord {ll_name} is in house {ll_placed} (dusthana).",
                    f"The {ck.upper()} Lagna lord in a dusthana weakens the chart's capacity to deliver results.",
                    "negative", 7, {"placement_quality_score": -4},
                ))

        for karaka_code in category_karakas:
            triggered.extend(_placement_rules(karaka_code, f"KARAKA_{karaka_code}", 6))

    return triggered


# ── GDC-02: Exception placements ────────────────────────────────────────────

def _gdc_02(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        ma = _planet(ch, "Ma")
        if ma.get("house") == 6:
            triggered.append(_rule(
                f"GDC_02_MARS_6TH_{ck.upper()}",
                ck,
                f"Mars is in the 6th house of {ck.upper()} — classical exception applies.",
                f"Mars in 6th of {ck.upper()} is a classical exception: it defeats enemies and obstacles for the chart's signification rather than harming it.",
                "positive", 5, {"placement_quality_score": 2, "obstacle_removal_score": 2},
            ))

        me = _planet(ch, "Me")
        if me.get("house") == 8:
            triggered.append(_rule(
                f"GDC_02_MERCURY_8TH_{ck.upper()}",
                ck,
                f"Mercury is in the 8th house of {ck.upper()} — classical exception applies.",
                f"Mercury in the 8th of {ck.upper()} is a classical exception: Mercury is considered favourable in the 8th of any divisional chart.",
                "positive", 5, {"placement_quality_score": 2},
            ))

        if ck == "d9":
            ve = _planet(ch, "Ve")
            if ve.get("house") == 12:
                triggered.append(_rule(
                    "GDC_02_VENUS_12TH_D9",
                    "d9",
                    "Venus is in the 12th house of D9 — classical exception applies.",
                    "Venus in 12th of Navamsha is a classical exception: despite the dusthana, this placement is considered good for the spouse and marital happiness.",
                    "positive", 5, {"marriage_score": 2, "placement_quality_score": 2},
                ))

    return triggered


# ── GDC-03: Double affliction ────────────────────────────────────────────────

def _gdc_03(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    d1 = _chart(chart_facts, "d1")
    if not d1:
        return triggered

    for ck in chart_keys:
        if ck == "d1":
            continue
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        for planet_data in ch.get("planets", []):
            code = planet_data.get("code")
            if not code or code == "Asc":
                continue
            if planet_data.get("house") not in DUSTHANA:
                continue
            d1_house = d1.get("planet_lookup", {}).get(code, {}).get("house")
            if d1_house in DUSTHANA:
                name = PLANET_NAMES.get(code, code)
                triggered.append(_rule(
                    f"GDC_03_DOUBLE_AFFLICTION_{code}_{ck.upper()}",
                    ck,
                    f"{name} is in dusthana in both D1 (house {d1_house}) and {ck.upper()} (house {planet_data['house']}).",
                    f"Double affliction: {name} poorly placed in the birth chart and again in {ck.upper()} cannot give good results for the chart's signification.",
                    "negative", 8, {"placement_quality_score": -5},
                ))

    return triggered


# ── GDC-06: Kartari on Lagna ─────────────────────────────────────────────────

def _gdc_06(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        planets = ch.get("planets", [])
        h2 = {p.get("code") for p in planets if p.get("house") == 2 and p.get("code") and p.get("code") != "Asc"}
        h12 = {p.get("code") for p in planets if p.get("house") == 12 and p.get("code") and p.get("code") != "Asc"}

        if not h2 or not h12:
            continue

        benefic_2 = bool(h2 & NATURAL_BENEFICS)
        benefic_12 = bool(h12 & NATURAL_BENEFICS)
        malefic_2 = bool(h2 & NATURAL_MALEFICS)
        malefic_12 = bool(h12 & NATURAL_MALEFICS)

        if benefic_2 and benefic_12:
            triggered.append(_rule(
                f"GDC_06_SUBHA_KARTARI_{ck.upper()}",
                ck,
                f"Subha Kartari on {ck.upper()} Lagna: benefics in 2nd and 12th flank the Lagna.",
                f"Subha Kartari on the {ck.upper()} Lagna strengthens it, improving the chart's capacity to deliver its significations.",
                "positive", 7, {"lagna_strength_score": 4},
            ))
        elif malefic_2 and malefic_12:
            triggered.append(_rule(
                f"GDC_06_PAPA_KARTARI_{ck.upper()}",
                ck,
                f"Papa Kartari on {ck.upper()} Lagna: malefics in 2nd and 12th surround the Lagna.",
                f"Papa Kartari on the {ck.upper()} Lagna weakens it, reducing the chart's ability to deliver its significations.",
                "negative", 7, {"lagna_strength_score": -4},
            ))

    return triggered


# ── GDC-07: Vargottam Lagna ──────────────────────────────────────────────────

def _gdc_07(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    d1_lagna_sign = _chart(chart_facts, "d1").get("lagna", {}).get("sign_number")
    if not d1_lagna_sign:
        return triggered

    for ck in chart_keys:
        if ck == "d1":
            continue
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        div_lagna = ch.get("lagna", {})
        if div_lagna.get("sign_number") != d1_lagna_sign:
            continue

        sign_name = div_lagna.get("sign", "")
        ll = _lagna_lord(ch)
        ll_placed = ll.get("placed_house")

        if ll_placed in DUSTHANA:
            triggered.append(_rule(
                f"GDC_07_VARGOTTAM_LAGNA_WEAK_{ck.upper()}",
                ck,
                f"{ck.upper()} Lagna is Vargottam ({sign_name}) but Lagna lord is in house {ll_placed}.",
                f"Vargottam Lagna in {ck.upper()} is auspicious in principle, but the Lagna lord in a dusthana reduces results to potential only — the promise may remain unrealized.",
                "mixed", 6, {"placement_quality_score": 1},
            ))
        else:
            triggered.append(_rule(
                f"GDC_07_VARGOTTAM_LAGNA_{ck.upper()}",
                ck,
                f"{ck.upper()} Lagna is Vargottam ({sign_name}) with Lagna lord well placed.",
                f"Vargottam Lagna with a well-placed Lagna lord in {ck.upper()} is highly auspicious — the chart's significations are strongly supported.",
                "positive", 8, {"placement_quality_score": 5, "lagna_strength_score": 3},
            ))

    return triggered


# ── GDC-09: Rahu/Ketu or 8th lord in Lagna ──────────────────────────────────

def _gdc_09(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        eighth_lord_code = _house_lord(ch, 8).get("lord")
        lagna_occupants = [
            p for p in ch.get("planets", [])
            if p.get("house") == 1 and p.get("code") and p.get("code") != "Asc"
        ]

        for p in lagna_occupants:
            code = p.get("code")
            name = PLANET_NAMES.get(code, code)

            if code in {"Ra", "Ke"}:
                triggered.append(_rule(
                    f"GDC_09_{code}_LAGNA_{ck.upper()}",
                    ck,
                    f"{'Rahu' if code == 'Ra' else 'Ketu'} is in the Lagna of {ck.upper()}.",
                    f"{'Rahu' if code == 'Ra' else 'Ketu'} in the {ck.upper()} Lagna causes stress and disruption for the chart's significations.",
                    "negative", 6, {"placement_quality_score": -3, "stress_score": 2},
                ))

            if code == eighth_lord_code:
                triggered.append(_rule(
                    f"GDC_09_8TH_LORD_LAGNA_{ck.upper()}",
                    ck,
                    f"The 8th lord ({name}) is placed in the Lagna of {ck.upper()}.",
                    f"The 8th lord in the {ck.upper()} Lagna brings obstruction, hidden pressure, and disruption to the chart's significations.",
                    "negative", 6, {"placement_quality_score": -3, "stress_score": 2},
                ))

    return triggered


# ── GDC-10: Raj Yoga in divisional ──────────────────────────────────────────

def _gdc_10(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    ANGLE_H = [1, 4, 7, 10]
    TRINE_H = [5, 9]

    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        all_pl = ch.get("all_lord_placements", {})
        house_to_lord: dict[int, str] = {}
        lord_to_placed: dict[str, int] = {}

        for h in range(1, 13):
            pl = all_pl.get(f"{h}_lord", {})
            lord = pl.get("lord")
            placed = pl.get("placed_house")
            if lord:
                house_to_lord[h] = lord
                lord_to_placed[lord] = placed

        seen: set[frozenset] = set()

        for angle_h in ANGLE_H:
            for trine_h in TRINE_H:
                al = house_to_lord.get(angle_h)
                tl = house_to_lord.get(trine_h)
                if not al or not tl or al == tl:
                    continue

                pair = frozenset({f"{angle_h}:{al}", f"{trine_h}:{tl}"})
                if pair in seen:
                    continue
                seen.add(pair)

                al_placed = lord_to_placed.get(al)
                tl_placed = lord_to_placed.get(tl)
                al_name = PLANET_NAMES.get(al, al)
                tl_name = PLANET_NAMES.get(tl, tl)

                if al_placed and tl_placed and al_placed == tl_placed and al_placed not in DUSTHANA:
                    triggered.append(_rule(
                        f"GDC_10_RAJ_YOGA_CONJ_{ck.upper()}_{al}_{tl}",
                        ck,
                        f"Raj Yoga in {ck.upper()}: {angle_h}th lord ({al_name}) and {trine_h}th lord ({tl_name}) conjunct in house {al_placed}.",
                        f"Raj Yoga by conjunction in {ck.upper()} elevates the chart's signification — most powerful during dasha of either participating planet.",
                        "positive", 8, {"raj_yoga_score": 4, "placement_quality_score": 3},
                    ))
                elif al_placed == trine_h and tl_placed == angle_h:
                    triggered.append(_rule(
                        f"GDC_10_RAJ_YOGA_EXCHANGE_{ck.upper()}_{al}_{tl}",
                        ck,
                        f"Raj Yoga by exchange in {ck.upper()}: {angle_h}th lord ({al_name}) in {trine_h}th, {trine_h}th lord ({tl_name}) in {angle_h}th.",
                        f"Raj Yoga by parivartana (exchange) in {ck.upper()} gives strong elevation of the chart's signification during relevant dasha periods.",
                        "positive", 9, {"raj_yoga_score": 5, "placement_quality_score": 4},
                    ))

    return triggered


# ── GDC-11: Dhana Yoga in divisional ────────────────────────────────────────

def _gdc_11(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    DHANA_PAIRS = [
        (2, 11, "wealth and gains"),
        (1, 2, "self and wealth"),
        (2, 9, "wealth and fortune"),
        (9, 11, "fortune and gains"),
    ]

    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        all_pl = ch.get("all_lord_placements", {})
        house_to_lord: dict[int, str] = {}
        lord_to_placed: dict[str, int] = {}

        for h in range(1, 13):
            pl = all_pl.get(f"{h}_lord", {})
            lord = pl.get("lord")
            placed = pl.get("placed_house")
            if lord:
                house_to_lord[h] = lord
                lord_to_placed[lord] = placed

        seen: set[frozenset] = set()

        for h1, h2, label in DHANA_PAIRS:
            l1 = house_to_lord.get(h1)
            l2 = house_to_lord.get(h2)
            if not l1 or not l2 or l1 == l2:
                continue

            pair = frozenset({f"{h1}:{l1}", f"{h2}:{l2}"})
            if pair in seen:
                continue
            seen.add(pair)

            p1 = lord_to_placed.get(l1)
            p2 = lord_to_placed.get(l2)
            n1 = PLANET_NAMES.get(l1, l1)
            n2 = PLANET_NAMES.get(l2, l2)

            if p1 and p2 and p1 == p2 and p1 not in DUSTHANA:
                triggered.append(_rule(
                    f"GDC_11_DHANA_YOGA_CONJ_{ck.upper()}_{l1}_{l2}",
                    ck,
                    f"Dhana Yoga in {ck.upper()}: {h1}th lord ({n1}) and {h2}th lord ({n2}) conjunct — {label}.",
                    f"A Dhana Yoga (wealth/resource yoga) in {ck.upper()} multiplies the material or wealth signification of the chart.",
                    "positive", 7, {"dhana_yoga_score": 3, "placement_quality_score": 2},
                ))
            elif p1 == h2 and p2 == h1:
                triggered.append(_rule(
                    f"GDC_11_DHANA_YOGA_EXCHANGE_{ck.upper()}_{l1}_{l2}",
                    ck,
                    f"Dhana Yoga by exchange in {ck.upper()}: {h1}th lord ({n1}) in {h2}th, {h2}th lord ({n2}) in {h1}th — {label}.",
                    f"A Dhana Yoga by parivartana in {ck.upper()} amplifies wealth and material gains from the chart's signification.",
                    "positive", 8, {"dhana_yoga_score": 4, "placement_quality_score": 3},
                ))

    return triggered


# ── GDC-12: Karaka in dusthana (Rule 15) ────────────────────────────────────

def _gdc_12(
    chart_facts: dict, chart_keys: list[str], category_karakas: list[str]
) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue
        for code in category_karakas:
            house = _planet(ch, code).get("house")
            if house in DUSTHANA:
                name = PLANET_NAMES.get(code, code)
                triggered.append(_rule(
                    f"GDC_12_KARAKA_{code}_{ck.upper()}_DUSTHANA",
                    ck,
                    f"Category karaka {name} is in house {house} (dusthana) of {ck.upper()}.",
                    f"The natural significator {name} in a dusthana of {ck.upper()} weakens the chart's capacity to deliver its signification — not welcome in a bad house.",
                    "negative", 6, {"placement_quality_score": -3},
                ))

    return triggered


# ── GDC-13: 3rd/8th = death-like (Rule 16) ──────────────────────────────────

def _gdc_13(
    chart_facts: dict,
    chart_keys: list[str],
    d1_lagna_lord: str | None,
    category_karakas: list[str],
) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        ll = _lagna_lord(ch)
        ll_code = ll.get("lord")
        ll_placed = ll.get("placed_house")
        if ll_code and ll_placed in DEATH_HOUSES:
            name = PLANET_NAMES.get(ll_code, ll_code)
            triggered.append(_rule(
                f"GDC_13_LAGNA_LORD_DEATH_HOUSE_{ck.upper()}",
                ck,
                f"{ck.upper()} Lagna lord {name} is in house {ll_placed} — a death-like house for the chart's signification.",
                f"Lagna lord in 3rd or 8th of {ck.upper()} is treated as death-like: it severely weakens what the divisional chart promises.",
                "negative", 7, {"placement_quality_score": -4},
            ))

        if d1_lagna_lord and d1_lagna_lord != ll_code:
            d1_ll_house = _planet(ch, d1_lagna_lord).get("house")
            if d1_ll_house in DEATH_HOUSES:
                name = PLANET_NAMES.get(d1_lagna_lord, d1_lagna_lord)
                triggered.append(_rule(
                    f"GDC_13_D1_LL_DEATH_HOUSE_{ck.upper()}",
                    ck,
                    f"D1 Lagna lord {name} is in house {d1_ll_house} (death-like) in {ck.upper()}.",
                    f"D1 Lagna lord in 3rd or 8th of {ck.upper()} is unfavorable for the chart's signification.",
                    "negative", 6, {"placement_quality_score": -3},
                ))

        for code in category_karakas:
            house = _planet(ch, code).get("house")
            if house in DEATH_HOUSES:
                name = PLANET_NAMES.get(code, code)
                triggered.append(_rule(
                    f"GDC_13_KARAKA_{code}_DEATH_HOUSE_{ck.upper()}",
                    ck,
                    f"Category karaka {name} is in house {house} (death-like) in {ck.upper()}.",
                    f"Category karaka {name} in 3rd or 8th of {ck.upper()} is death-like for the chart's signification.",
                    "negative", 6, {"placement_quality_score": -3},
                ))

    return triggered


# ── GDC-14: Chart-specific karaka in own divisional Lagna (Rule 17) ──────────

def _gdc_14(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    for ck in chart_keys:
        bad_karakas = KARAKA_IN_OWN_LAGNA_BAD.get(ck)
        if not bad_karakas:
            continue
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        lagna_occupants = {
            p.get("code")
            for p in ch.get("planets", [])
            if p.get("house") == 1 and p.get("code") and p.get("code") != "Asc"
        }

        for code in bad_karakas:
            if code not in lagna_occupants:
                continue
            name = PLANET_NAMES.get(code, code)
            triggered.append(_rule(
                f"GDC_14_KARAKA_{code}_OWN_LAGNA_{ck.upper()}",
                ck,
                f"{name} (chart significator) is in the Lagna of its own divisional chart {ck.upper()}.",
                f"{name} in the Lagna of {ck.upper()} acts as karaka-in-bhava — classical texts state this gives bad effects for the chart's signification; malefic association worsens it.",
                "negative", 7, {"placement_quality_score": -4},
            ))

    return triggered


# ── GDC-15: Vargottam planet (Rule 11) ──────────────────────────────────────

def _gdc_15(chart_facts: dict, chart_keys: list[str]) -> list[dict]:
    triggered = []
    d1 = _chart(chart_facts, "d1")
    if not d1:
        return triggered

    for ck in chart_keys:
        if ck == "d1":
            continue
        ch = _chart(chart_facts, ck)
        if not ch:
            continue

        for p in ch.get("planets", []):
            code = p.get("code")
            if not code or code == "Asc":
                continue
            d1_sign = d1.get("planet_lookup", {}).get(code, {}).get("sign_number")
            div_sign = p.get("sign_number")
            if d1_sign and div_sign and d1_sign == div_sign:
                name = PLANET_NAMES.get(code, code)
                triggered.append(_rule(
                    f"GDC_15_VARGOTTAM_{code}_{ck.upper()}",
                    ck,
                    f"{name} is Vargottam in {ck.upper()} (same sign {p.get('sign')} as D1).",
                    f"Vargottam {name} in {ck.upper()} has enhanced strength — its promises in this chart are more reliably delivered.",
                    "positive", 6, {"planet_strength_score": 3},
                ))

    return triggered


# ── GDC-16: D1 Lagna lord dignity in D1/D3/D9/D12 (Rule 14) ────────────────

def _gdc_16(chart_facts: dict) -> list[dict]:
    triggered = []
    d1_ll = _get_d1_lagna_lord(chart_facts)
    if not d1_ll:
        return triggered

    ll_name = PLANET_NAMES.get(d1_ll, d1_ll)

    for ck in ["d1", "d3", "d9", "d12"]:
        ch = _chart(chart_facts, ck)
        if not ch:
            continue
        dignity = _planet(ch, d1_ll).get("dignity")
        if dignity in {"exalted", "own_sign"}:
            triggered.append(_rule(
                f"GDC_16_D1_LL_STRONG_{ck.upper()}",
                ck,
                f"D1 Lagna lord {ll_name} is {dignity} in {ck.upper()}.",
                f"D1 Lagna lord strong in {ck.upper()} supports virtue, intelligence, and overall life quality per classical texts (Rule 14).",
                "positive", 7, {"placement_quality_score": 4, "overall_strength_score": 2},
            ))

    return triggered


# ── Main entry point ─────────────────────────────────────────────────────────

def evaluate_generic_varga_rules(
    chart_facts: dict[str, Any],
    category: str,
    category_karakas: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate all generic divisional chart rules against the category-relevant charts.

    Returns a list of triggered rule objects in the same format as the YAML rule engine.
    These should be merged into evidence_json['triggered_rules'] before score aggregation.
    """
    supported_charts: list[str] = chart_facts.get("varga", {}).get("supported_charts", [])
    if not supported_charts:
        return []

    d1_lagna_lord = _get_d1_lagna_lord(chart_facts)
    if category_karakas is None:
        category_karakas = _get_category_karakas(category)

    triggered: list[dict] = []
    triggered.extend(_gdc_01(chart_facts, supported_charts, d1_lagna_lord, category_karakas))
    triggered.extend(_gdc_02(chart_facts, supported_charts))
    triggered.extend(_gdc_03(chart_facts, supported_charts))
    triggered.extend(_gdc_06(chart_facts, supported_charts))
    triggered.extend(_gdc_07(chart_facts, supported_charts))
    triggered.extend(_gdc_09(chart_facts, supported_charts))
    triggered.extend(_gdc_10(chart_facts, supported_charts))
    triggered.extend(_gdc_11(chart_facts, supported_charts))
    triggered.extend(_gdc_12(chart_facts, supported_charts, category_karakas))
    triggered.extend(_gdc_13(chart_facts, supported_charts, d1_lagna_lord, category_karakas))
    triggered.extend(_gdc_14(chart_facts, supported_charts))
    triggered.extend(_gdc_15(chart_facts, supported_charts))
    triggered.extend(_gdc_16(chart_facts))
    return triggered
