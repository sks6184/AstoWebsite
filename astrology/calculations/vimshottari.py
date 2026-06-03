"""Deterministic Vimshottari Dasha calculation engine."""

from datetime import date, datetime, timedelta
from typing import Any

from astrology.constants import (
    NAKSHATRAS,
    PLANET_NAMES,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
)


NAKSHATRA_SPAN = 360 / 27
VIMSHOTTARI_CYCLE_YEARS = 120
SOLAR_YEAR_DAYS = 365.2425


def _format_date(value: date) -> str:
    return value.strftime("%d-%b-%Y")


def _add_years(value: datetime, years: float) -> datetime:
    return value + timedelta(days=years * SOLAR_YEAR_DAYS)


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


def generate_antardashas(
    mahadasha_lord: str,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    sequence = vimshottari_sequence_from(mahadasha_lord)
    total_days = (end - start).days
    current = start
    periods = []

    for index, lord in enumerate(sequence):
        sub_end = end if index == len(sequence) - 1 else current + timedelta(
            days=total_days * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_CYCLE_YEARS
        )
        years = (sub_end - current).days / SOLAR_YEAR_DAYS
        periods.append(
            {
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "start": current.date().isoformat(),
                "end": sub_end.date().isoformat(),
                "start_display": _format_date(current.date()),
                "end_display": _format_date(sub_end.date()),
                "years": round(years, 4),
                "nominal_fraction_years": round(
                    VIMSHOTTARI_YEARS[mahadasha_lord] * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_CYCLE_YEARS,
                    4,
                ),
            }
        )
        current = sub_end

    return periods


def generate_mahadasha_timeline(
    birth_date: date,
    moon_longitude: float,
    cycles: int = 1,
    include_antardashas: bool = True,
) -> list[dict[str, Any]]:
    birth_dasha = birth_mahadasha(moon_longitude)
    birth_lord = birth_dasha["lord"]
    current = datetime.combine(birth_date, datetime.min.time())
    periods = []

    def append_period(lord: str, start: datetime, end: datetime, balance: bool, cycle: int) -> None:
        years = (end - start).days / SOLAR_YEAR_DAYS
        period = {
            "lord": lord,
            "lord_name": PLANET_NAMES.get(lord, lord),
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "start_display": _format_date(start.date()),
            "end_display": _format_date(end.date()),
            "balance": balance,
            "years": round(years, 2),
            "nominal_years": VIMSHOTTARI_YEARS[lord],
            "cycle": cycle,
        }
        if include_antardashas:
            period["antardashas"] = generate_antardashas(lord, start, end)
        periods.append(period)

    first_end = _add_years(current, birth_dasha["remaining_years"])
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
        end = _add_years(current, VIMSHOTTARI_YEARS[lord])
        append_period(lord, current, end, balance=False, cycle=cycle)
        current = end

    return periods


def build_vimshottari_dasha(
    birth_date: date,
    moon_longitude: float,
    cycles: int = 1,
    include_antardashas: bool = True,
) -> dict[str, Any]:
    birth_dasha = birth_mahadasha(moon_longitude)
    periods = generate_mahadasha_timeline(
        birth_date,
        moon_longitude,
        cycles=cycles,
        include_antardashas=include_antardashas,
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
        },
        "moon_nakshatra": birth_dasha["moon_nakshatra"]["name"],
        "moon_nakshatra_details": birth_dasha["moon_nakshatra"],
        "balance_lord": birth_dasha["lord"],
        "birth_mahadasha": birth_dasha,
        "periods": periods,
    }

