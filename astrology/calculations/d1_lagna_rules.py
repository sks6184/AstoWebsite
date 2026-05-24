"""D1-specific rules from the Birth Chart chapter.

Source: Comprehensive Prediction by Divisional Charts — D1 chapter.

SET 1 (remaining yogas — Arishta / Dainya / Maha):
  D1-S1-03  Arishta Yoga — lagna lord conjunct/exchange with dusthana lord
  D1-S1-04  Dainya Yoga — dusthana lord exchanges with good house lord
  D1-S1-05  Maha Yoga — lagna lord in trikona with strong dignity, or exchange with 10th lord

SET 2 (Yogakaraka / Key Planets table, page 44):
  D1-S2-01  Yogakaraka mahadasha active — exceptional positive signal
  D1-S2-02  Yogakaraka antardasha active — supportive positive signal
  D1-S2-03  Yogakaraka planet strong/angular in D1 — chart-level strength
  D1-S2-04  Benefic mahadasha active — generally supportive
  D1-S2-05  Malefic mahadasha active — generally restrictive
  D1-S2-06  Maraka mahadasha active — caution flag (especially for health)
  D1-S2-07  Malefic antardasha inside benefic mahadasha — mixed signal
  D1-S2-08  Maraka antardasha active — secondary caution flag
  D1-S2-09  Yogakaraka in dusthana — promise weakened by placement
  D1-S2-10  Malefic planet in angle/trine — functional malefic gains power to restrict

SET 3 (Planet strength outcomes):
  D1-S3-EXALTED-{X}      Planet X exalted in D1 — peak natural strength
  D1-S3-OWN-SIGN-{X}     Planet X in own sign in D1 — stable natural strength
  D1-S3-DEBILITATED-{X}  Planet X debilitated in D1 — impaired natural significations

SET 4 (House-based category mapping):
  D1-S4-{N}TH-LORD-*     Category house lord {N} placement verdict in D1
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "D1 — Birth Chart"
_SOURCE_PAGE = "44"


# Lagna sign number (1=Aries … 12=Pisces) → planet role table
# Keys: "yogakaraka", "benefic", "malefic", "maraka"
# Empty list means none for that category.
LAGNA_PLANET_ROLES: dict[int, dict[str, list[str]]] = {
    1:  {"yogakaraka": [],           "benefic": ["Su", "Ju"],       "malefic": ["Me", "Ve", "Sa"], "maraka": ["Ve"]},
    2:  {"yogakaraka": ["Sa"],       "benefic": ["Su"],             "malefic": ["Mo", "Ju", "Ve"], "maraka": ["Ma"]},
    3:  {"yogakaraka": [],           "benefic": ["Ve"],             "malefic": ["Su", "Ma", "Ju"], "maraka": ["Mo"]},
    4:  {"yogakaraka": ["Ma"],       "benefic": ["Mo", "Ju"],       "malefic": ["Me", "Ve"],       "maraka": ["Sa"]},
    5:  {"yogakaraka": ["Ma"],       "benefic": ["Su", "Ju"],       "malefic": ["Sa", "Me", "Ve"], "maraka": ["Sa"]},
    6:  {"yogakaraka": [],           "benefic": ["Me", "Ve"],       "malefic": ["Mo", "Ma", "Ju"], "maraka": ["Ve"]},
    7:  {"yogakaraka": ["Sa"],       "benefic": ["Me"],             "malefic": ["Su", "Ma", "Ju"], "maraka": ["Ma"]},
    8:  {"yogakaraka": [],           "benefic": ["Mo", "Ju"],       "malefic": ["Me", "Ve", "Sa"], "maraka": ["Ve"]},
    9:  {"yogakaraka": [],           "benefic": ["Su", "Ma"],       "malefic": ["Ve"],             "maraka": ["Ve", "Sa"]},
    10: {"yogakaraka": ["Ve"],       "benefic": ["Me"],             "malefic": ["Mo", "Ma", "Ju"], "maraka": ["Ma"]},
    11: {"yogakaraka": ["Ve"],       "benefic": ["Sa"],             "malefic": ["Mo", "Ma", "Ju"], "maraka": ["Su", "Ma", "Ju"]},
    12: {"yogakaraka": [],           "benefic": ["Mo", "Ma", "Ju"], "malefic": ["Su", "Me", "Ve", "Sa"], "maraka": ["Me", "Sa"]},
}

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
GOOD_HOUSES = frozenset({1, 2, 4, 5, 7, 9, 10, 11})

# Natural significations per planet for Set 3 strength rules
_PLANET_SIG: dict[str, dict] = {
    "Su": {
        "domains": "authority, career, government, status, father",
        "pos": {"career": 4, "status": 4, "overall": 3},
        "neg": {"career": -3, "status": -3, "overall": -2},
    },
    "Mo": {
        "domains": "mind, public recognition, mother, emotions",
        "pos": {"overall": 3},
        "neg": {"overall": -2},
    },
    "Ma": {
        "domains": "energy, property, siblings, courage, technical skill",
        "pos": {"property": 4, "career": 3, "overall": 2},
        "neg": {"property": -3, "career": -2, "overall": -2},
    },
    "Me": {
        "domains": "intelligence, business, communication, education",
        "pos": {"business": 4, "education": 3, "career": 3, "overall": 2},
        "neg": {"business": -3, "career": -2, "overall": -2},
    },
    "Ju": {
        "domains": "wisdom, wealth, children, spirituality, law",
        "pos": {"overall": 5, "children": 4, "wealth": 3},
        "neg": {"overall": -3, "children": -3, "wealth": -2},
    },
    "Ve": {
        "domains": "luxury, relationships, arts, material comforts, marriage",
        "pos": {"marriage": 4, "overall": 3, "wealth": 3},
        "neg": {"marriage": -3, "overall": -2, "wealth": -2},
    },
    "Sa": {
        "domains": "longevity, discipline, service, masses, foreign lands",
        "pos": {"career": 3, "overall": 2},
        "neg": {"career": -3, "overall": -3},
    },
}

# Category-relevant house lords to check in D1 (Set 4)
_CATEGORY_KEY_HOUSES: dict[str, list[int]] = {
    "job":       [6, 10, 2, 11],
    "career":    [10, 1, 9, 11],
    "business":  [7, 2, 10, 11],
    "property":  [4, 2, 12, 11],
    "marriage":  [7, 2, 5, 11],
    "money":     [2, 11, 5, 9],
    "health":    [1, 6, 8, 12],
    "education": [5, 4, 9, 2],
    "children":  [5, 9, 11, 2],
    "general":   [1, 9, 10, 11],
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
        "system": "D1/LagnaRoles",
        "chart": "D1",
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
        "source_file": "d1_lagna_rules.py",
    }


def _get_lagna_sign(chart_facts: dict[str, Any]) -> int | None:
    lagna = (
        chart_facts.get("varga", {})
        .get("charts", {})
        .get("d1", {})
        .get("lagna", {})
    )
    return lagna.get("sign_number")


def _get_planet_in_d1(chart_facts: dict[str, Any], code: str) -> dict[str, Any]:
    return (
        chart_facts.get("varga", {})
        .get("charts", {})
        .get("d1", {})
        .get("planet_lookup", {})
        .get(code, {})
    )


def _get_vimshottari(evidence: dict[str, Any]) -> dict[str, Any]:
    return evidence.get("parashari_vimshottari") or {}


def _active_lords(vimshottari: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (mahadasha_lord, antardasha_lord) planet codes or None."""
    maha = vimshottari.get("current_mahadasha") or {}
    antar = vimshottari.get("current_antardasha") or {}
    return maha.get("lord"), antar.get("lord")


