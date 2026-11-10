"""Deterministic evidence cards for final answer synthesis."""

from typing import Any

from chat.prediction_context import CATEGORY_RULES
from astrology.constants import PLANET_NAMES


HOUSE_MEANINGS = {
    "foreign_travel": {
        3: "short journeys and movement",
        4: "home, homeland, residence, and return-to-base questions",
        7: "foreign/public-facing movement",
        9: "long-distance travel and fortune",
        12: "foreign stay, distance, and expenditure",
    },
    "vehicle": {
        2: "assets and purchase resources",
        4: "vehicles, comforts, and conveyance happiness",
        6: "loan, EMI, service, or repair burden",
        9: "fortune and support",
        11: "gains and fulfilment",
        12: "expense/outflow for purchase",
    },
}


def _window_label(window: dict[str, Any]) -> str:
    return (
        window.get("vimshottari_display")
        or (window.get("vimshottari") or {}).get("display")
        or window.get("label")
        or ""
    )


def _window_dates(window: dict[str, Any]) -> str:
    start = window.get("start_display") or window.get("start")
    end = window.get("end_display") or window.get("end")
    return f"{start} to {end}" if start and end else ""


def _compact_window(window: dict[str, Any]) -> dict[str, Any]:
    if not window:
        return {}
    return {
        "start": window.get("start"),
        "end": window.get("end"),
        "start_display": window.get("start_display"),
        "end_display": window.get("end_display"),
        "date_range": _window_dates(window),
        "vimshottari_display": _window_label(window),
        "intersection_tier": window.get("intersection_tier"),
        "confirmed_systems": window.get("confirmed_systems", []),
        "confidence": window.get("confidence"),
        "composite_score": window.get("composite_score"),
        "ranking_score": window.get("ranking_score"),
        "varga_score": window.get("varga_score"),
        "vimshottari": window.get("vimshottari", {}),
        "jaimini": window.get("jaimini", {}),
        "yogini": window.get("yogini", {}),
        "reasons": window.get("reasons", [])[:5],
    }


def _intersection_explanation(best: dict[str, Any], secondary: dict[str, Any], category: str) -> dict[str, Any]:
    if not best:
        return {}

    confirmed_systems = best.get("confirmed_systems", [])
    is_intersection = len(confirmed_systems) >= 2 or best.get("intersection_tier") in {
        "intersection_of_two",
        "intersection_of_three",
    }
    transit = best.get("transit_convergence") or {}
    connected_triggers = [
        trigger
        for trigger in transit.get("triggers", [])
        if trigger.get("connected_to_topic")
    ]
    overlap = []
    label = _window_label(best)
    if label:
        overlap.append(f"{label} is active")
    if best.get("jaimini"):
        overlap.append("Jaimini/Chara timing is supplied for the same window")
    if best.get("yogini"):
        overlap.append("Yogini timing is supplied for the same window")
    if best.get("varga_score"):
        overlap.append("divisional chart confirmation is present")
    if connected_triggers:
        overlap.append("transit triggers connect to the relevant houses")
    if transit.get("score"):
        overlap.append("transit/Ashtakavarga filter contributes timing support")

    return {
        "principle": (
            "Dasha gives permission/background theme; transit gives event trigger; "
            "Ashtakavarga filters strength; divisional chart confirms the theme."
        ),
        "explanation_rule": (
            "Explain this as an intersection window when two or more supplied factors overlap. "
            "Do not attribute the timing to one dasha or one transit alone."
        ),
        "is_intersection_window": is_intersection,
        "support_type": "intersection" if is_intersection else "single-factor",
        "confidence_sentence": (
            "This is an intersection window, so confidence is stronger."
            if is_intersection
            else "This is a single-factor indication, so confidence is lower."
        ),
        "base_timing": {
            "window": _window_dates(best),
            "vimshottari_display": label,
            "role": "broad possibility for the event",
        },
        "narrowing_factor": {
            "transit_status": transit.get("status"),
            "transit_score": transit.get("score"),
            "role": "narrows timing only when relevant houses are activated",
        },
        "strength_filter": {
            "ashtakavarga_rule": "Use Sarvashtakavarga/SAV points only when supplied by the calculation engine.",
            "connected_triggers": connected_triggers[:5],
        },
        "divisional_confirmation": {
            "varga_score": best.get("varga_score"),
            "role": "confirms whether the event theme is supported at a deeper chart level",
        },
        "overlapping_factors": overlap,
        "start_reason": (
            "The start date is the first date in the supplied candidate window where these supporting factors overlap. "
            "Do not invent a more specific cause unless it is present in the trigger details."
        ),
        "ending_reason": (
            "The end date is the supplied end of this candidate window; if the payload does not name a specific "
            "ending trigger, describe it as the end of the calculated support window."
        ),
        "comparison_with_secondary": (
            "Compare the best window against the secondary window using intersection tier, confirmed systems, "
            "divisional support, transit support, and caution flags only."
        ),
        "secondary_window": _compact_window(secondary),
        "category": category,
    }


def _relevant_houses(category: str) -> list[dict[str, Any]]:
    houses = CATEGORY_RULES.get(category, {}).get("houses", [])
    meanings = HOUSE_MEANINGS.get(category, {})
    return [{"house": house, "meaning": meanings.get(house, "")} for house in houses]


