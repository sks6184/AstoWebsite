from datetime import date, datetime
from typing import Any

from charts.jaimini_confirmation import build_jaimini_confirmation
from charts.divisional_confirmation import evaluate_divisional_confirmation
from charts.planetary_dasha_principles import evaluate_planetary_dasha_pair
from charts.vedic_utils import PLANET_NAMES, get_owned_houses, get_planet, get_planet_dignity
from charts.yogini_event_confirmation import build_event_confirmation
from charts.yogini_reference_frames import build_reference_frames

from .jaimini import build_enhanced_jaimini_facts
from .varga import get_planet_in_varga
from .yogini import build_yogini_facts


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value).date()


def _current_period(periods: list[dict[str, Any]], target_date: date) -> dict[str, Any]:
    for period in periods:
        start = _parse_date(period.get("start"))
        end = _parse_date(period.get("end"))
        if start and end and start <= target_date <= end:
            return period
    return periods[0] if periods else {}


def _compact_dasha_lord(chart_data: dict[str, Any], planet_code: str, category_houses: list[int]) -> dict[str, Any]:
    if not planet_code:
        return {}
    d1_planet = get_planet(chart_data, planet_code, "d1")
    owned_houses = get_owned_houses(chart_data, planet_code)
    connections = sorted(set(owned_houses + ([d1_planet.get("house")] if d1_planet.get("house") else [])))
    return {
        "code": planet_code,
        "name": PLANET_NAMES.get(planet_code, planet_code),
        "d1": {
            "house": d1_planet.get("house"),
            "sign": d1_planet.get("sign"),
            "sign_number": d1_planet.get("sign_number"),
            "nakshatra": d1_planet.get("nakshatra"),
            "jaimini_karaka": d1_planet.get("jaimini_karaka", ""),
            "dignity": get_planet_dignity(chart_data, planet_code, "d1"),
        },
        "d9": _compact_varga_planet(chart_data, "d9", planet_code),
        "d10": _compact_varga_planet(chart_data, "d10", planet_code),
        "owned_houses": owned_houses,
        "category_house_connections": [house for house in connections if house in category_houses],
        "connected_to_category": any(house in category_houses for house in connections),
    }


def _compact_varga_planet(chart_data: dict[str, Any], chart_key: str, planet_code: str) -> dict[str, Any]:
    planet = get_planet_in_varga(chart_data, chart_key, planet_code)
    return {
        "house": planet.get("house"),
        "sign": planet.get("sign"),
        "sign_number": planet.get("sign_number"),
    }


def build_vimshottari_facts(
    chart_data: dict[str, Any],
    category: str = "general",
    category_houses: list[int] | None = None,
    target_date: date | None = None,
) -> dict[str, Any]:
    target_date = target_date or date.today()
    category_houses = category_houses or [2, 6, 10, 11]
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    mahadasha = _current_period(vimshottari.get("periods", []), target_date)
    antardasha = _current_period(mahadasha.get("antardashas", []), target_date)
    lords = [lord for lord in [mahadasha.get("lord"), antardasha.get("lord")] if lord]

    findings = []
    for lord in lords:
        facts = _compact_dasha_lord(chart_data, lord, category_houses)
        if facts.get("connected_to_category"):
            findings.append(
                {
                    "factor": f"{facts['name']} dasha lord",
                    "finding": f"{facts['name']} connects to relevant house(s) {facts['category_house_connections']}.",
                    "impact": "Dasha timing can deliver results connected to the question category.",
                    "score": 7,
                }
            )

    pair_assessment = evaluate_planetary_dasha_pair(
        chart_data, mahadasha.get("lord"), antardasha.get("lord"), category_houses
    )
    divisional_confirmation = evaluate_divisional_confirmation(chart_data, category, category_houses, lords)
    for reason in pair_assessment.get("reasons", []):
        findings.append(
            {
                "factor": "Mahadasha / Antardasha relationship",
                "finding": reason,
                "impact": pair_assessment.get("status"),
                "score": 0,
            }
        )

    score = min(
        100,
        max(
            0,
            sum(item["score"] for item in findings) * 10
            + pair_assessment.get("score", 0)
            + divisional_confirmation.get("score", 0),
        ),
    )
    return {
        "system": "Parashari / Vimshottari",
        "category": category,
        "current_mahadasha": mahadasha,
        "current_antardasha": antardasha,
        "dasha_lord_facts": [
            _compact_dasha_lord(chart_data, lord, category_houses)
            for lord in lords
        ],
        "pair_assessment": pair_assessment,
        "divisional_confirmation": divisional_confirmation,
        "findings": findings,
        "score": score,
        "status": "supports" if score >= 60 else "mixed" if score else "not_confirmed",
    }


