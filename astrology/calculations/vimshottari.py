"""Deterministic Vimshottari Dasha calculation engine."""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from .periods import birth_instant, interval_metadata, resolve_timezone, timing_fields
from .solar_years import SiderealSolarYearClock

from astrology.constants import (
    NAKSHATRAS,
    PLANET_NAMES,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
)


NAKSHATRA_SPAN = 360 / 27
VIMSHOTTARI_CYCLE_YEARS = 120
# Used only to express a balance as approximate years/months/days for display.
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


def _elapsed_years_at_birth(moon_longitude: float, lord: str) -> float:
    """Unrounded years of the birth Mahadasha already elapsed at birth."""
    elapsed_degrees = (moon_longitude % 360) % NAKSHATRA_SPAN
    return VIMSHOTTARI_YEARS[lord] * elapsed_degrees / NAKSHATRA_SPAN


def generate_antardashas(
    mahadasha_lord: str,
    start_years: float,
    clock: SiderealSolarYearClock,
    display_zone: ZoneInfo | None = None,
) -> list[dict[str, Any]]:
    """Divide a full Mahadasha in Vimshottari order.

    ``start_years`` is the Mahadasha's start in dasha years from birth
    (negative for the birth Mahadasha). Antardasha lengths are proportional to
    planetary years and are measured in true sidereal solar years, so each
    boundary is an exact instant from ``clock``.
    """
    display_zone = display_zone or resolve_timezone(None)
    md_years = VIMSHOTTARI_YEARS[mahadasha_lord]
    periods = []
    cursor = start_years
    for lord in vimshottari_sequence_from(mahadasha_lord):
        length = md_years * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_CYCLE_YEARS
        periods.append(
            {
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                **timing_fields(clock.instant(cursor), clock.instant(cursor + length), display_zone),
                "years": round(length, 4),
                "nominal_fraction_years": round(length, 4),
            }
        )
        cursor += length
    return periods


def generate_mahadasha_timeline(
    birth: date | datetime,
    moon_longitude: float,
    cycles: int = 1,
    include_antardashas: bool = True,
    timezone_name: str | None = None,
) -> list[dict[str, Any]]:
    """Mahadasha timeline (owner decisions M1b).

    * The Mahadasha running at birth is a full period that began before
      birth; the elapsed part comes from the Moon's position in its
      nakshatra (fixes finding M1-F1).
    * Years are true sidereal solar years (see ``solar_years``).

    ``birth`` may be an aware datetime (exact birth moment) or a date, which
    means local midnight in ``timezone_name``.
    """
    display_zone = resolve_timezone(timezone_name)
    birth_lord = birth_mahadasha(moon_longitude)["lord"]
    clock = SiderealSolarYearClock(birth_instant(birth, timezone_name))
    cursor = -_elapsed_years_at_birth(moon_longitude, birth_lord)
    sequence = vimshottari_sequence_from(birth_lord)
    periods = []
    for index in range(cycles * len(VIMSHOTTARI_SEQUENCE)):
        lord = sequence[index % len(sequence)]
        years = VIMSHOTTARI_YEARS[lord]
        period = {
            "lord": lord,
            "lord_name": PLANET_NAMES.get(lord, lord),
            **timing_fields(clock.instant(cursor), clock.instant(cursor + years), display_zone),
            "balance": index == 0,
            "years": years,
            "nominal_years": years,
            "cycle": index // len(VIMSHOTTARI_SEQUENCE) + 1,
        }
        if index == 0:
            period["starts_before_birth"] = cursor < 0
            period["balance_years_at_birth"] = round(cursor + years, 6)
        if include_antardashas:
            period["antardashas"] = generate_antardashas(lord, cursor, clock, display_zone)
        periods.append(period)
        cursor += years
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
            "birth_mahadasha_period": "Full period that began before birth; the elapsed part comes from the Moon's position in its nakshatra.",
            "antardashas": "Each full Mahadasha is divided in Vimshottari order according to planetary year proportions out of 120.",
            "cycle_years": VIMSHOTTARI_CYCLE_YEARS,
            "cycles_generated": cycles,
            "pratyantardasha": "Not generated yet.",
            "dasha_year": "true sidereal solar year: dasha year Y is reached when the Sun's sidereal longitude has advanced 360*Y degrees from birth",
            "start_reference": "birth instant" if isinstance(birth, datetime) else "local midnight of the birth date",
            **interval_metadata(resolve_timezone(timezone_name)),
        },
        "moon_nakshatra": birth_dasha["moon_nakshatra"]["name"],
        "moon_nakshatra_details": birth_dasha["moon_nakshatra"],
        "balance_lord": birth_dasha["lord"],
        "birth_mahadasha": birth_dasha,
        "periods": periods,
    }

