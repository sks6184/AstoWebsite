from .vedic_utils import PLANET_NAMES, get_planets, house_from_sign


CATEGORY_KARAKAS = {
    "job": {"Atmakaraka", "Amatyakaraka"},
    "career": {"Atmakaraka", "Amatyakaraka"},
    "education": {"Atmakaraka", "Amatyakaraka", "Putrakaraka"},
    "money": {"Atmakaraka", "Amatyakaraka"},
    "health": {"Atmakaraka", "Gnatikaraka"},
    "marriage": {"Atmakaraka", "Darakaraka"},
    "children": {"Putrakaraka"},
    "foreign_travel": {"Atmakaraka", "Amatyakaraka"},
    "legal_and_enemies": {"Atmakaraka", "Gnatikaraka"},
    "spirituality": {"Atmakaraka", "Gnatikaraka"},
}

FOREIGN_HOUSES = {3, 7, 9, 12}


def _parse_date(value):
    from datetime import datetime

    return datetime.fromisoformat(value).date()


def _current_period(periods, target_date):
    for period in periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start <= target_date <= end:
            return period
    return periods[0] if periods else {}


def _karaka_planets(chart_data, category):
    wanted = CATEGORY_KARAKAS.get(category, {"Atmakaraka", "Amatyakaraka"})
    planets = []
    for planet in get_planets(chart_data, "d1"):
        if planet.get("jaimini_karaka") in wanted:
            planets.append(
                {
                    "code": planet.get("code"),
                    "name": planet.get("name") or PLANET_NAMES.get(planet.get("code"), planet.get("code")),
                    "karaka": planet.get("jaimini_karaka"),
                    "house": planet.get("house"),
                    "sign": planet.get("sign"),
                    "sign_number": planet.get("sign_number"),
                }
            )
    return planets


def _planets_in_sign(chart_data, sign_number):
    if not sign_number:
        return []
    return [
        {
            "code": planet.get("code"),
            "name": planet.get("name") or PLANET_NAMES.get(planet.get("code"), planet.get("code")),
            "karaka": planet.get("jaimini_karaka"),
            "house": planet.get("house"),
            "sign": planet.get("sign"),
        }
        for planet in get_planets(chart_data, "d1")
        if planet.get("sign_number") == sign_number
    ]


def build_jaimini_confirmation(chart_data, category, category_houses, target_date):
    chara = chart_data.get("jaimini", {}).get("chara_dasha", {})
    major = _current_period(chara.get("periods", []), target_date)
    subperiod = _current_period(major.get("subperiods", []), target_date)
    major_house = house_from_sign(chart_data, major.get("sign_number"))
    subperiod_house = house_from_sign(chart_data, subperiod.get("sign_number"))
    karakas = _karaka_planets(chart_data, category)
    score = 0
    reasons = []
    activated_houses = set()

    for label, period, house, weight in [
        ("Chara Mahadasha", major, major_house, 24),
        ("Chara Antardasha", subperiod, subperiod_house, 16),
    ]:
        if not period:
            continue
        if house:
            activated_houses.add(house)
        if house in category_houses:
            score += weight
            reasons.append(f"{label} sign {period.get('sign')} activates relevant house {house}.")
        elif category == "foreign_travel" and house in FOREIGN_HOUSES:
            score += weight
            reasons.append(f"{label} sign {period.get('sign')} supports foreign-stay houses through house {house}.")

    major_occupants = _planets_in_sign(chart_data, major.get("sign_number"))
    subperiod_occupants = _planets_in_sign(chart_data, subperiod.get("sign_number"))
    relevant_karaka_names = {planet["karaka"] for planet in karakas}
    for period_label, occupants in [("Mahadasha sign", major_occupants), ("Antardasha sign", subperiod_occupants)]:
        for planet in occupants:
            if planet.get("karaka") in relevant_karaka_names:
                score += 12
                reasons.append(
                    f"{period_label} contains {planet.get('name')} as {planet.get('karaka')}, supporting this topic."
                )

    for planet in karakas:
        if planet.get("house"):
            activated_houses.add(planet["house"])
        if planet.get("house") in category_houses:
            score += 14
            reasons.append(f"{planet['karaka']} {planet['name']} is placed in relevant house {planet['house']}.")
        elif category == "foreign_travel" and planet.get("house") in FOREIGN_HOUSES:
            score += 14
            reasons.append(f"{planet['karaka']} {planet['name']} connects with foreign-stay house {planet['house']}.")

    if category == "foreign_travel":
        for node_code in ["Ra", "Ke"]:
            node = next((planet for planet in get_planets(chart_data, "d1") if planet.get("code") == node_code), {})
            if node.get("house") in FOREIGN_HOUSES:
                score += 10
                activated_houses.add(node["house"])
                reasons.append(f"{PLANET_NAMES[node_code]} is placed in foreign-stay house {node['house']}.")

    if score >= 45:
        status = "supports"
        confidence_delta = "+medium"
    elif score >= 24:
        status = "mixed"
        confidence_delta = "neutral"
    elif score > 0:
        status = "weak"
        confidence_delta = "reduce"
    else:
        status = "not_confirmed"
        confidence_delta = "reduce"
        reasons.append("Jaimini factors do not strongly repeat the same topic in the current Chara Dasha.")

    return {
        "system": chara.get("system"),
        "source": chara.get("source"),
        "status": status,
        "score": score,
        "confidence_delta": confidence_delta,
        "active_chara_dasha": {
            "mahadasha": major,
            "antardasha": subperiod,
            "mahadasha_house_from_lagna": major_house,
            "antardasha_house_from_lagna": subperiod_house,
        },
        "relevant_karakas": karakas,
        "mahadasha_sign_occupants": major_occupants,
        "antardasha_sign_occupants": subperiod_occupants,
        "activated_houses": sorted(house for house in activated_houses if house),
        "reasons": reasons[:7],
    }