# ── Dasha-level rules ─────────────────────────────────────────────────────────

def _d1_s2_01_yogakaraka_maha(roles: dict, maha_lord: str | None) -> list[dict]:
    if not maha_lord or maha_lord not in roles.get("yogakaraka", []):
        return []
    name = _pname(maha_lord)
    return [_rule(
        "D1-S2-01",
        f"{name} mahadasha active; {name} is Yogakaraka for this lagna",
        f"{name} lords both an angle and a trine for this lagna, making it the most powerful functional benefic. "
        f"Its mahadasha is a period of exceptional support for career, growth, and overall auspiciousness.",
        "positive", 8,
        {"overall": 8, "career": 7, "status": 7},
        confidence="high",
    )]


def _d1_s2_02_yogakaraka_antar(roles: dict, maha_lord: str | None, antar_lord: str | None) -> list[dict]:
    if not antar_lord or antar_lord not in roles.get("yogakaraka", []):
        return []
    if antar_lord == maha_lord:
        return []
    name = _pname(antar_lord)
    maha_name = _pname(maha_lord) if maha_lord else "current maha"
    return [_rule(
        "D1-S2-02",
        f"{name} antardasha active within {maha_name} mahadasha; {name} is Yogakaraka for this lagna",
        f"{name} as Yogakaraka brings a supportive sub-period within the current mahadasha. "
        f"Expect uplift, opportunity, and momentum during this antardasha.",
        "positive", 5,
        {"overall": 5, "career": 4},
        confidence="medium",
    )]


