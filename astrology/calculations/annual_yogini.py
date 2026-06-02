"""Annual-chart Yogini periods from Chapter 12.

This module calculates the one-year Yogini schedule only. It does not calculate
the solar-return chart and must not be used for prediction scoring until a
deterministic Varshaphala calculator supplies the annual-chart start date.
"""
from datetime import date, datetime, timedelta
from typing import Any

from charts.vedic_utils import PLANET_NAMES

from .yogini import YOGINI_LORDS, YOGINI_SEQUENCE, YOGINI_YEARS


CHAPTER_TWELVE_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 12: Yogini Dasha and the Annual Chart",
    "printed_pages": "183-191",
    "pdf_pages": "191-199",
}

ANNUAL_YOGINI_DAYS = {
    yogini: years * 10
    for yogini, years in YOGINI_YEARS.items()
}


def _annual_subperiods(yogini: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    sequence_start = YOGINI_SEQUENCE.index(yogini)
    sequence = YOGINI_SEQUENCE[sequence_start:] + YOGINI_SEQUENCE[:sequence_start]
    total_days = (end - start).total_seconds() / 86400
    current = start
    periods = []
    for index, sub_yogini in enumerate(sequence):
        sub_end = (
            end
            if index == len(sequence) - 1
            else current + timedelta(days=total_days * ANNUAL_YOGINI_DAYS[sub_yogini] / 360)
        )
        lord = YOGINI_LORDS[sub_yogini]
        periods.append(
            {
                "yogini": sub_yogini,
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "start": current.date().isoformat(),
                "end": sub_end.date().isoformat(),
                "days": round((sub_end - current).total_seconds() / 86400, 4),
            }
        )
        current = sub_end
    return periods


def build_annual_yogini_periods(
    birth_nakshatra_number: int,
    completed_years: int,
    moon_remaining_fraction: float,
    annual_chart_start: date,
) -> dict[str, Any]:
    """Build the 360-day annual Yogini schedule after solar-return calculation."""
    if not 1 <= birth_nakshatra_number <= 27:
        raise ValueError("birth_nakshatra_number must be between 1 and 27.")
    if completed_years < 0:
        raise ValueError("completed_years must not be negative.")
    if not 0 <= moon_remaining_fraction <= 1:
        raise ValueError("moon_remaining_fraction must be between 0 and 1.")

    remainder = (birth_nakshatra_number + completed_years + 3) % 8
    first_index = 7 if remainder == 0 else remainder - 1
    first_yogini = YOGINI_SEQUENCE[first_index]
    first_total_days = ANNUAL_YOGINI_DAYS[first_yogini]
    first_balance_days = first_total_days * moon_remaining_fraction
    periods = []
    current = datetime.combine(annual_chart_start, datetime.min.time())

    def append_period(yogini: str, duration_days: float, balance: bool = False) -> None:
        nonlocal current
        end = current + timedelta(days=duration_days)
        lord = YOGINI_LORDS[yogini]
        periods.append(
            {
                "yogini": yogini,
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "start": current.date().isoformat(),
                "end": end.date().isoformat(),
                "days": round(duration_days, 4),
                "balance": balance,
                "subperiods": _annual_subperiods(yogini, current, end),
            }
        )
        current = end

    append_period(first_yogini, first_balance_days, balance=True)
    sequence = YOGINI_SEQUENCE[first_index + 1 :] + YOGINI_SEQUENCE[:first_index]
    for yogini in sequence:
        append_period(yogini, ANNUAL_YOGINI_DAYS[yogini])
    remaining_days = first_total_days - first_balance_days
    if remaining_days:
        append_period(first_yogini, remaining_days)

    return {
        "system": "Annual Chart Yogini Dasha",
        "calculation_status": "active",
        "scoring_status": "isolated_until_varshaphala_chart_is_calculated",
        "annual_chart_start": annual_chart_start.isoformat(),
        "annual_chart_end": current.date().isoformat(),
        "birth_nakshatra_number": birth_nakshatra_number,
        "completed_years": completed_years,
        "formula_remainder": remainder,
        "first_yogini": first_yogini,
        "first_balance_days": round(first_balance_days, 4),
        "periods": periods,
        "method": {
            "first_yogini_formula": "(birth nakshatra number + completed years + 3) mod 8",
            "balance": "Annual Yogini duration multiplied by the untraversed fraction of the natal Moon nakshatra.",
            "subperiods": "Proportional annual-chart Yogini subperiods.",
            "annual_cycle_days": 360,
        },
        "source_reference": CHAPTER_TWELVE_REFERENCE,
        "source_note": (
            "The printed example labels a 16-day balance inconsistently in one sentence. "
            "The formula and table identify it as Pingala, which this implementation follows."
        ),
    }
