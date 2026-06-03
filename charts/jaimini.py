from datetime import datetime, timedelta

from astrology.constants import JAIMINI_SIGN_LORD_CODES as SIGN_LORDS
from astrology.constants import SIGNS

DASHA_DIRECT_LAGNAS = {1, 5, 6, 7, 11, 12}
COUNT_DIRECT_SIGNS = {1, 2, 3, 7, 8, 9}


def _format_date(value):
    return value.strftime("%d-%b-%Y")


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


def _subperiods(major_sign_number, start, end, years):
    direct = major_sign_number in DASHA_DIRECT_LAGNAS
    order = _sign_order(major_sign_number, direct)
    order = order[1:] + [major_sign_number]
    current = start
    total_days = (end - start).days
    subperiods = []

    for index, sign_number in enumerate(order):
        sub_end = end if index == len(order) - 1 else current + timedelta(days=total_days / 12)
        subperiods.append(
            {
                "sign_number": sign_number,
                "sign": SIGNS[sign_number - 1],
                "start": current.date().isoformat(),
                "end": sub_end.date().isoformat(),
                "start_display": _format_date(current.date()),
                "end_display": _format_date(sub_end.date()),
                "duration_months": years,
                "order_direction": "direct" if direct else "indirect",
            }
        )
        current = sub_end
    return subperiods


def build_chara_dasha(birth_date, ascendant, planets, cycles=2):
    asc_sign_number = ascendant["sign_number"]
    direct = asc_sign_number in DASHA_DIRECT_LAGNAS
    order = _sign_order(asc_sign_number, direct)
    current = datetime.combine(birth_date, datetime.min.time())
    periods = []

    for cycle in range(1, cycles + 1):
        for sign_number in order:
            calculation = _period_calculation(sign_number, planets)
            years = calculation["duration_years"]
            end = current + timedelta(days=years * 365.2425)
            periods.append(
                {
                    "cycle": cycle,
                    "sign_number": sign_number,
                    "sign": SIGNS[sign_number - 1],
                    "start": current.date().isoformat(),
                    "end": end.date().isoformat(),
                    "start_display": _format_date(current.date()),
                    "end_display": _format_date(end.date()),
                    "duration_years": years,
                    "calculation": calculation,
                    "subperiods": _subperiods(sign_number, current, end, years),
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
        },
        "periods": periods,
    }