def _d1_s2_04_benefic_maha(roles: dict, maha_lord: str | None) -> list[dict]:
    if not maha_lord or maha_lord not in roles.get("benefic", []):
        return []
    if maha_lord in roles.get("yogakaraka", []):
        return []
    name = _pname(maha_lord)
    return [_rule(
        "D1-S2-04",
        f"{name} mahadasha active; {name} is a functional benefic for this lagna",
        f"{name} is a natural benefic for this lagna. Its mahadasha generally supports progress, "
        f"though outcomes depend on its placement and dignity in D1.",
        "positive", 4,
        {"overall": 4, "career": 3},
        confidence="medium",
    )]


def _d1_s2_05_malefic_maha(roles: dict, maha_lord: str | None) -> list[dict]:
    if not maha_lord or maha_lord not in roles.get("malefic", []):
        return []
    if maha_lord in roles.get("yogakaraka", []):
        return []
    name = _pname(maha_lord)
    return [_rule(
        "D1-S2-05",
        f"{name} mahadasha active; {name} is a functional malefic for this lagna",
        f"{name} acts as a functional malefic for this lagna. Its mahadasha can bring delays, "
        f"obstacles, or pressure. Benefic transits and antardashas can mitigate this.",
        "negative", 4,
        {"overall": -4, "career": -3},
        confidence="medium",
    )]


def _d1_s2_06_maraka_maha(roles: dict, maha_lord: str | None, category: str) -> list[dict]:
    if not maha_lord or maha_lord not in roles.get("maraka", []):
        return []
    name = _pname(maha_lord)
    health_note = " For health questions, this period warrants special attention." if category in {"health", "general"} else ""
    return [_rule(
        "D1-S2-06",
        f"{name} mahadasha active; {name} is a maraka (death-inflicting) planet for this lagna",
        f"{name} lords a maraka house (2nd or 7th) for this lagna.{health_note} "
        f"Career and financial matters can still progress, but this lord may bring endings, separations, or transitions.",
        "mixed", 3,
        {"overall": -3, "health": -4} if category == "health" else {"overall": -2},
        confidence="medium",
    )]


def _d1_s2_07_malefic_antar_in_benefic_maha(roles: dict, maha_lord: str | None, antar_lord: str | None) -> list[dict]:
    if not maha_lord or not antar_lord or maha_lord == antar_lord:
        return []
    if maha_lord not in roles.get("benefic", []) and maha_lord not in roles.get("yogakaraka", []):
        return []
    if antar_lord not in roles.get("malefic", []):
        return []
    maha_name = _pname(maha_lord)
    antar_name = _pname(antar_lord)
    return [_rule(
        "D1-S2-07",
        f"{antar_name} antardasha (malefic) within {maha_name} mahadasha (benefic) — mixed period",
        f"The current antardasha belongs to a functional malefic ({antar_name}) within an otherwise "
        f"supportive mahadasha ({maha_name}). Expect short-term friction, slowdowns, or friction within "
        f"the broader positive trend.",
        "mixed", 3,
        {"overall": -2, "career": -2},
        confidence="medium",
    )]


def _d1_s2_08_maraka_antar(roles: dict, maha_lord: str | None, antar_lord: str | None, category: str) -> list[dict]:
    if not antar_lord or antar_lord not in roles.get("maraka", []):
        return []
    if antar_lord == maha_lord:
        return []
    antar_name = _pname(antar_lord)
    maha_name = _pname(maha_lord) if maha_lord else "current maha"
    return [_rule(
        "D1-S2-08",
        f"{antar_name} antardasha (maraka) active within {maha_name} mahadasha",
        f"{antar_name} is a maraka (2nd/7th lord) for this lagna. During its antardasha, "
        f"take extra care with health, agreements, and key relationships. Endings or transitions are possible.",
        "mixed", 3,
        {"overall": -2, "health": -3} if category in {"health", "general"} else {"overall": -2},
        confidence="medium",
    )]