def _travel_cautions(evidence: dict[str, Any]) -> list[str]:
    cautions = []
    jaimini = evidence.get("timing_selection", {}).get("best_window", {}).get("jaimini", {})
    if jaimini.get("mahadasha_sign") and not jaimini.get("score"):
        cautions.append("Jaimini sign evidence is present but does not strongly score the travel houses.")
    q = (evidence.get("question") or {}).get("text", "").lower()
    if "india" in q or "return" in q or "home" in q:
        cautions.append("For India/home-return questions, the 4th house must be treated as homeland/residence evidence, not generic travel only.")
    return cautions


def _transit_basis(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    best = (evidence.get("timing_selection") or {}).get("best_window", {})
    segments = best.get("transit_segments", [])
    if segments:
        return [
            {"planet": s["lord_name"], "role": s["role"],
             "mahadasha_lord": s.get("mahadasha_lord"), "antardasha_lord": s.get("antardasha_lord"),
             "start": s["start"], "end": s["end"],
             "transit_sign": s.get("transit_sign"), "transit_sign_number": s.get("transit_sign_number"),
             "house_from_lagna": s.get("transit_house_from_lagna"),
             "sarvashtakavarga_points": s.get("sarvashtakavarga_points"),
             "ashtakavarga_threshold": s.get("ashtakavarga_threshold"),
             "note": "Period-scoped dasha-lord transit; use only within these inclusive dates."}
            for s in segments
        ]
    triggers = (best.get("transit_convergence") or {}).get("triggers", [])
    basis = []
    for trigger in triggers[:5]:
        basis.append(
            {
                "planet": trigger.get("planet_name") or PLANET_NAMES.get(trigger.get("planet"), trigger.get("planet")),
                "role": trigger.get("role"),
                "transit_sign": trigger.get("transit_sign"),
                "transit_sign_number": trigger.get("transit_sign_number"),
                "house_from_lagna": trigger.get("transit_house_from_lagna"),
                "house_from_moon": trigger.get("transit_house_from_moon"),
                "sarvashtakavarga_points": trigger.get("sarvashtakavarga_points"),
                "ashtakavarga_threshold": trigger.get("ashtakavarga_threshold"),
                "relevant_house_aspects": trigger.get("relevant_house_aspects", []),
                "connected_to_topic": trigger.get("connected_to_topic"),
                "score": trigger.get("score"),
                "note": "Use as confirmation/refinement only, not as sole prediction basis.",
            }
        )
    return basis


def _divisional_basis(evidence: dict[str, Any]) -> dict[str, Any]:
    required = evidence.get("synthesis", {}).get("prompt_payload", {}).get("required_divisional_charts")
    if not required:
        required = []
    rules = [
        {
            "rule_id": rule.get("rule_id"),
            "chart": rule.get("chart"),
            "reason": rule.get("reason"),
            "polarity": rule.get("polarity"),
        }
        for rule in evidence.get("triggered_rules", [])
        if rule.get("chart")
    ][:8]
    return {
        "required_charts": required,
        "triggered_chart_rules": rules,
    }


def build_evidence_card(evidence: dict[str, Any]) -> dict[str, Any]:
    category = (evidence.get("question") or {}).get("category", "general")
    timing = evidence.get("timing_selection", {})
    best = timing.get("best_window", {})
    secondary = (timing.get("secondary_windows") or [{}])[0]
    confidence = best.get("confidence") or evidence.get("confidence_summary", {}).get("level") or "medium"

    card = {
        "question_type": category,
        "answer_contract": (
            "Use only this evidence card and supplied triggered rules. Do not invent dasha labels, "
            "transit facts, divisional placements, or dates."
        ),
        "relevant_houses_checked": _relevant_houses(category),
        "best_window": _compact_window(best),
        "secondary_window": _compact_window(secondary),
        "intersection_timing": _intersection_explanation(best, secondary, category),
        "vimshottari_basis": {
            "must_copy_display_label": _window_label(best),
            "best_window": (best.get("vimshottari") or {}),
            "rule": "Never rewrite or infer the dasha label. Copy vimshottari_display exactly.",
        },
        "jaimini_basis": {
            "best_window": (best.get("jaimini") or {}),
            "rule": "Explain only how the active Chara signs connect to the relevant houses. Do not treat the 8th house as direct travel proof.",
        },
        "yogini_basis": {
            "best_window": (best.get("yogini") or {}),
        },
        "divisional_basis": _divisional_basis(evidence),
        "transit_ashtakavarga_basis": _transit_basis(evidence),
        "cautions": [],
        "confidence": confidence,
        "confidence_reason": (
            f"{best.get('intersection_tier') or 'timing'} with systems "
            f"{', '.join(best.get('confirmed_systems', [])) or 'not fully confirmed'}; "
            "transits are used only as refinement."
        ),
    }
    if category == "foreign_travel":
        card["cautions"].extend(_travel_cautions(evidence))
    if category == "vehicle":
        card["cautions"].append("Vehicle questions require D16/Shodashamsha as primary proof; D4 is secondary only.")
    return card
