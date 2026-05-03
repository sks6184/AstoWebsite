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

PLANET_CODES = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]

BENEFIC_HOUSES = {
    "Su": {
        "Su": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mo": [3, 6, 10, 11],
        "Ma": [1, 2, 4, 7, 8, 9, 10, 11],
        "Me": [3, 5, 6, 9, 10, 11, 12],
        "Ju": [5, 6, 9, 11],
        "Ve": [6, 7, 12],
        "Sa": [1, 2, 4, 7, 8, 9, 10, 11],
        "Asc": [3, 4, 6, 10, 11, 12],
    },
    "Mo": {
        "Su": [3, 6, 7, 8, 10, 11],
        "Mo": [1, 3, 6, 7, 10, 11],
        "Ma": [2, 3, 5, 6, 9, 10, 11],
        "Me": [1, 3, 4, 5, 7, 8, 10, 11],
        "Ju": [1, 4, 7, 8, 10, 11, 12],
        "Ve": [3, 4, 5, 7, 9, 10, 11],
        "Sa": [3, 5, 6, 11],
        "Asc": [3, 6, 10, 11],
    },
    "Ma": {
        "Su": [3, 5, 6, 10, 11],
        "Mo": [3, 6, 11],
        "Ma": [1, 2, 4, 7, 8, 10, 11],
        "Me": [3, 5, 6, 11],
        "Ju": [6, 10, 11, 12],
        "Ve": [6, 8, 11, 12],
        "Sa": [1, 4, 7, 8, 9, 10, 11],
        "Asc": [1, 3, 6, 10, 11],
    },
    "Me": {
        "Su": [5, 6, 9, 11, 12],
        "Mo": [2, 4, 6, 8, 10, 11],
        "Ma": [1, 2, 4, 7, 8, 9, 10, 11],
        "Me": [1, 3, 5, 6, 9, 10, 11, 12],
        "Ju": [6, 8, 11, 12],
        "Ve": [1, 2, 3, 4, 5, 8, 9, 11],
        "Sa": [1, 2, 4, 7, 8, 9, 10, 11],
        "Asc": [1, 2, 4, 6, 8, 10, 11],
    },
    "Ju": {
        "Su": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Mo": [2, 5, 7, 9, 11],
        "Ma": [1, 2, 4, 7, 8, 10, 11],
        "Me": [1, 2, 4, 5, 6, 9, 10, 11],
        "Ju": [1, 2, 3, 4, 7, 8, 10, 11],
        "Ve": [2, 5, 6, 9, 10, 11],
        "Sa": [3, 5, 6, 12],
        "Asc": [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "Ve": {
        "Su": [8, 11, 12],
        "Mo": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Ma": [3, 5, 6, 9, 11, 12],
        "Me": [3, 5, 6, 9, 11],
        "Ju": [5, 8, 9, 10, 11],
        "Ve": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Sa": [3, 4, 5, 8, 9, 10, 11],
        "Asc": [1, 2, 3, 4, 5, 8, 9, 11],
    },
    "Sa": {
        "Su": [1, 2, 4, 7, 8, 10, 11],
        "Mo": [3, 6, 11],
        "Ma": [3, 5, 6, 10, 11, 12],
        "Me": [6, 8, 9, 10, 11, 12],
        "Ju": [5, 6, 11, 12],
        "Ve": [6, 11, 12],
        "Sa": [3, 5, 6, 11],
        "Asc": [1, 3, 4, 6, 10, 11],
    },
}

EXPECTED_TOTALS = {
    "Su": 48,
    "Mo": 49,
    "Ma": 39,
    "Me": 54,
    "Ju": 56,
    "Ve": 52,
    "Sa": 39,
}


def _empty_scores():
    return [0 for _ in range(12)]


def build_ashtakavarga(ascendant, planets):
    reference_signs = {"Asc": ascendant["sign_number"] - 1}
    for planet in planets:
        if planet["code"] in PLANET_CODES:
            reference_signs[planet["code"]] = planet["sign_number"] - 1

    bhinna = {}
    for target_code, contributor_rules in BENEFIC_HOUSES.items():
        scores = _empty_scores()
        for contributor_code, houses in contributor_rules.items():
            reference_sign = reference_signs[contributor_code]
            for house in houses:
                scores[(reference_sign + house - 1) % 12] += 1
        bhinna[target_code] = {
            "scores": scores,
            "total": sum(scores),
            "expected_total": EXPECTED_TOTALS[target_code],
            "valid": sum(scores) == EXPECTED_TOTALS[target_code],
        }

    sarva_scores = [
        sum(bhinna[planet_code]["scores"][sign_index] for planet_code in PLANET_CODES)
        for sign_index in range(12)
    ]
    rows = []
    asc_sign_index = ascendant["sign_number"] - 1
    for sign_index, sign in enumerate(SIGNS):
        rows.append(
            {
                "sign": sign,
                "house": ((sign_index - asc_sign_index) % 12) + 1,
                "scores": {planet_code: bhinna[planet_code]["scores"][sign_index] for planet_code in PLANET_CODES},
                "sarva": sarva_scores[sign_index],
            }
        )

    return {
        "system": "Bhinna and Sarva Ashtakavarga",
        "planet_codes": PLANET_CODES,
        "bhinna": bhinna,
        "sarva": {"scores": sarva_scores, "total": sum(sarva_scores), "valid": sum(sarva_scores) == 337},
        "rows": rows,
    }
