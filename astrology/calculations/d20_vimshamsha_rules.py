"""D20-specific rules from the Vimshamsha chapter.

Source: Comprehensive Prediction by Divisional Charts — Vimshamsha D20 (pp. 206–221).

Also called the Upasana chart.
Purpose: Spirituality, worship, meditation, spiritual inclinations, religious activity,
the Guru, the deity to worship, and the religious advancement one attains.

Ruling Deity: 20 female deities, different for odd vs. even signs.
Formula (from D1 sign and degree):
  part = floor(degree_in_D1_sign / 1.5) + 1   [1–20]
Odd signs:  Kali Gauri Jaya Laxmi Vijaya Vimla Sati Tara Jwalamukhi Shweta
            Lalita Baglamukhi Pratyangira Sachi Raudri Bhavani Varada Jaya Tripura Samukhi
Even signs: Daya Medha Chinna-shirsha Pishachini Dhoomavati Matangi Bala Bhadra Aruna Anala
            Pingla Chhuchhuka Ghora Varahi Vaishnavi Sita Bhuvaneshi Bhairvi Mangla Aprajita

Key spiritual pillars:
  Lagna  → Self and spiritual identity (Dharma trine house 1)
  5th    → Mantra Siddhi, Poorva punya, devotion, deity to worship
  9th    → Guru, dharma path, Ishta Devata, Dhyana
  12th   → Moksha, Samadhi, total surrender

SET 1 (Vimshamsha Deity — D1 Lagna and key planets):
  D20-S1-LAGNA-DEITY-{name}      Deity of D1 Lagna in D20 → spiritual identity
  D20-S1-PLANET-DEITY-{p}        Deity of key planets (Ju/Sa/Ke/Mo) → worship path

SET 2 (Core Spiritual Pillars — Lagna, 5th, 9th):
  D20-S2-LAGNA-NATAL-CONFLICT    D20 Lagna = D1 10th/12th/4th sign — not conducive for path
  D20-S2-9TH-LORD-BENEFIC        9th lord with benefic connections — follows religion
  D20-S2-9TH-LORD-RAHU-RETRO     9th lord retrograde or with Rahu — won't follow religion
  D20-S2-SATURN-9TH-EXALTED      Exalted Saturn in 9th D20 — high spirituality
  D20-S2-SUN-STRONG              Sun strong in D20 — high level of spirituality
  D20-S2-5TH-LORD-UNASSOCIATED   5th lord unassociated — detachment, better for path
  D20-S2-5TH-LORD-AFFLICTED      5th lord afflicted/kartari — attachment, strings

SET 3 (Jupiter and Ketu — Divine Spark):
  D20-S3-JU-TRINE                Jupiter in trine D20 — control over senses
  D20-S3-JU-KETU-MOKSHA         Jupiter + Ketu linked to 5th/8th/12th — divine spark
  D20-S3-JU-AFFLICTED            Jupiter afflicted in D20 — curses from holy persons risk
  D20-S3-KETU-MOKSHA-HOUSE      Ketu in 4th/8th/12th — moksha placement
  D20-S3-KETU-5TH-9TH-JU       Ketu with 5th/9th lord + aspected by Jupiter — spiritual progress

SET 4 (Saturn, Venus, and Spiritual Path Quality):
  D20-S4-SATURN-MARS-KARMA       Saturn + Mars in D20 — Karma Yoga path
  D20-S4-VENUS-UNAFFLICTED       Venus unafflicted D20 — control of sex life, pure path
  D20-S4-VENUS-MALEFIC-ASSOC    Venus with Ra/Ke/Sa in D20 — tantric/tamsik path risk
  D20-S4-RAHU-PLANET-SKILLS     Rahu conjunct planet in D20 — special tantric skills

SET 5 (Renunciation and Sanyasa):
  D20-S5-SANYASA-4PLUS           4+ planets including 10th lord in kendra/trikona — Sanyasa yoga
  D20-S5-SATURN-ASPECTS-LAGNA   Saturn aspects Lagna/Lagna lord in D20 — renunciation
  D20-S5-5TH-7TH-IN-10TH-1ST   5th and 7th lord in 10th/1st D20 — asceticism after marriage

SET 6 (Deviation — Criminal/Unrighteous Path):
  D20-S6-CRIMINAL-PATH           6th/8th lord + Moon + retrograde Mercury — deviation from path
"""

from typing import Any

from charts.vedic_utils import PLANET_NAMES


_SOURCE_BOOK = "Comprehensive Prediction by Divisional Charts"
_SOURCE_CHAPTER = "Vimshamsha D20"
_SOURCE_PAGE = "206"

DUSTHANA = frozenset({6, 8, 12})
MOKSHA_TRINE = frozenset({4, 8, 12})
ANGLES = frozenset({1, 4, 7, 10})
TRINES = frozenset({1, 5, 9})
ANGLE_OR_TRINE = ANGLES | TRINES
DHARMA_TRINE = frozenset({1, 5, 9})
BENEFICS = frozenset({"Ju", "Ve", "Mo", "Me"})
MALEFICS = frozenset({"Su", "Ma", "Sa", "Ra", "Ke"})
NATURAL_MALEFICS = frozenset({"Ma", "Sa", "Ra", "Ke"})

