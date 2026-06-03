"""D16-specific rules from the Shodashamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Shodashamsha D16 (pp. 184–205).

Also called Kalamsha (16 Moon phases) or Niripmanamsha.
Purpose: Movable assets, vehicles, comforts, and the ability to enjoy happiness.
Measures: "How much a person is able to enjoy the happiness available to him."
Moon governs mental strength, patience, and endurance — negative side is mirage of pleasures.

Deity systems:
  Parashari Lord: 4-lord cycle (Brahma/Vishnu/Mahesh/Sun), direction depends on sign parity
  Tithi Lord: 16 Moon-phase lords (Agni → Pitra), same for all signs
  Cruel shodashamsha = Mahesh (Parashari) or Rudra/Yama/Shiva (Tithi)

Formula (from D1 degree and sign):
  part = floor(degree_in_D1_sign / 1.875) + 1   [1–16]
  Odd sign: parts 1,5,9,13→Brahma; 2,6,10,14→Vishnu; 3,7,11,15→Mahesh; 4,8,12,16→Sun
  Even sign: parts 1,5,9,13→Sun; 2,6,10,14→Mahesh; 3,7,11,15→Vishnu; 4,8,12,16→Brahma

SET 1 (Shodashamsha Lord Systems — Parashari + Tithi lords):
  D16-S1-LAGNA-PARASHARI-{lord}    D1 Lagna's Parashari lord → nature of happiness source
  D16-S1-VENUS-PARASHARI-{lord}    D1 Venus's Parashari lord → vehicle/luxury quality
  D16-S1-SUN-PARASHARI-{lord}      D1 Sun's Parashari lord → soul attachment to material
  D16-S1-LAGNA-TITHI-{tithi}       D1 Lagna's tithi lord → specific wish/blessing
  D16-S1-VENUS-TITHI-{tithi}       D1 Venus's tithi lord → vehicle/luxury wish-type
  D16-S1-CRUEL-DASHA-DAMAGE        Planets in cruel shodashamsha + 6/8/12/3 link → dasha damage

SET 2 (Core Examination — Venus, Jupiter, Moon, Mars, Sun):
  D16-S2-VENUS-STRONG              Venus in angle/trine/own/exalted D16 — luxuries and vehicles
  D16-S2-VENUS-CRUEL-SHODASHAMSHA  Venus in cruel (Mahesh/Shiva) shodashamsha — vehicles with danger
  D16-S2-VENUS-DIGBALA             Venus in 4th D16 — directional strength, good luxuries
  D16-S2-JUPITER-STRONG-ASPECTS    Jupiter strong and aspects D16 Lagna — inner happiness assured
  D16-S2-JUPITER-DUSTHANA          Jupiter in dusthana D16 — inner happiness obstructed
  D16-S2-MOON-STRONG               Moon well-placed D16 — mental acceptance and enjoyment of comforts
  D16-S2-MOON-WEAK                 Moon weak/dusthana D16 — mental dissatisfaction, can't enjoy
  D16-S2-MARS-PERMANENT            Mars well-placed D16 — permanent/long-lasting happiness

SET 3 (Vehicle Accident and Loss Indicators):
  D16-S3-6TH-8TH-LAGNA-4TH        6th/8th lord/house linked with Lagna or 4th — danger/accidents
  D16-S3-3RD-12TH-LAGNA-4TH       3rd/12th lord/house linked with Lagna or 4th — vehicle loss
  D16-S3-4TH-DUSTHANA-LINK        4th house linked with 6/8/12 → vehicular accident risk
  D16-S3-8TH-AFFLICTED             Afflicted planets in 8th D16 — fatal accident risk in their dasha
  D16-S3-LAGNA-6TH-8TH-LORD       6th or 8th lord occupies D16 Lagna — great vehicular danger

SET 4 (Happiness Level and Access):
  D16-S4-9TH-STRONG                9th house strong D16 — luck in luxuries, long travel comforts
  D16-S4-4TH-STRONG                4th house strong D16 — happiness from material comforts
  D16-S4-11TH-MALEFIC-GREED       Lagna + 11th both with malefics — insatiable greed for amenities
  D16-S4-D1-4TH-LORD-7TH-D16      D1 4th lord in D16 7th — vehicle/luxury provided by others
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Shodashamsha D16"
_SOURCE_PAGE = "184"

DUSTHANA = frozenset({6, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
BENEFICS = frozenset({"Ju", "Ve", "Mo", "Me"})
MALEFICS = frozenset({"Su", "Ma", "Sa", "Ra", "Ke"})
NATURAL_MALEFICS = frozenset({"Ma", "Sa", "Ra", "Ke"})

# Parashari lord themes
_PARASHARI_THEMES = {
    "Brahma":  ("creative",   "happiness through creating, starting new things, intelligence, knowledge bonds; creative power"),
    "Vishnu":  ("preserving", "happiness through order, discipline, maintenance; attachment to home, comforts, material world"),
    "Mahesh":  ("cruel",      "trouble and accidents; destruction of what is not per law; planet shows accident/damage energy"),
    "Sun":     ("royal",      "happiness through power, authority, fame; pride in achievements; karma yoga and work satisfaction"),
}

# Tithi lord → (quality, wish/blessing theme)
_TITHI_LORDS = {
    1:  ("Agni",        "auspicious", "fire, grains, wealth through prayer and havan"),
    2:  ("Brahma",      "auspicious", "all kinds of learning, feeds knowledge-seekers"),
    3:  ("Kuber",       "auspicious", "wealth and success in commercial dealings"),
    4:  ("Ganesh",      "auspicious", "destruction of all obstacles"),
    5:  ("Nagraj",      "auspicious", "freedom from fear of poison; spouse, son, and wealth"),
    6:  ("Kartikeya",   "auspicious", "handsome, long-lived, genius and fame"),
    7:  ("SunGod",      "auspicious", "protection and divine grace"),
    8:  ("Rudra",       "cruel",      "battle with bondage and death; knowledge, beauty, freedom — but also destroys"),
    9:  ("Durga",       "mixed",      "victorious in wars; all-round success but through challenge"),
    10: ("Yama",        "cruel",      "free from ailments but governs death; prevents hell"),
    11: ("Vishwadeva",  "auspicious", "progeny, wealth, and lands"),
    12: ("Vishnu_P",    "auspicious", "person becomes worshipable and victorious"),
    13: ("Kamdev",      "auspicious", "desired spouse and all desires fulfilled"),
    14: ("Shiva_T",     "cruel",      "luxuries, wealth, and sons — but Shiva also destroys; Shiva shodashamsha causes problems"),
    15: ("Moon_T",      "auspicious", "person rules over the entire world forever"),
    16: ("Pitra",       "mixed",      "wealth protected, long life and strength — but Pitra = departed souls, past karma"),
}

_CRUEL_TITHI = frozenset({8, 10, 14})   # Rudra, Yama, Shiva_T
_CRUEL_PARASHARI = "Mahesh"


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
        "system": "D16/ShodashamshRules",
        "chart": "D16",
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
        "source_file": "d16_shodashamsha_rules.py",
    }


def _get_d16_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d16", {})


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


def _d16_part(degree: float) -> int:
    """Return shodashamsha part (1–16) from degree within D1 sign (0–30°)."""
    try:
        return min(int(float(degree) / 1.875), 15) + 1  # clamp 0-15 then +1
    except (TypeError, ValueError):
        return 0


def _parashari_lord(sign_number: int, part: int) -> str:
    """Return Parashari lord for a shodashamsha part in a given D1 sign."""
    if part < 1 or part > 16:
        return ""
    idx = (part - 1) % 4  # 0,1,2,3
    if sign_number % 2 == 1:  # odd sign: Brahma→Vishnu→Mahesh→Sun
        return ["Brahma", "Vishnu", "Mahesh", "Sun"][idx]
    else:                      # even sign: Sun→Mahesh→Vishnu→Brahma
        return ["Sun", "Mahesh", "Vishnu", "Brahma"][idx]


def _tithi_lord_info(part: int) -> tuple[str, str, str]:
    """Return (name, quality, theme) for a shodashamsha part (1–16)."""
    if part < 1 or part > 16:
        return ("", "", "")
    name, quality, theme = _TITHI_LORDS[part]
    return name, quality, theme


# ── Set 1: Shodashamsha Lord Systems ─────────────────────────────────────────

def _d16_s1_lords(d16_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Parashari and Tithi lords for Lagna, Venus, and Sun. Cruel dasha damage rule."""
    if not d1_chart:
        return []

    d1_lookup = d1_chart.get("planet_lookup", {})
    d1_lagna = d1_chart.get("lagna", {})
    d16_lookup = d16_chart.get("planet_lookup", {})
    h2l_d16, l2p_d16 = _build_lord_maps(d16_chart)
    triggered = []

    def _lord_rule(planet_data: dict, label: str, p_rule: str, t_rule: str) -> list[dict]:
        result = []
        deg = planet_data.get("degree")
        sign_num = planet_data.get("sign_number")
        if deg is None or sign_num is None:
            return result
        part = _d16_part(float(deg))
        if part < 1:
            return result

        # Parashari lord
        p_lord = _parashari_lord(int(sign_num), part)
        if p_lord:
            ptheme_type, ptheme = _PARASHARI_THEMES.get(p_lord, ("neutral", ""))
            is_cruel = (p_lord == _CRUEL_PARASHARI)
            result.append(_rule(
                f"{p_rule}-{p_lord.upper()}",
                f"{label} in {p_lord} shodashamsha (part {part}) — {ptheme_type} happiness quality",
                f"The {label} falls in the {p_lord} shodashamsha (part {part} of its D1 sign). "
                f"{p_lord} governs: {ptheme}. "
                + ("This is a CRUEL shodashamsha. Planets in Mahesh (Shiva) shodashamsha show the "
                   "period of troubles like accident or damages. Their dasha periods carry risk "
                   "for vehicles and material comforts."
                   if is_cruel
                   else "The bhava whose lord is in a benefic shodashamsha will flourish."),
                "negative" if is_cruel else "positive", 4 if is_cruel else 3,
                {"overall": -3 if is_cruel else 2, "happiness": -4 if is_cruel else 3},
                confidence="high",
            ))

        # Tithi lord
        t_name, t_quality, t_theme = _tithi_lord_info(part)
        if t_name:
            is_cruel_t = (part in _CRUEL_TITHI)
            result.append(_rule(
                f"{t_rule}-{t_name.upper().replace('_', '')}",
                f"{label} in {t_name} shodashamsha (tithi {part}) — {t_quality}: {t_theme}",
                f"The {label} occupies the {t_name} shodashamsha (part {part}). "
                f"The tithi lord {t_name} bestows: {t_theme}. "
                + ("Rudra, Yama, and Shiva tithis are CRUEL. Planets here that are also linked "
                   "to 6th, 8th, 12th, or 3rd house in D16 cause damage in their dasha/antardasha."
                   if is_cruel_t
                   else "Worshipping this tithi lord with mantras, japa, and havan fulfils the wish "
                   "associated with this planet's portfolio."),
                "negative" if is_cruel_t else "neutral", 3 if is_cruel_t else 2,
                {"overall": -3 if is_cruel_t else 1, "happiness": -3 if is_cruel_t else 2},
                confidence="medium",
            ))

        return result

    # Lagna lords
    if d1_lagna:
        triggered.extend(_lord_rule(d1_lagna, "D1 Lagna", "D16-S1-LAGNA-PARASHARI", "D16-S1-LAGNA-TITHI"))

    # Venus lords (karaka for vehicles)
    ven_d1 = d1_lookup.get("Ve", {})
    if ven_d1:
        triggered.extend(_lord_rule(ven_d1, "Venus (vehicle karaka)", "D16-S1-VENUS-PARASHARI", "D16-S1-VENUS-TITHI"))

    # Sun lords (soul attachment to material)
    sun_d1 = d1_lookup.get("Su", {})
    if sun_d1:
        deg = sun_d1.get("degree")
        sign_num = sun_d1.get("sign_number")
        if deg is not None and sign_num is not None:
            part = _d16_part(float(deg))
            p_lord = _parashari_lord(int(sign_num), part) if part > 0 else ""
            if p_lord:
                ptheme_type, ptheme = _PARASHARI_THEMES.get(p_lord, ("neutral", ""))
                triggered.append(_rule(
                    f"D16-S1-SUN-PARASHARI-{p_lord.upper()}",
                    f"Sun in {p_lord} shodashamsha — soul attachment: {ptheme_type}",
                    f"The shodashamsha lord of Sun reveals the richness of material happiness and "
                    f"the soul's attachment to it. Sun is in the {p_lord} shodashamsha (part {part}). "
                    f"This means the soul's attachment to material pleasures is through: {ptheme}.",
                    "positive" if ptheme_type in {"creative", "preserving", "royal"} else "negative",
                    2,
                    {"overall": 1, "happiness": 2},
                    confidence="medium",
                ))

    # ── Cruel shodashamsha + 6/8/12/3 house link = dasha damage ─────────
    danger_houses = frozenset({3, 6, 8, 12})
    for code, pdata in d16_lookup.items():
        house = pdata.get("house")
        if house is None or house not in danger_houses:
            continue
        # Check if this planet is in cruel shodashamsha (from D1 data)
        d1_pdata = d1_lookup.get(code, {})
        deg = d1_pdata.get("degree")
        sign_num = d1_pdata.get("sign_number")
        if deg is None or sign_num is None:
            continue
        part = _d16_part(float(deg))
        p_lord = _parashari_lord(int(sign_num), part) if part > 0 else ""
        t_name, t_qual, _ = _tithi_lord_info(part)
        is_cruel_p = (p_lord == _CRUEL_PARASHARI)
        is_cruel_t = (part in _CRUEL_TITHI)
        if is_cruel_p or is_cruel_t:
            cruel_type = (f"{p_lord} (Parashari)" if is_cruel_p else "") + \
                         (" + " if is_cruel_p and is_cruel_t else "") + \
                         (f"{t_name} (Tithi)" if is_cruel_t else "")
            triggered.append(_rule(
                f"D16-S1-CRUEL-DASHA-{code}-H{house}",
                f"{_pname(code)} in cruel shodashamsha ({cruel_type}) and house {house} D16 — dasha/antardasha damage to vehicles/happiness",
                f"{_pname(code)} occupies house {house} (a danger/loss house) of D16 and is in a "
                f"cruel shodashamsha ({cruel_type}). Planets that fulfill both criteria — related to "
                "the 6th, 8th, 12th, or 3rd house AND placed in a cruel shodashamsha — cause damage "
                "in their dasha and antardasha periods. This is a first-rate indicator of vehicular "
                "or luxury-related arishta (harm) timed to this planet's dasha period.",
                "negative", 6,
                {"overall": -4, "happiness": -5, "vehicle": -6},
                confidence="high",
            ))

    return triggered