def build_jaimini_facts(
    chart_data: dict[str, Any],
    category: str = "general",
    category_houses: list[int] | None = None,
    target_date: date | None = None,
) -> dict[str, Any]:
    target_date = target_date or date.today()
    category_houses = category_houses or [2, 6, 10, 11]
    chara = chart_data.get("jaimini", {}).get("chara_dasha", {})
    major = _current_period(chara.get("periods", []), target_date)
    subperiod = _current_period(major.get("subperiods", []), target_date)
    confirmation = build_jaimini_confirmation(chart_data, category, category_houses, target_date)
    enhanced = build_enhanced_jaimini_facts(chart_data, category, category_houses, major, subperiod)
    karakas = {
        planet.get("jaimini_karaka"): planet
        for planet in chart_data.get("d1", {}).get("planets", [])
        if planet.get("jaimini_karaka") in {"Atmakaraka", "Amatyakaraka"}
    }
    combined_findings = [
        {
            "factor": "Jaimini confirmation",
            "finding": reason,
            "impact": confirmation.get("status"),
            "score": confirmation.get("score", 0),
        }
        for reason in confirmation.get("reasons", [])
    ] + enhanced.get("enhanced_findings", [])
    combined_score = min(100, confirmation.get("score", 0) + enhanced.get("enhanced_score", 0))
    status = "supports" if combined_score >= 60 else "mixed" if combined_score else "not_confirmed"

    return {
        "system": "Jaimini",
        "karakas": {
            "atmakaraka": karakas.get("Atmakaraka", {}),
            "amatyakaraka": karakas.get("Amatyakaraka", {}),
        },
        "current_jaimini_dasha": {
            "mahadasha": major,
            "antardasha": subperiod,
        },
        "findings": combined_findings,
        "score": combined_score,
        "status": status,
        "confirmation": confirmation,
        "calculation_status": enhanced.get("calculation_status"),
        "method_source": enhanced.get("method_source"),
        "karaka_method": enhanced.get("karaka_method", {}),
        "karakamsha": enhanced.get("karakamsha", {}),
        "padas": enhanced.get("padas", {}),
        "arudha_factors": enhanced.get("arudha_factors", {}),
        "dasha_sign_as_lagna": enhanced.get("dasha_sign_as_lagna", {}),
        "jaimini_yogas": enhanced.get("jaimini_yogas", []),
        "navamsha_jaimini_yogas": enhanced.get("navamsha_jaimini_yogas", []),
        "ak_amk_relation": enhanced.get("ak_amk_relation", {}),
        "atmakaraka_dasha_caution": enhanced.get("atmakaraka_dasha_caution", {}),
        "sagittarius_dasha_caution": enhanced.get("sagittarius_dasha_caution", {}),
        "enhanced_score": enhanced.get("enhanced_score", 0),
        "enhanced_status": enhanced.get("enhanced_status"),
    }


def build_dasha_facts(
    chart_data: dict[str, Any],
    category: str = "general",
    category_houses: list[int] | None = None,
    target_date: date | None = None,
) -> dict[str, Any]:
    target_date = target_date or date.today()
    category_houses = category_houses or [2, 6, 10, 11]
    vimshottari = build_vimshottari_facts(chart_data, category, category_houses, target_date)
    jaimini = build_jaimini_facts(chart_data, category, category_houses, target_date)
    yogini = build_yogini_facts(chart_data, category, category_houses, target_date)
    return {
        "parashari_vimshottari": vimshottari,
        "jaimini": jaimini,
        "yogini": yogini,
        "reference_frames": build_reference_frames(chart_data, category, category_houses),
        "event_confirmation": build_event_confirmation(
            vimshottari,
            jaimini,
            yogini,
            yogini.get("divisional_confirmation") or vimshottari.get("divisional_confirmation"),
        ),
    }
