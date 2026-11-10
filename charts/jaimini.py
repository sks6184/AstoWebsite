from datetime import datetime

from astrology.calculations.periods import add_years, birth_instant, interval_metadata, resolve_timezone, split_interval, timing_fields
from astrology.constants import JAIMINI_SIGN_LORD_CODES as SIGN_LORDS
from astrology.constants import SIGNS

CHARA_YEAR_DAYS = 365.2425

DASHA_DIRECT_LAGNAS = {1, 5, 6, 7, 11, 12}
COUNT_DIRECT_SIGNS = {1, 2, 3, 7, 8, 9}


def _sign_order(start_sign_number, direct):
    if direct:
        return [((start_sign_number - 1 + index) % 12) + 1 for index in range(12)]
    return [((start_sign_number - 1 - index) % 12) + 1 for index in range(12)]


def _count_inclusive(start_sign_number, end_sign_number, direct):
    if direct:
        return ((end_sign_number - start_sign_number) % 12) + 1
    return ((start_sign_number - end_sign_number) % 12) + 1


def _planet_by_code(planets, code):
    for planet in planets:
        if planet.get("code") == code:
            return planet
    return {}


def _same_sign_occupants(planets, sign_number):
    return [planet for planet in planets if planet.get("sign_number") == sign_number]


def _stronger_dual_lord_details(planets, first_code, second_code):
    first = _planet_by_code(planets, first_code)
    second = _planet_by_code(planets, second_code)
    first_associations = max(0, len(_same_sign_occupants(planets, first.get("sign_number"))) - 1)
    second_associations = max(0, len(_same_sign_occupants(planets, second.get("sign_number"))) - 1)

    if first_associations != second_associations:
        return (
            first if first_associations > second_associations else second,
            "more_associations",
        )

    first_degree = first.get("longitude", 0) % 30
    second_degree = second.get("longitude", 0) % 30
    return (
        first if first_degree >= second_degree else second,
        "higher_degree_within_sign",
    )


def _lord_for_sign_details(sign_number, planets):
    lords = SIGN_LORDS[sign_number]
    if len(lords) == 1:
        return _planet_by_code(planets, lords[0]), "single_lord"

    first = _planet_by_code(planets, lords[0])
    second = _planet_by_code(planets, lords[1])

    if first.get("sign_number") == sign_number and second.get("sign_number") == sign_number:
        return (
            {"code": "both", "sign_number": sign_number, "own_sign_full_years": True},
            "both_dual_lords_in_own_sign",
        )
    if first.get("sign_number") == sign_number:
        return second, "ignore_dual_lord_in_own_sign"
    if second.get("sign_number") == sign_number:
        return first, "ignore_dual_lord_in_own_sign"
    lord, strength_rule = _stronger_dual_lord_details(planets, lords[0], lords[1])
    return lord, f"stronger_dual_lord_by_{strength_rule}"


def _lord_for_sign(sign_number, planets):
    lord, _ = _lord_for_sign_details(sign_number, planets)
    return lord


def _period_calculation(sign_number, planets):
    lord, selection_rule = _lord_for_sign_details(sign_number, planets)
    count_direction = "direct" if sign_number in COUNT_DIRECT_SIGNS else "indirect"
    calculation = {
        "selected_lord": lord.get("code"),
        "lord_selection_rule": selection_rule,
        "count_direction": count_direction,
        "gross_count": 12,
        "deduction_years": 0,
        "duration_years": 12,
    }
    if lord.get("own_sign_full_years") or lord.get("sign_number") == sign_number:
        return calculation

    gross_count = _count_inclusive(
        sign_number,
        lord.get("sign_number"),
        sign_number in COUNT_DIRECT_SIGNS,
    )
    calculation.update(
        {
            "gross_count": gross_count,
            "deduction_years": 1,
            "duration_years": max(1, min(12, gross_count - 1)),
        }
    )
    return calculation


def _period_years(sign_number, planets):
    return _period_calculation(sign_number, planets)["duration_years"]


def _subperiods(major_sign_number, start, end, years, display_zone=None):
    display_zone = display_zone or resolve_timezone(None)
    start = start if start.tzinfo else start.replace(tzinfo=display_zone)
    end = end if end.tzinfo else end.replace(tzinfo=display_zone)
    direct = major_sign_number in DASHA_DIRECT_LAGNAS
    order = _sign_order(major_sign_number, direct)
    order = order[1:] + [major_sign_number]
    subperiods = []

    for sign_number, (current, sub_end) in zip(order, split_interval(start, end, [1] * len(order))):
        subperiods.append(
            {
                "sign_number": sign_number,
                "sign": SIGNS[sign_number - 1],
                **timing_fields(current, sub_end, display_zone),
                "duration_months": years,
                "order_direction": "direct" if direct else "indirect",
            }
        )
    return subperiods


def build_chara_dasha(birth, ascendant, planets, cycles=2, timezone_name=None):
    """Chara dasha from the birth instant (``birth`` may be an aware datetime or a date)."""
    display_zone = resolve_timezone(timezone_name)
    asc_sign_number = ascendant["sign_number"]
    direct = asc_sign_number in DASHA_DIRECT_LAGNAS
    order = _sign_order(asc_sign_number, direct)
    current = birth_instant(birth, timezone_name)
    periods = []

    for cycle in range(1, cycles + 1):
        for sign_number in order:
            calculation = _period_calculation(sign_number, planets)
            years = calculation["duration_years"]
            end = add_years(current, years, CHARA_YEAR_DAYS)
            periods.append(
                {
                    "cycle": cycle,
                    "sign_number": sign_number,
                    "sign": SIGNS[sign_number - 1],
                    **timing_fields(current, end, display_zone),
                    "duration_years": years,
                    "calculation": calculation,
                    "subperiods": _subperiods(sign_number, current, end, years, display_zone),
                }
            )
            current = end

    return {
        "system": "Jaimini Chara Dasha",
        "source": "predicting-through-jaimini-chara-dasha.pdf",
        "uses_seven_karakas": True,
        "order_direction": "direct" if direct else "indirect",
        "cycles_generated": cycles,
        "method": {
            "major_order": "Based on the ascendant group.",
            "period_length_count": "Count from each sign to its selected lord, then deduct one year.",
            "subperiod_order": "Use the major sign group and place the major sign itself last.",
            "repeat_rule": "Repeat the same twelve-sign sequence when a second cycle is needed.",
            "school": "K.N. Rao (declared source: Predicting Through Jaimini's Chara Dasha); no independent reference yet: UNVERIFIED",
            "dasha_year_days": CHARA_YEAR_DAYS,
            "start_reference": "birth instant" if isinstance(birth, datetime) else "local midnight of the birth date",
            **interval_metadata(display_zone),
        },
        "periods": periods,
    }
