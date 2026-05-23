from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .vedic_utils import (
    OWN_SIGNS,
    PLANET_NAMES,
    aspected_houses,
    get_owned_houses,
    get_planet,
    get_sarvashtakavarga_points,
    natal_mutual_aspects,
    natal_planet_aspects_on_house,
    transit_context_for_lord,
)


FAST_PLANETS = ["Su", "Me", "Ve", "Ma"]
SLOW_PLANETS = ["Ju", "Sa", "Ra", "Ke"]
WEEKLY_PLANETS = ["Mo"] + FAST_PLANETS + SLOW_PLANETS
MONTHLY_PLANETS = FAST_PLANETS + SLOW_PLANETS
ANNUAL_PLANETS = FAST_PLANETS + SLOW_PLANETS  # Moon excluded; slow planets weighted higher


def _angular_distance(lon1, lon2):
    diff = abs(lon1 - lon2) % 360
    return min(diff, 360 - diff)


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
        if horizon == "weekly":
            return 8
        if horizon == "monthly":
            return 6
        return 4  # annual: fast planets matter less
    # slow planets
    if horizon == "weekly":
        return 5
    if horizon == "monthly":
        return 10
    return 14  # annual: slow planets (Ju/Sa/Ra/Ke) are primary drivers


def _samples_for_horizon(start_date, horizon):
    if horizon == "weekly":
        return [
            datetime.combine(start_date + timedelta(days=offset), datetime.min.time(), tzinfo=ZoneInfo("UTC")).replace(hour=12)
            for offset in range(7)
        ]
    # monthly and annual: single mid-month snapshot
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
                    "natal_longitude": planet.get("longitude"),
                    "owned_houses": get_owned_houses(chart_data, lord),
                }
            )
    return targets


_MUTUAL_ASPECT_BONUS = {"weekly": 3, "monthly": 5, "annual": 8}


def _score_transit_event(chart_data, planet_code, sample_dt, category_houses, dasha_targets, mahadasha_lord, antardasha_lord, horizon, mutual_aspect_pairs=None):
    transit = transit_context_for_lord(chart_data, planet_code, sample_dt)
    transit_house = transit.get("transit_house_from_lagna")
    transit_sign = transit.get("transit_sign_number")
    transit_lon = transit.get("transit_longitude")
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

        # Tier 1: precise conjunction with natal dasha lord (within 5°)
        natal_lon = target.get("natal_longitude")
        if transit_lon is not None and natal_lon is not None and planet_code != target["lord"]:
            dist = _angular_distance(transit_lon, natal_lon)
            if dist <= 5:
                bonus = 22 if target["role"] == "Mahadasha lord" else 16
                score += bonus
                reasons.append(
                    f"Transit conjunct natal {target_name} ({target['role']}, {dist:.1f}° orb)."
                )
                if target.get("house"):
                    activated_houses.add(target["house"])

        # Tier 2: transit in owned house of dasha lord (existing) + owned sign bonus
        if transit_house in target["owned_houses"]:
            score += 10
            activated_houses.update(target["owned_houses"])
            reasons.append(f"Transit passes through a house owned by {target_name}.")
        if transit_sign and transit_sign in OWN_SIGNS.get(target["lord"], set()) and planet_code != target["lord"]:
            score += 8
            reasons.append(f"Transit in sign owned by {target_name} ({target['role']}).")
        if transit_sign and transit_sign == target["sign_number"]:
            score += 6
            reasons.append(f"Transit crosses natal {target_name}'s sign.")
        if transit_house and transit_house == target["house"]:
            score += 6
            reasons.append(f"Transit crosses natal {target_name}'s house.")

    # ── Outbound aspects: transit planet aspects natal houses (50% weight) ────
    if transit_house:
        for asp_house in aspected_houses(planet_code, transit_house):
            if asp_house in category_houses:
                asp_sav = get_sarvashtakavarga_points(chart_data, asp_house)
                asp_score, asp_label = _sav_score(asp_sav)
                score += 7 + asp_score // 2  # 50% weight; SAV halved
                activated_houses.add(asp_house)
                reasons.append(
                    f"{PLANET_NAMES.get(planet_code, planet_code)} aspects house {asp_house} "
                    f"({asp_label}, {asp_sav} pts)."
                )

    # ── Inbound aspects: natal lords that aspect the transit house (50% weight) ─
    if transit_house:
        for asp_code, asp_name in natal_planet_aspects_on_house(chart_data, transit_house):
            if asp_code in {mahadasha_lord, antardasha_lord}:
                bonus = 18 if asp_code == mahadasha_lord else 14
                score += bonus // 2  # 50% weight
                reasons.append(
                    f"Natal {asp_name} ({'MD' if asp_code == mahadasha_lord else 'AD'} lord) "
                    f"aspects transit house {transit_house}."
                )

    # ── Natal mutual aspect axis bonus ────────────────────────────────────────
    if transit_house and mutual_aspect_pairs:
        axis_bonus = _MUTUAL_ASPECT_BONUS.get(horizon, 5)
        cat_set = set(category_houses)
        for pair in mutual_aspect_pairs:
            linked = set(pair["linked_houses"])
            if transit_house not in linked:
                continue
            if not (transit_house in cat_set or linked & cat_set):
                continue
            score += axis_bonus
            activated_houses.update(h for h in linked if h)
            reasons.append(
                f"Transit activates natal {pair['planet_a_name']}–{pair['planet_b_name']} "
                f"mutual aspect axis (houses {pair['house_a']} & {pair['house_b']})."
            )

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
        "reasons": reasons[:6],
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
    if horizon == "weekly":
        planets = WEEKLY_PLANETS
    elif horizon == "annual":
        planets = ANNUAL_PLANETS
    else:
        planets = MONTHLY_PLANETS
    dasha_targets = _dasha_targets(chart_data, mahadasha_lord, antardasha_lord)
    mutual_pairs = natal_mutual_aspects(chart_data)
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
                    mutual_pairs,
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
        "priority_order": [
            "Tier 1: transit conjunct natal Mahadasha/Antardasha lord (within 5°)",
            "Tier 2: transit in sign owned by Mahadasha/Antardasha lord",
            "Mahadasha lord transit",
            "Antardasha lord transit",
            "Moon transit for weekly only",
            "Sun/Mercury/Venus/Mars for weekly and monthly",
            "Jupiter/Saturn/Rahu/Ketu primary for annual",
            "Sarvashtakavarga strength or weakness of transit house",
        ],
        "events": events,
    }