# ── Placement-level rules ─────────────────────────────────────────────────────

def _d1_s2_03_yogakaraka_strong(
    chart_facts: dict[str, Any], roles: dict, lagna_sign: int
) -> list[dict]:
    triggered = []
    for code in roles.get("yogakaraka", []):
        planet = _get_planet_in_d1(chart_facts, code)
        if not planet:
            continue
        house = planet.get("house")
        dignity = planet.get("dignity", "")
        name = _pname(code)
        in_angle = house in ANGLES
        in_trine = house in TRINES
        strong_dignity = dignity in {"exalted", "own_sign"}
        if in_angle or in_trine or strong_dignity:
            reasons = []
            if strong_dignity:
                reasons.append(f"{dignity} dignity")
            if in_angle:
                reasons.append(f"in angle (house {house})")
            elif in_trine:
                reasons.append(f"in trine (house {house})")
            triggered.append(_rule(
                "D1-S2-03",
                f"{name} (Yogakaraka) is well-placed in D1: {', '.join(reasons)}",
                f"{name} is the Yogakaraka for this lagna and is placed favorably in D1. "
                f"This strengthens its dasha results and provides sustained chart-level support.",
                "positive", 5,
                {"overall": 5, "career": 4, "status": 4},
                confidence="high",
            ))
    return triggered


def _d1_s2_09_yogakaraka_in_dusthana(
    chart_facts: dict[str, Any], roles: dict, lagna_sign: int
) -> list[dict]:
    triggered = []
    for code in roles.get("yogakaraka", []):
        planet = _get_planet_in_d1(chart_facts, code)
        if not planet:
            continue
        house = planet.get("house")
        if house in DUSTHANA:
            name = _pname(code)
            triggered.append(_rule(
                "D1-S2-09",
                f"{name} (Yogakaraka) is placed in dusthana house {house} in D1",
                f"Although {name} is the Yogakaraka for this lagna, its placement in a dusthana (6/8/12) "
                f"weakens its ability to deliver full results. Dasha periods may start with obstacles "
                f"before the underlying strength manifests.",
                "negative", 4,
                {"overall": -4, "career": -3},
                confidence="medium",
            ))
    return triggered


def _d1_s2_10_malefic_in_angle_trine(
    chart_facts: dict[str, Any], roles: dict
) -> list[dict]:
    triggered = []
    for code in roles.get("malefic", []):
        planet = _get_planet_in_d1(chart_facts, code)
        if not planet:
            continue
        house = planet.get("house")
        if house in (ANGLES | TRINES) and house != 1:
            name = _pname(code)
            triggered.append(_rule(
                "D1-S2-10",
                f"{name} (functional malefic for this lagna) occupies house {house} — an angle/trine",
                f"{name} is a functional malefic for this lagna placed in a powerful house. "
                f"This amplifies its capacity to obstruct or restrict the themes of that house during its dasha.",
                "negative", 3,
                {"overall": -3, "career": -2},
                confidence="medium",
            ))
    return triggered


# ── Shared D1 helpers ────────────────────────────────────────────────────────

def _get_d1_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d1", {})