# ── Set 2: Core Examination — Venus, Jupiter, Moon, Mars ─────────────────────

def _d16_s2_core(d16_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Venus, Jupiter, Moon, Mars examination in D16."""
    triggered = []
    d16_lookup = d16_chart.get("planet_lookup", {})
    h2l_d16, l2p_d16 = _build_lord_maps(d16_chart)
    d1_lookup = d1_chart.get("planet_lookup", {}) if d1_chart else {}

    # ── Venus in D16 ─────────────────────────────────────────────────────
    ven = d16_lookup.get("Ve", {})
    ven_house = ven.get("house")
    ven_dign = ven.get("dignity", "")
    if ven_house:
        if ven_house in ANGLE_OR_TRINE or ven_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D16-S2-VENUS-STRONG",
                f"Venus strong in D16 (house {ven_house}, {ven_dign or 'angle/trine'}) — luxuries and vehicles",
                "Venus is the primary karaka for vehicles, clothes, cosmetics, and material comforts "
                "in D16. A strong Venus placed in an angle or trine (or in exaltation/own sign) "
                "promises access to quality vehicles and material pleasures throughout life. "
                "Venus and Jupiter together are the karakas for the 4th house movable possessions — "
                "Venus indicates the quantity and type (quality of vehicle/comfort).",
                "positive", 6,
                {"overall": 4, "happiness": 6},
                confidence="high",
            ))

        # Venus in 4th = Digbala (directional strength)
        if ven_house == 4:
            triggered.append(_rule(
                "D16-S2-VENUS-DIGBALA",
                "Venus in 4th house D16 — Digbala (directional strength), best luxury promise",
                "Venus has Digbala (directional strength) in the 4th house. Directional strength "
                "of Venus in D16 promises good luxuries in life. This is one of the strongest "
                "placements for Venus in the context of vehicles and material comforts.",
                "positive", 5,
                {"overall": 3, "happiness": 5},
                confidence="high",
            ))

        # Venus in cruel shodashamsha (Mahesh) - computed from D1 sign
        ven_d1 = d1_lookup.get("Ve", {})
        v_deg = ven_d1.get("degree")
        v_sign = ven_d1.get("sign_number")
        if v_deg is not None and v_sign is not None:
            part = _d16_part(float(v_deg))
            p_lord = _parashari_lord(int(v_sign), part) if part > 0 else ""
            if p_lord == "Mahesh":
                triggered.append(_rule(
                    "D16-S2-VENUS-CRUEL-SHODASHAMSHA",
                    f"Venus in cruel Mahesh shodashamsha (part {part}) — vehicles but with danger",
                    f"Venus is in the Mahesh (Shiva) shodashamsha (part {part}). A strong Venus "
                    "placed in a cruel shodashamsha gives vehicles but also gives danger through "
                    "them. The native acquires vehicles and material pleasures but faces risk of "
                    "accidents or losses associated with them. The directional strength of Venus "
                    "in D16 would partially mitigate this.",
                    "negative", 5,
                    {"overall": -2, "happiness": -4, "vehicle": -5},
                    confidence="high",
                ))

    # ── Jupiter in D16 ───────────────────────────────────────────────────
    ju = d16_lookup.get("Ju", {})
    ju_house = ju.get("house")
    ju_dign = ju.get("dignity", "")
    if ju_house:
        # Check Jupiter aspects to Lagna (from houses 5, 7, 9)
        ju_aspects_lagna = ju_house in {5, 7, 9}

        if ju_house in ANGLE_OR_TRINE or ju_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D16-S2-JUPITER-STRONG" + ("-ASPECTS" if ju_aspects_lagna else ""),
                f"Jupiter strong in D16 (house {ju_house}{', aspects Lagna' if ju_aspects_lagna else ''}) — inner happiness assured",
                "Jupiter is the karaka for inner happiness and satisfaction in D16. A strong Jupiter "
                + ("that aspects the Lagna (from 5/7/9) is the best combination to ensure inner "
                   "happiness. Jupiter brings wisdom, spiritual contentment, and the ability to "
                   "derive genuine joy from available luxuries."
                   if ju_aspects_lagna
                   else "in a good position brings inner contentment, spiritual satisfaction, and "
                   "ability to appreciate the luxuries available. Jupiter indicates the quality of "
                   "possessions rather than quantity."),
                "positive", 6 if ju_aspects_lagna else 5,
                {"overall": 4, "happiness": 6 if ju_aspects_lagna else 5},
                confidence="high",
            ))
        elif ju_house in DUSTHANA or ju_dign == "debilitated":
            triggered.append(_rule(
                "D16-S2-JUPITER-DUSTHANA",
                f"Jupiter in dusthana D16 (house {ju_house}) — inner happiness obstructed",
                "Jupiter in a dusthana (6, 8, or 12) of D16 obstructs inner happiness and "
                "satisfaction. Despite having material luxuries, the native cannot derive genuine "
                "joy from them. A poorly placed Jupiter in D16 reduces the ability to experience "
                "the nectar of life's pleasures.",
                "negative", 5,
                {"overall": -3, "happiness": -5},
                confidence="high",
            ))

    # ── Moon in D16 ──────────────────────────────────────────────────────
    mo = d16_lookup.get("Mo", {})
    mo_house = mo.get("house")
    mo_dign = mo.get("dignity", "")
    if mo_house:
        if mo_house in ANGLE_OR_TRINE or mo_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D16-S2-MOON-STRONG",
                f"Moon well-placed in D16 (house {mo_house}) — mental acceptance and enjoyment of comforts",
                "Moon shows the mental acceptance of amenities available. A well-placed Moon in D16 "
                "indicates the native is the most attached to pleasures and can fully enjoy them. "
                "Moon governs mental strength, patience, and endurance in D16. The Parashari lord "
                "and tithi lord of Moon reveal the native's most treasured attachment.",
                "positive", 5,
                {"overall": 3, "happiness": 5},
                confidence="high",
            ))
        elif mo_house in DUSTHANA or mo_dign == "debilitated":
            triggered.append(_rule(
                "D16-S2-MOON-WEAK",
                f"Moon weak/dusthana in D16 (house {mo_house}) — mental dissatisfaction, cannot enjoy",
                "Moon in a dusthana of D16 indicates mental dissatisfaction with available pleasures. "
                "The native cannot enjoy their material possessions or vehicles even when present. "
                "On the negative side, this can be the mirage of pleasures leading to humiliation "
                "and unhappiness — the native craves but cannot be satisfied.",
                "negative", 4,
                {"overall": -3, "happiness": -4},
                confidence="medium",
            ))

    # ── Mars in D16 — permanency of happiness ────────────────────────────
    ma = d16_lookup.get("Ma", {})
    ma_house = ma.get("house")
    ma_dign = ma.get("dignity", "")
    if ma_house:
        if ma_house in ANGLE_OR_TRINE or ma_dign in {"exalted", "own_sign"}:
            triggered.append(_rule(
                "D16-S2-MARS-PERMANENT",
                f"Mars well-placed in D16 (house {ma_house}) — permanent and long-lasting happiness",
                "Mars is the karaka for permanency of happiness and luxuries in D16. A well-placed "
                "Mars ensures that the happiness and vehicles acquired are long-lasting and not "
                "temporary. The native holds onto their material comforts and vehicles for extended "
                "periods. Seeing the placement of Mars relative to the D1 9th lord in D16 "
                "confirms the duration of luxury enjoyment.",
                "positive", 4,
                {"overall": 3, "happiness": 4},
                confidence="medium",
            ))

    return triggered


# ── Set 3: Vehicle Accident and Loss Indicators ───────────────────────────────

def _d16_s3_vehicle_risk(d16_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Vehicle danger (6/8 house links) and loss (3/12 house links) indicators."""
    triggered = []
    h2l_d16, l2p_d16 = _build_lord_maps(d16_chart)
    d16_lookup = d16_chart.get("planet_lookup", {})

    lord_1 = h2l_d16.get(1)
    lord_4 = h2l_d16.get(4)
    placed_1 = l2p_d16.get(lord_1) if lord_1 else None
    placed_4 = l2p_d16.get(lord_4) if lord_4 else None

    planets_lagna = _planets_in_house(d16_chart, 1)
    planets_4th = _planets_in_house(d16_chart, 4)

    def _houses_linked(h1: int, h2: int) -> bool:
        """True if lords of h1 and h2 are conjunct or one placed in other's house."""
        lord_a = h2l_d16.get(h1)
        lord_b = h2l_d16.get(h2)
        if not (lord_a and lord_b):
            return False
        if lord_a == lord_b:
            return True
        pa = l2p_d16.get(lord_a)
        pb = l2p_d16.get(lord_b)
        return (pa == pb or pa == h2 or pb == h1)

    # ── Rule 4: 6th/8th association with Lagna or 4th → accidents ────────
    danger_link = False
    link_details = []
    for danger_h in (6, 8):
        lord_d = h2l_d16.get(danger_h)
        placed_d = l2p_d16.get(lord_d) if lord_d else None
        # Lord of danger house in Lagna or 4th
        if placed_d in {1, 4}:
            link_details.append(f"{danger_h}th lord {_pname(lord_d)} in house {placed_d}")
            danger_link = True
        # Lagna lord or 4th lord in danger house
        if placed_1 == danger_h:
            link_details.append(f"Lagna lord {_pname(lord_1)} in {danger_h}th")
            danger_link = True
        if placed_4 == danger_h:
            link_details.append(f"4th lord {_pname(lord_4)} in {danger_h}th")
            danger_link = True
        # Lord of 6/8 occupies Lagna/4th by conjunction (already covered by placed_d)
        # Occupants: 6/8 lord in lagna or 4th planets
        if lord_d and lord_d in (planets_lagna + planets_4th):
            if f"{danger_h}th lord {_pname(lord_d)}" not in " ".join(link_details):
                link_details.append(f"{danger_h}th lord {_pname(lord_d)} in Lagna/4th")
                danger_link = True

    if danger_link:
        desc = "; ".join(link_details)
        triggered.append(_rule(
            "D16-S3-6TH-8TH-LAGNA-4TH",
            f"6th/8th link with Lagna/4th in D16 ({desc}) — vehicular accident danger",
            f"Any association of 6th or 8th house/lords with Lagna or 4th house/lords in D16 "
            f"indicates danger or accidents through vehicles. Found: {desc}. "
            "The 4th house is the sukh sthana (happiness house) and its relation with 8th or 6th "
            "indicates vehicular or other accidents that cause loss of happiness.",
            "negative", 6,
            {"overall": -4, "happiness": -5, "vehicle": -6},
            confidence="high",
        ))

    # ── Rule 5: 3rd/12th association with Lagna or 4th → vehicle loss ────
    loss_link = False
    loss_details = []
    for loss_h in (3, 12):
        lord_l = h2l_d16.get(loss_h)
        placed_l = l2p_d16.get(lord_l) if lord_l else None
        if placed_l in {1, 4}:
            loss_details.append(f"{loss_h}th lord {_pname(lord_l)} in house {placed_l}")
            loss_link = True
        if placed_1 == loss_h:
            loss_details.append(f"Lagna lord {_pname(lord_1)} in {loss_h}th")
            loss_link = True
        if placed_4 == loss_h:
            loss_details.append(f"4th lord {_pname(lord_4)} in {loss_h}th")
            loss_link = True
        if lord_l and lord_l in (planets_lagna + planets_4th):
            if f"{loss_h}th lord {_pname(lord_l)}" not in " ".join(loss_details):
                loss_details.append(f"{loss_h}th lord {_pname(lord_l)} in Lagna/4th")
                loss_link = True

    if loss_link:
        desc = "; ".join(loss_details)
        triggered.append(_rule(
            "D16-S3-3RD-12TH-LAGNA-4TH",
            f"3rd/12th link with Lagna/4th in D16 ({desc}) — vehicle theft or loss",
            f"Association of 3rd and 12th house/lord with Lagna or 4th house/lord in D16 "
            f"shows loss of vehicles — due to theft or other accidents. Found: {desc}. "
            "The 12th is the house of loss and the 3rd is the house of own actions; their "
            "connection to the happiness and comfort axis triggers vehicle loss.",
            "negative", 5,
            {"overall": -3, "happiness": -4, "vehicle": -5},
            confidence="high",
        ))

    # ── 4th house direct dusthana link → vehicular accident risk ─────────
    lord_8 = h2l_d16.get(8)
    lord_6 = h2l_d16.get(6)
    placed_8 = l2p_d16.get(lord_8) if lord_8 else None
    placed_6 = l2p_d16.get(lord_6) if lord_6 else None
    occupants_4 = _planets_in_house(d16_chart, 4)
    malefics_4 = [p for p in occupants_4 if p in NATURAL_MALEFICS]

    if malefics_4 and (placed_8 == 4 or placed_6 == 4):
        active = [_pname(lord_8) if placed_8 == 4 else "", _pname(lord_6) if placed_6 == 4 else ""]
        active_str = ", ".join(x for x in active if x)
        triggered.append(_rule(
            "D16-S3-4TH-DUSTHANA-LINK",
            f"4th house D16 afflicted by 6th/8th lords ({active_str}) and malefics — vehicular accident",
            f"The 4th house of D16 (sukh sthana) has malefic occupants and is linked to the "
            f"6th/8th lords ({active_str}). Any relation of the 4th house with the 6th, 8th, or "
            "12th indicates vehicular or other accidents which cause loss of happiness. "
            "This configuration warrants watching the 4th house afflicting planets' dasha periods "
            "for accident risk.",
            "negative", 6,
            {"overall": -4, "happiness": -5, "vehicle": -6},
            confidence="high",
        ))

    # ── Planets in 8th D16 → long-term problems, fatal accident risk ─────
    planets_8 = _planets_in_house(d16_chart, 8)
    afflicted_8 = [p for p in planets_8 if p in NATURAL_MALEFICS]
    if afflicted_8:
        names = ", ".join(_pname(p) for p in afflicted_8)
        triggered.append(_rule(
            "D16-S3-8TH-AFFLICTED",
            f"Malefics {names} in 8th house D16 — long-term problems, fatal accident risk in dasha",
            f"The 8th house of D16 represents long-term problems due to luxuries or vehicles, "
            f"including fatal accidents due to any type of conveyance. Afflicted planets ({names}) "
            "in the 8th need to be watched carefully during their dasha periods. The 8th house "
            "accident can be fatal if devoid of any benefic aspect.",
            "negative", 6,
            {"overall": -4, "happiness": -5, "vehicle": -6},
            confidence="high",
        ))

    # ── 6th/8th lord in D16 Lagna → great vehicular danger ───────────────
    danger_lords_in_lagna = []
    for danger_h in (6, 8):
        lord_d = h2l_d16.get(danger_h)
        if lord_d and lord_d in planets_lagna:
            danger_lords_in_lagna.append(f"{danger_h}th lord {_pname(lord_d)}")

    if danger_lords_in_lagna:
        desc = ", ".join(danger_lords_in_lagna)
        triggered.append(_rule(
            "D16-S3-LAGNA-6TH-8TH-LORD",
            f"D16 Lagna occupied by {desc} — great danger from vehicles",
            f"The D16 Lagna being occupied by the 6th or 8th lord ({desc}) is one of the "
            "most serious indicators of vehicular danger. It shows great danger from vehicles "
            "including serious accidents. The Lagna is the general source of luxuries in D16 — "
            "its contamination by 6th/8th lords indicates the source of luxury also brings danger.",
            "negative", 7,
            {"overall": -5, "happiness": -5, "vehicle": -7},
            confidence="high",
        ))

    return triggered


# ── Set 4: Happiness Level and Access ────────────────────────────────────────

def _d16_s4_happiness(d16_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """9th house luck, 4th house quality, greed indicator, and D1 4th lord in D16 7th."""
    triggered = []
    h2l_d16, l2p_d16 = _build_lord_maps(d16_chart)
    h2l_d1, l2p_d1 = _build_lord_maps(d1_chart) if d1_chart else ({}, {})
    d16_lookup = d16_chart.get("planet_lookup", {})

    # ── 9th house: luck factor for luxuries ──────────────────────────────
    lord_9 = h2l_d16.get(9)
    placed_9 = l2p_d16.get(lord_9) if lord_9 else None
    lord_9_dign = d16_lookup.get(lord_9, {}).get("dignity", "") if lord_9 else ""

    if lord_9 and placed_9 and (placed_9 in ANGLE_OR_TRINE or lord_9_dign in {"exalted", "own_sign"}):
        triggered.append(_rule(
            "D16-S4-9TH-STRONG",
            f"D16 9th lord {_pname(lord_9)} well-placed (house {placed_9}) — luck in luxuries",
            f"The 9th house is the luck factor of luxuries in D16. Its lord {_pname(lord_9)} "
            f"in house {placed_9} is well-placed, indicating the native is lucky in acquiring "
            "and enjoying good vehicles and material comforts. A strong 9th house makes one "
            "possess good luxuries and enjoy them. It also governs long travels.",
            "positive", 4,
            {"overall": 3, "happiness": 4},
            confidence="medium",
        ))

    # ── 4th house: sukh sthana quality ───────────────────────────────────
    lord_4 = h2l_d16.get(4)
    placed_4 = l2p_d16.get(lord_4) if lord_4 else None
    lord_4_dign = d16_lookup.get(lord_4, {}).get("dignity", "") if lord_4 else ""
    occupants_4 = _planets_in_house(d16_chart, 4)
    benefics_4 = [p for p in occupants_4 if p in BENEFICS]

    if (lord_4 and placed_4 and placed_4 in ANGLE_OR_TRINE and lord_4_dign in {"exalted", "own_sign"}) or benefics_4:
        triggered.append(_rule(
            "D16-S4-4TH-STRONG",
            f"D16 4th house strong (lord {_pname(lord_4) if lord_4 else '?'} {'exalted/own' if lord_4_dign in {'exalted','own_sign'} else ''}{', benefic occupants' if benefics_4 else ''}) — happiness from material comforts",
            "The 4th house is the sukh sthana (happiness house) of D16 — the place where one "
            "tastes the nectar or poison of luxuries. A strong 4th house indicates genuine "
            "happiness and satisfaction from material comforts, vehicles, and the attitude "
            "toward happiness is positive and receptive.",
            "positive", 4,
            {"overall": 3, "happiness": 4},
            confidence="medium",
        ))

    # ── 11th + Lagna with malefics → insatiable greed ────────────────────
    planets_lagna = _planets_in_house(d16_chart, 1)
    planets_11 = _planets_in_house(d16_chart, 11)
    lagna_malefics = [p for p in planets_lagna if p in NATURAL_MALEFICS]
    eleventh_malefics = [p for p in planets_11 if p in NATURAL_MALEFICS]

    if lagna_malefics and eleventh_malefics:
        l_names = ", ".join(_pname(p) for p in lagna_malefics)
        e_names = ", ".join(_pname(p) for p in eleventh_malefics)
        triggered.append(_rule(
            "D16-S4-11TH-MALEFIC-GREED",
            f"Malefics in D16 Lagna ({l_names}) and 11th ({e_names}) — insatiable materialistic greed",
            f"Relation of Lagna and 11th house with malefic connection in D16 indicates a "
            "materialistic person whose greed for amenities can never be satisfied. The 11th "
            "house represents the gain or loss of luxuries and the level of greed towards "
            "amenities of life. With malefics in both, the native accumulates but remains "
            "perpetually unsatisfied.",
            "negative", 4,
            {"overall": -3, "happiness": -4},
            confidence="medium",
        ))

    # ── D1 4th lord in D16 7th → conveyance provided by others ──────────
    d1_4th_lord = h2l_d1.get(4) if h2l_d1 else None
    if d1_4th_lord:
        d16_4l_data = d16_lookup.get(d1_4th_lord, {})
        d16_4l_house = d16_4l_data.get("house")
        if d16_4l_house == 7:
            triggered.append(_rule(
                "D16-S4-D1-4TH-LORD-7TH-D16",
                f"D1 4th lord {_pname(d1_4th_lord)} in 7th house of D16 — conveyance provided by others",
                f"The lord of the 4th house in the natal chart ({_pname(d1_4th_lord)}) is "
                "placed in the 7th house of D16. The 7th house in D16 represents partners who "
                "enjoy or suffer the luxuries with the native. When the D1 4th lord is related "
                "to the 7th house of D16, conveyance is provided by others (spouse, business "
                "partners, employers) rather than being owned by the native themselves.",
                "neutral", 3,
                {"overall": 1, "happiness": 2},
                confidence="medium",
            ))

    return triggered


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d16_shodashamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d16_chart = _get_d16_chart(chart_facts)
    if not d16_chart:
        return []
    d1_chart = _get_d1_chart(chart_facts)
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d16_s1_lords(d16_chart, d1_chart))
    triggered.extend(_d16_s2_core(d16_chart, d1_chart))
    triggered.extend(_d16_s3_vehicle_risk(d16_chart, d1_chart))
    triggered.extend(_d16_s4_happiness(d16_chart, d1_chart))
    return triggered
