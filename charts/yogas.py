from .vedic_utils import (
    BENEFIC_PLANETS,
    DUSTHANA_HOUSES,
    KENDRA_HOUSES,
    MALEFIC_PLANETS,
    PLANET_NAMES,
    TRIKONA_HOUSES,
    are_conjunct,
    get_house_lord,
    get_house_lord_planet,
    get_owned_houses,
    get_planet,
    get_planets,
    get_planets_in_house,
    house_distance,
    houses_from_planet,
    is_exalted,
    is_own_sign,
)


YOGA_MEANINGS = {
    "Ruchaka Yoga": "Courage, energy, initiative, command, and leadership capacity.",
    "Bhadra Yoga": "Intelligence, speech, learning, strategy, and communication ability.",
    "Hamsa Yoga": "Wisdom, dharma, guidance, virtues, and spiritual inclination.",
    "Malavya Yoga": "Comforts, refinement, art, relationships, luxury, and aesthetic gifts.",
    "Sasa Yoga": "Authority, endurance, administration, public influence, and discipline.",
    "Gajakesari Yoga": "Intelligence, respect, prosperity, grace, and support from wisdom or counsel.",
    "Budhaditya Yoga": "Sharp intellect, skill, analysis, communication, and administrative success.",
    "Chandra-Mangala Yoga": "Commercial instinct, earning capacity, initiative, and active mind.",
    "Sunapha Yoga": "Self-earned progress, initiative, and capacity to build resources.",
    "Anapha Yoga": "Composure, dignity, restraint, and support through personal discipline.",
    "Durudhara Yoga": "Support on both sides of the mind, bringing stability and resources.",
    "Kemadruma Yoga": "Austere or unsupported phases of life; requires conscious emotional steadiness.",
    "Shakata Yoga": "Fluctuating fortune and periodic rise-fall patterns requiring patience.",
    "Vipareeta Raja Yoga": "Growth through challenge, hidden strength, and reversal of difficult conditions.",
    "Harsha Yoga": "Ability to overcome enemies, disease, competition, and daily struggles.",
    "Sarala Yoga": "Capacity to face sudden changes, obstacles, and hidden matters with resilience.",
    "Vimala Yoga": "Self-control, frugality, inner discipline, and strength through simplicity.",
    "Parivartana Yoga": "Mutual exchange between house lords, strongly linking two life areas.",
    "Dhana Yoga": "Wealth potential through connections among wealth, fortune, intelligence, and gains houses.",
    "Lakshmi Yoga": "Prosperity and grace through strength of Lagna and fortune factors.",
    "Dharma Karma Adhipati Yoga": "Connection between fortune and career, supporting purposeful action.",
    "Raja Sambandha Yoga": "Connection of Lagna with fortune or karma houses, supporting status and rise.",
    "Saraswati Yoga": "Learning, refinement, speech, arts, knowledge, and intellectual gifts.",
    "Mala Yoga": "Benefics in kendras, supporting protection, grace, and smoother progress.",
}


def _result(name, category, evidence, strength="moderate"):
    return {
        "name": name,
        "category": category,
        "strength": strength,
        "evidence": evidence,
        "meaning": YOGA_MEANINGS[name],
    }


def _planet_label(chart_data, code):
    planet = get_planet(chart_data, code)
    return f"{PLANET_NAMES.get(code, code)} in {planet.get('sign')} / house {planet.get('house')}"


def _add_pancha_mahapurusha(chart_data, yogas):
    definitions = {
        "Ma": "Ruchaka Yoga",
        "Me": "Bhadra Yoga",
        "Ju": "Hamsa Yoga",
        "Ve": "Malavya Yoga",
        "Sa": "Sasa Yoga",
    }
    for code, name in definitions.items():
        planet = get_planet(chart_data, code)
        if (
            planet
            and planet.get("house") in KENDRA_HOUSES
            and (is_own_sign(code, planet.get("sign_number")) or is_exalted(code, planet.get("sign_number")))
        ):
            dignity = "exalted" if is_exalted(code, planet.get("sign_number")) else "own sign"
            yogas.append(
                _result(
                    name,
                    "Pancha Mahapurusha",
                    [f"{PLANET_NAMES[code]} is in a kendra and {dignity}: {_planet_label(chart_data, code)}."],
                    "strong",
                )
            )


def _add_moon_yogas(chart_data, yogas):
    moon = get_planet(chart_data, "Mo")
    if not moon:
        return

    if houses_from_planet(chart_data, "Mo", "Ju") in KENDRA_HOUSES:
        yogas.append(
            _result(
                "Gajakesari Yoga",
                "Moon/Raja",
                [f"Jupiter is {houses_from_planet(chart_data, 'Mo', 'Ju')} houses from Moon."],
                "strong",
            )
        )

    if houses_from_planet(chart_data, "Mo", "Ju") in {6, 8}:
        yogas.append(
            _result(
                "Shakata Yoga",
                "Moon",
                [f"Jupiter is {houses_from_planet(chart_data, 'Mo', 'Ju')} houses from Moon."],
                "moderate",
            )
        )

    if are_conjunct(chart_data, "Mo", "Ma"):
        yogas.append(_result("Chandra-Mangala Yoga", "Dhana", ["Moon and Mars are conjunct."]))

    second_house = ((moon.get("house") or 1) % 12) + 1
    twelfth_house = ((moon.get("house") or 1) - 2) % 12 + 1
    second_planets = [p for p in get_planets_in_house(chart_data, second_house) if p.get("code") != "Su"]
    twelfth_planets = [p for p in get_planets_in_house(chart_data, twelfth_house) if p.get("code") != "Su"]

    if second_planets:
        yogas.append(
            _result(
                "Sunapha Yoga",
                "Moon",
                [f"Planet(s) in 2nd from Moon: {', '.join(p['name'] for p in second_planets)}."],
            )
        )
    if twelfth_planets:
        yogas.append(
            _result(
                "Anapha Yoga",
                "Moon",
                [f"Planet(s) in 12th from Moon: {', '.join(p['name'] for p in twelfth_planets)}."],
            )
        )
    if second_planets and twelfth_planets:
        yogas.append(_result("Durudhara Yoga", "Moon", ["Planets are present on both sides of Moon."], "strong"))
    if not second_planets and not twelfth_planets:
        yogas.append(_result("Kemadruma Yoga", "Moon", ["No planet is placed in 2nd or 12th from Moon."], "moderate"))