# Deity table: odd signs (index 0-19) → part 1-20
_ODD_DEITIES = [
    "Kali", "Gauri", "Jaya", "Laxmi", "Vijaya",
    "Vimla", "Sati", "Tara", "Jwalamukhi", "Shweta",
    "Lalita", "Baglamukhi", "Pratyangira", "Sachi", "Raudri",
    "Bhavani", "Varada", "Jaya_18", "Tripura", "Samukhi",
]

# Deity table: even signs (index 0-19) → part 1-20
_EVEN_DEITIES = [
    "Daya", "Medha", "Chinna-shirsha", "Pishachini", "Dhoomavati",
    "Matangi", "Bala", "Bhadra", "Aruna", "Anala",
    "Pingla", "Chhuchhuka", "Ghora", "Varahi", "Vaishnavi",
    "Sita", "Bhuvaneshi", "Bhairvi", "Mangla", "Aprajita",
]

# Deity → (quality_tier, brief_theme)
_DEITY_THEMES: dict[str, tuple[str, str]] = {
    "Kali":          ("sattvic",  "force of time and change; ultimate reality/Brahma Gyan; redeemer of universe"),
    "Gauri":         ("sattvic",  "purity, austerity; grants wishes through Shiva; beautiful aspect of Parvati"),
    "Jaya":          ("sattvic",  "victory, protection; Narayana; loves solitude, silence in meditation"),
    "Laxmi":         ("sattvic",  "wealth and fortune; removes miseries and money-related sorrows; prosperity"),
    "Vijaya":        ("sattvic",  "celebration of victory; conquers evil; self-control for seeker"),
    "Vimla":         ("sattvic",  "purity (another name of Laxmi); Shakti of Lord Jaganath; grants blessings by Bhakti"),
    "Sati":          ("rajasic",  "great courage and honour; sincere worshipper faces humiliation; divine sacrifice"),
    "Tara":          ("rajasic",  "governs birth/death/cosmos; asceticism, mysticism, protector of family"),
    "Jwalamukhi":    ("rajasic",  "fiery speech; tongue of Sati; tongue of worshipper emits flame-speech"),
    "Shweta":        ("sattvic",  "white and pure; related to Saraswati; provides pure knowledge"),
    "Lalita":        ("sattvic",  "Mahavidhya; goddess of art and culture; represented by Moon; Sri Chakra worship"),
    "Baglamukhi":    ("rajasic",  "Mahavidhya; Vak Siddhi; controls or captures; hypnotic powers"),
    "Pratyangira":   ("rajasic",  "Tantrik Goddess; worshipped for personal gains; bestows victory; when angry causes destruction"),
    "Sachi":         ("rajasic",  "wife of Lord Indra; wrath; jealousy and evil intent in worshipper"),
    "Raudri":        ("rajasic",  "terrifying aspect of Parvati; goddess of battlefield; destroys sin and evil thoughts"),
    "Bhavani":       ("sattvic",  "ferocious but giver of life; creative energy; controls evil; establishes peace"),
    "Varada":        ("sattvic",  "charity, giving, compassion, sincerity; giver of boon, child, and desired boon"),
    "Jaya_18":       ("sattvic",  "victory, protection (same as Jaya)"),
    "Tripura":       ("sattvic",  "radiant light in eyes of Shiva; Shri Vidhya and divine knowledge; grants all sixteen desires"),
    "Samukhi":       ("sattvic",  "beauty; good face or mouth; worship for beauty of life"),
    "Daya":          ("sattvic",  "compassion; linked to Lord Ram; all sins washed; worshipper enjoys bliss"),
    "Medha":         ("sattvic",  "Laxmi and Saraswati; intelligence and sacrifice; worshipper indulges in sacrifices with intelligence"),
    "Chinna-shirsha":("rajasic",  "severed head Devi; feeds own mouth; courage and discernment"),
    "Pishachini":    ("tamasic",  "leader of demons; gives tantrik worship; Shakti Sadhna"),
    "Dhoomavati":    ("tamasic",  "smoky Shakti; eternal widow without Shiva; ugly and fearsome; dark forces and black magic"),
    "Matangi":       ("tamasic",  "dark form of Saraswati; low-caste; command over speech, creativity, knowledge"),
    "Bala":          ("sattvic",  "young Parvati; energetic, playful, heroic, kind; worshipped Shiva"),
    "Bhadra":        ("sattvic",  "gentle Kali; wards off calamities; servant of Lord Shiva"),
    "Aruna":         ("sattvic",  "charioteer of Sun assumed female form; god of dawn; bestows radiance"),
    "Anala":         ("sattvic",  "goddess of fertility; like fire; one of Vasus; sharp intelligence and growth"),
    "Pingla":        ("sattvic",  "right breath and basic energy of life (Pran); disciplined; lives long"),
    "Chhuchhuka":    ("sattvic",  "consort of Vishnu; divine love and eternal happiness; mothers love"),
    "Ghora":         ("tamasic",  "supreme energy of Shiva; fearful for ignorant; creative for blissful; destructive for unaware; severe penance"),
    "Varahi":        ("sattvic",  "Shakti of Varaha (Vishnu avatar); holds rod of punishment; blessing for right path followers"),
    "Vaishnavi":     ("sattvic",  "energy of Vishnu; seated on Garuda; no fear, blessings; fearless in spiritual pursuit"),
    "Sita":          ("sattvic",  "wife of Shri Ram, Laxmi; long and arduous life but pure feminine power"),
    "Bhuvaneshi":    ("sattvic",  "three-eyed Mahavidhya; creator of world; dispels fear; destroys unnecessary evils"),
    "Bhairvi":       ("rajasic",  "ferocious form of Durga; mediator; beauty with power; balancing acts; serves humanity"),
    "Mangla":        ("sattvic",  "auspicious Devi Gauri; worshipped for long life of husband; happy married life"),
    "Aprajita":      ("sattvic",  "invincible; form of Durga; achieves goal, cannot be defeated"),
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
        "system": "D20/VimshamshaRules",
        "chart": "D20",
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
        "source_file": "d20_vimshamsha_rules.py",
    }


