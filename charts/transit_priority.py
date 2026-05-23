from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .vedic_utils import (
    PLANET_NAMES,
    get_owned_houses,
    get_planet,
    transit_context_for_lord,
)


FAST_PLANETS = ["Su", "Me", "Ve", "Ma"]
SLOW_PLANETS = ["Ju", "Sa", "Ra", "Ke"]
WEEKLY_PLANETS = ["Mo"] + FAST_PLANETS + SLOW_PLANETS
MONTHLY_PLANETS = FAST_PLANETS + SLOW_PLANETS


def _sav_score(points):
    if points > 28:
        return 12, "strong Sarvashtakavarga support"
    if points >= 25:
        return 5, "moderate Sarvashtakavarga support"
    if points >= 22:
        return -4, "low Sarvashtakavarga support"
    return -12, "very low Sarvashtakavarga support"


def _planet_speed_weight(planet_code, horizon):
    if planet_code == "Mo":
        return 10 if horizon == "weekly" else 0
    if planet_code in FAST_PLANETS:
        return 8 if horizon == "weekly" else 6
    return 5 if horizon == "weekly" else 10


def _samples_for_horizon(start_date, horizon):
    if horizon == "weekly":
        return [
            datetime.combine(start_date + timedelta(days=offset), datetime.min.time(), tzinfo=ZoneInfo("UTC")).replace(hour=12)
            for offset in range(7)
        ]
    return [datetime(start_date.year, start_date.month, 15, 12, tzinfo=ZoneInfo("UTC"))]


def _sample_label(sample_dt, horizon):
    if horizon == "weekly":
        return sample_dt.date().isoformat()
    return sample_dt.strftime("%B %Y")


def _role_weight(planet_code, mahadasha_lord, antardasha_lord):
    if planet_code == mahadasha_lord:
        return 40, "Mahadasha lord"
    if planet_code == antardasha_lord:
        return 32, "Antardasha lord"
    return 0, ""


def _dasha_targets(chart_data, mahadasha_lord, antardasha_lord):
    targets = []
    for role, lord in [("Mahadasha lord", mahadasha_lord), ("Antardasha lord", antardasha_lord)]:
        planet = get_planet(chart_data, lord) if lord else {}
        if planet:
            targets.append(
                {
                    "role": role,
                    "lord": lord,
                    "lord_name": PLANET_NAMES.get(lord, lord),
                    "house": planet.get("house"),
                    "sign_number": planet.get("sign_number"),
                    "owned_houses": get_owned_houses(chart_data, lord),
                }
            )
    return targets


def _score_transit_event(chart_data, planet_code, sample_dt, category_houses, dasha_targets, mahadasha_lord, antardasha_lord, horizon):
    transit = transit_context_for_lord(chart_data, planet_code, sample_dt)
    transit_house = transit.get("transit_house_from_lagna")
    transit_sign = transit.get("transit_sign_number")
    score = _planet_speed_weight(planet_code, horizon)
    reasons = []
    activated_houses = set()

    role_score, role = _role_weight(planet_code, mahadasha_lord, antardasha_lord)
    if role_score:
        score += role_score
        reasons.append(f"{PLANET_NAMES.get(planet_code, planet_code)} is the active {role}.")
        activated_houses.update(transit.get("owned_houses", []))
        if transit.get("natal_placed_house"):
            activated_houses.add(transit.get("natal_placed_house"))

    if transit_house:
        activated_houses.add(transit_house)

    if transit_house in category_houses:
        score += 14
        reasons.append(f"Transit activates relevant house {transit_house}.")

    sav_points = transit.get("sarvashtakavarga_points", 0)
    sav_delta, sav_label = _sav_score(sav_points)
    score += sav_delta
    reasons.append(f"Transit house has {sav_label} ({sav_points}).")

    for target in dasha_targets:
        target_name = target["lord_name"]
        if transit_house in target["owned_houses"]:
            score += 10
            activated_houses.update(target["owned_houses"])
            reasons.append(f"Transit passes through a house owned by {target_name}.")
        if transit_sign and transit_sign == target["sign_number"]:
            score += 10
            reasons.append(f"Transit crosses natal {target_name}'s sign.")
        if transit_house and transit_house == target["house"]:
            score += 8
            reasons.append(f"Transit crosses natal {target_name}'s house.")

    return {
        "planet": planet_code,
        "planet_name": PLANET_NAMES.get(planet_code, planet_code),
        "date": sample_dt.date().isoformat(),
        "label": _sample_label(sample_dt, horizon),
        "horizon": horizon,
        "score": score,
        "tone": "supportive" if score >= 25 else "challenging" if score < 0 else "mixed",
        "transit_sign": transit.get("transit_sign"),
        "transit_sign_number": transit.get("transit_sign_number"),
        "transit_house": transit_house,
        "sarvashtakavarga_points": sav_points,
        "activated_houses": sorted(house for house in activated_houses if house),
        "is_mahadasha_lord": planet_code == mahadasha_lord,
        "is_antardasha_lord": planet_code == antardasha_lord,
        "reasons": reasons[:5],
    }


def build_transit_priority_context(
    chart_data,
    category_houses,
    start_date,
    mahadasha_lord=None,
    antardasha_lord=None,
    horizon="monthly",
    cap=12,
):
    planets = WEEKLY_PLANETS if horizon == "weekly" else MONTHLY_PLANETS
    dasha_targets = _dasha_targets(chart_data, mahadasha_lord, antardasha_lord)
    events = []

    for planet_code in planets:
        for sample_dt in _samples_for_horizon(start_date, horizon):
            events.append(
                _score_transit_event(
                    chart_data,
                    planet_code,
                    sample_dt,
                    category_houses,
                    dasha_targets,
                    mahadasha_lord,
                    antardasha_lord,
                    horizon,
                )
            )

    if horizon == "weekly":
        deduped = {}
        for event in sorted(events, key=lambda item: abs(item["score"]), reverse=True):
            key = (event["planet"], event["transit_house"], event["tone"])
            deduped.setdefault(key, event)
        events = list(deduped.values())

    events = sorted(events, key=lambda item: abs(item["score"]), reverse=True)[:cap]
    return {
        "horizon": horizon,
        "moon_included": horizon == "weekly",
        "monthly_moon_excluded": horizon == "monthly",
        "priority_order": [
            "Mahadasha lord transit",
            "Antardasha lord transit",
            "Moon transit for weekly only",
            "Sun/Mercury/Venus/Mars",
            "Jupiter/Saturn/Rahu/Ketu background",
            "Sarvashtakavarga strength or weakness of transit house",
        ],
        "events": events,
    }
