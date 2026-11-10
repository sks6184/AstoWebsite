"""Date-resolution Vimshottari lord transits, followed by SAV assessment.

Source dasha end dates are exclusive (the next period starts on that date).
Public timeline rows use inclusive dates. Positions are sampled at 12:00 UTC
daily; these rows are not exact ingress times or muhurta calculations.
"""

from datetime import date, datetime, timedelta, timezone

from charts.vedic_utils import PLANET_NAMES, SIGN_NAMES, house_from_sign, transit_longitude

from .periods import select_period


def _date(value):
    return date.fromisoformat(value[:10]) if value else None


def lord_role(lord, md, ad):
    if lord == md == ad:
        return "Mahadasha and Antardasha lord"
    return "Mahadasha lord" if lord == md else "Antardasha lord"


def _active_pair(periods, day):
    # Shared [start, end) selector: start dates take precedence on shared boundaries.
    md = select_period(periods, day)
    if not md:
        return None, None
    ad = select_period(md.get("antardashas", []), day)
    return md.get("lord"), ad.get("lord") if ad else None


def build_dasha_transit_timeline(chart_data, start, end, category_houses):
    """Build every MD/AD interval, calculate rashi movement, then assess SAV."""
    if end < start:
        raise ValueError("Transit timeline end must be on or after its start.")
    periods = chart_data.get("dashas", {}).get("vimshottari", {}).get("periods", [])
    stop = end + timedelta(days=1)
    boundaries = {start, stop}
    for md in periods:
        for period in [md, *md.get("antardashas", [])]:
            for key in ("start", "end"):
                value = _date(period.get(key))
                if value and start < value < stop:
                    boundaries.add(value)
    dates = sorted(boundaries)
    intervals = []
    issues = []
    # Phase 1: complete period and rashi/house timeline. No SAV lookup here.
    for left, right in zip(dates, dates[1:]):
        md, ad = _active_pair(periods, left)
        row = {"start": left.isoformat(), "end": (right - timedelta(days=1)).isoformat(),
               "mahadasha_lord": md, "antardasha_lord": ad, "transit_segments": []}
        if not md or not ad:
            issues.append(f"Incomplete Vimshottari coverage: {row['start']} to {row['end']}.")
        for lord in dict.fromkeys(lord for lord in (md, ad) if lord):
            day = left
            previous = None
            while day < right:
                instant = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).replace(hour=12)
                sign = int(transit_longitude(lord, instant) // 30) + 1
                if previous is None or previous["transit_sign_number"] != sign:
                    previous = {
                        "lord": lord, "lord_name": PLANET_NAMES.get(lord, lord),
                        "role": lord_role(lord, md, ad),
                        "mahadasha_lord": md, "antardasha_lord": ad,
                        "start": day.isoformat(), "end": day.isoformat(),
                        "start_display": day.strftime("%d-%b-%Y"), "end_display": day.strftime("%d-%b-%Y"),
                        "transit_sign_number": sign, "transit_sign": SIGN_NAMES.get(sign),
                        "transit_house_from_lagna": house_from_sign(chart_data, sign),
                    }
                    row["transit_segments"].append(previous)
                previous["end"] = day.isoformat()
                previous["end_display"] = day.strftime("%d-%b-%Y")
                day += timedelta(days=1)
        intervals.append(row)

    # Phase 2: attach the existing house-based SAV model to calculated segments.
    sav_by_house = {r.get("house"): r.get("sarva") for r in chart_data.get("ashtakavarga", {}).get("rows", [])}
    for row in intervals:
        for segment in row["transit_segments"]:
            house = segment["transit_house_from_lagna"]
            sav = sav_by_house.get(house) if house else None
            quality = "unavailable" if sav is None else "strong" if sav > 28 else "moderate" if sav >= 25 else "weak"
            segment.update({
                "sarvashtakavarga_points": sav, "ashtakavarga_threshold": 28,
                "ashtakavarga_status": quality,
                "can_deliver_owned_or_placed_house_results": None if sav is None else sav > 28,
                "transit_score": (20 if house in category_houses else 0) + (16 if quality == "strong" else 8 if quality == "moderate" else 0),
            })
            if sav is None:
                issues.append(f"Missing Lagna/SAV evidence for {segment['lord_name']} from {segment['start']} to {segment['end']}.")
    return {"start": start.isoformat(), "end": end.isoformat(), "intervals": intervals,
            "resolution": "daily_12:00_UTC", "status": "preliminary" if issues else "complete",
            "issues": list(dict.fromkeys(issues)),
            "ashtakavarga_model": "Existing natal house-based Sarvashtakavarga; no separate Rahu/Ketu BAV inferred."}


def segments_in_range(timeline, start, end):
    """Clip precomputed evidence to a candidate window without changing its lords."""
    result = []
    for row in timeline.get("intervals", []):
        for segment in row["transit_segments"]:
            left, right = max(start, _date(segment["start"])), min(end, _date(segment["end"]))
            if left <= right:
                result.append({**segment, "start": left.isoformat(), "end": right.isoformat(),
                               "start_display": left.strftime("%d-%b-%Y"), "end_display": right.strftime("%d-%b-%Y")})
    return result


def summarize_segments(segments):
    """Duration-weighted transit support, once per distinct active lord."""
    checks = []
    for lord in dict.fromkeys(s["lord"] for s in segments):
        rows = [s for s in segments if s["lord"] == lord]
        days = [(_date(s["end"]) - _date(s["start"])).days + 1 for s in rows]
        checks.append({"lord": lord, "lord_name": rows[0]["lord_name"], "role": rows[0]["role"],
                       "start": min(s["start"] for s in rows), "end": max(s["end"] for s in rows),
                       "transit_score": round(sum(s["transit_score"] * n for s, n in zip(rows, days)) / sum(days), 2),
                       "assessment": "duration_weighted_across_all_rashi_segments",
                       "reasons": [f"{s['start']} to {s['end']}: {s['lord_name']} in {s['transit_sign']}, house {s['transit_house_from_lagna']}, SAV {s['sarvashtakavarga_points']}." for s in rows]})
    return checks
