"""D12-specific rules from the Dwadashamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Dwadashamsha D12 (pp. 170–183).

Purpose: Parents, grandparents, lineage, Gotra, poorva janam link, inheritance, and
the cause of evils (complement to D30). Sun = karaka for father; Moon = karaka for mother.
9th house = Lagna of father; 4th house = Lagna of mother.

Maraka houses:
  Father: 3rd and 10th of D12 (2nd and 7th from 9th); longevity = 4th of D12 (8th from 9th)
  Mother: 5th and 10th of D12 (2nd and 7th from 4th); longevity = 11th of D12 (8th from 4th)

SET 1 (Dwadashamsha Deity — nature of planet/parents from D1 degree):
  D12-S1-LAGNA-DEITY-{name}      D1 Lagna's dwadashamsha deity → nature of parental influence
  D12-S1-SUN-DEITY-{name}        D1 Sun's dwadashamsha deity → nature of father
  D12-S1-MOON-DEITY-{name}       D1 Moon's dwadashamsha deity → nature of mother
  D12-S1-PLANET-AHI              Planet in Ahi dwadashamsha → venomous affliction of that area
  D12-S1-PLANET-YAMA             Planet in Yama dwadashamsha → disciplined/rigid but difficult

SET 2 (Father — Sun and 9th house analysis):
  D12-S2-SUN-STRONG              Sun strong in angle/trine D12 — father well-placed
  D12-S2-SUN-DUSTHANA            Sun in 6/8/12 D12 — father has pain and difficulties
  D12-S2-9TH-LORD-ANGLE-TRINE    9th lord in angle/trine — father's lagna lord strong
  D12-S2-9TH-LORD-DUSTHANA       9th lord in dusthana — father's lagna lord weakened
  D12-S2-FATHER-MARAKA-3RD       Malefics in 3rd D12 — 2nd maraka from father's lagna
  D12-S2-FATHER-MARAKA-10TH      Malefics in 10th D12 — primary maraka from father's lagna
  D12-S2-FATHER-LONGEVITY-4TH    4th house analysis — 8th from father's lagna (longevity)

SET 3 (Mother — Moon and 4th house analysis):
  D12-S3-MOON-STRONG             Moon in angle/trine D12 — mother well-placed
  D12-S3-MOON-DUSTHANA           Moon in 6/8/12 D12 — mother has pain and difficulties
  D12-S3-4TH-LORD-ANGLE-TRINE    4th lord in angle/trine — mother's lagna lord strong
  D12-S3-4TH-LORD-DUSTHANA       4th lord in dusthana — mother's lagna lord weakened
  D12-S3-MOTHER-MARAKA-5TH       Malefics in 5th D12 — primary maraka from mother's lagna
  D12-S3-MOTHER-MARAKA-10TH      Malefics in 10th D12 — second maraka for mother and father
  D12-S3-MOTHER-LONGEVITY-11TH   11th house strong — 8th from mother's lagna (longevity)

SET 4 (Lineage, Inheritance, and Native-Parent Bond):
  D12-S4-PATERNAL-LINEAGE        Jupiter/Rahu for paternal lineage strength
  D12-S4-MATERNAL-LINEAGE        Mercury/Ketu for maternal lineage condition
  D12-S4-7TH-BENEFIC             Benefic in D12 7th — noble spouse, lineage continues
  D12-S4-5TH-POORVA-PUNYA        Jupiter + 5th lord strong — poorva punya, can be father
  D12-S4-5TH-AFFLICTED           Jupiter + 5th house afflicted — challenge in male progeny
  D12-S4-12TH-GOTRA              Planets in 12th D12 determine Gotra direction

SET 5 (Native-Parent Mutual Relation):
  D12-S5-LL-5TH-MUTUAL           Lagna lord and 5th lord mutually strong — good parent-child bond
  D12-S5-LL-5TH-HOSTILE          Lagna lord and 5th lord in mutual dusthana — strained bond
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Dwadashamsha D12"
_SOURCE_PAGE = "170"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
BENEFICS = frozenset({"Ju", "Ve", "Mo", "Me"})
MALEFICS = frozenset({"Su", "Ma", "Sa", "Ra", "Ke"})
NATURAL_MALEFICS = frozenset({"Ma", "Sa", "Ra", "Ke"})

# D12 deity cycle (repeats 3× in 12 dwadashamsha parts)
_D12_DEITIES = {1: "Ganesh", 2: "AshwiniKumar", 3: "Yama", 4: "Ahi"}

# Deity → (quality, career_or_parent_theme)
_DEITY_THEMES = {
    "Ganesh":        ("auspicious", "divine protection, obstacle removal, education, right direction"),
    "AshwiniKumar":  ("auspicious", "divine healing, good health care, caring and nurturing parents"),
    "Yama":          ("difficult",  "disciplined, rigid, inflexible; planet shows strict/harsh energy"),
    "Ahi":           ("malefic",    "venomous serpent energy; heavy affliction to what the planet signifies"),
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
        "system": "D12/DwadashamshaRules",
        "chart": "D12",
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
        "source_file": "d12_dwadashamsha_rules.py",
    }


def _get_d12_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d12", {})


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


def _d12_deity(degree: float) -> str:
    """Return D12 deity from D1 degree within sign (0–30°).

    D12 divides each sign into 12 equal parts of 2°30'.
    Deity cycle (repeating 3×): Ganesh → Ashwini Kumar → Yama → Ahi.
    Formula: deity_index = floor(degree / 2.5) % 4
    """
    try:
        idx = int(float(degree) / 2.5) % 4  # 0-indexed: 0=Ganesh,1=AK,2=Yama,3=Ahi
        return _D12_DEITIES[idx + 1]
    except (TypeError, ValueError, ZeroDivisionError):
        return ""


# ── Set 1: Dwadashamsha Deity System ─────────────────────────────────────────

def _d12_s1_deity(d12_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Deity of D12 Lagna, Sun, Moon, and malefic deity planets."""
    if not d1_chart:
        return []

    d1_lookup = d1_chart.get("planet_lookup", {})
    d1_lagna = d1_chart.get("lagna", {})
    triggered = []

    def _planet_deity(planet_data: dict, label: str, rule_id_prefix: str) -> dict | None:
        deg = planet_data.get("degree")
        if deg is None:
            return None
        deity = _d12_deity(deg)
        if not deity:
            return None
        quality, theme = _DEITY_THEMES[deity]
        polarity = "positive" if quality == "auspicious" else "negative"
        return _rule(
            f"{rule_id_prefix}-{deity.upper().replace(' ', '')}",
            f"{label} in {deity} dwadashamsha ({quality}) — {theme}",
            f"The {label} falls in the {deity} dwadashamsha. "
            f"{deity} brings the following quality: {theme}. "
            + (
                "This is an auspicious division, indicating divine protection and support "
                "for the corresponding parent/lineage area."
                if quality == "auspicious"
                else "This is a difficult division. Planets in Yama/Ahi dwadashamsha cause "
                "heavy affliction to the significations of that planet — the area it governs "
                "will carry rigidity, harshness, or venom. It associates this difficult energy "
                "to any planet it conjoins or aspects."
            ),
            polarity, 3 if quality == "auspicious" else 4,
            {"overall": 2 if quality == "auspicious" else -3, "family": 3 if quality == "auspicious" else -4},
            confidence="medium",
        )

    # Lagna deity
    if d1_lagna:
        r = _planet_deity(d1_lagna, "D1 Lagna", "D12-S1-LAGNA-DEITY")
        if r:
            triggered.append(r)

    # Sun deity (father)
    su_d1 = d1_lookup.get("Su", {})
    if su_d1:
        r = _planet_deity(su_d1, "Sun (father karaka)", "D12-S1-SUN-DEITY")
        if r:
            triggered.append(r)

    # Moon deity (mother)
    mo_d1 = d1_lookup.get("Mo", {})
    if mo_d1:
        r = _planet_deity(mo_d1, "Moon (mother karaka)", "D12-S1-MOON-DEITY")
        if r:
            triggered.append(r)

    # Flag key planets in Yama or Ahi (afflicted deities)
    afflicted_deities = {"Yama", "Ahi"}
    for code, label in [("Su", "Sun (father)"), ("Mo", "Moon (mother)"),
                        ("Ju", "Jupiter (paternal lineage)"), ("Sa", "Saturn")]:
        pdata = d1_lookup.get(code, {})
        deg = pdata.get("degree")
        if deg is None:
            continue
        deity = _d12_deity(deg)
        if deity not in afflicted_deities:
            continue
        rule_id = f"D12-S1-PLANET-{'AHI' if deity == 'Ahi' else 'YAMA'}-{code}"
        _, theme = _DEITY_THEMES[deity]
        triggered.append(_rule(
            rule_id,
            f"{label} in {deity} dwadashamsha — afflicted energy for its significations",
            f"{label} falls in the {deity} dwadashamsha, which {theme}. "
            "This creates a difficult energy around what this planet represents — for Sun, "
            "father faces hardship or strictness; for Moon, mother suffers; for Jupiter, "
            "the paternal lineage or progeny is affected. The influence spreads through "
            "any planets this body associates with by conjunction or aspect in D12.",
            "negative", 5,
            {"overall": -3, "family": -5},
            confidence="medium",
        ))

    return triggered