def _get_d20_chart(chart_facts: dict[str, Any]) -> dict[str, Any]:
    return chart_facts.get("varga", {}).get("charts", {}).get("d20", {})


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


def _d20_deity(sign_number: int, degree: float) -> str:
    """Return vimshamsha deity name from D1 sign_number (1-12) and degree (0-30°)."""
    try:
        part = min(int(float(degree) / 1.5), 19)  # 0-indexed 0-19
        if sign_number % 2 == 1:
            return _ODD_DEITIES[part]
        else:
            return _EVEN_DEITIES[part]
    except (TypeError, ValueError, IndexError):
        return ""


def _house_sign(lagna_sign: int, house_number: int) -> int:
    """Return sign number occupying a given house, given lagna sign."""
    return ((lagna_sign - 1 + house_number - 1) % 12) + 1


# ── Set 1: Vimshamsha Deity ───────────────────────────────────────────────────

def _d20_s1_deity(d20_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Vimshamsha deity for D1 Lagna and key spiritual planets."""
    if not d1_chart:
        return []

    d1_lookup = d1_chart.get("planet_lookup", {})
    d1_lagna = d1_chart.get("lagna", {})
    triggered = []

    def _fire_deity(planet_data: dict, label: str, rule_prefix: str) -> dict | None:
        deg = planet_data.get("degree")
        sign = planet_data.get("sign_number")
        if deg is None or sign is None:
            return None
        deity = _d20_deity(int(sign), float(deg))
        if not deity:
            return None
        quality, theme = _DEITY_THEMES.get(deity, ("sattvic", ""))
        display_name = deity.replace("_18", "")  # clean Jaya_18 → Jaya
        polarity = "positive" if quality == "sattvic" else ("neutral" if quality == "rajasic" else "negative")
        weight = 3 if quality == "sattvic" else (2 if quality == "rajasic" else 4)
        return _rule(
            f"{rule_prefix}-{deity.upper().replace('-', '').replace('_18', '')}",
            f"{label} in {display_name} vimshamsha ({quality}) — {theme[:60]}",
            f"The {label} falls in the {display_name} vimshamsha. "
            f"This deity's nature: {theme}. "
            f"The attributes of this deity decide the happiness and spiritual quality granted by this planet/lagna. "
            + ("This is a tamasic deity — the spiritual path associated here requires careful discernment "
               "and may incline toward tamsik or tantric practices rather than sattvic worship."
               if quality == "tamasic"
               else "The bhava whose lord is in a benefic vimshamsha will flourish on the spiritual path."),
            polarity, weight,
            {"overall": 1, "spirituality": 3 if quality == "sattvic" else (1 if quality == "rajasic" else -2)},
            confidence="medium",
        )

    # D1 Lagna deity
    if d1_lagna:
        r = _fire_deity(d1_lagna, "D1 Lagna", "D20-S1-LAGNA-DEITY")
        if r:
            triggered.append(r)

    # Key spiritual planets
    for code, label in [("Ju", "Jupiter (dharma guru)"), ("Sa", "Saturn (tapasvi/karma)"),
                        ("Ke", "Ketu (moksha karaka)"), ("Mo", "Moon (Bhakti mind)"),
                        ("Ve", "Venus (Guru/deity)"), ("Su", "Sun (soul/Shiva)")]:
        pdata = d1_lookup.get(code, {})
        deg = pdata.get("degree")
        sign = pdata.get("sign_number")
        if deg is not None and sign is not None:
            r = _fire_deity(pdata, label, f"D20-S1-PLANET-DEITY-{code}")
            if r:
                triggered.append(r)

    return triggered


# ── Set 2: Core Spiritual Pillars ─────────────────────────────────────────────

def _d20_s2_pillars(d20_chart: dict[str, Any], d1_chart: dict[str, Any]) -> list[dict]:
    """Lagna quality, 5th/9th analysis, Sun, Saturn 9th."""
    triggered = []
    h2l_d20, l2p_d20 = _build_lord_maps(d20_chart)
    d20_lookup = d20_chart.get("planet_lookup", {})
    d1_lagna = d1_chart.get("lagna", {}) if d1_chart else {}

    # ── D20 Lagna should NOT match D1 10th/12th/4th sign ─────────────────
    d20_lagna = d20_chart.get("lagna", {})
    d20_lagna_sign = d20_lagna.get("sign_number")
    d1_lagna_sign = d1_lagna.get("sign_number") if d1_lagna else None

    if d20_lagna_sign and d1_lagna_sign:
        conflict_houses = {4: "4th", 10: "10th", 12: "12th"}
        for hnum, hlabel in conflict_houses.items():
            d1_house_sign = _house_sign(int(d1_lagna_sign), hnum)
            if d1_house_sign == int(d20_lagna_sign):
                triggered.append(_rule(
                    f"D20-S2-LAGNA-NATAL-CONFLICT-{hnum}TH",
                    f"D20 Lagna sign = D1 {hlabel} house sign — 6th/8th/12th from D20 5th, not conducive for spiritual path",
                    f"The Lagna of the D20 (vimshamsha) chart is in the same sign as the {hlabel} house "
                    "of the natal chart. These signs — corresponding to the 10th, 12th, and 4th houses "
                    "of the natal chart — are the 6th, 8th, and 12th from the 5th house of D20. "
                    "They are not conducive for progress on the religious path. This creates a fundamental "
                    "challenge to spiritual development as the self-identity in D20 is placed in a house "
                    "of obstacle, hidden matters, or worldly action relative to the spiritual axis.",
                    "negative", 5,
                    {"overall": -3, "spirituality": -5},
                    confidence="high",
                ))

    # ── 9th lord analysis ────────────────────────────────────────────────
    lord_9 = h2l_d20.get(9)
    placed_9 = l2p_d20.get(lord_9) if lord_9 else None
    lord_9_dign = d20_lookup.get(lord_9, {}).get("dignity", "") if lord_9 else ""
    lord_9_retrograde = d20_lookup.get(lord_9, {}).get("retrograde", False) if lord_9 else False

    planets_in_9 = _planets_in_house(d20_chart, 9)
    rahu_in_9 = "Ra" in planets_in_9
    rahu_with_9th_lord = (placed_9 is not None and "Ra" in _planets_in_house(d20_chart, placed_9))

    if lord_9 and placed_9:
        benefics_with_9 = any(p in BENEFICS for p in _planets_in_house(d20_chart, placed_9) if p != lord_9)
        if placed_9 in ANGLE_OR_TRINE or lord_9_dign in {"exalted", "own_sign"} or benefics_with_9:
            triggered.append(_rule(
                "D20-S2-9TH-LORD-BENEFIC",
                f"9th lord {_pname(lord_9)} well-placed/aspected in D20 (house {placed_9}) — follows religion",
                f"The 9th house is the last house of the Dharma trine in D20 — it governs kindness, "
                f"good conduct, pilgrimage, guru, charity, internal purity, and recitation (japa). "
                f"Its lord ({_pname(lord_9)}) is well placed with benefic connections, indicating the "
                "native genuinely follows a religious/spiritual path with true devotion and a good Guru.",
                "positive", 6,
                {"overall": 4, "spirituality": 6},
                confidence="high",
            ))

    if lord_9 and (lord_9_retrograde or rahu_in_9 or rahu_with_9th_lord):
        reason_parts = []
        if lord_9_retrograde:
            reason_parts.append(f"{_pname(lord_9)} is retrograde")
        if rahu_in_9:
            reason_parts.append("Rahu in 9th")
        if rahu_with_9th_lord and not rahu_in_9:
            reason_parts.append(f"Rahu conjunct 9th lord in house {placed_9}")
        triggered.append(_rule(
            "D20-S2-9TH-LORD-RAHU-RETRO",
            f"9th lord issue in D20 ({'; '.join(reason_parts)}) — will not follow religion properly",
            f"When the 9th lord is retrograde or is with Rahu in D20, the native will not follow "
            "religion in the standard or traditional sense. Retrograde 9th lord turns the spiritual "
            "inclination inward or toward unorthodox paths. Rahu with the 9th lord creates "
            "unconventional, foreign, or mixed religious practices rather than pure devotion.",
            "negative", 5,
            {"overall": -2, "spirituality": -4},
            confidence="high",
        ))

    # ── Exalted Saturn in 9th → high spirituality ────────────────────────
    sa_d20 = d20_lookup.get("Sa", {})
    sa_house = sa_d20.get("house")
    sa_dign = sa_d20.get("dignity", "")
    if sa_house == 9 and sa_dign == "exalted":
        triggered.append(_rule(
            "D20-S2-SATURN-9TH-EXALTED",
            "Exalted Saturn in 9th house D20 — highest level of spirituality",
            "Exalted Saturn in the 9th house of D20 is one of the clearest indicators of a high "
            "level of spirituality. Saturn's exaltation here gives deep dedication, tapasya, "
            "penance, and concentration in spiritual practice. The native attains a high level "
            "of spiritual discipline and follows the path of Yog Sadhna and dharma with remarkable "
            "focus and perseverance.",
            "positive", 7,
            {"overall": 4, "spirituality": 7},
            confidence="high",
        ))

    # ── Sun strong → high spirituality ───────────────────────────────────
    su_d20 = d20_lookup.get("Su", {})
    su_house = su_d20.get("house")
    su_dign = su_d20.get("dignity", "")
    if su_dign == "exalted" or (su_house in {5, 8}):  # exaltation best; Scorpio/Leo also mentioned
        triggered.append(_rule(
            "D20-S2-SUN-STRONG",
            f"Sun strong in D20 ({su_dign or f'house {su_house}'}) — high level of spirituality",
            "Sun should be strong for a high level of spirituality in D20. Sun is best in exaltation, "
            "next is its placement in Scorpio or Leo. A strong Sun in D20 gives the native deep "
            "soul awareness, enlightenment, purity of mind, and the awakening of divine presence. "
            "Sun represents the Atma (soul) and its strength determines the depth of spiritual insight.",
            "positive", 5,
            {"overall": 3, "spirituality": 5},
            confidence="high",
        ))

    # ── 5th lord analysis ────────────────────────────────────────────────
    lord_5 = h2l_d20.get(5)
    placed_5 = l2p_d20.get(lord_5) if lord_5 else None
    planets_5th = _planets_in_house(d20_chart, 5)

    if lord_5 and placed_5:
        # 5th lord unassociated = better for detachment
        associated_with = [p for p in _planets_in_house(d20_chart, placed_5) if p != lord_5]
        if not associated_with and not planets_5th:
            triggered.append(_rule(
                "D20-S2-5TH-LORD-UNASSOCIATED",
                f"5th lord {_pname(lord_5)} unassociated in D20 (house {placed_5}), 5th house vacant — avoids attachment",
                "The 5th lord should be unassociated in D20 to avoid attachment. Even Kartari "
                "(siege) on the 5th lord gives strings. An unassociated 5th lord with a vacant 5th "
                "house is ideal — it indicates detachment, freedom from clinging desires, and a "
                "natural inclination toward pure spiritual aspiration without ego or attachment.",
                "positive", 4,
                {"overall": 3, "spirituality": 4},
                confidence="medium",
            ))

        # Kartari on 5th lord or malefics in 5th
        malefics_5 = [p for p in planets_5th if p in NATURAL_MALEFICS]
        # Kartari = malefics on both sides of 5th lord's house
        house_before = ((placed_5 - 2) % 12) + 1
        house_after = (placed_5 % 12) + 1
        malefics_before = [p for p in _planets_in_house(d20_chart, house_before) if p in NATURAL_MALEFICS]
        malefics_after = [p for p in _planets_in_house(d20_chart, house_after) if p in NATURAL_MALEFICS]
        if malefics_5 or (malefics_before and malefics_after):
            affliction = f"malefics in 5th: {', '.join(_pname(p) for p in malefics_5)}" if malefics_5 else "Kartari on 5th lord"
            triggered.append(_rule(
                "D20-S2-5TH-LORD-AFFLICTED",
                f"5th lord {_pname(lord_5)} afflicted in D20 ({affliction}) — attachment and strings on spiritual path",
                f"Affliction to the 5th lord or 5th house in D20 creates 'strings' — attachments "
                "that hold the native back from pure spiritual progress. The 5th house represents "
                "Mantra Siddhi, devotion, emotion in prayers, and the deity to be worshipped. "
                "Kartari or malefic influence here indicates spiritual aspirations entangled with "
                "ego, desire for recognition, or worldly outcomes.",
                "negative", 4,
                {"overall": -2, "spirituality": -4},
                confidence="medium",
            ))

    return triggered


# ── Set 3: Jupiter and Ketu — Divine Spark ────────────────────────────────────

def _d20_s3_jupiter_ketu(d20_chart: dict[str, Any]) -> list[dict]:
    """Jupiter in trines, Jupiter+Ketu divine spark, afflicted Jupiter warning, Ketu in moksha."""
    triggered = []
    h2l_d20, l2p_d20 = _build_lord_maps(d20_chart)
    d20_lookup = d20_chart.get("planet_lookup", {})

    ju = d20_lookup.get("Ju", {})
    ke = d20_lookup.get("Ke", {})
    ju_house = ju.get("house")
    ke_house = ke.get("house")
    ju_dign = ju.get("dignity", "")

    # ── Jupiter in trines → control over senses ───────────────────────────
    if ju_house in TRINES:
        triggered.append(_rule(
            "D20-S3-JU-TRINE",
            f"Jupiter in trine (house {ju_house}) D20 — control over senses",
            "Jupiter in trines in the vimshamsha gives control over the senses. This is the "
            "foundation of all spiritual practice — without sensory control, meditation, mantra "
            "siddhi, and dhyan are not possible. Jupiter in a trine also indicates the native can "
            "worship Lord Brahma, Shiva, Shakti, or Lord Krishna in his updesh (teaching) form. "
            "Inspiration comes from chanting Vedic Mantras and blessings from saints or holy persons.",
            "positive", 6,
            {"overall": 4, "spirituality": 6},
            confidence="high",
        ))

    # ── Jupiter + Ketu with 5th/8th/12th = divine spark ──────────────────
    ju_linked_moksha = ju_house in MOKSHA_TRINE
    ke_linked_moksha = ke_house in MOKSHA_TRINE

    lord_5 = h2l_d20.get(5)
    placed_5 = l2p_d20.get(lord_5) if lord_5 else None
    lord_8 = h2l_d20.get(8)
    placed_8 = l2p_d20.get(lord_8) if lord_8 else None
    lord_12 = h2l_d20.get(12)
    placed_12 = l2p_d20.get(lord_12) if lord_12 else None

    ju_with_ke = (ju_house is not None and ke_house is not None and ju_house == ke_house)
    ke_5th_link = (ke_house == 5 or placed_5 == ke_house or
                   (lord_5 and lord_5 in _planets_in_house(d20_chart, ke_house or 0)))
    ke_8th_link = ke_house == 8
    ke_12th_link = ke_house == 12

    if (ju_linked_moksha or ju_with_ke) and (ke_linked_moksha or ke_5th_link):
        triggered.append(_rule(
            "D20-S3-JU-KETU-MOKSHA",
            f"Jupiter (house {ju_house}) + Ketu (house {ke_house}) linked to moksha/5th/8th/12th — divine spark",
            "Association of Jupiter and Ketu with the 5th, 8th, or 12th house gives divine spark "
            "to the person. Jupiter and Ketu together represent the highest spiritual intelligence — "
            "Jupiter provides wisdom and Ketu provides detachment and moksha orientation. This "
            "combination is a strong indicator of genuine spiritual inclination and potential "
            "for deep astrological insight (Jupiter aspecting 9th house with Ketu).",
            "positive", 7,
            {"overall": 4, "spirituality": 7},
            confidence="high",
        ))

    # ── Ketu in Moksha trine → salvation placement ────────────────────────
    if ke_house in MOKSHA_TRINE:
        quality_map = {12: ("best", 7), 8: ("second best", 6), 4: ("third", 5)}
        quality, wt = quality_map[ke_house]
        triggered.append(_rule(
            f"D20-S3-KETU-MOKSHA-HOUSE-{ke_house}",
            f"Ketu in {ke_house}th house D20 — {quality} moksha placement",
            f"Ketu is the karaka for salvation (Moksha) in D20. The Moksha trine is the 4th, 8th, "
            f"and 12th house. Ketu in the {ke_house}th is the {quality} placement for the spiritual "
            "path. The 12th is best (total surrender, Samadhi), 8th is second (renunciation, "
            "Sanyasa, secrets of worship), and 4th is third (house of action for religious activities). "
            "An unassociated or unaspected Ketu here is not ideal — it should be with or aspected "
            "by the 5th or 9th lord for the spiritual potential to fully manifest.",
            "positive", wt,
            {"overall": 3, "spirituality": wt},
            confidence="high",
        ))

    # ── Ketu with 5th/9th lord + aspected by Jupiter → spiritual progress ─
    planets_ke_house = _planets_in_house(d20_chart, ke_house or 0) if ke_house else []
    ke_with_5th_lord = (lord_5 and lord_5 in planets_ke_house)
    ke_with_9th_lord = (h2l_d20.get(9) and h2l_d20.get(9) in planets_ke_house)
    ju_aspects_ke = (ju_house is not None and ke_house is not None and ju_house in {ke_house - 4, ke_house - 2, ke_house + 4} or
                     abs(ju_house - ke_house) in {4, 2} if (ju_house and ke_house) else False)

    if (ke_with_5th_lord or ke_with_9th_lord) and ju_house and ke_house:
        lords = []
        if ke_with_5th_lord:
            lords.append(f"5th lord {_pname(lord_5)}")
        if ke_with_9th_lord:
            lords.append(f"9th lord {_pname(h2l_d20.get(9))}")
        triggered.append(_rule(
            "D20-S3-KETU-5TH-9TH-JU",
            f"Ketu with {', '.join(lords)} in D20 — spiritual progress and purity of devotion",
            f"Ketu (house {ke_house}) is associated with {', '.join(lords)}. This connection is "
            "considered good for progress of spirituality. Association of Jupiter, Mercury, 5th lord, "
            "or 9th lord with Ketu is checked for purity of devotion and spiritual progress. "
            "Ketu karaka of salvation, combined with the dharma lords, creates a strong platform "
            "for genuine spiritual advancement and pure devotion.",
            "positive", 6,
            {"overall": 3, "spirituality": 6},
            confidence="high",
        ))

    # ── Afflicted Jupiter in D20 — warning ───────────────────────────────
    if ju_house and (ju_house in DUSTHANA or ju_dign == "debilitated"):
        triggered.append(_rule(
            "D20-S3-JU-AFFLICTED",
            f"Jupiter afflicted in D20 (house {ju_house}, {ju_dign or 'dusthana'}) — risk of displeasure from holy persons",
            "An afflicted Jupiter in D20 is to be taken seriously. Such a person must avoid any "
            "action that may invite curses from holy persons. The native should rather serve the "
            "preceptors and seek their blessings, not confront or disrespect them. Jupiter "
            "represents Narayan, Maha Vishnu, and Sada Shiva in D20 — its affliction undermines "
            "the Guru relationship and can create spiritual obstacles that are difficult to overcome.",
            "negative", 5,
            {"overall": -3, "spirituality": -5},
            confidence="high",
        ))

    return triggered


# ── Set 4: Saturn, Venus, Rahu — Spiritual Path Quality ──────────────────────

def _d20_s4_path_quality(d20_chart: dict[str, Any]) -> list[dict]:
    """Saturn+Mars karma yoga, Venus for purity, Rahu special skills."""
    triggered = []
    d20_lookup = d20_chart.get("planet_lookup", {})

    sa = d20_lookup.get("Sa", {})
    ma = d20_lookup.get("Ma", {})
    ve = d20_lookup.get("Ve", {})
    ra = d20_lookup.get("Ra", {})

    sa_house = sa.get("house")
    ma_house = ma.get("house")
    ve_house = ve.get("house")
    ve_dign = ve.get("dignity", "")

    # ── Saturn + Mars → Karma Yoga ─────────────────────────────────────────
    if sa_house and ma_house and sa_house == ma_house:
        triggered.append(_rule(
            "D20-S4-SATURN-MARS-KARMA",
            f"Saturn + Mars conjunct in D20 (house {sa_house}) — Karma Yoga path",
            f"Association of Saturn with Mars in D20 gives Karma Yoga. The native follows "
            "the path of dedicated selfless action and service as their spiritual practice. "
            "One should worship Dharam Raj and follow the righteous path. The worship of "
            "Hanuman is also good. Saturn is not inauspicious and works under divine instructions "
            "without fear or favour — with Mars, this creates a warrior-karma-yogi energy.",
            "positive", 4,
            {"overall": 3, "spirituality": 4},
            confidence="medium",
        ))

    # ── Venus unafflicted → pure path ─────────────────────────────────────
    if ve_house:
        malefic_assoc = [p for p in _planets_in_house(d20_chart, ve_house) if p in {"Ra", "Ke", "Sa"} and p != "Ve"]
        if not malefic_assoc and ve_dign not in {"debilitated"}:
            if ve_house in ANGLE_OR_TRINE or ve_dign in {"exalted", "own_sign"}:
                triggered.append(_rule(
                    "D20-S4-VENUS-UNAFFLICTED",
                    f"Venus unafflicted and well-placed in D20 (house {ve_house}) — control of sex life, pure path",
                    "A strong and unafflicted Venus in D20 is desirable for control of sex life "
                    "and a pure spiritual path. Venus represents Guru, Yajurveda, Laxmi, Gauri, "
                    "Radha, poetry, music, dance, and charming speech in D20. When unafflicted, "
                    "the native maintains purity and genuine devotion. Venus should ideally be lord "
                    "of the 5th house or placed in trines for the strongest spiritual benefit.",
                    "positive", 4,
                    {"overall": 3, "spirituality": 4},
                    confidence="medium",
                ))
        if malefic_assoc:
            names = ", ".join(_pname(p) for p in malefic_assoc)
            triggered.append(_rule(
                "D20-S4-VENUS-MALEFIC-ASSOC",
                f"Venus with malefics {names} in D20 (house {ve_house}) — tantric/tamsik path risk",
                f"The malefic association with Venus ({names}) in D20, especially with Rahu, Ketu, "
                "or Saturn, may lead the person towards tantric practices. The pure Vaisesika "
                "philosophy of Venus gets contaminated. One should worship the pure form of female "
                "deities rather than tamsik forms. This combination needs careful spiritual guidance.",
                "negative", 4,
                {"overall": -2, "spirituality": -3},
                confidence="medium",
            ))

    # ── Rahu conjunct planet → special tantric skills ─────────────────────
    ra_house = ra.get("house")
    if ra_house:
        ra_companions = [p for p in _planets_in_house(d20_chart, ra_house) if p not in ("Ra", "Ke")]
        for companion in ra_companions:
            triggered.append(_rule(
                f"D20-S4-RAHU-PLANET-{companion}",
                f"Rahu conjunct {_pname(companion)} in D20 (house {ra_house}) — special tantric skills to {_pname(companion)}'s significations",
                f"Rahu conjunct {_pname(companion)} in D20 imparts special skills to the "
                f"significations of {_pname(companion)} in the spiritual domain. This can manifest "
                "as exceptional ability in tantra vidhya, unusual spiritual powers, or deep "
                "expertise in the area this planet governs. However, it may also incline toward "
                "tamsik practices — worship of Mansa Devi would be auspicious in this case.",
                "neutral", 3,
                {"overall": 1, "spirituality": 2},
                confidence="medium",
            ))

    return triggered


# ── Set 5: Renunciation and Sanyasa Yogas ────────────────────────────────────

def _d20_s5_sanyasa(d20_chart: dict[str, Any]) -> list[dict]:
    """Sanyasa yoga: 4+ planets in kendra/trikona, Saturn aspecting Lagna, 5th+7th in 10th/1st."""
    triggered = []
    h2l_d20, l2p_d20 = _build_lord_maps(d20_chart)
    d20_lookup = d20_chart.get("planet_lookup", {})

    # ── Sanyasa yoga: 4+ planets (including 10th lord) in kendra/trikona ──
    lord_10 = h2l_d20.get(10)
    planets_all = d20_chart.get("planets", [])
    # Group planets by house
    house_groups: dict[int, list[str]] = {}
    for p in planets_all:
        h = p.get("house")
        code = p.get("code")
        if h and code:
            house_groups.setdefault(h, []).append(code)

    for house, occupants in house_groups.items():
        if house not in ANGLE_OR_TRINE:
            continue
        if len(occupants) >= 4 and lord_10 in occupants:
            names = ", ".join(_pname(p) for p in occupants)
            triggered.append(_rule(
                f"D20-S5-SANYASA-4PLUS-H{house}",
                f"Sanyasa yoga: {len(occupants)} planets ({names}) including 10th lord {_pname(lord_10)} in house {house} D20 (kendra/trikona)",
                f"When four or more planets including the 10th house lord are combined in a single "
                f"kendra or trikona house in D20, Sanyasa yoga is formed. Found in house {house}: "
                f"{names}. This is a powerful indicator of renunciation, asceticism, and the "
                "potential to leave worldly life for a spiritual path. The house occupied indicates "
                "the nature of renunciation.",
                "positive", 7,
                {"overall": 3, "spirituality": 7},
                confidence="high",
            ))

    # ── Saturn aspecting Lagna or Lagna lord → renunciation ───────────────
    sa = d20_lookup.get("Sa", {})
    sa_house = sa.get("house")
    lord_1 = h2l_d20.get(1)
    placed_1 = l2p_d20.get(lord_1) if lord_1 else None

    if sa_house:
        lagna_occupants = _planets_in_house(d20_chart, 1)
        # Saturn aspects: 3rd, 7th, 10th from its position
        sa_aspects = {(sa_house + 2) % 12 + 1 if sa_house <= 10 else (sa_house + 2 - 12) + 1,
                      ((sa_house - 1 + 6) % 12) + 1,
                      ((sa_house - 1 + 9) % 12) + 1}
        sa_aspects_lagna = 1 in sa_aspects
        sa_aspects_ll = (placed_1 in sa_aspects) if placed_1 else False

        if sa_aspects_lagna or sa_aspects_ll:
            target = "Lagna" if sa_aspects_lagna else f"Lagna lord {_pname(lord_1)} in house {placed_1}"
            triggered.append(_rule(
                "D20-S5-SATURN-ASPECTS-LAGNA",
                f"Saturn (house {sa_house}) aspects {target} in D20 — renunciation",
                f"Saturn aspecting the Lagna or Lagna lord in D20 gives renunciation. Saturn "
                "represents Narayan, Yog Sadhna, Brahma, Yama, traditions, tapasvi, penance, "
                "dedication, and concentration in D20. Its aspect on the spiritual identity "
                "(Lagna) or Lagna lord turns the native toward disciplined renunciation and "
                "detachment from material life.",
                "positive", 5,
                {"overall": 2, "spirituality": 5},
                confidence="medium",
            ))

    # ── 5th + 7th lord in 10th or 1st → asceticism after marriage ─────────
    lord_5 = h2l_d20.get(5)
    lord_7 = h2l_d20.get(7)
    placed_5 = l2p_d20.get(lord_5) if lord_5 else None
    placed_7 = l2p_d20.get(lord_7) if lord_7 else None

    if placed_5 in {1, 10} and placed_7 in {1, 10}:
        triggered.append(_rule(
            "D20-S5-5TH-7TH-IN-10TH-1ST",
            f"5th lord {_pname(lord_5)} (house {placed_5}) and 7th lord {_pname(lord_7)} (house {placed_7}) both in 10th/1st D20 — asceticism after marriage",
            "Combination of the 5th and 7th lord in the 10th or 1st house of D20 leads to "
            "asceticism after marriage. The native begins their spiritual journey through or "
            "after the experience of worldly relationships. This is a Sanyasa indicator that "
            "ripens after fulfilling dharmic duties in partnership.",
            "positive", 4,
            {"overall": 2, "spirituality": 4},
            confidence="medium",
        ))

    return triggered


# ── Set 6: Deviation — Criminal or Unrighteous Path ──────────────────────────

def _d20_s6_deviation(d20_chart: dict[str, Any]) -> list[dict]:
    """Malefic combination: 6/8 lord + Moon + retrograde Mercury → unrighteous path."""
    triggered = []
    h2l_d20, l2p_d20 = _build_lord_maps(d20_chart)
    d20_lookup = d20_chart.get("planet_lookup", {})

    lord_6 = h2l_d20.get(6)
    lord_8 = h2l_d20.get(8)
    placed_6 = l2p_d20.get(lord_6) if lord_6 else None
    placed_8 = l2p_d20.get(lord_8) if lord_8 else None

    mo = d20_lookup.get("Mo", {})
    me = d20_lookup.get("Me", {})
    mo_house = mo.get("house")
    me_house = me.get("house")
    me_retrograde = me.get("retrograde", False)

    if not (mo_house and me_house and me_retrograde):
        return triggered

    # Check if 6th or 8th lord is associated with Moon
    mo_companions = _planets_in_house(d20_chart, mo_house)
    lord_6_with_moon = (lord_6 and lord_6 in mo_companions)
    lord_8_with_moon = (lord_8 and lord_8 in mo_companions)

    # Also check aspects: 6th/8th lord placed in house that aspects Moon
    if lord_6_with_moon or lord_8_with_moon:
        culprit = lord_6 if lord_6_with_moon else lord_8
        culprit_h = 6 if lord_6_with_moon else 8
        triggered.append(_rule(
            "D20-S6-CRIMINAL-PATH",
            f"{culprit_h}th lord {_pname(culprit)} with Moon + retrograde Mercury in D20 — deviation from righteous path",
            f"A malefic combination of the {culprit_h}th lord ({_pname(culprit)}) with Moon and "
            "retrograde Mercury in D20 indicates deviation from the righteous path. Such a "
            "horoscope does not follow the right spiritual path. This combination may give birth "
            "to criminal tendencies or unrighteous behaviour. This is seen and confirmed across "
            "the rashi chart, navamsha, and vimshamsha for a definitive judgment.",
            "negative", 7,
            {"overall": -5, "spirituality": -7},
            confidence="medium",
        ))

    return triggered


# ── Entry point ───────────────────────────────────────────────────────────────

def evaluate_d20_vimshamsha_rules(
    chart_facts: dict[str, Any],
    category: str = "general",
) -> list[dict[str, Any]]:
    d20_chart = _get_d20_chart(chart_facts)
    if not d20_chart:
        return []
    d1_chart = _get_d1_chart(chart_facts)
    triggered: list[dict[str, Any]] = []
    triggered.extend(_d20_s1_deity(d20_chart, d1_chart))
    triggered.extend(_d20_s2_pillars(d20_chart, d1_chart))
    triggered.extend(_d20_s3_jupiter_ketu(d20_chart))
    triggered.extend(_d20_s4_path_quality(d20_chart))
    triggered.extend(_d20_s5_sanyasa(d20_chart))
    triggered.extend(_d20_s6_deviation(d20_chart))
    return triggered
