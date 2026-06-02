from datetime import date
from typing import Any

from chat.timing_windows import build_timing_windows
from charts.transit_priority import build_transit_priority_context
from charts.yogini_transit_convergence import evaluate_transit_convergence


def _add_months(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, 28)
    return value.replace(year=year, month=month, day=day)


def _compact_future_window(window: dict[str, Any]) -> dict[str, Any]:
    # Top-3 sub-periods by composite score (compact — scores + dasha labels only)
    sub_breakdown = window.get("sub_period_breakdown", [])
    top_breakdown = sorted(sub_breakdown, key=lambda x: x.get("composite_score", 0), reverse=True)[:3]

    # Slim jaimini_confirmation — drop sign-occupant lists, keep status/score/signs/top-2 reasons
    jai = window.get("jaimini_confirmation", {})
    jai_chara = jai.get("active_chara_dasha", {})
    jai_compact = {
        "status": jai.get("status"),
        "score": jai.get("score", 0),
        "mahadasha_sign": (jai_chara.get("mahadasha") or {}).get("sign"),
        "mahadasha_sign_house_from_lagna": jai_chara.get("mahadasha_house_from_lagna"),
        "mahadasha_sign_lord": jai_chara.get("mahadasha_sign_lord"),
        "mahadasha_sign_lord_name": jai_chara.get("mahadasha_sign_lord_name"),
        "antardasha_sign": (jai_chara.get("antardasha") or {}).get("sign"),
        "antardasha_sign_house_from_lagna": jai_chara.get("antardasha_house_from_lagna"),
        "antardasha_sign_lord": jai_chara.get("antardasha_sign_lord"),
        "antardasha_sign_lord_name": jai_chara.get("antardasha_sign_lord_name"),
        "reasons": jai.get("reasons", [])[:2],
    }

    # Slim yogini_alignment — drop full lord objects, keep essential fields
    yog = window.get("yogini_alignment", {})
    pair = yog.get("pair_assessment", {})
    divisional = yog.get("divisional_confirmation", {})
    baseline = yog.get("classical_baseline", {})
    yog_compact = {
        "status": yog.get("status"),
        "score": yog.get("score", 0),
        "yogini": yog.get("yogini"),
        "major_lord": yog.get("major_lord"),
        "major_lord_name": yog.get("major_lord_name"),
        "sub_yogini": yog.get("sub_yogini"),
        "sub_lord": yog.get("sub_lord"),
        "sub_lord_name": yog.get("sub_lord_name"),
        "major_lord_quality": yog.get("major_lord_quality"),
        "sub_lord_quality": yog.get("sub_lord_quality"),
        "pair_assessment": {
            "status": pair.get("status"),
            "score": pair.get("score", 0),
            "distance_from_major_to_subperiod": pair.get("distance_from_major_to_subperiod"),
            "is_kendra_or_trikona": pair.get("is_kendra_or_trikona"),
            "is_six_eight": pair.get("is_six_eight"),
            "is_two_twelve": pair.get("is_two_twelve"),
            "reasons": pair.get("reasons", [])[:2],
        },
        "divisional_confirmation": {
            "primary_varga": divisional.get("primary_varga"),
            "status": divisional.get("status"),
            "score": divisional.get("score", 0),
            "factors": divisional.get("factors", [])[:3],
        },
        "classical_baseline": {
            "major_baseline": baseline.get("major_baseline", {}),
            "pair_baseline": baseline.get("pair_baseline", {}),
            "score": baseline.get("score", 0),
            "is_low_weight_modifier": baseline.get("is_low_weight_modifier", True),
        },
        "snapshot_checklist": yog.get("snapshot_checklist", {}),
        "reasons": yog.get("reasons", [])[:2],
    }

    # Cap transit_segments to 4 total (representative sign transitions only)
    segs = window.get("transit_segments", [])
    segs_compact = [
        {k: s[k] for k in ("lord_name", "role", "start_display", "end_display",
                            "transit_house_from_lagna", "sarvashtakavarga_points") if k in s}
        for s in segs[:4]
    ]

    return {
        "start": window.get("start"),
        "end": window.get("end"),
        "start_display": window.get("start_display"),
        "end_display": window.get("end_display"),
        "label": window.get("label"),
        "composite_score": window.get("composite_score", window.get("score", 0)),
        "score": window.get("score", 0),
        "vimshottari_score": window.get("vimshottari_score", 0),
        "jaimini_score": window.get("jaimini_score", 0),
        "yogini_score": window.get("yogini_score", 0),
        "varga_score": window.get("varga_score", 0),
        "confirmation_count": window.get("confirmation_count", 0),
        "intersection_tier": window.get("intersection_tier"),
        "mahadasha_lord": window.get("mahadasha_lord"),
        "antardasha_lord": window.get("antardasha_lord"),
        "jaimini_active_sign": window.get("jaimini_active_sign"),
        "jaimini_active_sign_house_from_lagna": window.get("jaimini_active_sign_house_from_lagna"),
        "jaimini_active_sub_sign": window.get("jaimini_active_sub_sign"),
        "jaimini_active_sub_sign_house_from_lagna": window.get("jaimini_active_sub_sign_house_from_lagna"),
        "yogini_name": window.get("yogini_name"),
        "sub_yogini_name": window.get("sub_yogini_name"),
        "reasons": window.get("reasons", [])[:4],
        "jaimini_confirmation": jai_compact,
        "yogini_alignment": yog_compact,
        "transit_convergence": window.get("transit_convergence", {}),
        "sub_period_breakdown": top_breakdown,
        "transit_segments": segs_compact,
    }


