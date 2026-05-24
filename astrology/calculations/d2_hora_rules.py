"""D2-specific rules from the Hora chart chapter.

Source: Comprehensive Prediction by Divisional Charts — Hora D2 (pp. 45–66).

SET 1 (Jupiter — natural wealth karaka in D2):
  D2-S1-JU-EXALTED         Jupiter exalted in D2 — peak wealth karaka strength
  D2-S1-JU-OWN             Jupiter in own sign in D2 — stable wealth karaka
  D2-S1-JU-DEBILITATED     Jupiter debilitated in D2 — weakened wealth karaka
  D2-S1-JU-ANGULAR         Jupiter in angle (1/4/7/10) in D2 — powerfully placed
  D2-S1-JU-TRINE           Jupiter in pure trine (5/9) in D2 — fortunately placed
  D2-S1-JU-DUSTHANA        Jupiter in dusthana (6/8/12) in D2 — obstructed

SET 2 (Key house lords in D2 — 2nd, 9th, 11th):
  D2-S2-{N}TH-LORD-ANGULAR-{X}     lord in angle/trine — supported
  D2-S2-{N}TH-LORD-DUSTHANA-{X}    lord in dusthana — obstructed
  D2-S2-{N}TH-LORD-DEBILITATED-{X} lord debilitated — weakened

SET 3 (Dhana Yoga combinations in D2 — Labh Mandook rules 2–6):
  D2-S3-DHANA-2-11-{X}-{Y}   2nd + 11th lords conjunct → dhana yoga
  D2-S3-DHANA-9-2-{X}-{Y}    9th lord related to 2nd → luck in wealth
  D2-S3-DHANA-5-2-{X}        5th lord related to 2nd/11th → speculative wealth
  D2-S3-INHERIT-8-{X}        8th lord related to 2nd/11th → inheritance

SET 4 (Lagna lord relationships in D2 — Labh Mandook rules 3, 4, 10):
  D2-S4-LL-3RD-RELATED-{X}-{Y}  LL + 3rd lord related → skill to earn
  D2-S4-LL-9TH-RELATED-{X}-{Y}  LL + 9th lord related → luck in earning
  D2-S4-LL-12TH-{X}             LL in 12th → earnings dispersed

SET 5 (Parashari hora distribution — only if D2 uses Cancer/Leo computation):
  D2-S5-{X}-FAVORABLE-HORA      Planet in its auspicious hora
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Hora D2"
_SOURCE_PAGE = "45"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES


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
        "system": "D2/HoraRules",
        "chart": "D2",
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
        "source_file": "d2_hora_rules.py",
    }


def _get_d2_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d2", {})


def _build_lord_maps(d2_chart: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    """Return (house→lord_code, lord_code→placed_house) for all 12 houses."""
    all_pl = d2_chart.get("all_lord_placements", {})
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
    """Return True if two lords are related: conjunct, or one placed in the other's natal house."""
    if code_a == code_b or placed_a is None or placed_b is None:
        return False
    return (
        placed_a == placed_b or  # conjunction
        placed_a == house_b or   # A placed in B's house
        placed_b == house_a      # B placed in A's house (parivartana)
    )


# ── Set 1: Jupiter (natural wealth karaka) in D2 ─────────────────────────────

