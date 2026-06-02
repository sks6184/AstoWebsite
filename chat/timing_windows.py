from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from charts.jaimini_confirmation import build_jaimini_confirmation
from charts.yogini_alignment import build_yogini_alignment
from charts.vedic_utils import PLANET_NAMES, get_owned_houses, get_planet, transit_context_for_lord

from .prediction_context import CATEGORY_RULES


SLOW_TRANSIT_LORDS = ["Ju", "Sa", "Ra", "Ke"]

# Maps question category to the primary divisional chart for period-lord validation.
_CATEGORY_PRIMARY_VARGA = {
    "job": "d10",
    "career": "d10",
    "business": "d10",
    "money": "d2",
    "marriage": "d9",
    "children": "d7",
    "health": "d9",
    "education": "d24",
    "spirituality": "d20",
    "general": "d9",
}


def _planet_in_varga(chart_data: dict, chart_key: str, planet_code: str) -> dict:
    """Read a planet's pre-computed varga placement directly from chart_data."""
    for planet in chart_data.get(chart_key, {}).get("planets", []):
        if planet.get("code") == planet_code:
            return planet
    return {}


def _varga_score_for_window_lord(
    chart_data: dict, lord_code: str, category: str, category_houses: list
) -> tuple[int, list[str]]:
    """
    Score the antardasha lord's placement in the category-relevant divisional chart.
    Career/business → D10. Wealth → D2. Marriage → D9. Others → D9.
    Also checks D9 as a secondary strength indicator for career/business.
    """
    if not lord_code:
        return 0, []

    primary_varga = _CATEGORY_PRIMARY_VARGA.get(category, "d9")
    score = 0
    reasons = []
    lord_name = PLANET_NAMES.get(lord_code, lord_code)

    planet = _planet_in_varga(chart_data, primary_varga, lord_code)
    house = planet.get("house")
    if house:
        if house in category_houses:
            score += 20
            reasons.append(
                f"{lord_name} is in {primary_varga.upper()} house {house}, "
                f"confirming the {category} theme in the divisional chart."
            )
        elif house in {1, 5, 9, 10, 11}:
            score += 8
            reasons.append(
                f"{lord_name} is in {primary_varga.upper()} house {house} "
                f"(kendra/trikona/upachaya strength)."
            )

    if category in {"career", "job", "business"} and primary_varga != "d9":
        d9_planet = _planet_in_varga(chart_data, "d9", lord_code)
        d9_house = d9_planet.get("house")
        if d9_house in {1, 5, 9, 10}:
            score += 6
            reasons.append(
                f"{lord_name} is in D9 house {d9_house} (Navamsha vargottama strength)."
            )

    return min(score, 30), reasons


def _format_date(value):
    return value.strftime("%d-%b-%Y")


def _parse_date(value):
    return datetime.fromisoformat(value).date()


def _add_months(value, months):
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, 28)
    return value.replace(year=year, month=month, day=day)


def _overlaps(start, end, range_start, range_end):
    return start <= range_end and end >= range_start


def _periods_in_range(periods, start_date, end_date):
    return [
        period
        for period in periods
        if _overlaps(_parse_date(period["start"]), _parse_date(period["end"]), start_date, end_date)
    ]


def _house_score(chart_data, planet_code, category_houses, category=""):
    planet = get_planet(chart_data, planet_code)
    owned = get_owned_houses(chart_data, planet_code)
    placed = planet.get("house")
    score = 0
    reasons = []

    matching_owned = [house for house in owned if house in category_houses]
    if matching_owned:
        score += 18
        reasons.append(f"{PLANET_NAMES.get(planet_code, planet_code)} owns relevant house(s) {matching_owned}.")

    if placed in category_houses:
        score += 14
        reasons.append(f"{PLANET_NAMES.get(planet_code, planet_code)} is placed in relevant house {placed}.")

    if planet.get("jaimini_karaka") in {"Amatyakaraka", "Atmakaraka"}:
        score += 8
        reasons.append(f"{PLANET_NAMES.get(planet_code, planet_code)} is {planet.get('jaimini_karaka')}.")

    # Divisional chart dusthana penalty: if the lord is in house 6/8/12 of the
    # category's primary varga, reduce confidence — D1 promise is not confirmed.
    primary_varga = _CATEGORY_PRIMARY_VARGA.get(category)
    if primary_varga:
        varga_planet = _planet_in_varga(chart_data, primary_varga, planet_code)
        varga_house = varga_planet.get("house")
        if varga_house in {6, 8, 12}:
            score -= 15
            reasons.append(
                f"{PLANET_NAMES.get(planet_code, planet_code)} is in {primary_varga.upper()} "
                f"house {varga_house} (dusthana) — divisional chart weakens D1 timing promise."
            )

    return score, reasons


