from .sade_sati import build_sade_sati_context
from .vedic_utils import get_planets


MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}
CLASSICAL_PLANETS = {"Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"}


REPORT_CHART_KEYS = ["d1", "d2", "d4", "d7", "d9", "d10", "d20", "d24", "d30"]


def build_chart_report_context(chart, report_language="English"):
    chart_data = chart.chart_data or {}
    planets = get_planets(chart_data, "d1", include_ascendant=True)
    ascendant = chart_data.get("ascendant", {}) or next(
        (planet for planet in planets if planet.get("code") == "Asc"),
        {},
    )
    moon = next((planet for planet in planets if planet.get("code") == "Mo"), {})
    mars = next((planet for planet in planets if planet.get("code") == "Ma"), {})
    rahu = next((planet for planet in planets if planet.get("code") == "Ra"), {})
    ketu = next((planet for planet in planets if planet.get("code") == "Ke"), {})
    kaal_sarpa = _has_kaal_sarpa_dosha(planets, rahu, ketu)
    sade_sati = build_sade_sati_context(chart_data, language=report_language)
    return {
        "birth_details": {
            "name": chart.name,
            "birth_date": chart.birth_date,
            "birth_time": chart.birth_time,
            "birth_place": chart.birth_place,
            "latitude": chart.latitude,
            "longitude": chart.longitude,
            "timezone": chart.timezone,
            "janma_nakshatra": moon.get("nakshatra"),
            "chandra_rashi": moon.get("sign"),
            "lagna": ascendant.get("sign"),
            "lagnesh": ascendant.get("sign_lord"),
            "manglik": bool(mars.get("house") in MANGLIK_HOUSES),
            "manglik_house": mars.get("house"),
            "kaal_sarpa_dosha": kaal_sarpa,
            "sade_sati": sade_sati,
        },
        "sade_sati": sade_sati,
        "calculation": {
            "system": chart_data.get("system"),
            "ayanamsa": chart_data.get("ayanamsa"),
            "calculation_error": chart_data.get("calculation_error"),
            "has_full_chart": bool(chart_data.get("d1")),
        },
        "charts": {
            chart_key: chart_data.get(chart_key)
            for chart_key in REPORT_CHART_KEYS
            if chart_data.get(chart_key)
        },
        "planet_details": planets,
        "ashtakavarga": chart_data.get("ashtakavarga", {}),
        "vimshottari": chart_data.get("dashas", {}).get("vimshottari", {}),
        "jaimini": chart_data.get("jaimini", {}),
        "yogas": chart_data.get("yogas", []),
    }


def _arc_contains(start_longitude, end_longitude, point_longitude):
    start = float(start_longitude) % 360
    end = float(end_longitude) % 360
    point = float(point_longitude) % 360
    distance_end = (end - start) % 360
    distance_point = (point - start) % 360
    return 0 <= distance_point <= distance_end


def _has_kaal_sarpa_dosha(planets, rahu, ketu):
    if not rahu or not ketu:
        return False
    classical = [planet for planet in planets if planet.get("code") in CLASSICAL_PLANETS]
    if len(classical) < len(CLASSICAL_PLANETS):
        return False

    rahu_longitude = rahu.get("longitude")
    ketu_longitude = ketu.get("longitude")
    if rahu_longitude is None or ketu_longitude is None:
        return False

    between_rahu_ketu = [
        _arc_contains(rahu_longitude, ketu_longitude, planet.get("longitude"))
        for planet in classical
    ]
    between_ketu_rahu = [
        _arc_contains(ketu_longitude, rahu_longitude, planet.get("longitude"))
        for planet in classical
    ]
    return all(between_rahu_ketu) or all(between_ketu_rahu)