def _d2_s1_jupiter(d2_chart: dict[str, Any]) -> list[dict]:
    """Jupiter's placement and dignity in D2 — primary wealth karaka signal."""
    ju = d2_chart.get("planet_lookup", {}).get("Ju", {})
    if not ju:
        return []

    house = ju.get("house")
    dignity = ju.get("dignity", "")
    triggered = []

    if dignity == "exalted":
        triggered.append(_rule(
            "D2-S1-JU-EXALTED",
            f"Jupiter exalted in D2 (house {house}) — peak wealth karaka strength",
            "Exalted Jupiter in D2 is the strongest signal for wealth accumulation. As the natural "
            "significator of wealth, an exalted Jupiter in the hora chart supports exceptional "
            "financial growth and fortune during its dasha period.",
            "positive", 6,
            {"overall": 5, "money": 6, "business": 4},
            confidence="high",
        ))
    elif dignity == "own_sign":
        triggered.append(_rule(
            "D2-S1-JU-OWN",
            f"Jupiter in own sign in D2 (house {house}) — stable wealth karaka",
            "Jupiter in its own sign in D2 provides reliable, sustained support for wealth "
            "accumulation. Financial results are consistent and well-supported during its dasha.",
            "positive", 4,
            {"overall": 3, "money": 4, "business": 3},
            confidence="high",
        ))
    elif dignity == "debilitated":
        triggered.append(_rule(
            "D2-S1-JU-DEBILITATED",
            f"Jupiter debilitated in D2 (house {house}) — weakened wealth karaka",
            "Debilitated Jupiter in D2 is the natural wealth significator at its lowest strength. "
            "Financial accumulation faces persistent obstacles, and its dasha may bring losses or "
            "stagnation unless neechabhanga applies.",
            "negative", 5,
            {"overall": -4, "money": -5, "business": -3},
            confidence="high",
        ))

    if house in ANGLES:
        triggered.append(_rule(
            "D2-S1-JU-ANGULAR",
            f"Jupiter in angle (house {house}) in D2 — wealth karaka powerfully placed",
            "Angular Jupiter in D2 gives the natural wealth significator direct visibility and "
            "strength. Wealth flows more easily and with public recognition during Jupiter's periods.",
            "positive", 5,
            {"overall": 4, "money": 5, "business": 3},
            confidence="medium",
        ))
    elif house in TRINES and house != 1:
        triggered.append(_rule(
            "D2-S1-JU-TRINE",
            f"Jupiter in trine (house {house}) in D2 — wealth karaka fortunately placed",
            "Jupiter in a trikona in D2 brings wealth through fortune and dharmic means. "
            "Financial gains feel natural and aligned with the native's life purpose during Jupiter's period.",
            "positive", 4,
            {"overall": 3, "money": 4, "business": 3},
            confidence="medium",
        ))
    elif house in DUSTHANA:
        triggered.append(_rule(
            "D2-S1-JU-DUSTHANA",
            f"Jupiter in dusthana (house {house}) in D2 — wealth karaka obstructed",
            "Jupiter placed in a dusthana (6/8/12) in D2 challenges the natural wealth significator. "
            "Financial progress is inconsistent, hidden losses arise, and wealth accumulation "
            "faces obstacles — especially during Jupiter's mahadasha.",
            "negative", 4,
            {"overall": -3, "money": -4, "business": -2},
            confidence="medium",
        ))

    return triggered


# ── Set 2: Key house lords (2nd, 9th, 11th) in D2 ────────────────────────────

