from datetime import date, datetime, timedelta
from typing import Any

from charts.vedic_utils import PLANET_NAMES, get_owned_houses, get_planet, get_planet_dignity

from .varga import get_planet_in_varga


NAKSHATRA_SPAN = 360 / 27
YOGINI_SEQUENCE = ["Mangala", "Pingala", "Dhanya", "Bhramari", "Bhadrika", "Ulka", "Siddha", "Sankata"]
YOGINI_LORDS = {
    "Mangala": "Mo",
    "Pingala": "Su",
    "Dhanya": "Ju",
    "Bhramari": "Ma",
    "Bhadrika": "Me",
    "Ulka": "Sa",
    "Siddha": "Ve",
    "Sankata": "Ra",
}
YOGINI_YEARS = {
    "Mangala": 1,
    "Pingala": 2,
    "Dhanya": 3,
    "Bhramari": 4,
    "Bhadrika": 5,
    "Ulka": 6,
    "Siddha": 7,
    "Sankata": 8,
}
NAKSHATRA_NAMES = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]


def _format_date(value: date) -> str:
    return value.strftime("%d-%b-%Y")


def _parse_birth_date(chart_data: dict[str, Any]) -> date | None:
    value = chart_data.get("birth_date")
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def _add_years(value: datetime, years: float) -> datetime:
    return value + timedelta(days=years * 365.2425)


def _current_period(periods: list[dict[str, Any]], target_date: date) -> dict[str, Any]:
    for period in periods:
        start = datetime.fromisoformat(period["start"]).date()
        end = datetime.fromisoformat(period["end"]).date()
        if start <= target_date <= end:
            return period
    return periods[-1] if periods else {}


def _yogini_for_nakshatra(nakshatra_number: int) -> str:
    remainder = (nakshatra_number + 3) % 8
    index = 7 if remainder == 0 else remainder - 1
    return YOGINI_SEQUENCE[index]