def _build_lord_maps(d1_chart: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    """Return (house→lord_code, lord_code→placed_house) for all 12 houses."""
    all_pl = d1_chart.get("all_lord_placements", {})
    h2l: dict[int, str] = {}
    l2p: dict[str, int] = {}
    for h in range(1, 13):
        pl = all_pl.get(f"{h}_lord", {})
        lord = pl.get("lord")
        placed = pl.get("placed_house")
        if lord:
            h2l[h] = lord
            l2p[lord] = placed
    return h2l, l2p


# ── Set 1 remaining: Arishta / Dainya / Maha yogas ───────────────────────────

def _d1_s1_03_arishta_yoga(d1_chart: dict[str, Any]) -> list[dict]:
    """Lagna lord conjunct with or exchanging with a dusthana lord — Arishta Yoga."""
    all_pl = d1_chart.get("all_lord_placements", {})
    ll = all_pl.get("1_lord", {})
    ll_code = ll.get("lord")
    ll_placed = ll.get("placed_house")
    if not ll_code or not ll_placed:
        return []

    triggered = []
    ll_name = _pname(ll_code)

    for dusthana_h in (6, 8, 12):
        dl = all_pl.get(f"{dusthana_h}_lord", {})
        dl_code = dl.get("lord")
        dl_placed = dl.get("placed_house")
        if not dl_code or dl_code == ll_code or not dl_placed:
            continue

        dl_name = _pname(dl_code)

        if ll_placed == dl_placed:
            triggered.append(_rule(
                f"D1-S1-03-ARISHTA-{ll_code}-{dl_code}",
                f"Arishta Yoga: lagna lord {ll_name} conjunct {dusthana_h}th lord {dl_name} in house {ll_placed}",
                f"Lagna lord {ll_name} is conjunct with {dl_name} ({dusthana_h}th lord) in D1. "
                f"This Arishta Yoga pollutes the lagna lord with dusthana energy, bringing obstacles, "
                f"health concerns, or recurring setbacks — especially during their shared dasha period.",
                "negative", 6,
                {"overall": -4, "health": -3, "lagna_strength_score": -3},
                confidence="high",
            ))
        elif ll_placed == dusthana_h and dl_placed == 1:
            triggered.append(_rule(
                f"D1-S1-03-ARISHTA-EXCHANGE-{ll_code}-{dl_code}",
                f"Arishta Yoga by exchange: lagna lord {ll_name} in {dusthana_h}th, {dusthana_h}th lord {dl_name} in lagna",
                f"Lagna lord {ll_name} and {dusthana_h}th lord {dl_name} exchange houses. "
                f"This Arishta Yoga by parivartana deeply links the lagna with a dusthana — "
                f"persistent vulnerability in health and life quality across both lords' dasha periods.",
                "negative", 7,
                {"overall": -5, "health": -4, "lagna_strength_score": -4},
                confidence="high",
            ))

    return triggered


def _d1_s1_04_dainya_yoga(d1_chart: dict[str, Any]) -> list[dict]:
    """Dusthana lord (6/8/12) exchanges signs with a non-dusthana house lord — Dainya Yoga."""
    h2l, l2p = _build_lord_maps(d1_chart)
    triggered = []
    seen: set[frozenset] = set()

    for dusthana_h in (6, 8, 12):
        dl = h2l.get(dusthana_h)
        if not dl:
            continue
        dl_placed = l2p.get(dl)
        if not dl_placed or dl_placed in DUSTHANA:
            continue

        good_lord = h2l.get(dl_placed)
        if not good_lord or good_lord == dl:
            continue
        if l2p.get(good_lord) != dusthana_h:
            continue

        pair = frozenset({f"{dusthana_h}:{dl}", f"{dl_placed}:{good_lord}"})
        if pair in seen:
            continue
        seen.add(pair)

        dl_name = _pname(dl)
        gl_name = _pname(good_lord)
        triggered.append(_rule(
            f"D1-S1-04-DAINYA-{dl}-{good_lord}",
            f"Dainya Yoga: {dusthana_h}th lord {dl_name} exchanges with {dl_placed}th lord {gl_name}",
            f"{dusthana_h}th lord {dl_name} is in house {dl_placed} while {dl_placed}th lord {gl_name} "
            f"is in house {dusthana_h}. This Dainya Yoga (degradation yoga) taints the {dl_placed}th house "
            f"with dusthana energy — results in that life area come with struggle, obstruction, or reversals.",
            "negative", 6,
            {"overall": -3, "placement_quality_score": -3},
            confidence="medium",
        ))

    return triggered


def _d1_s1_05_maha_yoga(d1_chart: dict[str, Any]) -> list[dict]:
    """Lagna lord in trikona with strong dignity OR lagna lord-10th lord exchange — Maha Yoga."""
    all_pl = d1_chart.get("all_lord_placements", {})
    ll = all_pl.get("1_lord", {})
    ll_code = ll.get("lord")
    ll_placed = ll.get("placed_house")
    ll_dignity = ll.get("dignity", "")
    if not ll_code or not ll_placed:
        return []

    triggered = []
    ll_name = _pname(ll_code)

    if ll_placed in TRINES and ll_dignity in {"exalted", "own_sign"}:
        triggered.append(_rule(
            "D1-S1-05-MAHA-YOGA-TRIKONA",
            f"Maha Yoga: lagna lord {ll_name} in {ll_placed}th (trikona) with {ll_dignity} dignity",
            f"Lagna lord {ll_name} in a trikona with {ll_dignity} dignity forms Maha Yoga — one of the "
            f"strongest D1 configurations. The native has inherent fortune and resilience; rise is "
            f"pronounced during this planet's mahadasha.",
            "positive", 9,
            {"overall": 7, "career": 5, "status": 5, "lagna_strength_score": 4},
            confidence="high",
        ))

    h2l, l2p = _build_lord_maps(d1_chart)
    tenth_lord = h2l.get(10)
    if tenth_lord and tenth_lord != ll_code:
        if ll_placed == 10 and l2p.get(tenth_lord) == 1:
            tl_name = _pname(tenth_lord)
            triggered.append(_rule(
                f"D1-S1-05-MAHA-YOGA-10TH-EXCHANGE-{ll_code}-{tenth_lord}",
                f"Maha Yoga by exchange: lagna lord {ll_name} in 10th, 10th lord {tl_name} in lagna",
                f"Lagna lord {ll_name} and 10th lord {tl_name} exchange houses — a powerful Maha Yoga "
                f"linking self with authority and career. Exceptional rise in status and recognition "
                f"is possible during both lords' dasha periods.",
                "positive", 9,
                {"overall": 6, "career": 7, "status": 6},
                confidence="high",
            ))

    return triggered


# ── Set 3: Planet strength outcomes ──────────────────────────────────────────

def _d1_s3_planet_strength(d1_chart: dict[str, Any]) -> list[dict]:
    triggered = []
    planet_lookup = d1_chart.get("planet_lookup", {})

    for code, sig in _PLANET_SIG.items():
        p = planet_lookup.get(code, {})
        if not p:
            continue
        dignity = p.get("dignity", "")
        house = p.get("house")
        name = _pname(code)

        if dignity == "exalted":
            triggered.append(_rule(
                f"D1-S3-EXALTED-{code}",
                f"{name} is exalted in D1 (house {house}) — peak strength for {sig['domains']}",
                f"Exalted {name} in D1 delivers outstanding results in its natural domains "
                f"({sig['domains']}) during its dasha. This is the highest possible strength.",
                "positive", 7, sig["pos"], confidence="high",
            ))
        elif dignity == "own_sign":
            triggered.append(_rule(
                f"D1-S3-OWN-SIGN-{code}",
                f"{name} is in own sign in D1 (house {house}) — strong for {sig['domains']}",
                f"{name} in its own sign in D1 is stable and fully capable of delivering its "
                f"natural significations ({sig['domains']}) reliably during its periods.",
                "positive", 5, sig["pos"], confidence="high",
            ))
        elif dignity == "debilitated":
            triggered.append(_rule(
                f"D1-S3-DEBILITATED-{code}",
                f"{name} is debilitated in D1 (house {house}) — weakened for {sig['domains']}",
                f"Debilitated {name} in D1 struggles to deliver its natural significations "
                f"({sig['domains']}). Its dasha can bring reversals unless neechabhanga applies.",
                "negative", 6, sig["neg"], confidence="high",
            ))

    return triggered


# ── Set 4: House-based category mapping ──────────────────────────────────────

def _d1_s4_category_house_lords(d1_chart: dict[str, Any], category: str) -> list[dict]:
    """Check D1 placement of the key house lords for the given category."""
    key_houses = _CATEGORY_KEY_HOUSES.get(category, _CATEGORY_KEY_HOUSES["general"])
    all_pl = d1_chart.get("all_lord_placements", {})
    triggered = []

    for house_num in key_houses:
        pl = all_pl.get(f"{house_num}_lord", {})
        lord = pl.get("lord")
        placed = pl.get("placed_house")
        dignity = pl.get("dignity", "")
        if not lord or placed is None:
            continue

        name = _pname(lord)
        strong_dignity = dignity in {"exalted", "own_sign"}
        weak_dignity = dignity == "debilitated"

        if placed in ANGLE_OR_TRINE:
            weight = 7 if strong_dignity else 5
            conf = "high" if strong_dignity else "medium"
            dignity_note = f" with {dignity} dignity" if strong_dignity else ""
            triggered.append(_rule(
                f"D1-S4-{house_num}TH-LORD-ANGULAR-{lord}",
                f"{house_num}th lord {name} in house {placed} (angle/trine){dignity_note} — D1 supports {category}",
                f"The {house_num}th lord {name} is placed in an angle or trine in D1{dignity_note}. "
                f"This supports the {category} promise of this house with reliable, sustained results.",
                "positive", weight, {"overall": 5 if strong_dignity else 3, "placement_quality_score": 3 if strong_dignity else 2},
                confidence=conf,
            ))
        elif placed in DUSTHANA:
            triggered.append(_rule(
                f"D1-S4-{house_num}TH-LORD-DUSTHANA-{lord}",
                f"{house_num}th lord {name} in house {placed} (dusthana) — D1 weakens {category}",
                f"The {house_num}th lord {name} placed in a dusthana (6/8/12) in D1 weakens the "
                f"{category} signification — obstacles and delays are likely in this domain.",
                "negative", 5,
                {"overall": -3, "placement_quality_score": -3},
                confidence="medium",
            ))
        elif weak_dignity:
            triggered.append(_rule(
                f"D1-S4-{house_num}TH-LORD-DEBILITATED-{lord}",
                f"{house_num}th lord {name} is debilitated in D1 (house {placed}) — weakens {category}",
                f"The {house_num}th lord {name} is debilitated in D1. Even if not in a dusthana, "
                f"its weakened state reduces the {category} results it can deliver.",
                "negative", 5,
                {"overall": -3, "placement_quality_score": -2},
                confidence="medium",
            ))

    return triggered


# ── Main entry point ──────────────────────────────────────────────────────────

def evaluate_d1_lagna_roles(
    chart_facts: dict[str, Any],
    evidence: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    """Evaluate all D1 rule sets (Set 1 remaining, Set 2, Set 3, Set 4).

    Returns triggered-rule dicts in the same format as the YAML rule engine
    and varga_generic_rules.py.
    """
    d1_chart = _get_d1_chart(chart_facts)
    if not d1_chart:
        return []

    triggered: list[dict[str, Any]] = []

    # ── Set 1 remaining: special D1 yogas ────────────────────────────────────
    triggered.extend(_d1_s1_03_arishta_yoga(d1_chart))
    triggered.extend(_d1_s1_04_dainya_yoga(d1_chart))
    triggered.extend(_d1_s1_05_maha_yoga(d1_chart))

    # ── Set 2: Yogakaraka / Key Planets (requires lagna sign) ────────────────
    lagna_sign = _get_lagna_sign(chart_facts)
    if lagna_sign and lagna_sign in LAGNA_PLANET_ROLES:
        roles = LAGNA_PLANET_ROLES[lagna_sign]
        vimshottari = _get_vimshottari(evidence)
        maha_lord, antar_lord = _active_lords(vimshottari)

        triggered.extend(_d1_s2_01_yogakaraka_maha(roles, maha_lord))
        triggered.extend(_d1_s2_02_yogakaraka_antar(roles, maha_lord, antar_lord))
        triggered.extend(_d1_s2_04_benefic_maha(roles, maha_lord))
        triggered.extend(_d1_s2_05_malefic_maha(roles, maha_lord))
        triggered.extend(_d1_s2_06_maraka_maha(roles, maha_lord, category))
        triggered.extend(_d1_s2_07_malefic_antar_in_benefic_maha(roles, maha_lord, antar_lord))
        triggered.extend(_d1_s2_08_maraka_antar(roles, maha_lord, antar_lord, category))
        triggered.extend(_d1_s2_03_yogakaraka_strong(chart_facts, roles, lagna_sign))
        triggered.extend(_d1_s2_09_yogakaraka_in_dusthana(chart_facts, roles, lagna_sign))
        triggered.extend(_d1_s2_10_malefic_in_angle_trine(chart_facts, roles))

    # ── Set 3: Planet strength outcomes ──────────────────────────────────────
    triggered.extend(_d1_s3_planet_strength(d1_chart))

    # ── Set 4: Category house lord placement in D1 ───────────────────────────
    triggered.extend(_d1_s4_category_house_lords(d1_chart, category))

    return triggered
