from astrology.synthesis.answer_schema import REQUIRED_SECTIONS


def _section_body(answer: str, heading: str) -> str:
    lowered = answer.lower()
    marker = f"### {heading.lower()}"
    start = lowered.find(marker)
    if start == -1:
        return ""
    next_start = lowered.find("### ", start + len(marker))
    return answer[start: next_start if next_start != -1 else len(answer)]


def _windows(evidence: dict) -> list:
    return (evidence.get("transits") or {}).get("future_timing", {}).get("windows", [])


def _jaimini_available(evidence: dict) -> bool:
    """Jaimini is available if the evidence has jaimini data OR any timing window has a chara sign."""
    jaimini = evidence.get("jaimini") or {}
    if jaimini and any(jaimini.get(k) for k in ("active_chara_dasha", "chara_dasha", "mahadasha")):
        return True
    return any(w.get("jaimini_active_sign") for w in _windows(evidence))


def _yogini_available(evidence: dict) -> bool:
    """Yogini is available if the evidence has yogini data OR any timing window has a yogini name."""
    yogini = evidence.get("yogini") or {}
    if yogini and any(yogini.get(k) for k in ("current_yogini", "mahadasha", "periods")):
        return True
    return any(w.get("yogini_name") for w in _windows(evidence))


def check_completeness(answer: str, evidence: dict) -> list[str]:
    lowered = answer.lower()
    issues = []
    missing = [section for section in REQUIRED_SECTIONS if section.lower() not in lowered]
    if missing:
        issues.append(f"Answer is missing required sections: {', '.join(missing)}.")

    # System coverage — use data presence, not calculation_status (stripped in compact payload)
    if evidence.get("parashari") and "mahadasha" not in lowered:
        issues.append("Answer does not name the active Mahadasha — Parashari/Vimshottari data is present.")
    if _jaimini_available(evidence) and not any(w in lowered for w in ["jaimini", "chara dasha", "chara"]):
        issues.append(
            "Answer ignores available Jaimini/Chara Dasha data. "
            "Para 2 of 'Why We Advise That' MUST name the active Chara sign and its house from Lagna."
        )
    if _yogini_available(evidence) and "yogini" not in lowered:
        issues.append(
            "Answer ignores available Yogini data. "
            "Para 3 of 'Why We Advise That' MUST name the active Yogini and sub-Yogini."
        )
    if evidence.get("transits", {}).get("future_timing") and "transit" not in lowered:
        issues.append("Answer does not mention transit timing.")

    # Category-specific D-chart checks
    category = evidence.get("question", {}).get("category")
    if category in {"career", "job"} and "d10" not in lowered:
        issues.append("Career/job answer must mention D10 (Dashamsha) — it is the mandatory divisional chart for this category.")
    if category == "marriage" and "d9" not in lowered:
        issues.append("Marriage answer must mention D9 (Navamsha) — it is the mandatory divisional chart.")
    if category == "children" and "d7" not in lowered:
        issues.append("Children/birth answer must mention D7 (Saptamsha) — it is the mandatory divisional chart.")
    if category == "money" and "d2" not in lowered:
        issues.append("Money/wealth answer must mention D2 (Hora) — it is the mandatory divisional chart.")
    if category == "health" and "d30" not in lowered:
        issues.append("Health answer must mention D30 (Trimshamsha) — it is the mandatory divisional chart.")
    if category == "education" and "d24" not in lowered:
        issues.append("Education answer must mention D24 (Chaturvimshamsha) — it is the mandatory divisional chart.")
    if category == "property":
        if "d4" not in lowered and "chaturthamsha" not in lowered:
            issues.append("Property answer must mention D4 (Chaturthamsha) — it is the mandatory divisional chart.")
        if not any(h in lowered for h in ["4th house", "4th lord", "fourth house"]):
            issues.append("Property answer must discuss the 4th house — it is the primary house for home/property.")
        if "mars" not in lowered:
            issues.append("Property answer must mention Mars — it is the natural karaka (naisargika karaka) for land and real estate.")
    if category == "business" and not all(term in lowered for term in ["7th", "10th", "11th"]):
        issues.append("Business answer does not mention 7th/10th/11th indicators.")
    if category == "foreign_travel":
        if "d4" not in lowered and "chaturthamsha" not in lowered:
            issues.append("Foreign travel/relocation answer should mention D4 (Chaturthamsha).")
        if not any(h in lowered for h in ["4th", "fourth", "12th", "twelfth"]):
            issues.append("Foreign travel/relocation answer must reference 4th and/or 12th house indicators.")

    # System naming violations
    if "parashari, vimshottari" in lowered:
        issues.append("Do not list Parashari and Vimshottari as separate peer systems; Vimshottari belongs under Parashari dasha timing.")
    if "vimshottari system" in lowered:
        issues.append("Vimshottari should be described as a Parashari dasha, not a separate system.")
    if "chara system" in lowered or "chara dasha system" in lowered:
        issues.append("Chara should be described as a Jaimini dasha, not a separate system.")

    # ── Timing scan checks ──
    time_scope = (evidence.get("question") or {}).get("time_scope") or {}
    if not time_scope.get("is_fixed", True):
        windows = _windows(evidence)
        if windows:
            top_md = windows[0].get("mahadasha_lord", "")
            top_ad = windows[0].get("antardasha_lord", "")
            top_start = windows[0].get("start_display") or windows[0].get("start", "")
            if top_md and top_ad:
                if top_md.lower() not in lowered or top_ad.lower() not in lowered:
                    issues.append(
                        f"'Why We Advise That' must reference the recommended window's dasha lords "
                        f"({top_md} Mahadasha / {top_ad} Antardasha)."
                    )
            # Check that the top-scored window appears as "Best window", not demoted to secondary
            if top_start and "best window" in lowered:
                best_window_pos = lowered.find("best window")
                secondary_pos = lowered.find("secondary window")
                # The top window's date should appear before "secondary window" in the answer
                top_date_pos = lowered.find(top_start.lower()[:7])  # match first 7 chars (e.g. "Oct 202")
                if secondary_pos != -1 and top_date_pos != -1 and top_date_pos > secondary_pos:
                    issues.append(
                        f"Window ranking is wrong: the engine's top-scored window "
                        f"({top_md}/{top_ad}, from {top_start}) must be the 'Best window', "
                        f"not demoted to secondary. Use future_timing.windows[0] for 'Best window'."
                    )
        # For timing scans, 'Why We Advise That' must cover all 4 systems
        why_section = _section_body(answer, "Why We Advise That")
        why_lower = why_section.lower()
        if why_section:
            if _jaimini_available(evidence) and not any(w in why_lower for w in ["chara", "jaimini"]):
                issues.append(
                    "'Why We Advise That' is missing Para 2 (Jaimini/Chara). "
                    "Must name the active Chara sign and its house from Lagna for each recommended window."
                )
            if _yogini_available(evidence) and "yogini" not in why_lower:
                issues.append(
                    "'Why We Advise That' is missing Para 3 (Yogini). "
                    "Must name the active Yogini and sub-Yogini for each recommended window."
                )
            primary_d = (evidence.get("question") or {}).get("primary_divisional_chart", "d1")
            if primary_d != "d1" and primary_d not in why_lower.replace(" ", ""):
                issues.append(
                    f"'Why We Advise That' is missing Para 4 (Divisional Charts). "
                    f"Must mention {primary_d.upper()} for the recommended windows."
                )

    return issues