def _transit_score(chart_data, planet_code, target_date, category_houses):
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo("UTC")).replace(hour=12)
    context = transit_context_for_lord(chart_data, planet_code, target_dt)
    score = 0
    reasons = []

    if context["transit_house_from_lagna"] in category_houses:
        score += 20
        reasons.append(
            f"{context['lord_name']} transits relevant house {context['transit_house_from_lagna']}."
        )

    if context["sarvashtakavarga_points"] > 28:
        score += 16
        reasons.append(
            f"Transit house has SAV {context['sarvashtakavarga_points']}, above 28."
        )
    elif context["sarvashtakavarga_points"] >= 25:
        score += 8
        reasons.append(f"Transit house has moderate SAV {context['sarvashtakavarga_points']}.")

    return score, reasons, context


def _lord_role(planet_code, mahadasha_lord, antardasha_lord):
    if planet_code == mahadasha_lord:
        return "Mahadasha lord"
    if planet_code == antardasha_lord:
        return "Antardasha lord"
    return "Transit lord"


def _dasha_lord_transit_checks(chart_data, lords, target_date, category_houses, mahadasha_lord=None, antardasha_lord=None):
    checks = []
    for lord in dict.fromkeys([lord for lord in lords if lord]):
        transit_score, transit_reasons, transit_context = _transit_score(chart_data, lord, target_date, category_houses)
        checks.append(
            {
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "role": _lord_role(lord, mahadasha_lord, antardasha_lord),
                "transit_score": transit_score,
                "transit_house_from_lagna": transit_context.get("transit_house_from_lagna"),
                "transit_sign_number": transit_context.get("transit_sign_number"),
                "sarvashtakavarga_points": transit_context.get("sarvashtakavarga_points"),
                "ashtakavarga_threshold": transit_context.get("ashtakavarga_threshold"),
                "can_deliver_owned_or_placed_house_results": transit_context.get(
                    "can_deliver_owned_or_placed_house_results"
                ),
                "owned_houses": transit_context.get("owned_houses", []),
                "natal_placed_house": transit_context.get("natal_placed_house"),
                "reasons": transit_reasons,
            }
        )
    return checks


def _context_signature(context):
    return (
        context.get("transit_house_from_lagna"),
        context.get("transit_sign_number"),
        context.get("sarvashtakavarga_points"),
    )


def _transit_segments_for_lord(chart_data, lord, start_date, end_date, category_houses, mahadasha_lord=None, antardasha_lord=None):
    segments = []
    current_date = start_date
    current_context = None
    current_start = start_date

    while current_date <= end_date:
        _, _, context = _transit_score(chart_data, lord, current_date, category_houses)
        signature = _context_signature(context)

        if current_context is None:
            current_context = context
            current_start = current_date
        elif signature != _context_signature(current_context):
            segment_end = current_date - timedelta(days=1)
            segments.append(_segment_payload(lord, current_context, current_start, segment_end, mahadasha_lord, antardasha_lord))
            current_context = context
            current_start = current_date

        current_date += timedelta(days=1)

    if current_context is not None:
        segments.append(_segment_payload(lord, current_context, current_start, end_date, mahadasha_lord, antardasha_lord))

    return segments


def _segment_payload(lord, context, start_date, end_date, mahadasha_lord=None, antardasha_lord=None):
    return {
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "role": _lord_role(lord, mahadasha_lord, antardasha_lord),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "start_display": _format_date(start_date),
        "end_display": _format_date(end_date),
        "transit_house_from_lagna": context.get("transit_house_from_lagna"),
        "transit_sign_number": context.get("transit_sign_number"),
        "sarvashtakavarga_points": context.get("sarvashtakavarga_points"),
        "ashtakavarga_threshold": context.get("ashtakavarga_threshold"),
        "can_deliver_owned_or_placed_house_results": context.get("can_deliver_owned_or_placed_house_results"),
    }


def _transit_segments(chart_data, lords, start_date, end_date, category_houses, mahadasha_lord=None, antardasha_lord=None):
    segments = []
    for lord in dict.fromkeys([lord for lord in lords if lord]):
        segments.extend(
            _transit_segments_for_lord(
                chart_data,
                lord,
                start_date,
                end_date,
                category_houses,
                mahadasha_lord,
                antardasha_lord,
            )
        )
    return segments


