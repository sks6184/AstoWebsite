from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from .remedies import remedies_for_dasha
from .vedic_utils import SIGN_NAMES, get_planet, normalize_sign_number, transit_longitude


SEARCH_YEARS = 35
SCAN_STEP_DAYS = 7


def _saturn_sign(day):
    dt = datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
    return int(transit_longitude("Sa", dt) // 30) + 1


def _is_active(day, active_signs):
    return _saturn_sign(day) in active_signs


def _find_transition(start_day, end_day, active_signs, entering=True):
    day = start_day
    while day <= end_day:
        if _is_active(day, active_signs) == entering:
            return day
        day += timedelta(days=1)
    return end_day


def _phase_for_sign(saturn_sign, moon_sign):
    previous_sign = normalize_sign_number(moon_sign - 1)
    next_sign = normalize_sign_number(moon_sign + 1)
    if saturn_sign == previous_sign:
        return "First phase: Saturn transits 12th from natal Moon"
    if saturn_sign == moon_sign:
        return "Second phase: Saturn transits over natal Moon"
    if saturn_sign == next_sign:
        return "Third phase: Saturn transits 2nd from natal Moon"
    return ""


def _periods(active_signs, start_day, end_day):
    periods = []
    day = start_day
    in_period = _is_active(day, active_signs)
    period_start = day if in_period else None
    previous_day = day
    day += timedelta(days=SCAN_STEP_DAYS)

    while day <= end_day:
        active = _is_active(day, active_signs)
        if active and not in_period:
            period_start = _find_transition(previous_day, day, active_signs, entering=True)
            in_period = True
        elif in_period and not active:
            period_end = _find_transition(previous_day, day, active_signs, entering=False) - timedelta(days=1)
            periods.append({"start": period_start, "end": period_end})
            period_start = None
            in_period = False
        previous_day = day
        day += timedelta(days=SCAN_STEP_DAYS)

    if in_period and period_start:
        periods.append({"start": period_start, "end": end_day})
    return periods


def _phase_windows(period, moon_sign):
    phases = []
    day = period["start"]
    phase_start = day
    current_sign = _saturn_sign(day)
    current_phase = _phase_for_sign(current_sign, moon_sign)

    while day <= period["end"]:
        sign = _saturn_sign(day)
        phase = _phase_for_sign(sign, moon_sign)
        if phase != current_phase:
            transition_day = _find_sign_transition(day - timedelta(days=SCAN_STEP_DAYS), day, current_sign)
            phases.append(
                {
                    "phase": current_phase,
                    "sign": SIGN_NAMES.get(current_sign),
                    "start": phase_start,
                    "end": transition_day - timedelta(days=1),
                }
            )
            phase_start = transition_day
            current_sign = sign
            current_phase = phase
        day += timedelta(days=SCAN_STEP_DAYS)

    phases.append(
        {
            "phase": current_phase,
            "sign": SIGN_NAMES.get(current_sign),
            "start": phase_start,
            "end": period["end"],
        }
    )
    return phases


def _find_sign_transition(start_day, end_day, previous_sign):
    day = start_day
    while day <= end_day:
        if _saturn_sign(day) != previous_sign:
            return day
        day += timedelta(days=1)
    return end_day


def _fmt(value):
    return value.strftime("%d-%b-%Y") if value else ""


def build_sade_sati_context(chart_data, target_date=None, language="English"):
    target_date = target_date or timezone.localdate()
    moon = get_planet(chart_data, "Mo")
    moon_sign = moon.get("sign_number")
    if not moon_sign:
        return {"available": False}

    active_sign_sequence = [
        normalize_sign_number(moon_sign - 1),
        normalize_sign_number(moon_sign),
        normalize_sign_number(moon_sign + 1),
    ]
    active_signs = set(active_sign_sequence)
    start_day = target_date - timedelta(days=SEARCH_YEARS * 365)
    end_day = target_date + timedelta(days=SEARCH_YEARS * 365)
    all_periods = _periods(active_signs, start_day, end_day)
    current = next(
        (period for period in all_periods if period["start"] <= target_date <= period["end"]),
        None,
    )
    upcoming = next(
        (period for period in all_periods if period["start"] > target_date),
        None,
    )
    selected = current or upcoming
    saturn_sign = _saturn_sign(target_date)
    remedies = remedies_for_dasha("Sa", None, language)
    natal_tone = ""
    if moon_sign == 2:
        natal_tone = (
            "Natal Moon is in Taurus. In standard Vedic dignity Saturn is exalted in Libra, not Taurus; "
            "Taurus is Venus-ruled, so some traditions treat the tone as comparatively steadier."
        )

    return {
        "available": True,
        "running": bool(current),
        "status": "Running" if current else "No",
        "natal_moon_sign": moon.get("sign"),
        "natal_moon_sign_number": moon_sign,
        "active_signs": [SIGN_NAMES.get(sign) for sign in active_sign_sequence],
        "current_saturn_sign": SIGN_NAMES.get(saturn_sign),
        "current_phase": _phase_for_sign(saturn_sign, moon_sign) if current else "",
        "start": selected["start"] if selected else None,
        "end": selected["end"] if selected else None,
        "start_display": _fmt(selected["start"]) if selected else "",
        "end_display": _fmt(selected["end"]) if selected else "",
        "phase_windows": [
            {**phase, "start_display": _fmt(phase["start"]), "end_display": _fmt(phase["end"])}
            for phase in (_phase_windows(selected, moon_sign) if selected else [])
        ],
        "remedies": remedies,
        "natal_tone": natal_tone,
    }
