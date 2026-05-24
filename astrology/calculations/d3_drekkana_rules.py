"""D3-specific rules from the Drekkana chart chapter.

Source: Comprehensive Prediction by Divisional Charts — Drekkana D3 (pp. 67–91).

SET 1 (Key lord connections in D3 — Examination section, p. 73):
  D3-S1-1-5-9-ALL-RELATED       1st/5th/9th lords all connected — atma-jeevatma-parmatma unity
  D3-S1-1-5-RELATED-{X}-{Y}    1st + 5th lords related in D3
  D3-S1-1-9-RELATED-{X}-{Y}    1st + 9th lords related in D3
  D3-S1-5-9-RELATED-{X}-{Y}    5th + 9th lords related in D3
  D3-S1-3RD-LORD-ANGLE-{X}     3rd lord (effort/action) in angle/trine — fruits of action succeed
  D3-S1-3RD-LORD-DUSTHANA-{X}  3rd lord in dusthana — hindrances in efforts
  D3-S1-3RD-LORD-WEAK-{X}      3rd lord debilitated — weakened initiative
  D3-S1-MARS-EXALTED            Mars (natural 3rd karaka) exalted in D3
  D3-S1-MARS-OWN                Mars in own sign in D3
  D3-S1-MARS-DEBILITATED        Mars debilitated — courage/effort impaired

SET 2 (22nd Drekkana / Kharesh — pp. 71–73):
  D3-S2-KHARESH-TRIK            D3 8th lord in dusthana — malefic obstacles amplified
  D3-S2-KHARESH-LAGNA           D3 8th lord in 1st house — kharesh at self
  D3-S2-D1-8TH-IN-D3-LAGNA-{X} D1's 8th lord placed in D3 lagna — cross-chart malefic

SET 3 (BPHS drekkana category from D1 sign/degree — pp. 73–74, table p. 70):
  D3-S3-LL-SARPA-{X}            Lagna lord in Sarpa drekkana — scheming, negative
  D3-S3-5TH-SARPA-{X}          5th lord in Sarpa drekkana — no rise despite effort
  D3-S3-9TH-SARPA-{X}          9th lord in Sarpa drekkana — fortune withheld
  D3-S3-10TH-SARPA-{X}         10th lord in Sarpa drekkana — no professional fulfillment
  D3-S3-10TH-AYUDH-{X}         10th lord in Ayudh drekkana — valour in career (positive)
  D3-S3-8TH-AYUDH-WARN-{X}     8th lord in Ayudh drekkana — accidents warning
  D3-S3-SA-AYUDH-WARN           Saturn in Ayudh drekkana — accidents warning
  D3-S3-RAJYOGA-FEMALE-ANGLE-{X} Trikona lord in Female/Laxmi drekkana + angle/trine in D3 → high position
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Drekkana D3"
_SOURCE_PAGE = "67"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES

# BPHS drekkana category table (p. 70).
# Key: (sign_number 1–12, drekkana_number 1/2/3) → frozenset of categories.
# Drekkana number derived from planet's degree within sign: 0–10° = 1, 10–20° = 2, 20–30° = 3.
BPHS_DREKKANA_CATEGORY: dict[tuple[int, int], frozenset] = {
    # Aries (1)
    (1, 1): frozenset({"Ayudh", "Chatuspad"}),
    (1, 2): frozenset({"Chatuspad"}),                        # Female
    (1, 3): frozenset({"Ayudh"}),
    # Taurus (2)
    (2, 1): frozenset({"Chatuspad"}),                        # Female
    (2, 2): frozenset({"Sarpa", "Chatuspad"}),
    (2, 3): frozenset({"Chatuspad"}),
    # Gemini (3)
    (3, 1): frozenset({"Chatuspad"}),                        # Female
    (3, 2): frozenset({"Ayudh", "Pakshi"}),
    (3, 3): frozenset({"Ayudh"}),
    # Cancer (4)
    (4, 1): frozenset({"Chatuspad", "Varaha"}),
    (4, 2): frozenset({"Sarpa"}),                            # Female
    (4, 3): frozenset({"Sarpa"}),
    # Leo (5)
    (5, 1): frozenset({"Ayudh", "Chatuspad", "Pakshi"}),
    (5, 2): frozenset({"Ayudh"}),
    (5, 3): frozenset({"Ayudh", "Chatuspad"}),
    # Virgo (6)
    (6, 1): frozenset({"Pakshi"}),                           # Female
    (6, 2): frozenset({"Pakshi"}),
    (6, 3): frozenset({"Pakshi"}),
    # Libra (7)
    (7, 1): frozenset({"Pakshi"}),
    (7, 2): frozenset({"Pakshi"}),
    (7, 3): frozenset({"Chatuspad"}),
    # Scorpio (8)
    (8, 1): frozenset({"Sarpa"}),                            # Female
    (8, 2): frozenset({"Sarpa", "Pakshi"}),                  # Female
    (8, 3): frozenset({"Chatuspad"}),
    # Sagittarius (9)
    (9, 1): frozenset({"Pakshi"}),
    (9, 2): frozenset({"Ratna_Bhandhar"}),                   # Female
    (9, 3): frozenset({"Ayudh"}),
    # Capricorn (10)
    (10, 1): frozenset({"Chatuspad", "Pakshi", "Nigada"}),
    (10, 2): frozenset({"Chatuspad"}),                       # Female
    (10, 3): frozenset({"Chatuspad"}),
    # Aquarius (11)
    (11, 1): frozenset({"Ayudh"}),
    (11, 2): frozenset({"Ayudh"}),                           # Female
    (11, 3): frozenset({"Ayudh"}),
    # Pisces (12)
    (12, 1): frozenset({"Ayudh"}),
    (12, 2): frozenset({"Ayudh"}),                           # Female
    (12, 3): frozenset({"Sarpa"}),
}

# Female (Laxmi) drekkana positions — the book calls these "Laxmi drekkana" (p.74 rule 11).
# A planet whose D1 (sign_number, drekkana_partition) falls here is in a Female drekkana.
FEMALE_DREKKANA: frozenset[tuple[int, int]] = frozenset({
    (1, 2),   # Ari D2
    (2, 1),   # Tau D1
    (3, 1),   # Gem D1
    (4, 2),   # Can D2
    (6, 1),   # Vir D1
    (8, 1),   # Sco D1
    (8, 2),   # Sco D2
    (9, 2),   # Sag D2
    (10, 2),  # Cap D2
    (11, 2),  # Aqu D2
    (12, 2),  # Pis D2
})


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
        "system": "D3/DrekkanaRules",
        "chart": "D3",
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
        "source_file": "d3_drekkana_rules.py",
    }


def _get_d1_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d1", {})


def _get_d3_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d3", {})


def _build_lord_maps(d3_chart: dict[str, Any]) -> tuple[dict[int, str], dict[str, int]]:
    all_pl = d3_chart.get("all_lord_placements", {})
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
    return (
        placed_a == placed_b or  # conjunction
        placed_a == house_b or   # A placed in B's natal house
        placed_b == house_a      # B placed in A's natal house (parivartana)
    )


def _drekkana_partition(degree: float | None) -> int | None:
    if degree is None:
        return None
    d = float(degree) % 30
    if d < 10:
        return 1
    if d < 20:
        return 2
    return 3


def _get_bphs_category(d1_planet: dict[str, Any]) -> frozenset:
    sign_num = d1_planet.get("sign_number")
    degree = d1_planet.get("degree")
    partition = _drekkana_partition(degree)
    if not sign_num or not partition:
        return frozenset()
    return BPHS_DREKKANA_CATEGORY.get((int(sign_num), partition), frozenset())


# ── Set 1a: 1st / 5th / 9th lord connections in D3 ───────────────────────────

def _d3_s1_key_lords(d3_chart: dict[str, Any]) -> list[dict]:
    """Examination rule 1 (p.73): 1st + 5th + 9th lords connected in D3 → happy, fruitful life."""
    all_pl = d3_chart.get("all_lord_placements", {})
    triggered = []

    def _lord(n: int) -> tuple[str | None, int | None]:
        pl = all_pl.get(f"{n}_lord", {})
        return pl.get("lord"), pl.get("placed_house")

    l1, p1 = _lord(1)
    l5, p5 = _lord(5)
    l9, p9 = _lord(9)

    rel_1_5 = bool(l1 and l5 and _lords_related(l1, 1, p1, l5, 5, p5))
    rel_1_9 = bool(l1 and l9 and _lords_related(l1, 1, p1, l9, 9, p9))
    rel_5_9 = bool(l5 and l9 and _lords_related(l5, 5, p5, l9, 9, p9))

    if rel_1_5 and rel_1_9 and rel_5_9:
        triggered.append(_rule(
            "D3-S1-1-5-9-ALL-RELATED",
            f"D3: 1st ({_pname(l1)}), 5th ({_pname(l5)}), 9th ({_pname(l9)}) lords all connected — atma-jeevatma-parmatma unity",
            "All three soul-level lords (lagna = atma, 5th = jeevatma, 9th = parmatma) are connected "
            "in D3. Per Examination rule 1 (p.73), this is the signature of a happy, fulfilled life "
            "where efforts consistently bear fruit. The native's actions align with their karmic path.",
            "positive", 7,
            {"overall": 6, "career": 5, "business": 4},
            confidence="high",
        ))
    else:
        if rel_1_5:
            triggered.append(_rule(
                f"D3-S1-1-5-RELATED-{l1}-{l5}",
                f"D3: lagna lord {_pname(l1)} related to 5th lord {_pname(l5)} — self-expression and intelligence linked",
                "The lagna lord and 5th lord (intelligence, creativity, poorva punya) are connected in D3. "
                "Personal initiative bears fruit through creative and intellectual application. "
                "Planned actions tend to succeed.",
                "positive", 4,
                {"overall": 3, "career": 3, "business": 3},
                confidence="medium",
            ))
        if rel_1_9:
            triggered.append(_rule(
                f"D3-S1-1-9-RELATED-{l1}-{l9}",
                f"D3: lagna lord {_pname(l1)} related to 9th lord {_pname(l9)} — fortune supports self",
                "The lagna lord and 9th lord (bhagya, luck, dharma) are connected in D3. "
                "The native's efforts are guided and supported by fortune. Personal actions "
                "tend to align with broader life purpose.",
                "positive", 4,
                {"overall": 3, "career": 3, "business": 3},
                confidence="medium",
            ))
        if rel_5_9:
            triggered.append(_rule(
                f"D3-S1-5-9-RELATED-{l5}-{l9}",
                f"D3: 5th lord {_pname(l5)} related to 9th lord {_pname(l9)} — planning linked to fortune",
                "The 5th lord (intelligence, planning) and 9th lord (bhagya) are connected in D3. "
                "Planned efforts are supported by fortune, and the native's karma unfolds positively.",
                "positive", 3,
                {"overall": 3, "career": 2, "business": 2},
                confidence="medium",
            ))

    return triggered


# ── Set 1b: 3rd lord placement in D3 ─────────────────────────────────────────

def _d3_s1_third_lord(d3_chart: dict[str, Any]) -> list[dict]:
    """3rd lord placement in D3 (Examination rule 2, p.73) — success/failure of actions."""
    all_pl = d3_chart.get("all_lord_placements", {})
    pl = all_pl.get("3_lord", {})
    lord = pl.get("lord")
    placed = pl.get("placed_house")
    dignity = pl.get("dignity", "")
    triggered = []

    if not lord or placed is None:
        return []

    name = _pname(lord)
    strong = dignity in {"exalted", "own_sign"}
    weak = dignity == "debilitated"

    if placed in ANGLE_OR_TRINE:
        weight = 6 if strong else 4
        note = f" with {dignity} dignity" if strong else ""
        triggered.append(_rule(
            f"D3-S1-3RD-LORD-ANGLE-{lord}",
            f"D3 3rd lord {name} in house {placed} (angle/trine){note} — fruits of action succeed",
            f"The 3rd lord {name} (effort, courage, initiative) is well-placed in D3{note}. "
            "Per Examination rule 2 (p.73), planets strongly involving the 3rd house or its lord "
            "indicate success in undertakings. Efforts consistently translate into results.",
            "positive", weight,
            {"overall": 4, "career": 4, "business": 3},
            confidence="high" if strong else "medium",
        ))
    elif placed in DUSTHANA:
        triggered.append(_rule(
            f"D3-S1-3RD-LORD-DUSTHANA-{lord}",
            f"D3 3rd lord {name} in dusthana (house {placed}) — hindrances in efforts",
            f"The 3rd lord {name} (effort, action, courage) is in a dusthana in D3. "
            "Per Examination rule 2 (p.73), this indicates repeated hindrances in pursuing goals — "
            "fruits of effort are delayed, obstructed, or withheld.",
            "negative", 4,
            {"overall": -3, "career": -4, "business": -3},
            confidence="medium",
        ))
    elif weak:
        triggered.append(_rule(
            f"D3-S1-3RD-LORD-WEAK-{lord}",
            f"D3 3rd lord {name} debilitated (house {placed}) — weakened initiative",
            f"The 3rd lord {name} is debilitated in D3, weakening the drive and courage to act. "
            "Efforts are inconsistent or undermined by self-doubt.",
            "negative", 3,
            {"overall": -2, "career": -3, "business": -2},
            confidence="medium",
        ))

    return triggered


# ── Set 1c: Mars (natural 3rd karaka) dignity in D3 ──────────────────────────

def _d3_s1_mars(d3_chart: dict[str, Any]) -> list[dict]:
    """Mars as natural karaka of 3rd house — courage and effort quality in D3."""
    ma = d3_chart.get("planet_lookup", {}).get("Ma", {})
    if not ma:
        return []

    dignity = ma.get("dignity", "")
    house = ma.get("house")
    triggered = []

    if dignity == "exalted":
        triggered.append(_rule(
            "D3-S1-MARS-EXALTED",
            f"Mars (natural 3rd karaka) exalted in D3 (house {house}) — peak courage and drive",
            "Mars, the natural significator of the 3rd house (courage, initiative, effort), is exalted "
            "in D3. This is the strongest indicator of exceptional drive, boldness, and the ability "
            "to sustain effort against obstacles. Actions taken are powerful and decisive.",
            "positive", 5,
            {"overall": 4, "career": 5, "business": 4},
            confidence="high",
        ))
    elif dignity == "own_sign":
        triggered.append(_rule(
            "D3-S1-MARS-OWN",
            f"Mars (natural 3rd karaka) in own sign in D3 (house {house}) — reliable courage",
            "Mars in its own sign in D3 gives reliable, sustained courage and initiative. "
            "The native follows through on efforts with consistency, and actions tend to bear fruit.",
            "positive", 3,
            {"overall": 3, "career": 3, "business": 3},
            confidence="medium",
        ))
    elif dignity == "debilitated":
        triggered.append(_rule(
            "D3-S1-MARS-DEBILITATED",
            f"Mars (natural 3rd karaka) debilitated in D3 (house {house}) — impaired courage",
            "Mars debilitated in D3 weakens the primary significator of courage and sustained effort. "
            "The native may struggle with follow-through, face external resistance, or lack the "
            "boldness needed to convert intentions into results.",
            "negative", 4,
            {"overall": -3, "career": -3, "business": -3},
            confidence="medium",
        ))

    return triggered


# ── Set 2: 22nd Drekkana / Kharesh ───────────────────────────────────────────

def _d3_s2_kharesh(d3_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """22nd Drekkana (kharesh = D3's 8th lord) rules — pp. 71–73."""
    all_pl_d3 = d3_chart.get("all_lord_placements", {})
    triggered = []

    kh_pl = all_pl_d3.get("8_lord", {})
    kh_lord = kh_pl.get("lord")
    kh_placed = kh_pl.get("placed_house")

    if kh_lord and kh_placed is not None:
        kh_name = _pname(kh_lord)
        if kh_placed in DUSTHANA:
            triggered.append(_rule(
                "D3-S2-KHARESH-TRIK",
                f"D3 8th lord / kharesh {kh_name} in dusthana (house {kh_placed}) — malefic obstacles amplified",
                f"The kharesh (22nd drekkana lord / D3 8th lord) {kh_name} is in a dusthana. "
                "Per pp.71–73, the kharesh in a trik house amplifies obstacles related to longevity, "
                "hidden enemies, and inner turmoil — especially during its dasha period.",
                "negative", 4,
                {"overall": -3, "career": -3, "business": -2},
                confidence="medium",
            ))
        if kh_placed == 1:
            triggered.append(_rule(
                "D3-S2-KHARESH-LAGNA",
                f"D3 kharesh {kh_name} in 1st house — 22nd drekkana lord directly on self",
                f"The kharesh {kh_name} occupies the D3 lagna. Per p.73, this intense placement "
                "brings personal struggles with longevity, hidden opposition, and inner conflict — "
                "most potent during the kharesh's dasha period.",
                "negative", 5,
                {"overall": -4, "career": -3, "business": -2},
                confidence="medium",
            ))

    # Cross-chart: D1's 8th lord placed in D3 1st house (p.73, Indira Gandhi example)
    all_pl_d1 = d1_chart.get("all_lord_placements", {})
    d1_8th_lord = all_pl_d1.get("8_lord", {}).get("lord")
    if d1_8th_lord:
        d3_placement = d3_chart.get("planet_lookup", {}).get(d1_8th_lord, {})
        if d3_placement.get("house") == 1:
            triggered.append(_rule(
                f"D3-S2-D1-8TH-IN-D3-LAGNA-{d1_8th_lord}",
                f"D1 8th lord {_pname(d1_8th_lord)} occupies D3 lagna — cross-chart malefic signal",
                f"The 8th lord of D1 ({_pname(d1_8th_lord)}) is in the 1st house of D3. "
                "Per p.73, this cross-chart combination — when activated by mutual dashas of D1's "
                "8th lord and the kharesh — can bring loss of position, humiliation, or serious reversal.",
                "negative", 5,
                {"overall": -4, "career": -4, "business": -3},
                confidence="medium",
            ))

    return triggered


# ── Set 3: BPHS drekkana category from D1 planet position ────────────────────

def _d3_s3_bphs_category(d3_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """BPHS drekkana category rules (pp. 73–74) using D1 planet sign + degree partition."""
    all_pl_d1 = d1_chart.get("all_lord_placements", {})
    d1_planets = d1_chart.get("planet_lookup", {})
    triggered = []

    def _lord_code(n: int) -> str | None:
        return all_pl_d1.get(f"{n}_lord", {}).get("lord")

    def _d1_planet(code: str | None) -> dict[str, Any]:
        return d1_planets.get(code, {}) if code else {}

    def _category(code: str | None) -> frozenset:
        return _get_bphs_category(_d1_planet(code))

    # ── Rule 7: Sarpa drekkana (p.74) ────────────────────────────────────────

    ll = _lord_code(1)
    if "Sarpa" in _category(ll):
        triggered.append(_rule(
            f"D3-S3-LL-SARPA-{ll}",
            f"Lagna lord {_pname(ll)} in Sarpa drekkana (D1) — scheming and jealous tendencies",
            f"The lagna lord {_pname(ll)} occupies a Sarpa (serpent) drekkana in D1. Per rule 7 (p.74), "
            "the person tends toward jealousy, secretiveness, and scheming. "
            "Relationships may be strained and the spouse's health can be compromised.",
            "negative", 4,
            {"overall": -3, "career": -2, "business": -2},
            confidence="medium",
        ))

    l5 = _lord_code(5)
    if "Sarpa" in _category(l5):
        triggered.append(_rule(
            f"D3-S3-5TH-SARPA-{l5}",
            f"5th lord {_pname(l5)} in Sarpa drekkana (D1) — no rise despite effort",
            f"The 5th lord {_pname(l5)} is in a Sarpa drekkana. Per rule 7 (p.74), "
            "the person puts in great effort but situations conspire to force failure. "
            "Intelligence and planning are present but fruits are consistently withheld.",
            "negative", 4,
            {"overall": -3, "career": -4, "business": -3},
            confidence="medium",
        ))

    l9 = _lord_code(9)
    if "Sarpa" in _category(l9):
        triggered.append(_rule(
            f"D3-S3-9TH-SARPA-{l9}",
            f"9th lord {_pname(l9)} in Sarpa drekkana (D1) — fortune withheld despite bhagya",
            f"The 9th lord {_pname(l9)} is in a Sarpa drekkana. Per rule 7 (p.74), "
            "even with bhagya support, circumstances tend to force failure. "
            "Fortune is present but blocked — exceptional effort is required to break through.",
            "negative", 4,
            {"overall": -3, "career": -3, "business": -3},
            confidence="medium",
        ))

    l10 = _lord_code(10)
    if "Sarpa" in _category(l10):
        triggered.append(_rule(
            f"D3-S3-10TH-SARPA-{l10}",
            f"10th lord {_pname(l10)} in Sarpa drekkana (D1) — no professional fulfillment",
            f"The 10th lord {_pname(l10)} occupies a Sarpa drekkana. Per rule 7 (p.74), "
            "the native is indecisive in career and professional fulfillment remains elusive. "
            "Success is possible but consistently undermined by circumstances or inner hesitancy.",
            "negative", 5,
            {"overall": -3, "career": -5, "business": -4},
            confidence="medium",
        ))

    # ── Rule 8: Ayudh drekkana (p.74) ────────────────────────────────────────

    if "Ayudh" in _category(l10):
        triggered.append(_rule(
            f"D3-S3-10TH-AYUDH-{l10}",
            f"10th lord {_pname(l10)} in Ayudh drekkana (D1) — valour and self-reliance in career",
            f"The 10th lord {_pname(l10)} occupies an Ayudh (weapon) drekkana. Per rule 8 (p.74), "
            "planets in Ayudh drekkana grant valour and vitality — deficiencies are overcome by "
            "personal effort. The native rises in career through courage and self-reliance.",
            "positive", 5,
            {"overall": 3, "career": 5, "business": 3},
            confidence="medium",
        ))

    l8 = _lord_code(8)
    sa_planet = _d1_planet("Sa")
    if "Ayudh" in _category(l8):
        triggered.append(_rule(
            f"D3-S3-8TH-AYUDH-WARN-{l8}",
            f"8th lord {_pname(l8)} in Ayudh drekkana (D1) — accidents and harm by sharp objects",
            f"The 8th lord {_pname(l8)} is in an Ayudh drekkana. Per rule 8 (p.74), "
            "the 8th lord or Saturn in Ayudh drekkana indicates risk of accidents and harm — "
            "especially during the 8th lord's dasha period.",
            "negative", 4,
            {"overall": -3, "career": -2, "business": -2},
            confidence="medium",
        ))
    elif sa_planet and "Ayudh" in _get_bphs_category(sa_planet):
        triggered.append(_rule(
            "D3-S3-SA-AYUDH-WARN",
            "Saturn in Ayudh drekkana (D1) — accidents and harm warning",
            "Saturn occupies an Ayudh drekkana. Per rule 8 (p.74), Saturn in Ayudh drekkana "
            "indicates risk of accidents and harm — especially during Saturn's dasha or key transits.",
            "negative", 3,
            {"overall": -2, "career": -2, "business": -1},
            confidence="medium",
        ))

    # ── Rule 11: Female (Laxmi) drekkana + rajyoga planet in angle/trine in D3 ─

    trikona_lords = {_lord_code(h) for h in (1, 5, 9)} - {None}
    for lord_code in trikona_lords:
        d1_p = _d1_planet(lord_code)
        sign_num = d1_p.get("sign_number")
        degree = d1_p.get("degree")
        partition = _drekkana_partition(degree)
        if not sign_num or not partition:
            continue
        if (int(sign_num), partition) not in FEMALE_DREKKANA:
            continue
        d3_p = d3_chart.get("planet_lookup", {}).get(lord_code, {})
        d3_house = d3_p.get("house")
        if d3_house and d3_house in ANGLE_OR_TRINE:
            triggered.append(_rule(
                f"D3-S3-RAJYOGA-FEMALE-ANGLE-{lord_code}",
                f"Rajyoga lord {_pname(lord_code)} in Female/Laxmi drekkana (D1) + house {d3_house} in D3 — high position",
                f"{_pname(lord_code)} (trikona lord) occupies a Female / Laxmi drekkana (D1) and "
                f"is in an angle/trine (house {d3_house}) in D3. Per rule 11 (p.74), "
                "this combination strongly indicates high social position, wealth, and all amenities — "
                "the Laxmi drekkana empowers the planet's rajyoga promise.",
                "positive", 6,
                {"overall": 5, "career": 5, "business": 4},
                confidence="medium",
            ))

    return triggered


# ── Main entry point ──────────────────────────────────────────────────────────

def evaluate_d3_drekkana_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    """Evaluate all D3 drekkana rule sets.

    Returns triggered-rule dicts in the same format as the YAML rule engine,
    varga_generic_rules.py, d1_lagna_rules.py, and d2_hora_rules.py.
    """
    d3_chart = _get_d3_chart(chart_facts)
    d1_chart = _get_d1_chart(chart_facts)
    if not d3_chart:
        return []

    triggered: list[dict[str, Any]] = []

    triggered.extend(_d3_s1_key_lords(d3_chart))
    triggered.extend(_d3_s1_third_lord(d3_chart))
    triggered.extend(_d3_s1_mars(d3_chart))
    triggered.extend(_d3_s2_kharesh(d3_chart, d1_chart))
    triggered.extend(_d3_s3_bphs_category(d3_chart, d1_chart))

    return triggered
