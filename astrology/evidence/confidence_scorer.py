from __future__ import annotations

_LABELS = {4: "High", 3: "Moderate-High", 2: "Moderate", 1: "Low", 0: "Very Low"}
_SUMMARIES = {
    4: "All 4 systems confirm",
    3: "3 of 4 systems confirm (75%)",
    2: "2 of 4 systems confirm (50%)",
    1: "1 of 4 systems confirms (25%)",
    0: "No system confirms",
}

_SYSTEM_NAMES = {
    "vimshottari": "Vimshottari/Parashari",
    "jaimini": "Jaimini/Chara Dasha",
    "yogini": "Yogini Dasha",
    "varga": "Divisional Charts",
}


def _make_summary(count: int, confirmed: list[str], not_confirmed: list[str], window: dict) -> dict:
    label = _LABELS[count]
    summary = _SUMMARIES[count]
    instruction = (
        f"Confidence is {label} — {summary}. "
        "At the end of '### Why We Advise That', state: "
        f"'Overall confidence: {label} ({summary}).' "
    )
    if not_confirmed:
        names = " and ".join(_SYSTEM_NAMES.get(k, k) for k in not_confirmed)
        instruction += f"{names} did not show clear support for this window — name the reason."
    return {
        "systems_confirmed_count": count,
        "confidence_label": label,
        "confirmation_summary": summary,
        "confirmed_systems": [_SYSTEM_NAMES.get(k, k) for k in confirmed],
        "not_confirmed_systems": [_SYSTEM_NAMES.get(k, k) for k in not_confirmed],
        "window_label": window.get("label", ""),
        "window_start": window.get("start_display") or window.get("start", ""),
        "window_end": window.get("end_display") or window.get("end", ""),
        "instruction": instruction,
    }


def _from_top_window(window: dict) -> dict:
    checks = {
        "vimshottari": (window.get("vimshottari_score") or 0) > 0,
        "jaimini": (window.get("jaimini_score") or 0) > 0,
        "yogini": (window.get("yogini_score") or 0) > 0,
        "varga": (window.get("varga_score") or 0) > 0,
    }
    confirmed = [k for k, ok in checks.items() if ok]
    not_confirmed = [k for k, ok in checks.items() if not ok]
    return _make_summary(len(confirmed), confirmed, not_confirmed, window)


def _from_evidence_layer(evidence: dict) -> dict:
    """Fallback for is_fixed=True questions where no timing windows exist."""
    vim = evidence.get("parashari_vimshottari") or {}
    jai = evidence.get("jaimini") or {}
    yog = evidence.get("yogini") or {}
    var = evidence.get("varga") or {}

    checks = {
        "vimshottari": bool(vim.get("current_mahadasha")),
        "jaimini": bool(jai.get("active_chara_dasha") or jai.get("chara_dasha")),
        "yogini": bool(yog.get("current_yogini") or yog.get("periods")),
        "varga": var.get("status") not in {None, "missing", "unavailable"},
    }
    confirmed = [k for k, ok in checks.items() if ok]
    not_confirmed = [k for k, ok in checks.items() if not ok]
    return _make_summary(len(confirmed), confirmed, not_confirmed, {})


def build_confidence_summary(evidence: dict) -> dict:
    """
    Compute a 4-system confidence score for the best timing window.

    For timing scans (is_fixed=False): uses per-system scores from windows[0].
    For fixed-period questions (is_fixed=True): checks data availability as a proxy.

    Returns a dict with: confidence_label, systems_confirmed_count,
    confirmed_systems, not_confirmed_systems, and an LLM instruction.
    """
    windows = (evidence.get("transits") or {}).get("future_timing", {}).get("windows", [])
    if windows:
        return _from_top_window(windows[0])
    return _from_evidence_layer(evidence)