def _d2_s2_key_lords(d2_chart: dict[str, Any]) -> list[dict]:
    """Placement of 2nd (wealth), 9th (luck in earning), and 11th (gains) lords in D2."""
    all_pl = d2_chart.get("all_lord_placements", {})
    triggered = []

    lord_meta: dict[int, tuple[str, dict, dict]] = {
        2:  ("wealth accumulation",
             {"overall": 4, "money": 5, "business": 3},
             {"overall": -3, "money": -4, "business": -2}),
        9:  ("luck in earning",
             {"overall": 3, "money": 4, "business": 3},
             {"overall": -2, "money": -3, "business": -2}),
        11: ("gains and income inflow",
             {"overall": 4, "money": 5, "business": 3},
             {"overall": -3, "money": -4, "business": -2}),
    }

    for house_num, (theme, pos_out, neg_out) in lord_meta.items():
        pl = all_pl.get(f"{house_num}_lord", {})
        lord = pl.get("lord")
        placed = pl.get("placed_house")
        dignity = pl.get("dignity", "")
        if not lord or placed is None:
            continue

        name = _pname(lord)
        strong = dignity in {"exalted", "own_sign"}
        weak = dignity == "debilitated"

        if placed in ANGLE_OR_TRINE:
            weight = 6 if strong else 4
            dignity_note = f" with {dignity} dignity" if strong else ""
            triggered.append(_rule(
                f"D2-S2-{house_num}TH-LORD-ANGULAR-{lord}",
                f"D2 {house_num}th lord {name} in house {placed} (angle/trine){dignity_note} — {theme} supported",
                f"The {house_num}th lord {name} is well-placed in D2{dignity_note}, directly supporting "
                f"{theme}. Wealth-related outcomes in this domain are reliably delivered.",
                "positive", weight, pos_out,
                confidence="high" if strong else "medium",
            ))
        elif placed in DUSTHANA:
            triggered.append(_rule(
                f"D2-S2-{house_num}TH-LORD-DUSTHANA-{lord}",
                f"D2 {house_num}th lord {name} in dusthana (house {placed}) — {theme} obstructed",
                f"The {house_num}th lord {name} is placed in a dusthana in D2, creating friction in "
                f"{theme}. Financial results in this domain come with recurring obstacles or delay.",
                "negative", 4, neg_out,
                confidence="medium",
            ))
        elif weak:
            triggered.append(_rule(
                f"D2-S2-{house_num}TH-LORD-DEBILITATED-{lord}",
                f"D2 {house_num}th lord {name} debilitated (house {placed}) — {theme} weakened",
                f"The {house_num}th lord {name} is debilitated in D2, weakening its capacity for "
                f"{theme}. Neechabhanga would partially remedy this.",
                "negative", 3, neg_out,
                confidence="medium",
            ))

    return triggered


# ── Set 3: Dhana Yoga combinations in D2 ─────────────────────────────────────

def _d2_s3_dhana_yogas(d2_chart: dict[str, Any]) -> list[dict]:
    """Dhana yoga combinations in D2 per Labh Mandook hora rules #2–6 (p.49–50)."""
    all_pl = d2_chart.get("all_lord_placements", {})
    triggered = []

    def _lord(n: int) -> tuple[str | None, int | None]:
        pl = all_pl.get(f"{n}_lord", {})
        return pl.get("lord"), pl.get("placed_house")

    l2, p2 = _lord(2)
    l5, p5 = _lord(5)
    l8, p8 = _lord(8)
    l9, p9 = _lord(9)
    l11, p11 = _lord(11)

    # Rule #2: 2nd + 11th lords conjunct → dhana yoga
    if l2 and l11 and l2 != l11 and p2 and p2 == p11:
        triggered.append(_rule(
            f"D2-S3-DHANA-2-11-{l2}-{l11}",
            f"Dhana Yoga in D2: 2nd lord {_pname(l2)} conjunct 11th lord {_pname(l11)} in house {p2}",
            f"The 2nd lord (wealth accumulation) and 11th lord (gains) are conjunct in D2, "
            f"forming a classic Dhana Yoga. Earned income reliably converts into accumulated "
            f"wealth — a strong financial promise activated during their dasha periods.",
            "positive", 7,
            {"overall": 5, "money": 7, "business": 5},
            confidence="high",
        ))

    # Rule #4: 9th lord related to 2nd → luck in earning
    if l9 and l2 and l9 != l2 and _lords_related(l9, 9, p9, l2, 2, p2):
        triggered.append(_rule(
            f"D2-S3-DHANA-9-2-{l9}-{l2}",
            f"D2: 9th lord {_pname(l9)} related to 2nd lord {_pname(l2)} — luck supports wealth",
            f"The 9th lord (bhagya) is connected to the 2nd lord (wealth) in D2. "
            f"Per Labh Mandook rule #4, the native earns through fortune and luck — "
            f"a strong bhagya link is essential for effortless, sustained wealth.",
            "positive", 5,
            {"overall": 4, "money": 5, "business": 3},
            confidence="medium",
        ))

    # Rule #3: 5th lord related to 2nd or 11th → creative/speculative wealth
    if l5:
        related_to_2 = bool(l2 and l5 != l2 and _lords_related(l5, 5, p5, l2, 2, p2))
        related_to_11 = bool(l11 and l5 != l11 and _lords_related(l5, 5, p5, l11, 11, p11))
        if related_to_2 or related_to_11:
            triggered.append(_rule(
                f"D2-S3-DHANA-5-2-{l5}",
                f"D2: 5th lord {_pname(l5)} related to 2nd/11th — speculative and creative wealth",
                f"The 5th lord (intelligence, investment, creativity) links to the 2nd or 11th "
                f"lord in D2 per Labh Mandook rule #3. Wealth comes through creative, speculative, "
                f"or skill-based endeavors — investment gains and windfalls are supported.",
                "positive", 4,
                {"overall": 3, "money": 4, "business": 4},
                confidence="medium",
            ))

    # Rule #6: 8th lord related to 2nd or 11th → inheritance wealth
    if l8:
        related_to_2 = bool(l2 and l8 != l2 and _lords_related(l8, 8, p8, l2, 2, p2))
        related_to_11 = bool(l11 and l8 != l11 and _lords_related(l8, 8, p8, l11, 11, p11))
        if related_to_2 or related_to_11:
            triggered.append(_rule(
                f"D2-S3-INHERIT-8-{l8}",
                f"D2: 8th lord {_pname(l8)} related to 2nd/11th — inheritance wealth indicated",
                f"The 8th lord (inheritance, hidden sources) connects to the 2nd or 11th lord in D2. "
                f"Per Labh Mandook rule #6, wealth from inheritance, windfall, or unearned sources "
                f"is indicated — most prominent during the 8th lord's dasha.",
                "positive", 4,
                {"overall": 3, "money": 4, "business": 2},
                confidence="medium",
            ))

    return triggered