# ── Set 2: Father Analysis (Sun and 9th house) ────────────────────────────────

def _d12_s2_father(d12_chart: dict[str, Any]) -> list[dict]:
    """Father indicators: Sun placement, 9th lord (father's lagna lord), maraka houses for father."""
    triggered = []
    h2l, l2p = _build_lord_maps(d12_chart)
    d12_lookup = d12_chart.get("planet_lookup", {})

    # ── Sun in D12 ───────────────────────────────────────────────────────
    su = d12_lookup.get("Su", {})
    su_house = su.get("house")
    su_dignity = su.get("dignity", "")
    if su_house:
        if su_house in ANGLE_OR_TRINE or su_dignity in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D12-S2-SUN-STRONG",
                f"Sun strong in D12 (house {su_house}, {su_dignity or 'angle/trine'}) — father well-placed and prominent",
                "Sun is the primary karaka for father. A strong Sun in an angular or trine house "
                "of D12 indicates that the father is well-placed in life — holding authority, "
                "good health, and positive influence over the native. The father is likely "
                "prominent in his field and provides strong support to the family.",
                "positive", 5,
                {"overall": 3, "family": 5},
                confidence="high",
            ))
        if su_house in DUSTHANA or su_dignity == "debilitated":
            triggered.append(_rule(
                "D12-S2-SUN-DUSTHANA",
                f"Sun in dusthana D12 (house {su_house}, {su_dignity or 'dusthana'}) — father faces pain and difficulties",
                "Sun in a dusthana (6, 8, or 12) of D12 indicates the father faces pain, "
                "suffering, or serious difficulties in life. As the primary natural significator "
                "of father in D12, a weakened or dusthana Sun creates obstacles for the father — "
                "health problems, career difficulties, or early separation from the native. "
                "Sun afflicted in D12 shows pain to father.",
                "negative", 5,
                {"overall": -3, "family": -5},
                confidence="high",
            ))

    # ── 9th lord (father's lagna lord in D12) ───────────────────────────
    lord_9 = h2l.get(9)
    placed_9 = l2p.get(lord_9) if lord_9 else None
    lord_9_dign = d12_lookup.get(lord_9, {}).get("dignity", "") if lord_9 else ""
    if lord_9 and placed_9:
        if placed_9 in ANGLE_OR_TRINE or lord_9_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D12-S2-9TH-LORD-ANGLE-TRINE",
                f"9th lord {_pname(lord_9)} in angle/trine D12 (house {placed_9}) — father's lagna lord strong",
                f"The 9th house is the Lagna of father in D12. Its lord ({_pname(lord_9)}) in "
                f"an angle or trine (house {placed_9}) means father's lagna lord is strong — "
                "the father has a stable foundation, good standing, and a positive direction "
                "in life. The native benefits from a well-established paternal figure.",
                "positive", 5,
                {"overall": 3, "family": 5},
                confidence="high",
            ))
        elif placed_9 in DUSTHANA or lord_9_dign == "debilitated":
            triggered.append(_rule(
                "D12-S2-9TH-LORD-DUSTHANA",
                f"9th lord {_pname(lord_9)} in dusthana D12 (house {placed_9}) — father's lagna lord weakened",
                f"The 9th house (father's lagna) lord {_pname(lord_9)} is placed in a dusthana "
                f"(house {placed_9}) of D12, weakening the paternal foundation. The father may "
                "face difficulties in establishing himself, health challenges, or disruptions in "
                "his life that indirectly affect the native's parental support.",
                "negative", 4,
                {"overall": -2, "family": -4},
                confidence="high",
            ))

    # ── Maraka houses for father: 3rd and 10th of D12 ────────────────────
    # 3rd = 7th from 9th (= primary maraka from father's lagna)
    malefics_3rd = [p for p in _planets_in_house(d12_chart, 3) if p in NATURAL_MALEFICS]
    if malefics_3rd:
        names = ", ".join(_pname(p) for p in malefics_3rd)
        triggered.append(_rule(
            "D12-S2-FATHER-MARAKA-3RD",
            f"Malefic(s) {names} in 3rd house D12 — 7th from father's lagna, maraka for father",
            f"The 3rd house of D12 is the 7th from the 9th house (father's lagna), making it "
            f"a primary maraka house for father. Malefics ({names}) here indicate threat to "
            "father's longevity or serious health challenges. The 3rd lord and the planets "
            "here both function as marakas for the father — their dasha periods carry risk "
            "for the father's wellbeing.",
            "negative", 5,
            {"overall": -2, "family": -5},
            confidence="medium",
        ))

    # 10th = 2nd from 9th (= second maraka from father's lagna AND 7th from mother's lagna)
    malefics_10th = [p for p in _planets_in_house(d12_chart, 10) if p in NATURAL_MALEFICS]
    if malefics_10th:
        names = ", ".join(_pname(p) for p in malefics_10th)
        triggered.append(_rule(
            "D12-S2-FATHER-MARAKA-10TH",
            f"Malefic(s) {names} in 10th house D12 — maraka house for both parents",
            f"The 10th house of D12 is the karma house of parents — it is the 2nd from the "
            f"9th (second maraka for father) and the 7th from the 4th (primary maraka for "
            f"mother). Malefics ({names}) here carry maraka energy for both parents. This "
            "house is the most critical danger point for parental longevity in D12.",
            "negative", 6,
            {"overall": -3, "family": -6},
            confidence="medium",
        ))

    # ── 4th house = 8th from 9th = longevity indicator for father ────────
    planets_4th = _planets_in_house(d12_chart, 4)
    malefics_4th = [p for p in planets_4th if p in NATURAL_MALEFICS]
    benefics_4th = [p for p in planets_4th if p in BENEFICS]
    if malefics_4th and not benefics_4th:
        names = ", ".join(_pname(p) for p in malefics_4th)
        triggered.append(_rule(
            "D12-S2-FATHER-LONGEVITY-4TH",
            f"Malefic(s) {names} in 4th house D12 — 8th from father's lagna, longevity concern",
            f"The 4th house of D12 is the 8th from the 9th house (father's lagna), making it "
            f"the house of father's longevity in D12. Malefics ({names}) here with no benefic "
            "protection indicate challenges to the father's lifespan. Sun's weakness combined "
            "with affliction in the 4th from 9th is a significant indicator of father's "
            "health or lifespan concerns.",
            "negative", 5,
            {"overall": -2, "family": -5},
            confidence="medium",
        ))

    return triggered


