"""
Build the evidence payload for periodic rashifal (horoscope) readings.

Three horizons:
  weekly  — Moon transit primary; birth chart + current dasha
  monthly — Sun/Mercury/Venus/Mars transits; birth chart + current dasha
  annual  — All planets month-by-month; Jupiter/Saturn/Rahu/Ketu weighted highest;
             output = significant months only (current month → same month next year)

Transit precedence rule (applied in transit_priority._score_transit_event):
  Tier 1: transiting planet conjunct natal MD/AD lord position (within 5°)  → highest bonus
  Tier 2: transiting planet in a sign owned by MD/AD lord                    → medium bonus
  Role  : MD lord transiting anywhere                                         → strong bonus
"""
from calendar import monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

from charts.transit_priority import build_transit_priority_context
from charts.vedic_utils import PLANET_NAMES, SIGN_NAMES, natal_mutual_aspects, transit_longitude


# ── Life area definition ──────────────────────────────────────────────────────

_AREA_HOUSES = {
    "job":                 [6, 2, 10, 11],
    "career":              [10, 2, 6, 11],
    "education":           [4, 5, 9, 11],
    "marriage_relationship": [2, 7, 8, 11],
    "financial":           [2, 6, 8, 9, 11],
    "debt":                [6, 8, 12],
    "relocation":          [3, 9, 12],
    "health":              [1, 6, 8, 12],
}

_AREA_LABELS = {
    "job":                 "Job / Employment",
    "career":              "Career / Promotion",
    "education":           "Education",
    "marriage_relationship": "Marriage / Relationship",
    "financial":           "Financial",
    "debt":                "Debt / Liability",
    "relocation":          "Relocation / Travel",
    "health":              "Health",
}

# Houses whose activation triggers a given life area
_HOUSE_TO_AREAS = {}
for _area, _houses in _AREA_HOUSES.items():
    for _h in _houses:
        _HOUSE_TO_AREAS.setdefault(_h, []).append(_area)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(value):
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _current_period(periods, target_date):
    for period in periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start <= target_date <= end:
            return period
    return periods[0] if periods else {}


def _get_dasha_for_date(chart_data, target_date):
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    mahadasha = _current_period(vimshottari.get("periods", []), target_date)
    antardasha = _current_period(mahadasha.get("antardashas", []), target_date)
    return {
        "mahadasha": mahadasha,
        "antardasha": antardasha,
        "md_lord": mahadasha.get("lord"),
        "ad_lord": antardasha.get("lord"),
    }


def _detect_life_areas(chart_data, target_date):
    """
    Return ordered list of life-area keys to cover, derived from the chart.
    Career vs Education is age-driven. Debt / Relocation / Health are
    included only when the relevant houses are occupied.
    """
    areas = []

    birth_date_str = chart_data.get("birth_date")
    age = None
    if birth_date_str:
        try:
            birth = _parse_date(birth_date_str)
            age = (target_date - birth).days // 365
        except (ValueError, TypeError):
            pass

    # Career vs Education
    if age is not None and age < 23:
        areas.append("education")
    else:
        areas.append("career")

    # Marriage / Relationship always
    areas.append("marriage_relationship")

    # Financial always
    areas.append("financial")

    # Debt — include if 6th or 8th house occupied
    d1_planets = chart_data.get("d1", {}).get("planets", [])
    occupied_houses = {p.get("house") for p in d1_planets if p.get("house")}
    if 6 in occupied_houses or 8 in occupied_houses:
        areas.append("debt")

    # Relocation — include if 12th or 9th house occupied
    if 12 in occupied_houses or 9 in occupied_houses:
        areas.append("relocation")

    # Health — include if malefic in 6th / 8th / 1st
    from charts.vedic_utils import MALEFIC_PLANETS
    malefic_houses = {p.get("house") for p in d1_planets if p.get("code") in MALEFIC_PLANETS}
    if malefic_houses & {1, 6, 8}:
        areas.append("health")

    return areas


def _triggered_areas(activated_houses):
    """Map a set of activated houses to life area keys."""
    areas = set()
    for house in activated_houses:
        for area in _HOUSE_TO_AREAS.get(house, []):
            areas.add(area)
    return sorted(areas)


# ── Sign change detection (annual only) ──────────────────────────────────────

_SIGN_CHANGE_PLANETS = ["Ju", "Sa", "Ra", "Ke"]

