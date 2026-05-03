from datetime import datetime, timedelta


SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_LORDS = {
    1: ["Ma"],
    2: ["Ve"],
    3: ["Me"],
    4: ["Mo"],
    5: ["Su"],
    6: ["Me"],
    7: ["Ve"],
    8: ["Ma", "Ke"],
    9: ["Ju"],
    10: ["Sa"],
    11: ["Sa", "Ra"],
    12: ["Ju"],
}

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


def _stronger_dual_lord(planets, first_code, second_code):
    first = _planet_by_code(planets, first_code)
    second = _planet_by_code(planets, second_code)
    first_associations = max(0, len(_same_sign_occupants(planets, first.get("sign_number"))) - 1)
    second_associations = max(0, len(_same_sign_occupants(planets, second.get("sign_number"))) - 1)

    if first_associations != second_associations:
        return first if first_associations > second_associations else second

    first_degree = first.get("longitude", 0) % 30
    second_degree = second.get("longitude", 0) % 30
    return first if first_degree >= second_degree else second


def _lord_for_sign(sign_number, planets):
    lords = SIGN_LORDS[sign_number]
    if len(lords) == 1:
        return _planet_by_code(planets, lords[0])

    first = _planet_by_code(planets, lords[0])
    second = _planet_by_code(planets, lords[1])

    if first.get("sign_number") == sign_number and second.get("sign_number") == sign_number:
        return {"code": "both", "sign_number": sign_number, "own_sign_full_years": True}
    if first.get("sign_number") == sign_number:
        return second
    if second.get("sign_number") == sign_number:
        return first
    return _stronger_dual_lord(planets, lords[0], lords[1])


def _period_years(sign_number, planets):
    lord = _lord_for_sign(sign_number, planets)
    if lord.get("own_sign_full_years"):
        return 12

    lord_sign = lord.get("sign_number")
    if lord_sign == sign_number:
        return 12

    direct_count = sign_number in COUNT_DIRECT_SIGNS
    years = _count_inclusive(sign_number, lord_sign, direct_count) - 1
    return max(1, min(12, years))


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
            }
        )
        current = sub_end
    return subperiods


def build_chara_dasha(birth_date, ascendant, planets):
    asc_sign_number = ascendant["sign_number"]
    direct = asc_sign_number in DASHA_DIRECT_LAGNAS
    order = _sign_order(asc_sign_number, direct)
    current = datetime.combine(birth_date, datetime.min.time())
    periods = []

    for sign_number in order:
        years = _period_years(sign_number, planets)
        end = current + timedelta(days=years * 365.2425)
        periods.append(
            {
                "sign_number": sign_number,
                "sign": SIGNS[sign_number - 1],
                "start": current.date().isoformat(),
                "end": end.date().isoformat(),
                "start_display": _format_date(current.date()),
                "end_display": _format_date(end.date()),
                "duration_years": years,
                "subperiods": _subperiods(sign_number, current, end, years),
            }
        )
        current = end

    return {
        "system": "Jaimini Chara Dasha",
        "source": "predicting-through-jaimini-chara-dasha.pdf",
        "uses_seven_karakas": True,
        "order_direction": "direct" if direct else "indirect",
        "periods": periods,
    }