def _window_explanation(
    active_dasha_label,
    transit_checks,
    transit_segments=None,
    yogini_alignment=None,
    varga_score=0,
    varga_reasons=None,
):
    parts = [f"Active dasha for this window: {active_dasha_label}."]
    changing_segments = [
        segment
        for segment in (transit_segments or [])
        if segment["start"] != segment["end"]
    ]
    if changing_segments:
        parts.append("Do not treat this whole period as one fixed transit. Transit segments inside this period:")
        for segment in changing_segments[:10]:
            parts.append(
                f"{segment['role']} {segment['lord_name']}: {segment['start_display']} to {segment['end_display']} "
                f"house {segment['transit_house_from_lagna']} with SAV {segment['sarvashtakavarga_points']}."
            )
    else:
        for check in transit_checks:
            parts.append(
                f"{check['role']} {check['lord_name']} transits house {check['transit_house_from_lagna']} "
                f"with Sarvashtakavarga {check['sarvashtakavarga_points']} "
                f"(threshold {check['ashtakavarga_threshold']})."
            )

    if yogini_alignment and yogini_alignment.get("calculation_status") == "active":
        major = yogini_alignment.get("yogini")
        sub = yogini_alignment.get("sub_yogini")
        nature = yogini_alignment.get("major_nature", "mixed")
        major_lord_name = yogini_alignment.get("major_lord_name", "")
        sub_lord_name = yogini_alignment.get("sub_lord_name", "")
        parts.append(
            f"Yogini: {major} major period ({major_lord_name}, {nature}) "
            f"/ {sub} sub-period ({sub_lord_name}). "
            f"Yogini score: {yogini_alignment.get('score', 0)}."
        )

    if varga_score and varga_reasons:
        parts.append(
            f"Divisional chart: {varga_reasons[0]} (varga score {varga_score})."
        )

    return " ".join(parts)


# ── Multi-dasha convergence ───────────────────────────────────────────────────

def _current_period_at(periods, target_date):
    """Return the period whose [start, end] contains target_date."""
    for period in periods:
        try:
            start = _parse_date(period.get("start", ""))
            end = _parse_date(period.get("end", ""))
            if start <= target_date <= end:
                return period
        except (ValueError, TypeError):
            continue
    return periods[-1] if periods else {}


def _vimshottari_at(chart_data, target_date):
    """Return (mahadasha dict, antardasha dict) active at target_date."""
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    for md in vimshottari.get("periods", []):
        try:
            md_start = _parse_date(md.get("start", ""))
            md_end = _parse_date(md.get("end", ""))
        except (ValueError, TypeError):
            continue
        if md_start <= target_date <= md_end:
            for ad in md.get("antardashas", []):
                try:
                    ad_start = _parse_date(ad.get("start", ""))
                    ad_end = _parse_date(ad.get("end", ""))
                except (ValueError, TypeError):
                    continue
                if ad_start <= target_date <= ad_end:
                    return md, ad
    return {}, {}


def _collect_all_dasha_boundaries(chart_data, start_date, end_date):
    """Collect all period boundary dates from Vimshottari, Jaimini, and Yogini."""
    boundaries = {start_date, end_date}

    def _add(date_str):
        if not date_str:
            return
        try:
            d = _parse_date(date_str)
            if start_date < d < end_date:
                boundaries.add(d)
        except (ValueError, TypeError):
            pass

    for md in chart_data.get("dashas", {}).get("vimshottari", {}).get("periods", []):
        for ad in md.get("antardashas", []):
            _add(ad.get("start"))
            _add(ad.get("end"))

    for md in chart_data.get("jaimini", {}).get("chara_dasha", {}).get("periods", []):
        for sub in md.get("subperiods", []):
            _add(sub.get("start"))
            _add(sub.get("end"))

    for md in chart_data.get("dashas", {}).get("yogini", {}).get("periods", []):
        for sub in md.get("subperiods", []):
            _add(sub.get("start"))
            _add(sub.get("end"))

    return sorted(boundaries)


