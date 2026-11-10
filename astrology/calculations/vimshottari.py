"""Deterministic Vimshottari Dasha calculation engine."""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .periods import add_years, birth_instant, interval_metadata, resolve_timezone, split_interval, timing_fields

from astrology.constants import (
    NAKSHATRAS,
    PLANET_NAMES,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
)


NAKSHATRA_SPAN = 360 / 27
VIMSHOTTARI_CYCLE_YEARS = 120
SOLAR_YEAR_DAYS = 365.2425


def _period_year_month_day(years: float) -> dict[str, int]:
    total_days = max(0, round(years * SOLAR_YEAR_DAYS))
    whole_years, remainder = divmod(total_days, round(SOLAR_YEAR_DAYS))
    months, days = divmod(remainder, 30)
    return {"years": whole_years, "months": months, "days": days}


def vimshottari_sequence_from(lord: str) -> list[str]:
    sequence_start = VIMSHOTTARI_SEQUENCE.index(lord)
    return VIMSHOTTARI_SEQUENCE[sequence_start:] + VIMSHOTTARI_SEQUENCE[:sequence_start]


def moon_nakshatra_details(moon_longitude: float) -> dict[str, Any]:
    longitude = moon_longitude % 360
    index = int(longitude // NAKSHATRA_SPAN)
    start = index * NAKSHATRA_SPAN
    end = start + NAKSHATRA_SPAN
    elapsed_degrees = longitude - start
    remaining_degrees = end - longitude
    elapsed_fraction = elapsed_degrees / NAKSHATRA_SPAN
    remaining_fraction = 1 - elapsed_fraction
    pada = int(elapsed_degrees // (NAKSHATRA_SPAN / 4)) + 1
    name, lord = NAKSHATRAS[index]

    return {
        "number": index + 1,
        "name": name,
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "pada": pada,
        "start_longitude": round(start, 6),
        "end_longitude": round(end, 6),
        "elapsed_degrees": round(elapsed_degrees, 6),
        "remaining_degrees": round(remaining_degrees, 6),
        "elapsed_fraction": round(elapsed_fraction, 8),
        "remaining_fraction": round(remaining_fraction, 8),
    }


def birth_mahadasha(moon_longitude: float) -> dict[str, Any]:
    nakshatra = moon_nakshatra_details(moon_longitude)
    lord = nakshatra["lord"]
    nominal_years = VIMSHOTTARI_YEARS[lord]
    elapsed_years = nominal_years * nakshatra["elapsed_fraction"]
    remaining_years = nominal_years * nakshatra["remaining_fraction"]

    return {
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "nominal_years": nominal_years,
        "elapsed_years": round(elapsed_years, 6),
        "remaining_years": round(remaining_years, 6),
        "elapsed": _period_year_month_day(elapsed_years),
        "balance": _period_year_month_day(remaining_years),
        "moon_nakshatra": nakshatra,
    }


def _aware(value: datetime, display_zone: ZoneInfo) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=display_zone)


def generate_antardashas(
    mahadasha_lord: str,
    start: datetime,
    end: datetime,
    display_zone: ZoneInfo | None = None,
) -> list[dict[str, Any]]:
    """Divide ``[start, end)`` in Vimshottari order, in exact proportion to planetary years."""
    display_zone = display_zone or resolve_timezone(None)
    start, end = _aware(start, display_zone), _aware(end, display_zone)
    sequence = vimshottari_sequence_from(mahadasha_lord)
    periods = []
    for lord, (current, sub_end) in zip(sequence, split_interval(start, end, [VIMSHOTTARI_YEARS[lord] for lord in sequence])):
        years = (sub_end - current).total_seconds() / 86400 / SOLAR_YEAR_DAYS
        periods.append(
            {
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                **timing_fields(current, sub_end, display_zone),
                "years": round(years, 4),
                "nominal_fraction_years": round(
                    VIMSHOTTARI_YEARS[mahadasha_lord] * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_CYCLE_YEARS,
                    4,
                ),
            }
        )
    return periods


def generate_mahadasha_timeline(
    birth: date | datetime,
    moon_longitude: float,
    cycles: int = 1,
    include_antardashas: bool = True,
    timezone_name: str | None = None,
) -> list[dict[str, Any]]:
    """Mahadasha timeline from the birth instant.

    ``birth`` may be an aware datetime (exact birth moment) or a date, which
    means local midnight in ``timezone_name`` (the pre-M1 behaviour).
    """
    display_zone = resolve_timezone(timezone_name)
    birth_dasha = birth_mahadasha(moon_longitude)
    birth_lord = birth_dasha["lord"]
    current = birth_instant(birth, timezone_name)
    periods = []

    def append_period(lord: str, start: datetime, end: datetime, balance: bool, cycle: int) -> None:
        years = (end - start).total_seconds() / 86400 / SOLAR_YEAR_DAYS
        period = {
            "lord": lord,
            "lord_name": PLANET_NAMES.get(lord, lord),
            **timing_fields(start, end, display_zone),
            "balance": balance,
            "years": round(years, 2),
            "nominal_years": VIMSHOTTARI_YEARS[lord],
            "cycle": cycle,
        }
        if include_antardashas:
            # Unchanged in M1: the balance Mahadasha's antardashas divide the
            # remaining balance only (finding M1-F1, awaiting owner decision).
            period["antardashas"] = generate_antardashas(lord, start, end, display_zone)
        periods.append(period)

    first_end = add_years(current, birth_dasha["remaining_years"], SOLAR_YEAR_DAYS)
    append_period(birth_lord, current, first_end, balance=True, cycle=1)
    current = first_end

    sequence = vimshottari_sequence_from(birth_lord)
    remaining_sequence = sequence[1:] + sequence
    total_periods = cycles * len(VIMSHOTTARI_SEQUENCE)
    cycle = 1
    for index in range(total_periods - 1):
        lord = remaining_sequence[index % len(remaining_sequence)]
        if lord == birth_lord:
            cycle += 1
        end = add_years(current, VIMSHOTTARI_YEARS[lord], SOLAR_YEAR_DAYS)
        append_period(lord, current, end, balance=False, cycle=cycle)
        current = end

    return periods


def build_vimshottari_dasha(
    birth: date | datetime,
    moon_longitude: float,
    cycles: int = 1,
    include_antardashas: bool = True,
    timezone_name: str | None = None,
) -> dict[str, Any]:
    birth_dasha = birth_mahadasha(moon_longitude)
    periods = generate_mahadasha_timeline(
        birth,
        moon_longitude,
        cycles=cycles,
        include_antardashas=include_antardashas,
        timezone_name=timezone_name,
    )

    return {
        "system": "Vimshottari",
        "calculation_status": "active",
        "method": {
            "birth_mahadasha": "Moon's birth nakshatra lord determines the first Mahadasha.",
            "balance": "Remaining Moon nakshatra arc divided by full nakshatra span, multiplied by the lord's Vimshottari years.",
            "antardashas": "Mahadasha duration is divided in Vimshottari order according to planetary year proportions out of 120.",
            "cycle_years": VIMSHOTTARI_CYCLE_YEARS,
            "cycles_generated": cycles,
            "pratyantardasha": "Not generated yet.",
            "dasha_year_days": SOLAR_YEAR_DAYS,
            "start_reference": "birth instant" if isinstance(birth, datetime) else "local midnight of the birth date",
            **interval_metadata(resolve_timezone(timezone_name)),
        },
        "moon_nakshatra": birth_dasha["moon_nakshatra"]["name"],
        "moon_nakshatra_details": birth_dasha["moon_nakshatra"],
        "balance_lord": birth_dasha["lord"],
        "birth_mahadasha": birth_dasha,
        "periods": periods,
    }