def _add_conjunction_yogas(chart_data, yogas):
    if are_conjunct(chart_data, "Su", "Me"):
        yogas.append(_result("Budhaditya Yoga", "Raja/Dhana", ["Sun and Mercury are conjunct."]))

    benefics = ["Ju", "Ve", "Me"]
    if all(get_planet(chart_data, code).get("house") in (KENDRA_HOUSES | TRIKONA_HOUSES) for code in benefics):
        yogas.append(
            _result(
                "Saraswati Yoga",
                "Learning",
                ["Jupiter, Venus, and Mercury are in kendras/trikonas."],
                "strong",
            )
        )

    benefic_kendras = [p for p in get_planets(chart_data) if p.get("code") in BENEFIC_PLANETS and p.get("house") in KENDRA_HOUSES]
    if len({p.get("house") for p in benefic_kendras}) >= 3:
        yogas.append(_result("Mala Yoga", "Auspicious", ["Benefics occupy three kendras."], "strong"))


def _add_lordship_yogas(chart_data, yogas):
    wealth_lords = {get_house_lord(chart_data, house) for house in [2, 5, 9, 11]}
    for first in wealth_lords:
        for second in wealth_lords:
            if first and second and first < second and are_conjunct(chart_data, first, second):
                yogas.append(
                    _result(
                        "Dhana Yoga",
                        "Dhana",
                        [f"{PLANET_NAMES[first]} and {PLANET_NAMES[second]} connect wealth houses by conjunction."],
                    )
                )
                break
        else:
            continue
        break

    lagna_lord = get_house_lord(chart_data, 1)
    ninth_lord = get_house_lord(chart_data, 9)
    tenth_lord = get_house_lord(chart_data, 10)

    lagna_lord_planet = get_planet(chart_data, lagna_lord)
    ninth_lord_planet = get_planet(chart_data, ninth_lord)
    if lagna_lord_planet.get("house") in KENDRA_HOUSES and ninth_lord_planet and (
        is_own_sign(ninth_lord, ninth_lord_planet.get("sign_number"))
        or is_exalted(ninth_lord, ninth_lord_planet.get("sign_number"))
        or ninth_lord_planet.get("house") in KENDRA_HOUSES
    ):
        yogas.append(
            _result(
                "Lakshmi Yoga",
                "Dhana",
                ["Lagna lord is in a kendra and 9th lord has supportive strength/placement."],
                "strong",
            )
        )

    if ninth_lord and tenth_lord and are_conjunct(chart_data, ninth_lord, tenth_lord):
        yogas.append(
            _result(
                "Dharma Karma Adhipati Yoga",
                "Raja",
                ["9th lord and 10th lord are conjunct."],
                "strong",
            )
        )

    for lord in [ninth_lord, tenth_lord]:
        if lagna_lord and lord and are_conjunct(chart_data, lagna_lord, lord):
            yogas.append(
                _result(
                    "Raja Sambandha Yoga",
                    "Raja",
                    [f"Lagna lord connects with {PLANET_NAMES[lord]}, lord of 9th/10th."],
                    "strong",
                )
            )
            break

    for first_house in range(1, 13):
        first_lord = get_house_lord(chart_data, first_house)
        first_planet = get_planet(chart_data, first_lord)
        if not first_lord or not first_planet:
            continue
        target_house = first_planet.get("house")
        second_lord = get_house_lord(chart_data, target_house)
        second_planet = get_planet(chart_data, second_lord)
        if second_planet.get("house") == first_house and first_house < target_house:
            yogas.append(
                _result(
                    "Parivartana Yoga",
                    "Exchange",
                    [f"Lords of houses {first_house} and {target_house} exchange signs."],
                    "strong",
                )
            )


def _add_vipareeta_yogas(chart_data, yogas):
    dusthana_lords = {
        6: ("Harsha Yoga", get_house_lord_planet(chart_data, 6)),
        8: ("Sarala Yoga", get_house_lord_planet(chart_data, 8)),
        12: ("Vimala Yoga", get_house_lord_planet(chart_data, 12)),
    }
    present = []
    for house, (name, planet) in dusthana_lords.items():
        if planet.get("house") in DUSTHANA_HOUSES:
            yogas.append(
                _result(
                    name,
                    "Vipareeta",
                    [f"Lord of {house}th house is placed in dusthana house {planet.get('house')}."],
                )
            )
            present.append(name)
    if present:
        yogas.append(_result("Vipareeta Raja Yoga", "Vipareeta", [f"Present forms: {', '.join(present)}."], "strong"))


def detect_yogas(chart_data):
    if not chart_data.get("d1"):
        return []

    yogas = []
    _add_pancha_mahapurusha(chart_data, yogas)
    _add_moon_yogas(chart_data, yogas)
    _add_conjunction_yogas(chart_data, yogas)
    _add_lordship_yogas(chart_data, yogas)
    _add_vipareeta_yogas(chart_data, yogas)

    unique = {}
    for yoga in yogas:
        unique.setdefault(yoga["name"], yoga)
    return sorted(unique.values(), key=lambda item: (item["category"], item["name"]))