# ── Set 3: Mother Analysis (Moon and 4th house) ───────────────────────────────

def _d12_s3_mother(d12_chart: dict[str, Any]) -> list[dict]:
    """Mother indicators: Moon placement, 4th lord (mother's lagna lord), maraka houses for mother."""
    triggered = []
    h2l, l2p = _build_lord_maps(d12_chart)
    d12_lookup = d12_chart.get("planet_lookup", {})

    # ── Moon in D12 ──────────────────────────────────────────────────────
    mo = d12_lookup.get("Mo", {})
    mo_house = mo.get("house")
    mo_dignity = mo.get("dignity", "")
    if mo_house:
        if mo_house in ANGLE_OR_TRINE or mo_dignity in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D12-S3-MOON-STRONG",
                f"Moon strong in D12 (house {mo_house}) — mother well-placed and nurturing",
                "Moon is the primary karaka for mother in D12. A well-placed Moon in an angle "
                "or trine indicates a strong, nurturing, and long-lived mother. The mother is "
                "emotionally available, supportive, and a positive force in the native's life. "
                "Her wellbeing and longevity are generally well-supported.",
                "positive", 5,
                {"overall": 3, "family": 5},
                confidence="high",
            ))
        if mo_house in DUSTHANA or mo_dignity == "debilitated":
            triggered.append(_rule(
                "D12-S3-MOON-DUSTHANA",
                f"Moon in dusthana D12 (house {mo_house}) — mother has pain and difficulties",
                "Moon in a dusthana of D12 indicates the mother faces pain, suffering, or "
                "health difficulties. As the karaka for mother, a weak or dusthana Moon in "
                "D12 is one of the clearest indicators of trouble for the mother — physical "
                "illness, emotional distress, or early separation from the native. "
                "Moon afflicted in D12 shows pain to mother.",
                "negative", 5,
                {"overall": -3, "family": -5},
                confidence="high",
            ))

    # ── 4th lord (mother's lagna lord in D12) ────────────────────────────
    lord_4 = h2l.get(4)
    placed_4 = l2p.get(lord_4) if lord_4 else None
    lord_4_dign = d12_lookup.get(lord_4, {}).get("dignity", "") if lord_4 else ""
    if lord_4 and placed_4:
        if placed_4 in ANGLE_OR_TRINE or lord_4_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D12-S3-4TH-LORD-ANGLE-TRINE",
                f"4th lord {_pname(lord_4)} in angle/trine D12 (house {placed_4}) — mother's lagna lord strong",
                f"The 4th house is the Lagna of mother in D12. Its lord ({_pname(lord_4)}) in "
                f"an angle or trine (house {placed_4}) means mother's lagna lord is well placed — "
                "the mother has strength, good health, and a positive role in the native's life. "
                "The maternal bond is strong and the mother is a stabilising presence.",
                "positive", 5,
                {"overall": 3, "family": 5},
                confidence="high",
            ))
        elif placed_4 in DUSTHANA or lord_4_dign == "debilitated":
            triggered.append(_rule(
                "D12-S3-4TH-LORD-DUSTHANA",
                f"4th lord {_pname(lord_4)} in dusthana D12 (house {placed_4}) — mother's lagna lord weakened",
                f"The 4th house (mother's lagna) lord {_pname(lord_4)} is placed in a dusthana "
                f"(house {placed_4}) of D12, weakening the maternal foundation. The mother may "
                "face health challenges, adversity, or a difficult life path that creates "
                "distance or strain in the mother-child relationship.",
                "negative", 4,
                {"overall": -2, "family": -4},
                confidence="high",
            ))

    # ── Maraka houses for mother: 5th and 10th of D12 ────────────────────
    # 5th = 2nd from 4th (primary maraka for mother's lagna)
    malefics_5th = [p for p in _planets_in_house(d12_chart, 5) if p in NATURAL_MALEFICS]
    if malefics_5th:
        names = ", ".join(_pname(p) for p in malefics_5th)
        triggered.append(_rule(
            "D12-S3-MOTHER-MARAKA-5TH",
            f"Malefic(s) {names} in 5th house D12 — 2nd from mother's lagna, primary maraka",
            f"The 5th house of D12 is the 2nd from the 4th house (mother's lagna), making it "
            f"a primary maraka for mother. Malefics ({names}) here indicate a significant "
            "threat to the mother's wellbeing or longevity. Their dasha periods are timing "
            "windows for challenges to the mother's health and life.",
            "negative", 5,
            {"overall": -2, "family": -5},
            confidence="medium",
        ))

    # 10th = already noted in father analysis as shared maraka; flagged separately for mother clarity
    lord_10 = h2l.get(10)
    placed_10 = l2p.get(lord_10) if lord_10 else None
    lord_10_dign = d12_lookup.get(lord_10, {}).get("dignity", "") if lord_10 else ""
    if lord_10 and placed_10 in DUSTHANA:
        triggered.append(_rule(
            "D12-S3-MOTHER-MARAKA-10TH",
            f"D12 10th lord {_pname(lord_10)} in dusthana (house {placed_10}) — maraka lord weak",
            f"The 10th house of D12 is the 7th from mother's lagna (4th) AND the 2nd from "
            f"father's lagna (9th) — it is the karma house and a maraka for both parents. "
            f"Its lord {_pname(lord_10)} in a dusthana (house {placed_10}) means this maraka "
            "is activated, adding pressure to both parents' wellbeing.",
            "negative", 4,
            {"overall": -2, "family": -4},
            confidence="medium",
        ))

    # ── 11th house = 8th from mother's lagna (4th) = longevity of mother ─
    lord_11 = h2l.get(11)
    placed_11 = l2p.get(lord_11) if lord_11 else None
    lord_11_dign = d12_lookup.get(lord_11, {}).get("dignity", "") if lord_11 else ""
    if lord_11 and placed_11:
        if placed_11 in ANGLE_OR_TRINE or lord_11_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D12-S3-MOTHER-LONGEVITY-11TH",
                f"D12 11th lord {_pname(lord_11)} well-placed (house {placed_11}) — mother's longevity supported",
                f"The 11th house of D12 is the 8th from the 4th (mother's lagna), making it "
                f"the longevity house for mother. Its lord {_pname(lord_11)} well-placed in "
                f"house {placed_11} supports the mother's long life and recovery from illness. "
                "A strong 11th lord in D12 is one of the protective indicators for the mother.",
                "positive", 4,
                {"overall": 2, "family": 4},
                confidence="medium",
            ))

    return triggered