def build_future_transit_windows(
    question: str,
    chart_data: dict[str, Any],
    category: str,
    start_date: date,
    months: int = 36,
    end_date: date | None = None,
) -> dict[str, Any]:
    end_date = end_date or _add_months(start_date, months)
    windows = build_timing_windows(
        question,
        chart_data,
        category,
        start_date,
        months=months,
        end_date=end_date,
    )
    compact = [_compact_future_window(window) for window in windows]
    return {
        "scan_months": months,
        "scan_years": round(months / 12, 1),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "windows": compact,
    }


def build_transit_facts(
    chart_data: dict[str, Any],
    category_houses: list[int],
    dasha_facts: dict[str, Any],
    question: str = "",
    category: str = "general",
    target_date: date | None = None,
    horizon: str = "monthly",
    future_months: int = 36,
    end_date: date | None = None,
) -> dict[str, Any]:
    target_date = target_date or date.today()
    vimshottari = dasha_facts.get("parashari_vimshottari", {})
    mahadasha_lord = vimshottari.get("current_mahadasha", {}).get("lord")
    antardasha_lord = vimshottari.get("current_antardasha", {}).get("lord")
    priority = build_transit_priority_context(
        chart_data,
        category_houses,
        target_date,
        mahadasha_lord=mahadasha_lord,
        antardasha_lord=antardasha_lord,
        horizon=horizon,
        cap=12,
    )
    events = priority.get("events", [])
    supporting = [event for event in events if event.get("tone") == "supportive"]
    pressure = [event for event in events if event.get("tone") == "challenging"]
    dasha_lord_events = [
        event
        for event in events
        if event.get("is_mahadasha_lord") or event.get("is_antardasha_lord")
    ]
    positive_score = sum(max(event.get("score", 0), 0) for event in supporting[:5])
    pressure_score = sum(abs(min(event.get("score", 0), 0)) for event in pressure[:5])
    score = max(0, min(100, positive_score - pressure_score))
    transit_convergence = evaluate_transit_convergence(chart_data, category_houses, target_date)
    future_timing = build_future_transit_windows(
        question, chart_data, category, target_date,
        months=future_months, end_date=end_date,
    )

    return {
        "system": "Transit",
        "status": "active",
        "horizon": horizon,
        "target_date": target_date.isoformat(),
        "relevant_transits": events[:12],
        "dasha_lord_transits": dasha_lord_events[:6],
        "transit_convergence": transit_convergence,
        "future_timing": future_timing,
        "score": score,
    }
