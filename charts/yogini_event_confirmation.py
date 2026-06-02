"""Cross-system event confirmation from Yogini Dasha Chapter 9."""
from typing import Any


CHAPTER_NINE_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 9: Confirmation of an Event",
    "printed_pages": "82-97",
    "pdf_pages": "90-105",
}

_CONFIRMING_STATUSES = {"supports", "mixed"}


def build_event_confirmation(
    vimshottari: dict[str, Any],
    jaimini: dict[str, Any],
    yogini: dict[str, Any],
    divisional: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize whether independent timing systems support the same topic."""
    systems = {
        "vimshottari": vimshottari,
        "jaimini": jaimini,
        "yogini": yogini,
    }
    system_results = {
        name: {
            "status": facts.get("status", "not_confirmed"),
            "score": facts.get("score", 0),
            "confirmed": facts.get("status") in _CONFIRMING_STATUSES,
        }
        for name, facts in systems.items()
    }
    confirmed_systems = [
        name for name, result in system_results.items() if result["confirmed"]
    ]
    count = len(confirmed_systems)
    tier = (
        "intersection_of_three"
        if count == 3
        else "intersection_of_two"
        if count == 2
        else "single_system_support"
        if count == 1
        else "no_intersection"
    )
    contradictions = [
        name
        for name, result in system_results.items()
        if result["status"] in {"pressured", "not_confirmed"}
    ]
    divisional = divisional or {}
    return {
        "calculation_status": "active",
        "confirmation_count": count,
        "intersection_tier": tier,
        "confirmed_systems": confirmed_systems,
        "system_results": system_results,
        "divisional_confirmation": {
            "primary_varga": divisional.get("primary_varga"),
            "status": divisional.get("status", "not_confirmed"),
            "score": divisional.get("score", 0),
        },
        "contradicting_or_unconfirmed_systems": contradictions,
        "ranking_instruction": (
            "Rank intersections of three first, intersections of two second, "
            "then use divisional-chart support and composite score."
        ),
        "source_reference": CHAPTER_NINE_REFERENCE,
    }