# ── Set 4: Lineage, Inheritance, and Native-Parent Bond ──────────────────────

def _d12_s4_lineage(d12_chart: dict[str, Any]) -> list[dict]:
    """Lineage, inheritance, poorva punya, continuation of family line."""
    triggered = []
    h2l, l2p = _build_lord_maps(d12_chart)
    d12_lookup = d12_chart.get("planet_lookup", {})

    # ── Paternal lineage: Jupiter and Rahu ───────────────────────────────
    ju = d12_lookup.get("Ju", {})
    ra = d12_lookup.get("Ra", {})
    ju_house = ju.get("house")
    ju_dign = ju.get("dignity", "")
    ra_house = ra.get("house")

    if ju_house and (ju_house in ANGLE_OR_TRINE or ju_dign in {"exalted", "own_sign"}):
        triggered.append(_rule(
            "D12-S4-PATERNAL-LINEAGE-JU",
            f"Jupiter well-placed in D12 (house {ju_house}) — paternal lineage strong",
            "Jupiter and Rahu are seen for the paternal lineage. A well-placed Jupiter in "
            f"house {ju_house} of D12 indicates a strong, auspicious paternal line with good "
            "ancestry and dharmic heritage. The native benefits from the blessings and "
            "standing of the paternal family. Jupiter's strength also supports the native's "
            "ability to continue the paternal lineage.",
            "positive", 4,
            {"overall": 3, "family": 4},
            confidence="medium",
        ))
    elif ju_house and ju_house in DUSTHANA:
        triggered.append(_rule(
            "D12-S4-PATERNAL-LINEAGE-JU-WEAK",
            f"Jupiter in dusthana D12 (house {ju_house}) — paternal lineage under strain",
            "Jupiter in a dusthana of D12 weakens the paternal lineage indicator. Obstacles "
            "in the paternal family ancestry, breaks in the lineage, or difficulty in "
            "maintaining the family's traditional or spiritual heritage are indicated.",
            "negative", 4,
            {"overall": -2, "family": -4},
            confidence="medium",
        ))

    # ── Maternal lineage: Mercury and Ketu ───────────────────────────────
    me = d12_lookup.get("Me", {})
    ke = d12_lookup.get("Ke", {})
    me_house = me.get("house")
    me_dign = me.get("dignity", "")
    ke_house = ke.get("house")

    if me_house and (me_house in ANGLE_OR_TRINE or me_dign in {"exalted", "own_sign"}):
        triggered.append(_rule(
            "D12-S4-MATERNAL-LINEAGE-ME",
            f"Mercury well-placed in D12 (house {me_house}) — maternal lineage strong",
            "Mercury and Ketu are seen for the maternal lineage. Well-placed Mercury in "
            f"house {me_house} of D12 indicates a well-functioning maternal family line — "
            "good maternal ancestry, supportive maternal relatives, and positive energy "
            "from the maternal side of the family.",
            "positive", 3,
            {"overall": 2, "family": 3},
            confidence="medium",
        ))

    if ke_house and ke_house in DUSTHANA:
        triggered.append(_rule(
            "D12-S4-MATERNAL-LINEAGE-KE-DUSTHANA",
            f"Ketu in dusthana D12 (house {ke_house}) — maternal lineage challenges",
            f"Ketu in the dusthana (house {ke_house}) of D12 puts pressure on the maternal "
            "lineage. The maternal ancestry may carry karmic debts, breaks in lineage, or "
            "health challenges that pass through the maternal line. Mercury/Ketu in Sarpa "
            "(Ahi) dwadashamsha is particularly concerning for the maternal side.",
            "negative", 3,
            {"overall": -2, "family": -3},
            confidence="medium",
        ))

    # ── Benefic in 7th → continuation of lineage, noble spouse ──────────
    benefics_7th = [p for p in _planets_in_house(d12_chart, 7) if p in BENEFICS]
    if benefics_7th:
        names = ", ".join(_pname(p) for p in benefics_7th)
        triggered.append(_rule(
            "D12-S4-7TH-BENEFIC",
            f"Benefic(s) {names} in D12 7th house — noble spouse, lineage continues",
            f"A benefic planet ({names}) in the 7th house of D12 promises a noble spouse who "
            "will be able to continue the lineage of the family. The 7th house in D12 "
            "represents partners who promote and continue the family line. A benefic here "
            "is one of the strongest indicators of a good marriage from the parental/lineage "
            "perspective.",
            "positive", 5,
            {"overall": 3, "family": 5, "marriage": 3},
            confidence="high",
        ))

    # ── Jupiter + 5th house/lord: poorva punya and male child potential ──
    lord_5 = h2l.get(5)
    placed_5 = l2p.get(lord_5) if lord_5 else None
    planets_5th = _planets_in_house(d12_chart, 5)
    malefics_5 = [p for p in planets_5th if p in NATURAL_MALEFICS]

    # 5th afflicted AND Jupiter weak/dusthana → challenge in male progeny
    ju_in_dusthana = ju_house in DUSTHANA if ju_house else False
    lord_5_in_dusthana = placed_5 in DUSTHANA if placed_5 else False

    if ju_in_dusthana and lord_5_in_dusthana:
        triggered.append(_rule(
            "D12-S4-5TH-AFFLICTED",
            f"Jupiter (house {ju_house}) and 5th lord {_pname(lord_5) if lord_5 else '?'} (house {placed_5}) both in dusthana D12 — poorva punya reduced, male progeny challenge",
            "Jupiter, the 5th house, and the 5th lord together indicate poorva punya (past life "
            "merit from parents) and the native's capacity for fatherhood. When both Jupiter "
            "and the 5th lord are in dusthana of D12, the poorva punya from parents is reduced "
            "and there may be challenges in the birth of a male child. This also suggests the "
            "parents' own good karma was tested.",
            "negative", 5,
            {"overall": -3, "family": -4, "children": -4},
            confidence="medium",
        ))
    elif ju_house and (ju_house in ANGLE_OR_TRINE and placed_5 and placed_5 in ANGLE_OR_TRINE):
        triggered.append(_rule(
            "D12-S4-5TH-POORVA-PUNYA",
            f"Jupiter (house {ju_house}) and 5th lord {_pname(lord_5) if lord_5 else '?'} (house {placed_5}) both well-placed D12 — strong poorva punya from parents",
            "Jupiter, the 5th house, and the 5th lord in D12 indicate poorva punya — the "
            "accumulated good karma from parents passed to the native. Both being well-placed "
            "means the native inherits strong blessings, can become a good parent, and the "
            "family line continues with merit and spiritual strength.",
            "positive", 4,
            {"overall": 3, "family": 4, "children": 3},
            confidence="medium",
        ))

    # ── 12th house: Gotra and lineage markers ────────────────────────────
    planets_12th = _planets_in_house(d12_chart, 12)
    if planets_12th:
        names = ", ".join(_pname(p) for p in planets_12th)
        triggered.append(_rule(
            "D12-S4-12TH-GOTRA",
            f"Planets {names} in 12th house D12 — Gotra and lineage direction indicated",
            f"The 12th house of D12 indicates the Gotra (clan lineage) of the family. "
            f"{names} in the 12th, along with the 12th lord, determine the nature of the "
            "family's Gotra and ancestral lineage. This house also represents the paternal "
            "grandmother (4th from 9th) and the maternal grandmother (9th from 4th). "
            "Malefics here may indicate breaks in lineage or Gotra-related karmic challenges.",
            "neutral", 2,
            {"overall": 1, "family": 2},
            confidence="low",
        ))

    return triggered


