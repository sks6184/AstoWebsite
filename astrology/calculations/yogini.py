from datetime import date, datetime
from typing import Any

from charts.vedic_utils import PLANET_NAMES, get_owned_houses, get_planet, get_planet_dignity
from charts.divisional_confirmation import evaluate_divisional_confirmation
from charts.planetary_dasha_principles import evaluate_planetary_dasha_pair
from charts.yogini_baselines import evaluate_yogini_baseline
from charts.yogini_principles import evaluate_yogini_lord
from charts.yogini_snapshot import build_yogini_snapshot_checklist

from .periods import add_years, chart_birth_instant, interval_metadata, resolve_timezone, select_period, split_interval, timing_fields
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


YOGINI_YEAR_DAYS = 365.2425


def _current_period(periods: list[dict[str, Any]], target_date: date) -> dict[str, Any]:
    # [start, end); out-of-range keeps the pre-M1 fallback (last period).
    return select_period(periods, target_date, fallback="last")


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


def _subperiods(major: str, start: datetime, end: datetime, display_zone=None) -> list[dict[str, Any]]:
    display_zone = display_zone or resolve_timezone(None)
    start = start if start.tzinfo else start.replace(tzinfo=display_zone)
    end = end if end.tzinfo else end.replace(tzinfo=display_zone)
    sequence_start = YOGINI_SEQUENCE.index(major)
    sequence = YOGINI_SEQUENCE[sequence_start:] + YOGINI_SEQUENCE[:sequence_start]
    periods = []
    for yogini, (current, sub_end) in zip(sequence, split_interval(start, end, [YOGINI_YEARS[y] for y in sequence])):
        lord = YOGINI_LORDS[yogini]
        periods.append(
            {
                "yogini": yogini,
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                **timing_fields(current, sub_end, display_zone),
                "years": round(YOGINI_YEARS[yogini] * YOGINI_YEARS[major] / 36, 4),
            }
        )
    return periods


def build_yogini_periods(chart_data: dict[str, Any], cycles: int = 4) -> dict[str, Any]:
    birth = chart_birth_instant(chart_data)
    display_zone = resolve_timezone(chart_data.get("timezone"))
    moon = get_planet(chart_data, "Mo", "d1")
    moon_longitude = moon.get("longitude")
    if birth is None or moon_longitude is None:
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
    current = birth
    first_end = add_years(current, first_years, YOGINI_YEAR_DAYS)
    periods = []

    def append_period(yogini: str, start: datetime, end: datetime, balance: bool = False, cycle: int = 1):
        lord = YOGINI_LORDS[yogini]
        periods.append(
            {
                "yogini": yogini,
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                **timing_fields(start, end, display_zone),
                "years": round((end - start).total_seconds() / 86400 / YOGINI_YEAR_DAYS, 4),
                "nominal_years": YOGINI_YEARS[yogini],
                "balance": balance,
                "cycle": cycle,
                # Unchanged in M1: the balance period's subperiods divide the
                # remaining balance only (finding M1-F1, awaiting owner decision).
                "subperiods": _subperiods(yogini, start, end, display_zone),
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
        end = add_years(current, YOGINI_YEARS[yogini], YOGINI_YEAR_DAYS)
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
            "dasha_year_days": YOGINI_YEAR_DAYS,
            "start_reference": "birth instant",
            **interval_metadata(display_zone),
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

    pair_assessment = evaluate_planetary_dasha_pair(
        chart_data, current_major.get("lord"), current_sub.get("lord"), category_houses
    )
    divisional_confirmation = evaluate_divisional_confirmation(chart_data, category, category_houses, lords)
    classical_baseline = evaluate_yogini_baseline(current_major.get("yogini"), current_sub.get("yogini"))
    major_assessment = evaluate_yogini_lord(chart_data, current_major.get("lord"), category, category_houses)
    sub_assessment = evaluate_yogini_lord(chart_data, current_sub.get("lord"), category, category_houses)
    snapshot_checklist = build_yogini_snapshot_checklist(
        current_major.get("yogini"), current_sub.get("yogini"), major_assessment, sub_assessment
    )
    for reason in pair_assessment.get("reasons", []):
        findings.append(
            {
                "factor": "Yogini major / subperiod relationship",
                "finding": reason,
                "impact": pair_assessment.get("status"),
                "score": 0,
            }
        )

    score = min(
        100,
        max(
            0,
            sum(item["score"] for item in findings)
            + pair_assessment.get("score", 0)
            + divisional_confirmation.get("score", 0)
            + classical_baseline.get("score", 0),
        ),
    )
    return {
        **dasha,
        "category": category,
        "current_yogini_dasha": current_major,
        "current_yogini_subperiod": current_sub,
        "yogini_lord_facts": lord_facts,
        "pair_assessment": pair_assessment,
        "divisional_confirmation": divisional_confirmation,
        "classical_baseline": classical_baseline,
        "snapshot_checklist": snapshot_checklist,
        "findings": findings,
        "score": score,
        "status": "supports" if score >= 24 else "mixed" if score else "not_confirmed",
    }