# ── Set 4: Lagna lord relationships in D2 ────────────────────────────────────

def _d2_s4_lagna_lord(d2_chart: dict[str, Any]) -> list[dict]:
    """Lagna lord position and relationships in D2 (Labh Mandook rules #3, #4, p.49–50)."""
    all_pl = d2_chart.get("all_lord_placements", {})
    triggered = []

    def _lord(n: int) -> tuple[str | None, int | None]:
        pl = all_pl.get(f"{n}_lord", {})
        return pl.get("lord"), pl.get("placed_house")

    l1, p1 = _lord(1)
    l3, p3 = _lord(3)
    l9, p9 = _lord(9)

    if not l1 or p1 is None:
        return []

    ll_name = _pname(l1)

    # Rule #3: lagna lord + 3rd lord related → skill and drive to earn
    if l3 and l3 != l1 and _lords_related(l1, 1, p1, l3, 3, p3):
        triggered.append(_rule(
            f"D2-S4-LL-3RD-RELATED-{l1}-{l3}",
            f"D2: lagna lord {ll_name} related to 3rd lord {_pname(l3)} — skill and drive to earn",
            f"The lagna lord {ll_name} connects to the 3rd lord (effort, skill, initiative) in D2. "
            f"Per Labh Mandook rule #3, the native has the inclination and capability to actively "
            f"pursue and build wealth through personal effort — self-made prosperity is strongly indicated.",
            "positive", 4,
            {"overall": 3, "money": 4, "career": 3},
            confidence="medium",
        ))

    # Rule #4: lagna lord + 9th lord related → luck in earning
    if l9 and l9 != l1 and _lords_related(l1, 1, p1, l9, 9, p9):
        triggered.append(_rule(
            f"D2-S4-LL-9TH-RELATED-{l1}-{l9}",
            f"D2: lagna lord {ll_name} related to 9th lord {_pname(l9)} — bhagya supports wealth",
            f"The lagna lord {ll_name} and 9th lord (bhagya/luck) are related in D2. "
            f"Per Labh Mandook rule #4, fortune actively supports the native's wealth-building — "
            f"earnings come with relative ease during these lords' dasha periods.",
            "positive", 5,
            {"overall": 4, "money": 5, "business": 3},
            confidence="medium",
        ))

    # Lagna lord in 12th → earnings dispersed (K.N. Rao example, p.54)
    if p1 == 12:
        triggered.append(_rule(
            f"D2-S4-LL-12TH-{l1}",
            f"D2: lagna lord {ll_name} in 12th — earnings tend to be spent or dispersed",
            f"Lagna lord {ll_name} in the 12th house of D2 indicates that earnings exist "
            f"but are consistently spent, donated, or lost rather than accumulated. "
            f"Wealth generation is possible but retention remains a persistent challenge.",
            "negative", 4,
            {"overall": -3, "money": -4, "business": -2},
            confidence="medium",
        ))

    return triggered


