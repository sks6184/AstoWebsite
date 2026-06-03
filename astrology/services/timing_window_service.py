"""Final deterministic timing-window selector.

This service ranks timing windows by cross-system agreement:

1. Vimshottari + Jaimini + Yogini intersections.
2. Any two-system intersections.
3. Single-system support only when practical and strong.

Divisional support and transits refine the ranking; they do not replace dasha
agreement.
"""

from datetime import date, datetime
from typing import Any

from chat.timing_windows import build_timing_windows


TIER_RANK = {
    "intersection_of_three": 3,
    "intersection_of_two": 2,
    "single_system_support": 1,
    "no_intersection": 0,
    None: 0,
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value).date()


def _months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def _bucket_for(window: dict[str, Any]) -> str:
    tier = window.get("intersection_tier")
    if tier == "intersection_of_three":
        return "three_system"
    if tier == "intersection_of_two":
        return "two_system"
    if tier == "single_system_support":
        return "single_system"
    return "no_intersection"


def _confidence_for(window: dict[str, Any]) -> str:
    tier = window.get("intersection_tier")
    varga_score = int(window.get("varga_score") or 0)
    transit_score = int((window.get("transit_convergence") or {}).get("score") or 0)
    score = int(window.get("composite_score") or window.get("score") or 0)

    if tier == "intersection_of_three" and varga_score >= 10:
        return "high"
    if tier == "intersection_of_three":
        return "medium-high"
    if tier == "intersection_of_two" and (varga_score >= 10 or transit_score >= 15):
        return "medium-high"
    if tier == "intersection_of_two":
        return "medium"
    if tier == "single_system_support" and score >= 55 and varga_score >= 10:
        return "medium"
    return "low"


def _practical_penalty(window: dict[str, Any], start_date: date, practical_months: int) -> int:
    window_start = _parse_date(window.get("start")) or start_date
    months_out = _months_between(start_date, window_start)
    if months_out <= practical_months:
        return 0
    # Penalize far-future windows without discarding them from lifetime ranking.
    return min(35, (months_out - practical_months) // 6)


def _ranking_score(window: dict[str, Any], start_date: date, practical_months: int) -> int:
    tier_bonus = TIER_RANK.get(window.get("intersection_tier"), 0) * 100
    composite = int(window.get("composite_score") or window.get("score") or 0)
    varga = int(window.get("varga_score") or 0)
    transit = int((window.get("transit_convergence") or {}).get("score") or 0)
    penalty = _practical_penalty(window, start_date, practical_months)
    return tier_bonus + composite + varga // 2 + transit // 4 - penalty


def _compact_window(window: dict[str, Any], start_date: date, practical_months: int) -> dict[str, Any]:
    ranking_score = _ranking_score(window, start_date, practical_months)
    return {
        "start": window.get("start"),
        "end": window.get("end"),
        "start_display": window.get("start_display"),
        "end_display": window.get("end_display"),
        "label": window.get("label"),
        "confidence": _confidence_for(window),
        "ranking_score": ranking_score,
        "composite_score": window.get("composite_score", window.get("score", 0)),
        "intersection_tier": window.get("intersection_tier"),
        "confirmation_count": window.get("confirmation_count", 0),
        "confirmed_systems": (window.get("event_confirmation") or {}).get("confirmed_systems", []),
        "vimshottari": {
            "mahadasha_lord": window.get("mahadasha_lord"),
            "antardasha_lord": window.get("antardasha_lord"),
            "score": window.get("vimshottari_score", 0),
        },
        "jaimini": {
            "mahadasha_sign": window.get("jaimini_active_sign"),
            "antardasha_sign": window.get("jaimini_active_sub_sign"),
            "score": window.get("jaimini_score", 0),
        },
        "yogini": {
            "major": window.get("yogini_name"),
            "sub": window.get("sub_yogini_name"),
            "score": window.get("yogini_score", 0),
        },
        "varga_score": window.get("varga_score", 0),
        "transit_convergence": window.get("transit_convergence", {}),
        "reasons": window.get("reasons", [])[:6],
    }


def build_timing_window_selection(
    chart_data: dict[str, Any],
    question: str,
    category: str,
    start_date: date,
    months: int = 60,
    end_date: date | None = None,
    practical_months: int = 60,
    precomputed_windows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if category == "general":
        return {
            "status": "unavailable",
            "reason": "Timing-window selection requires a classified question category.",
            "best_window": {},
            "secondary_windows": [],
            "system_intersections": {"three_system": [], "two_system": [], "single_system": []},
        }

    windows = precomputed_windows
    if windows is None:
        windows = build_timing_windows(question, chart_data, category, start_date, months=months, end_date=end_date)

    compact = [_compact_window(window, start_date, practical_months) for window in windows]
    compact.sort(key=lambda item: item["ranking_score"], reverse=True)

    buckets = {
        "three_system": [],
        "two_system": [],
        "single_system": [],
        "no_intersection": [],
    }
    for window in compact:
        buckets[_bucket_for(window)].append(window)

    practical = [
        window
        for window in compact
        if (_parse_date(window.get("start")) or start_date) <= (end_date or start_date.replace(year=start_date.year + 5))
    ]
    best_pool = practical or compact
    best = best_pool[0] if best_pool else {}
    secondary = [window for window in compact if window is not best][:4]

    return {
        "status": "active" if compact else "not_confirmed",
        "category": category,
        "scan_start": start_date.isoformat(),
        "scan_end": (end_date.isoformat() if end_date else ""),
        "scan_months": months,
        "practical_months": practical_months,
        "selection_rule": (
            "Rank three-system intersections first, two-system intersections second, "
            "single-system windows third; then apply divisional support, transit refinement, "
            "composite score, and far-future penalty."
        ),
        "best_window": best,
        "secondary_windows": secondary,
        "system_intersections": {
            "three_system": buckets["three_system"][:5],
            "two_system": buckets["two_system"][:5],
            "single_system": buckets["single_system"][:5],
            "no_intersection": buckets["no_intersection"][:3],
        },
    }