def _moon_nakshatra(moon_longitude: float) -> dict[str, Any]:
    index = int(moon_longitude // NAKSHATRA_SPAN)
    start = index * NAKSHATRA_SPAN
    end = start + NAKSHATRA_SPAN
    elapsed = moon_longitude - start
    remaining = end - moon_longitude
    nakshatra_number = index + 1
    yogini = _yogini_for_nakshatra(nakshatra_number)
    return {
        "number": nakshatra_number,
        "name": NAKSHATRA_NAMES[index],
        "start_longitude": round(start, 6),
        "end_longitude": round(end, 6),
        "elapsed_degrees": round(elapsed, 6),
        "remaining_degrees": round(remaining, 6),
        "birth_yogini": yogini,
    }


def _subperiods(major: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    sequence_start = YOGINI_SEQUENCE.index(major)
    sequence = YOGINI_SEQUENCE[sequence_start:] + YOGINI_SEQUENCE[:sequence_start]
    total_days = (end - start).days
    current = start
    periods = []
    for index, yogini in enumerate(sequence):
        sub_end = end if index == len(sequence) - 1 else current + timedelta(days=total_days * YOGINI_YEARS[yogini] / 36)
        lord = YOGINI_LORDS[yogini]
        periods.append(
            {
                "yogini": yogini,
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "start": current.date().isoformat(),
                "end": sub_end.date().isoformat(),
                "start_display": _format_date(current.date()),
                "end_display": _format_date(sub_end.date()),
                "years": round(YOGINI_YEARS[yogini] * YOGINI_YEARS[major] / 36, 4),
            }
        )
        current = sub_end
    return periods


def build_yogini_periods(chart_data: dict[str, Any], cycles: int = 4) -> dict[str, Any]:
    birth_date = _parse_birth_date(chart_data)
    moon = get_planet(chart_data, "Mo", "d1")
    moon_longitude = moon.get("longitude")
    if birth_date is None or moon_longitude is None:
        return {
            "system": "Yogini Dasha",
            "calculation_status": "unavailable",
            "error": "Birth date and Moon longitude are required.",
            "periods": [],
        }

    nakshatra = _moon_nakshatra(float(moon_longitude))
    birth_yogini = nakshatra["birth_yogini"]
    elapsed_fraction = nakshatra["elapsed_degrees"] / NAKSHATRA_SPAN
    remaining_fraction = 1 - elapsed_fraction
    first_years = YOGINI_YEARS[birth_yogini] * remaining_fraction
    current = datetime.combine(birth_date, datetime.min.time())
    first_end = _add_years(current, first_years)
    periods = []

    def append_period(yogini: str, start: datetime, end: datetime, balance: bool = False, cycle: int = 1):
        lord = YOGINI_LORDS[yogini]
        periods.append(
            {
                "yogini": yogini,
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "start": start.date().isoformat(),
                "end": end.date().isoformat(),
                "start_display": _format_date(start.date()),
                "end_display": _format_date(end.date()),
                "years": round((end - start).days / 365.2425, 4),
                "nominal_years": YOGINI_YEARS[yogini],
                "balance": balance,
                "cycle": cycle,
                "subperiods": _subperiods(yogini, start, end),
            }
        )

    append_period(birth_yogini, current, first_end, balance=True, cycle=1)
    current = first_end
    sequence_start = YOGINI_SEQUENCE.index(birth_yogini)
    sequence = YOGINI_SEQUENCE[sequence_start + 1 :] + YOGINI_SEQUENCE[: sequence_start + 1]
    total_periods = cycles * len(YOGINI_SEQUENCE)
    cycle = 1
    for index in range(total_periods - 1):
        yogini = sequence[index % len(sequence)]
        if yogini == birth_yogini and index:
            cycle += 1
        end = _add_years(current, YOGINI_YEARS[yogini])
        append_period(yogini, current, end, balance=False, cycle=cycle)
        current = end

    return {
        "system": "Yogini Dasha",
        "calculation_status": "active",
        "method_source": "Applications of Yogini Dasha for Brilliant Predictions",
        "method": {
            "birth_yogini_formula": "(Moon nakshatra number + 3) mod 8",
            "balance": "Remaining Moon nakshatra arc divided by full nakshatra span, multiplied by birth Yogini years.",
            "subperiods": "Natural Yogini order starting from the major Yogini itself, proportionate to Yogini years.",
            "cycle_years": 36,
            "cycles_generated": cycles,
        },
        "moon_nakshatra": nakshatra,
        "periods": periods,
    }


def _compact_varga_planet(chart_data: dict[str, Any], chart_key: str, planet_code: str) -> dict[str, Any]:
    planet = get_planet_in_varga(chart_data, chart_key, planet_code)
    return {
        "house": planet.get("house"),
        "sign": planet.get("sign"),
        "sign_number": planet.get("sign_number"),
        "dignity": get_planet_dignity(chart_data, planet_code, chart_key),
    }


def _lord_facts(chart_data: dict[str, Any], planet_code: str, category_houses: list[int]) -> dict[str, Any]:
    planet = get_planet(chart_data, planet_code, "d1")
    owned_houses = get_owned_houses(chart_data, planet_code)
    placed_house = planet.get("house")
    connections = sorted(set(owned_houses + ([placed_house] if placed_house else [])))
    return {
        "code": planet_code,
        "name": PLANET_NAMES.get(planet_code, planet_code),
        "d1": {
            "house": placed_house,
            "sign": planet.get("sign"),
            "sign_number": planet.get("sign_number"),
            "dignity": get_planet_dignity(chart_data, planet_code, "d1"),
        },
        "d9": _compact_varga_planet(chart_data, "d9", planet_code),
        "d10": _compact_varga_planet(chart_data, "d10", planet_code),
        "owned_houses": owned_houses,
        "category_house_connections": [house for house in connections if house in category_houses],
        "connected_to_category": any(house in category_houses for house in connections),
    }


def build_yogini_facts(
    chart_data: dict[str, Any],
    category: str = "general",
    category_houses: list[int] | None = None,
    target_date: date | None = None,
) -> dict[str, Any]:
    target_date = target_date or date.today()
    category_houses = category_houses or [2, 6, 10, 11]
    dasha = build_yogini_periods(chart_data)
    if dasha.get("calculation_status") != "active":
        return {
            **dasha,
            "category": category,
            "current_yogini_dasha": {},
            "current_yogini_subperiod": {},
            "yogini_lord_facts": [],
            "findings": [],
            "score": 0,
            "status": "not_confirmed",
        }

    current_major = _current_period(dasha["periods"], target_date)
    current_sub = _current_period(current_major.get("subperiods", []), target_date)
    lords = [lord for lord in [current_major.get("lord"), current_sub.get("lord")] if lord]
    lord_facts = [_lord_facts(chart_data, lord, category_houses) for lord in dict.fromkeys(lords)]
    findings = []

    for role, period in [("Yogini Mahadasha", current_major), ("Yogini subperiod", current_sub)]:
        lord = period.get("lord")
        facts = next((item for item in lord_facts if item["code"] == lord), {})
        if facts.get("connected_to_category"):
            findings.append(
                {
                    "factor": role,
                    "finding": f"{period.get('yogini')} lord {facts.get('name')} connects to relevant house(s) {facts.get('category_house_connections')}.",
                    "impact": "Yogini timing supports the question category when other systems agree.",
                    "score": 12 if role == "Yogini Mahadasha" else 8,
                }
            )
        if category in {"career", "job", "business"} and facts.get("d10", {}).get("house") in category_houses:
            findings.append(
                {
                    "factor": f"{role} in D10",
                    "finding": f"{facts.get('name')} is placed in D10 house {facts.get('d10', {}).get('house')}.",
                    "impact": "D10 placement repeats the career/business theme.",
                    "score": 8,
                }
            )

    score = min(100, sum(item["score"] for item in findings))
    return {
        **dasha,
        "category": category,
        "current_yogini_dasha": current_major,
        "current_yogini_subperiod": current_sub,
        "yogini_lord_facts": lord_facts,
        "findings": findings,
        "score": score,
        "status": "supports" if score >= 24 else "mixed" if score else "not_confirmed",
    }