# ── Set 5: Parashari hora planet distribution ─────────────────────────────────

def _d2_s5_parashari_hora(d2_chart: dict[str, Any]) -> list[dict]:
    """Parashari hora planet distribution (p.46) — only fires if D2 uses Cancer/Leo signs.

    Detection: if all 7 main planets are placed only in Cancer (4) or Leo (5),
    the chart uses Parashari computation and hora-based rules apply.
    """
    planet_lookup = d2_chart.get("planet_lookup", {})
    main_planets = {c: p for c, p in planet_lookup.items() if c in {"Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"}}
    if not main_planets:
        return []

    sign_numbers = [p.get("sign_number") for p in main_planets.values() if p.get("sign_number")]
    if not sign_numbers or not all(s in {4, 5} for s in sign_numbers):
        return []

    SUN_HORA = 5   # Leo — self-effort, authority
    MOON_HORA = 4  # Cancer — family blessings, legacy

    favorable: dict[str, int] = {
        "Su": SUN_HORA, "Ma": SUN_HORA, "Ju": SUN_HORA,
        "Mo": MOON_HORA, "Ve": MOON_HORA, "Sa": MOON_HORA,
    }
    hora_labels = {SUN_HORA: "Sun hora (Leo)", MOON_HORA: "Moon hora (Cancer)"}
    hora_themes = {
        "Su": "authority and self-effort",
        "Ma": "courage and initiative",
        "Ju": "wisdom and fortune",
        "Mo": "family blessings and legacy",
        "Ve": "comforts and material inheritance",
        "Sa": "service and steady accumulation",
    }

    triggered = []
    for code, good_hora in favorable.items():
        p = main_planets.get(code, {})
        if not p:
            continue
        sign_num = p.get("sign_number")
        if sign_num != good_hora:
            continue
        name = _pname(code)
        triggered.append(_rule(
            f"D2-S5-{code}-FAVORABLE-HORA",
            f"{name} in {hora_labels[good_hora]} in D2 — auspicious hora for {hora_themes[code]}",
            f"{name} occupies its auspicious hora in D2. Per Parashari hora analysis (p.46), "
            f"this supports wealth accumulation through {hora_themes[code]} during its dasha period.",
            "positive", 3,
            {"overall": 2, "money": 3, "business": 2},
            confidence="medium",
        ))

    return triggered


# ── Main entry point ──────────────────────────────────────────────────────────

def evaluate_d2_hora_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    """Evaluate all D2 hora rule sets.

    Returns triggered-rule dicts in the same format as the YAML rule engine,
    varga_generic_rules.py, and d1_lagna_rules.py.
    """
    d2_chart = _get_d2_chart(chart_facts)
    if not d2_chart:
        return []

    triggered: list[dict[str, Any]] = []

    triggered.extend(_d2_s1_jupiter(d2_chart))
    triggered.extend(_d2_s2_key_lords(d2_chart))
    triggered.extend(_d2_s3_dhana_yogas(d2_chart))
    triggered.extend(_d2_s4_lagna_lord(d2_chart))
    triggered.extend(_d2_s5_parashari_hora(d2_chart))

    return triggered