def _score_micro_period(chart_data, category, category_houses, period_start, period_end):
    """Score a micro-period at its midpoint across all 3 dasha systems + varga (fast, no day-by-day segments)."""
    midpoint = period_start + timedelta(days=(period_end - period_start).days // 2)

    md, ad = _vimshottari_at(chart_data, midpoint)
    md_lord = md.get("lord")
    ad_lord = ad.get("lord")

    score = 10
    reasons = []
    if md_lord or ad_lord:
        reasons.append(f"Runs during {md_lord}/{ad_lord} Vimshottari period.")
    for lord in dict.fromkeys([l for l in [md_lord, ad_lord] if l]):
        lord_score, lord_reasons = _house_score(chart_data, lord, category_houses, category)
        transit_s, transit_r, _ = _transit_score(chart_data, lord, midpoint, category_houses)
        score += lord_score + transit_s
        reasons.extend(lord_reasons)
        reasons.extend(transit_r)
    vimshottari_score = max(0, score - 10)

    jaimini_conf = build_jaimini_confirmation(chart_data, category, category_houses, midpoint)
    jaimini_score = jaimini_conf.get("score", 0)

    yogini_aln = build_yogini_alignment(chart_data, category, category_houses, midpoint)
    yogini_score = yogini_aln.get("score", 0)

    varga_score, varga_reasons = _varga_score_for_window_lord(chart_data, ad_lord, category, category_houses)
    reasons.extend(varga_reasons)

    composite_score = min(100, max(0, round(
        vimshottari_score * 0.40
        + jaimini_score * 0.25
        + yogini_score * 0.20
        + varga_score * 0.15
    )))

    jaimini_chara = chart_data.get("jaimini", {}).get("chara_dasha", {})
    jaimini_major = _current_period_at(jaimini_chara.get("periods", []), midpoint)
    jaimini_sub = _current_period_at(jaimini_major.get("subperiods", []), midpoint)

    yogini_data = chart_data.get("dashas", {}).get("yogini", {})
    yogini_major = _current_period_at(yogini_data.get("periods", []), midpoint)
    yogini_sub = _current_period_at(yogini_major.get("subperiods", []), midpoint) if yogini_major else {}

    return {
        "start": period_start.isoformat(),
        "end": period_end.isoformat(),
        "start_display": _format_date(period_start),
        "end_display": _format_date(period_end),
        "mahadasha_lord": md_lord,
        "antardasha_lord": ad_lord,
        "jaimini_sign": jaimini_major.get("sign"),
        "jaimini_sub_sign": jaimini_sub.get("sign"),
        "yogini": yogini_major.get("yogini"),
        "sub_yogini": yogini_sub.get("yogini"),
        "yogini_lord": yogini_major.get("lord"),
        "sub_yogini_lord": yogini_sub.get("lord"),
        "vimshottari_score": min(vimshottari_score, 100),
        "jaimini_score": jaimini_score,
        "yogini_score": yogini_score,
        "varga_score": varga_score,
        "composite_score": composite_score,
        "jaimini_confirmation": jaimini_conf,
        "yogini_alignment": yogini_aln,
        "reasons": reasons[:6],
    }


def _build_convergence_window(group):
    """Build a merged window from a group of consecutive micro-periods sharing the same Vimshottari MD/AD."""
    first = group[0]
    last = group[-1]
    md_lord = first.get("mahadasha_lord")
    ad_lord = first.get("antardasha_lord")
    best = max(group, key=lambda m: m.get("composite_score", 0))
    composite_score = best.get("composite_score", 0)

    seen: set = set()
    all_reasons = []
    for mp in group:
        for r in mp.get("reasons", []):
            if r not in seen:
                seen.add(r)
                all_reasons.append(r)

    # Flat Jaimini and Yogini fields from the best-scoring sub-period for easy display
    jaimini_chara = best.get("jaimini_confirmation", {}).get("active_chara_dasha", {})
    jaimini_active_sign = (jaimini_chara.get("mahadasha") or {}).get("sign") or best.get("jaimini_sign")
    jaimini_active_sub_sign = (jaimini_chara.get("antardasha") or {}).get("sign") or best.get("jaimini_sub_sign")
    # house_from_lagna already computed in jaimini_confirmation — surface it flat so LLM never guesses
    jaimini_active_sign_house = jaimini_chara.get("mahadasha_house_from_lagna")
    jaimini_active_sub_sign_house = jaimini_chara.get("antardasha_house_from_lagna")
    yogini_name = best.get("yogini_alignment", {}).get("yogini") or best.get("yogini")
    sub_yogini_name = best.get("yogini_alignment", {}).get("sub_yogini") or best.get("sub_yogini")

    # Compact breakdown — one entry per micro-period, no nested objects
    compact_breakdown = [
        {
            "start": sp.get("start"),
            "end": sp.get("end"),
            "jaimini_sign": sp.get("jaimini_sign"),
            "jaimini_sub_sign": sp.get("jaimini_sub_sign"),
            "yogini": sp.get("yogini"),
            "sub_yogini": sp.get("sub_yogini"),
            "composite_score": sp.get("composite_score", 0),
            "vimshottari_score": sp.get("vimshottari_score", 0),
            "jaimini_score": sp.get("jaimini_score", 0),
            "yogini_score": sp.get("yogini_score", 0),
        }
        for sp in group
    ]

    return {
        "start": first["start"],
        "end": last["end"],
        "start_display": first["start_display"],
        "end_display": last["end_display"],
        "label": f"{md_lord}/{ad_lord}",
        "mahadasha_lord": md_lord,
        "antardasha_lord": ad_lord,
        "jaimini_active_sign": jaimini_active_sign,
        "jaimini_active_sign_house_from_lagna": jaimini_active_sign_house,
        "jaimini_active_sub_sign": jaimini_active_sub_sign,
        "jaimini_active_sub_sign_house_from_lagna": jaimini_active_sub_sign_house,
        "yogini_name": yogini_name,
        "sub_yogini_name": sub_yogini_name,
        "active_dasha": {
            "mahadasha": md_lord,
            "antardasha": ad_lord,
            "label": f"{md_lord}/{ad_lord}",
        },
        "score": composite_score,
        "composite_score": composite_score,
        "vimshottari_score": best.get("vimshottari_score", 0),
        "jaimini_score": best.get("jaimini_score", 0),
        "yogini_score": best.get("yogini_score", 0),
        "varga_score": best.get("varga_score", 0),
        "type": "convergence_window",
        "reasons": all_reasons[:8],
        "jaimini_confirmation": best.get("jaimini_confirmation", {}),
        "yogini_alignment": best.get("yogini_alignment", {}),
        "sub_period_breakdown": compact_breakdown,
        "dasha_lord_transit_checks": [],
        "transit_segments": [],
        "required_explanation": "",
    }


def _merge_adjacent_convergence_windows(micro_periods):
    """Group consecutive micro-periods with the same Vimshottari MD+AD into one convergence window."""
    if not micro_periods:
        return []

    merged = []
    group = [micro_periods[0]]

    for mp in micro_periods[1:]:
        prev = group[-1]
        same_vim = (
            mp.get("mahadasha_lord") == prev.get("mahadasha_lord")
            and mp.get("antardasha_lord") == prev.get("antardasha_lord")
        )
        if same_vim:
            group.append(mp)
        else:
            merged.append(_build_convergence_window(group))
            group = [mp]

    merged.append(_build_convergence_window(group))
    return merged


def _enrich_with_transit_segments(chart_data, windows, category):
    """Add day-by-day transit segments and required_explanation to the top windows (expensive step)."""
    category_houses = CATEGORY_RULES.get(category, {}).get("houses", [])
    for window in windows:
        md_lord = window.get("mahadasha_lord")
        ad_lord = window.get("antardasha_lord")
        window_start = _parse_date(window["start"])
        window_end = _parse_date(window["end"])
        midpoint = window_start + timedelta(days=(window_end - window_start).days // 2)

        transit_checks = _dasha_lord_transit_checks(
            chart_data, [md_lord, ad_lord], midpoint, category_houses, md_lord, ad_lord
        )
        transit_segs = _transit_segments(
            chart_data, [md_lord, ad_lord], window_start, window_end,
            category_houses, md_lord, ad_lord,
        )
        window["dasha_lord_transit_checks"] = transit_checks
        window["transit_segments"] = transit_segs
        window["required_explanation"] = _window_explanation(
            f"{md_lord}/{ad_lord}",
            transit_checks,
            transit_segs,
            window.get("yogini_alignment"),
            window.get("varga_score", 0),
            window.get("jaimini_confirmation", {}).get("reasons"),
        )
    return windows


def build_timing_windows(question, chart_data, category, start_date, months=60, end_date=None):
    if category == "general":
        return []

    end_date = end_date or _add_months(start_date, months)
    category_houses = CATEGORY_RULES.get(category, {}).get("houses", [])

    # Slice the timeline at every period boundary from all 3 dasha systems
    boundaries = _collect_all_dasha_boundaries(chart_data, start_date, end_date)

    micro_periods = []
    for i in range(len(boundaries) - 1):
        mp_start = boundaries[i]
        mp_end = boundaries[i + 1] - timedelta(days=1)
        if mp_start > mp_end:
            continue
        micro_periods.append(
            _score_micro_period(chart_data, category, category_houses, mp_start, mp_end)
        )

    if not micro_periods:
        return []

    # Merge by Vimshottari antardasha, rank, then enrich top-8 with transit segments
    merged = _merge_adjacent_convergence_windows(micro_periods)
    merged.sort(key=lambda w: (w.get("composite_score", 0), w["start"]), reverse=True)
    top_windows = merged[:8]
    _enrich_with_transit_segments(chart_data, top_windows, category)

    return top_windows