# ── Set 5: Native-Parent Mutual Relation ─────────────────────────────────────

def _d12_s5_native_parent_bond(d12_chart: dict[str, Any]) -> list[dict]:
    """Lagna lord (parents) and 5th lord (native) mutual relation in D12."""
    triggered = []
    h2l, l2p = _build_lord_maps(d12_chart)

    lord_1 = h2l.get(1)
    lord_5 = h2l.get(5)
    placed_1 = l2p.get(lord_1) if lord_1 else None
    placed_5 = l2p.get(lord_5) if lord_5 else None

    if not (lord_1 and lord_5 and placed_1 and placed_5):
        return []

    # "In the astrological scheme, the lords of trines are friends to each other."
    # Check if Lagna lord and 5th lord are mutually well-placed from each other.
    # Mutual strength = both in angle/trine from D12 Lagna
    mutual_strong = placed_1 in ANGLE_OR_TRINE and placed_5 in ANGLE_OR_TRINE
    # Mutual hostile = one in dusthana of the other (placed_1 hostile to placed_5's house)
    hostile = placed_1 in DUSTHANA and placed_5 in DUSTHANA

    if mutual_strong and lord_1 != lord_5:
        triggered.append(_rule(
            "D12-S5-LL-5TH-MUTUAL",
            f"D12 Lagna lord {_pname(lord_1)} (house {placed_1}) and 5th lord {_pname(lord_5)} (house {placed_5}) both well-placed — good parent-child bond",
            f"In D12, the Lagna represents the parents and the 5th house represents the native "
            f"(the child of the parents). When both the Lagna lord ({_pname(lord_1)}) and the "
            f"5th lord ({_pname(lord_5)}) are well placed in angles or trines, the lords of "
            "these two trine houses are in harmony — signifying a strong, loving, and mutually "
            "supportive relationship between the native and their parents. The native inherits "
            "good qualities from the parental family.",
            "positive", 4,
            {"overall": 3, "family": 4},
            confidence="medium",
        ))
    elif hostile:
        triggered.append(_rule(
            "D12-S5-LL-5TH-HOSTILE",
            f"D12 Lagna lord {_pname(lord_1)} (house {placed_1}) and 5th lord {_pname(lord_5)} (house {placed_5}) both in dusthana — strained parent-child bond",
            f"In D12, Lagna lord ({_pname(lord_1)}) and 5th lord ({_pname(lord_5)}) both in "
            "dusthana positions creates strain in the relationship between the native and their "
            "parents. Distance, tension, unresolved karma, or adversity shapes the parent-child "
            "dynamic. The native may feel disconnected from family roots or struggle to receive "
            "parental support.",
            "negative", 4,
            {"overall": -3, "family": -4},
            confidence="medium",
        ))

    return triggered


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d12_dwadashamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d12_chart = _get_d12_chart(chart_facts)
    if not d12_chart:
        return []
    d1_chart = _get_d1_chart(chart_facts)
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d12_s1_deity(d12_chart, d1_chart))
    triggered.extend(_d12_s2_father(d12_chart))
    triggered.extend(_d12_s3_mother(d12_chart))
    triggered.extend(_d12_s4_lineage(d12_chart))
    triggered.extend(_d12_s5_native_parent_bond(d12_chart))
    return triggered