# Sampling checkpoints within a month for week-level sign-change precision
_WEEK_DAYS = [1, 8, 15, 22, 28]


def _detect_sign_changes(year, month):
    """
    Return list of slow-planet sign changes that occur during the given month.
    Compares sign at start vs end of month (sidereal, Lahiri).
    """
    start_dt = datetime(year, month, 1, 12, tzinfo=ZoneInfo("UTC"))
    last_day = monthrange(year, month)[1]
    end_dt = datetime(year, month, last_day, 12, tzinfo=ZoneInfo("UTC"))

    changes = []
    for code in _SIGN_CHANGE_PLANETS:
        try:
            start_lon = transit_longitude(code, start_dt)
            end_lon = transit_longitude(code, end_dt)
        except Exception:
            continue
        start_sign = int(start_lon // 30) + 1
        end_sign = int(end_lon // 30) + 1
        if start_sign != end_sign:
            changes.append({
                "planet": code,
                "planet_name": PLANET_NAMES.get(code, code),
                "from_sign": SIGN_NAMES.get(start_sign, str(start_sign)),
                "to_sign": SIGN_NAMES.get(end_sign, str(end_sign)),
            })
    return changes


def _find_sign_change_week(planet_code, year, month):
    """
    Narrow down the week of a sign change within a month.
    Samples 1st, 8th, 15th, 22nd, 28th. Returns an approximate date string.
    """
    last_day = monthrange(year, month)[1]
    days = [d for d in _WEEK_DAYS if d <= last_day]
    prev_sign = None
    for day in days:
        try:
            dt = datetime(year, month, day, 12, tzinfo=ZoneInfo("UTC"))
            lon = transit_longitude(planet_code, dt)
            sign = int(lon // 30) + 1
        except Exception:
            continue
        if prev_sign is not None and sign != prev_sign:
            return f"~{day} {datetime(year, month, 1).strftime('%b %Y')}"
        prev_sign = sign
    return datetime(year, month, 1).strftime("%b %Y")


# ── Slow-planet year arc (annual only) ───────────────────────────────────────

def _build_slow_planet_year_arc(chart_data, start_year, start_month, annual_end, md_lord, ad_lord):
    """
    For each slow planet (Ju/Sa/Ra/Ke) compute a year-long arc:
      - Starting house, sign, SAV
      - All sign changes (with week-level dates)
      - Months within 5° of natal MD/AD lord
      - Aspected category houses from each sign position + their SAV
    Returns a list of planet arc dicts.
    """
    from charts.vedic_utils import (
        aspected_houses as _aspected_houses,
        get_sarvashtakavarga_points,
        get_planet,
        house_from_sign,
        SIGN_NAMES,
        PLANET_NAMES,
    )

    arcs = []
    dasha_lords = {lord: role for lord, role in [(md_lord, "Mahadasha lord"), (ad_lord, "Antardasha lord")] if lord}

    # Natal positions for MD/AD lords (for conjunction check)
    natal_positions = {}
    for lord in dasha_lords:
        p = get_planet(chart_data, lord)
        natal_positions[lord] = p.get("longitude")

    for code in _SIGN_CHANGE_PLANETS:
        planet_name = PLANET_NAMES.get(code, code)

        # Starting position
        start_dt = datetime(start_year, start_month, 15, 12, tzinfo=ZoneInfo("UTC"))
        try:
            start_lon = transit_longitude(code, start_dt)
        except Exception:
            continue
        start_sign = int(start_lon // 30) + 1
        start_house = house_from_sign(chart_data, start_sign) or 1
        start_sav = get_sarvashtakavarga_points(chart_data, start_house)

        sign_changes = []
        conjunction_months = []
        positions_by_month = []

        y, m = start_year, start_month
        prev_sign = start_sign

        while True:
            month_date = date(y, m, 1)
            if month_date > annual_end:
                break

            mid_dt = datetime(y, m, 15, 12, tzinfo=ZoneInfo("UTC"))
            try:
                lon = transit_longitude(code, mid_dt)
            except Exception:
                m += 1
                if m > 12:
                    m = 1
                    y += 1
                continue

            sign = int(lon // 30) + 1
            house = house_from_sign(chart_data, sign) or 1
            sav = get_sarvashtakavarga_points(chart_data, house)

            # Sign change detection (refined to week level)
            if sign != prev_sign:
                approx_date = _find_sign_change_week(code, y, m)
                sign_changes.append({
                    "from_sign": SIGN_NAMES.get(prev_sign, str(prev_sign)),
                    "to_sign": SIGN_NAMES.get(sign, str(sign)),
                    "approximate_date": approx_date,
                    "house": house,
                    "sav": sav,
                })
                prev_sign = sign

            # Conjunction check with natal MD/AD lord (within 5°)
            for lord, role in dasha_lords.items():
                natal_lon = natal_positions.get(lord)
                if natal_lon is not None:
                    diff = abs(lon - natal_lon) % 360
                    dist = min(diff, 360 - diff)
                    if dist <= 5 and code != lord:
                        conjunction_months.append({
                            "month": datetime(y, m, 1).strftime("%B %Y"),
                            "lord": lord,
                            "lord_name": PLANET_NAMES.get(lord, lord),
                            "role": role,
                            "orb": round(dist, 1),
                        })

            # Aspected houses from current position
            asp_houses = _aspected_houses(code, house)
            aspected_info = [
                {
                    "house": h,
                    "sav": get_sarvashtakavarga_points(chart_data, h),
                }
                for h in asp_houses
            ]

            positions_by_month.append({
                "month": datetime(y, m, 1).strftime("%B %Y"),
                "sign": SIGN_NAMES.get(sign, str(sign)),
                "sign_number": sign,
                "house": house,
                "sav": sav,
                "aspected_houses": aspected_info,
            })

            m += 1
            if m > 12:
                m = 1
                y += 1

        arcs.append({
            "planet": code,
            "planet_name": planet_name,
            "is_mahadasha_lord": code == md_lord,
            "is_antardasha_lord": code == ad_lord,
            "start_sign": SIGN_NAMES.get(start_sign, str(start_sign)),
            "start_house": start_house,
            "start_sav": start_sav,
            "sign_changes": sign_changes,
            "conjunction_months": conjunction_months,
            "positions_by_month": positions_by_month,
        })

    return arcs


# ── Dasha lord transit arc (annual only) ─────────────────────────────────────

def _build_dasha_lord_transit_arc(chart_data, start_year, start_month, annual_end, md_lord, ad_lord):
    """
    Track monthly transit positions for the Mahadasha and Antardasha lords.

    Moon exception: Moon transits all 12 signs every 27 days — useless for annual tracking.
    If the lord is Moon, record only the natal house/sign/SAV as the permanent anchor, and
    note that slow planets passing through Moon's natal sign are the activation signal.

    Slow planet lords (Ju/Sa/Ra/Ke): already fully covered in slow_planet_year_arc;
    we just cross-reference rather than duplicate the computation.

    Fast planet lords (Su/Ma/Me/Ve): track month-by-month transit house + SAV.
    """
    from charts.vedic_utils import (
        get_planet,
        get_sarvashtakavarga_points,
        house_from_sign,
        SIGN_NAMES,
        PLANET_NAMES,
    )

    arcs = []
    seen_lords = set()
    lord_pairs = [(md_lord, "Mahadasha lord"), (ad_lord, "Antardasha lord")]

    for lord, role in lord_pairs:
        if not lord or lord in seen_lords:
            continue
        seen_lords.add(lord)

        planet_name = PLANET_NAMES.get(lord, lord)
        natal_p = get_planet(chart_data, lord)
        natal_house = natal_p.get("house")
        natal_sign_num = natal_p.get("sign_number")
        natal_lon = natal_p.get("longitude")
        natal_sav = get_sarvashtakavarga_points(chart_data, natal_house) if natal_house else 0

        # Moon exception: too fast for annual transit tracking
        if lord == "Mo":
            arcs.append({
                "planet": lord,
                "planet_name": planet_name,
                "role": role,
                "type": "natal_only",
                "natal_house": natal_house,
                "natal_sign": SIGN_NAMES.get(natal_sign_num) if natal_sign_num else None,
                "natal_sav": natal_sav,
                "natal_longitude": natal_lon,
                "note": (
                    "Moon transits all 12 signs in 27 days — monthly transit tracking is not meaningful "
                    "for annual rashifal. The natal Moon house is the permanent focal point of this dasha. "
                    "Check slow_planet_year_arc for months when a slow planet transits Moon's natal sign — "
                    "those are the peak activation windows for Moon Mahadasha/Antardasha."
                ),
            })
            continue

        # Slow planet lords: already in slow_planet_year_arc — avoid duplication
        if lord in {"Ju", "Sa", "Ra", "Ke"}:
            arcs.append({
                "planet": lord,
                "planet_name": planet_name,
                "role": role,
                "type": "see_slow_planet_year_arc",
                "natal_house": natal_house,
                "natal_sav": natal_sav,
                "note": (
                    f"{planet_name} is a slow planet — full year arc including sign changes, "
                    "SAV, and conjunctions is in slow_planet_year_arc."
                ),
            })
            continue

        # Fast planet lords (Su/Ma/Me/Ve): month-by-month transit
        monthly = []
        y, m = start_year, start_month

        while True:
            if date(y, m, 1) > annual_end:
                break
            mid_dt = datetime(y, m, 15, 12, tzinfo=ZoneInfo("UTC"))
            try:
                lon = transit_longitude(lord, mid_dt)
            except Exception:
                m += 1
                if m > 12:
                    m, y = 1, y + 1
                continue

            sign = int(lon // 30) + 1
            house = house_from_sign(chart_data, sign) or 1
            sav = get_sarvashtakavarga_points(chart_data, house)

            # Flag when lord is close to its natal longitude (within 15° — return to natal area)
            near_natal = False
            if natal_lon is not None:
                diff = abs(lon - natal_lon) % 360
                near_natal = min(diff, 360 - diff) <= 15

            monthly.append({
                "month": datetime(y, m, 1).strftime("%B %Y"),
                "transit_house": house,
                "transit_sign": SIGN_NAMES.get(sign, str(sign)),
                "sav": sav,
                "sav_strong": sav > 28,
                "near_natal_position": near_natal,
            })

            m += 1
            if m > 12:
                m, y = 1, y + 1

        arcs.append({
            "planet": lord,
            "planet_name": planet_name,
            "role": role,
            "type": "monthly_transit",
            "natal_house": natal_house,
            "natal_sign": SIGN_NAMES.get(natal_sign_num) if natal_sign_num else None,
            "natal_sav": natal_sav,
            "monthly": monthly,
            "note": (
                f"When {planet_name} ({role}) transits a house with SAV > 28, it can deliver "
                "strong results for that house's significations."
            ),
        })

    return arcs


# ── Monthly snapshot (annual rashifal) ───────────────────────────────────────

_ANNUAL_SIGNIFICANCE_THRESHOLD = 18


def _build_month_snapshot(chart_data, year, month, life_areas):
    """
    Score all planets for the given month (mid-month snapshot).
    Returns a snapshot dict; significant=True if score ≥ threshold or
    a slow-planet sign change occurs.
    """
    mid_date = date(year, month, 15)
    dasha = _get_dasha_for_date(chart_data, mid_date)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]

    # All houses across all life areas = category_houses for scoring
    all_category_houses = []
    for area in life_areas:
        all_category_houses.extend(_AREA_HOUSES.get(area, []))
    category_houses = list(set(all_category_houses))

    transit_ctx = build_transit_priority_context(
        chart_data,
        category_houses,
        mid_date,
        mahadasha_lord=md_lord,
        antardasha_lord=ad_lord,
        horizon="annual",
        cap=8,
    )

    events = transit_ctx.get("events", [])
    top_score = events[0]["score"] if events else 0

    # Aggregate all activated houses from all events
    all_activated = set()
    for event in events:
        all_activated.update(event.get("activated_houses", []))

    sign_changes = _detect_sign_changes(year, month)
    triggered = _triggered_areas(all_activated)

    return {
        "month": datetime(year, month, 1).strftime("%B %Y"),
        "year": year,
        "month_number": month,
        "score": top_score,
        "significant": top_score >= _ANNUAL_SIGNIFICANCE_THRESHOLD or bool(sign_changes),
        "dasha": {
            "mahadasha_lord": md_lord,
            "mahadasha_lord_name": PLANET_NAMES.get(md_lord, md_lord),
            "antardasha_lord": ad_lord,
            "antardasha_lord_name": PLANET_NAMES.get(ad_lord, ad_lord),
            "mahadasha_end": dasha["mahadasha"].get("end"),
            "antardasha_end": dasha["antardasha"].get("end"),
        },
        "top_events": events[:4],
        "triggered_areas": triggered,
        "sign_changes": sign_changes,
    }


# ── Main builders ─────────────────────────────────────────────────────────────

def _jaimini_cross_check(chart_data, target_date):
    chara = chart_data.get("jaimini", {}).get("chara_dasha", {})
    major = _current_period(chara.get("periods", []), target_date)
    subperiod = _current_period(major.get("subperiods", []), target_date)
    return {
        "system": chara.get("system"),
        "mahadasha": major,
        "antardasha": subperiod,
    }


def build_rashifal_context(question, chart_data, horizon, target_date=None, answer_language="English"):
    """
    Build the full rashifal evidence payload for the LLM.

    Returns a dict ready to be sent as the prompt payload.
    """
    from django.utils import timezone as tz
    target_date = target_date or tz.localdate()

    life_areas = _detect_life_areas(chart_data, target_date)
    dasha = _get_dasha_for_date(chart_data, target_date)
    md_lord = dasha["md_lord"]
    ad_lord = dasha["ad_lord"]

    all_category_houses = list({h for area in life_areas for h in _AREA_HOUSES.get(area, [])})
    jaimini = _jaimini_cross_check(chart_data, target_date)

    base = {
        "is_rashifal": True,
        "horizon": horizon,
        "question": question,
        "current_date": target_date.isoformat(),
        "answer_language": answer_language,
        "life_areas": [
            {"key": area, "label": _AREA_LABELS.get(area, area), "houses": _AREA_HOUSES.get(area, [])}
            for area in life_areas
        ],
        "dasha": {
            "mahadasha": dasha["mahadasha"],
            "antardasha": dasha["antardasha"],
            "mahadasha_lord_name": PLANET_NAMES.get(md_lord, md_lord),
            "antardasha_lord_name": PLANET_NAMES.get(ad_lord, ad_lord),
        },
        "jaimini_cross_check": jaimini,
        "calculation_policy": {
            "source_of_truth": "django_swiss_ephemeris_engine",
            "gpt_must_not_recalculate": True,
            "gpt_role": "rashifal_synthesis_only",
        },
        "natal_mutual_aspects": natal_mutual_aspects(chart_data),
    }

    if horizon == "weekly":
        week_end = date(target_date.year, target_date.month,
                        min(target_date.day + 6, monthrange(target_date.year, target_date.month)[1]))
        base["window"] = {
            "start": target_date.isoformat(),
            "end": week_end.isoformat(),
            "label": f"{target_date.strftime('%d %b')} – {week_end.strftime('%d %b %Y')}",
        }
        base["transit_context"] = build_transit_priority_context(
            chart_data, all_category_houses, target_date,
            mahadasha_lord=md_lord, antardasha_lord=ad_lord,
            horizon="weekly", cap=14,
        )

    elif horizon == "monthly":
        last_day = monthrange(target_date.year, target_date.month)[1]
        base["window"] = {
            "start": target_date.isoformat(),
            "end": date(target_date.year, target_date.month, last_day).isoformat(),
            "label": target_date.strftime("%B %Y"),
        }
        base["transit_context"] = build_transit_priority_context(
            chart_data, all_category_houses, target_date,
            mahadasha_lord=md_lord, antardasha_lord=ad_lord,
            horizon="monthly", cap=12,
        )

    else:  # annual
        # Window: current month → same month next year
        end_year = target_date.year + 1 if target_date.month < 12 else target_date.year
        end_month = target_date.month  # same calendar month, one year later
        end_day = monthrange(end_year, end_month)[1]
        annual_end = date(end_year, end_month, end_day)

        base["window"] = {
            "start": target_date.isoformat(),
            "end": annual_end.isoformat(),
            "label": f"{target_date.strftime('%B %Y')} – {annual_end.strftime('%B %Y')}",
        }

        # Build month-by-month snapshots
        snapshots = []
        y, m = target_date.year, target_date.month
        for _ in range(13):  # 13 iterations covers current month + 12 ahead
            if date(y, m, 1) > annual_end:
                break
            snapshot = _build_month_snapshot(chart_data, y, m, life_areas)
            snapshots.append(snapshot)
            m += 1
            if m > 12:
                m = 1
                y += 1

        base["monthly_snapshots"] = snapshots
        base["significant_months"] = [s for s in snapshots if s["significant"]]
        base["slow_planet_year_arc"] = _build_slow_planet_year_arc(
            chart_data,
            target_date.year,
            target_date.month,
            annual_end,
            md_lord,
            ad_lord,
        )
        base["dasha_lord_transit_arc"] = _build_dasha_lord_transit_arc(
            chart_data,
            target_date.year,
            target_date.month,
            annual_end,
            md_lord,
            ad_lord,
        )

    return base
