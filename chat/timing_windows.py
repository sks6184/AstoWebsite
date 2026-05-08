from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .prediction_context import CATEGORY_RULES, PLANET_NAMES, _owned_houses, _planet_by_code, _transit_context_for_lord


SLOW_TRANSIT_LORDS = ["Ju", "Sa", "Ra", "Ke"]


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


def _house_score(chart_data, planet_code, category_houses):
    planet = _planet_by_code(chart_data, planet_code)
    owned = _owned_houses(chart_data, planet_code)
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

    return score, reasons


def _transit_score(chart_data, planet_code, target_date, category_houses):
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
    context = _transit_context_for_lord(chart_data, planet_code, target_dt)
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


def _window_explanation(active_dasha_label, transit_checks, transit_segments=None):
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
    return " ".join(parts)


def _window_from_antardasha(chart_data, mahadasha, antardasha, category, start_date, end_date):
    category_houses = CATEGORY_RULES.get(category, {}).get("houses", [])
    md_lord = mahadasha.get("lord")
    ad_lord = antardasha.get("lord")
    window_start = max(_parse_date(antardasha["start"]), start_date)
    window_end = min(_parse_date(antardasha["end"]), end_date)
    midpoint = window_start + timedelta(days=(window_end - window_start).days // 2)
    score = 10
    reasons = [f"Runs during {md_lord}/{ad_lord} Vimshottari period."]
    transit_checks = _dasha_lord_transit_checks(
        chart_data,
        [md_lord, ad_lord],
        midpoint,
        category_houses,
        md_lord,
        ad_lord,
    )
    transit_segments = _transit_segments(
        chart_data,
        [md_lord, ad_lord],
        window_start,
        window_end,
        category_houses,
        md_lord,
        ad_lord,
    )

    for lord, transit_check in zip(dict.fromkeys([md_lord, ad_lord]), transit_checks):
        lord_score, lord_reasons = _house_score(chart_data, lord, category_houses)
        score += lord_score + transit_check["transit_score"]
        reasons.extend(lord_reasons)
        reasons.extend(transit_check["reasons"])
        if transit_check["can_deliver_owned_or_placed_house_results"]:
            reasons.append(
                f"{transit_check['lord_name']} can deliver owned/placed house results by SAV rule."
            )

    return {
        "start": window_start.isoformat(),
        "end": window_end.isoformat(),
        "start_display": _format_date(window_start),
        "end_display": _format_date(window_end),
        "label": f"{md_lord}/{ad_lord}",
        "mahadasha_lord": md_lord,
        "antardasha_lord": ad_lord,
        "active_dasha": {
            "mahadasha": md_lord,
            "antardasha": ad_lord,
            "label": f"{md_lord}/{ad_lord}",
        },
        "dasha_lord_transit_checks": transit_checks,
        "transit_segments": transit_segments,
        "required_explanation": _window_explanation(f"{md_lord}/{ad_lord}", transit_checks, transit_segments),
        "score": min(score, 100),
        "type": "vimshottari_antardasha_window",
        "reasons": reasons[:8],
    }


def _monthly_transit_windows(chart_data, category, start_date, end_date, mahadasha_lord=None, antardasha_lord=None):
    category_houses = CATEGORY_RULES.get(category, {}).get("houses", [])
    windows = []
    current = start_date
    dasha_lords = [lord for lord in [mahadasha_lord, antardasha_lord] if lord]
    transit_lords = list(dict.fromkeys(dasha_lords or SLOW_TRANSIT_LORDS))
    dasha_label = "/".join(dasha_lords) if dasha_lords else ""

    while current <= end_date:
        month_end = min(_add_months(current, 1) - timedelta(days=1), end_date)
        score = 0
        reasons = []
        transit_checks = _dasha_lord_transit_checks(
            chart_data,
            transit_lords,
            current,
            category_houses,
            mahadasha_lord,
            antardasha_lord,
        )
        for transit_check in transit_checks:
            if transit_check["transit_score"]:
                is_dasha_lord = transit_check["lord"] in dasha_lords
                score += transit_check["transit_score"] + (12 if is_dasha_lord else 0)
                if transit_check["lord"] == mahadasha_lord:
                    reasons.append(f"{transit_check['lord_name']} is the Mahadasha lord for this window.")
                elif transit_check["lord"] == antardasha_lord:
                    reasons.append(f"{transit_check['lord_name']} is the Antardasha lord for this window.")
                reasons.extend(transit_check["reasons"])

        if score:
            windows.append(
                {
                    "start": current.isoformat(),
                    "end": month_end.isoformat(),
                    "start_display": _format_date(current),
                    "end_display": _format_date(month_end),
                    "label": f"{dasha_label} transit support" if dasha_lords else "Transit support",
                    "mahadasha_lord": mahadasha_lord,
                    "antardasha_lord": antardasha_lord,
                    "active_dasha": {
                        "mahadasha": mahadasha_lord,
                        "antardasha": antardasha_lord,
                        "label": dasha_label,
                    },
                    "dasha_lord_transit_checks": transit_checks,
                    "required_explanation": _window_explanation(dasha_label, transit_checks),
                    "score": min(score, 100),
                    "type": "monthly_transit_window",
                    "reasons": reasons[:8],
                }
            )
        current = _add_months(current, 1)

    return windows


def build_timing_windows(question, chart_data, category, start_date, months=24):
    if category == "general":
        return []

    end_date = _add_months(start_date, months)
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    windows = []

    for mahadasha in _periods_in_range(vimshottari.get("periods", []), start_date, end_date):
        for antardasha in _periods_in_range(mahadasha.get("antardashas", []), start_date, end_date):
            windows.append(
                _window_from_antardasha(chart_data, mahadasha, antardasha, category, start_date, end_date)
            )
            mahadasha_lord = mahadasha.get("lord")
            antardasha_lord = antardasha.get("lord")
            window_start = max(_parse_date(antardasha["start"]), start_date)
            window_end = min(_parse_date(antardasha["end"]), end_date)
            windows.extend(
                _monthly_transit_windows(
                    chart_data,
                    category,
                    window_start,
                    window_end,
                    mahadasha_lord,
                    antardasha_lord,
                )
            )

    if not windows:
        windows.extend(_monthly_transit_windows(chart_data, category, start_date, end_date))
    windows.sort(key=lambda item: (item["score"], item["start"]), reverse=True)

    return windows[:8]
