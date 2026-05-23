from astrology.synthesis.answer_schema import REQUIRED_SECTIONS


def _section_body(answer: str, heading: str) -> str:
    lowered = answer.lower()
    marker = f"### {heading.lower()}"
    start = lowered.find(marker)
    if start == -1:
        return ""
    next_start = lowered.find("### ", start + len(marker))
    return answer[start: next_start if next_start != -1 else len(answer)]


def check_completeness(answer: str, evidence: dict) -> list[str]:
    lowered = answer.lower()
    issues = []
    missing = [section for section in REQUIRED_SECTIONS if section.lower() not in lowered]
    if missing:
        issues.append(f"Answer is missing required sections: {', '.join(missing)}.")
    if evidence.get("parashari", {}).get("calculation_status") == "active" and "parashari" not in lowered:
        issues.append("Answer does not mention available Parashari evidence.")
    if evidence.get("jaimini", {}).get("calculation_status") == "active" and "jaimini" not in lowered:
        issues.append("Answer does not mention available Jaimini evidence.")
    if evidence.get("yogini", {}).get("calculation_status") == "active" and "yogini" not in lowered:
        issues.append("Answer does not mention active Yogini evidence.")
    if evidence.get("transits", {}).get("future_timing") and "transit" not in lowered:
        issues.append("Answer does not mention transit timing.")
    category = evidence.get("question", {}).get("category")
    if category == "marriage" and "d9" not in lowered:
        issues.append("Marriage/relationship answer does not mention D9 evidence.")
    if category == "business" and not all(term in lowered for term in ["7th", "10th", "11th"]):
        issues.append("Business answer does not mention 7th/10th/11th indicators.")
    if category == "foreign_travel":
        if "d4" not in lowered and "chaturthamsha" not in lowered:
            issues.append("Foreign travel/relocation answer should mention D4 (Chaturthamsha) for residence confirmation.")
        if not any(h in lowered for h in ["4th", "fourth", "12th", "twelfth"]):
            issues.append("Foreign travel/relocation answer must reference 4th and/or 12th house indicators.")
    if "parashari, vimshottari" in lowered:
        issues.append("Do not list Parashari and Vimshottari as separate peer systems; Vimshottari belongs under Parashari dasha timing.")
    if "vimshottari system" in lowered:
        issues.append("Vimshottari should be described as a Parashari dasha, not a separate system.")
    if "chara system" in lowered or "chara dasha system" in lowered:
        issues.append("Chara should be described as a Jaimini dasha, not a separate system.")

    # ── Period match rule: 'Why We Advise That' must use the recommended window's lords ──
    time_scope = (evidence.get("question") or {}).get("time_scope") or {}
    if not time_scope.get("is_fixed", True):
        # Timing scan — check that at least one future window's dasha lord appears in the answer
        windows = (evidence.get("transits") or {}).get("future_timing", {}).get("windows", [])
        if windows:
            top_md = windows[0].get("mahadasha_lord", "")
            top_ad = windows[0].get("antardasha_lord", "")
            if top_md and top_ad:
                # The top-recommended window's lords should appear somewhere in the answer
                if top_md.lower() not in lowered or top_ad.lower() not in lowered:
                    issues.append(
                        f"'Why We Advise That' should reference the recommended window's dasha lords "
                        f"({top_md} Mahadasha / {top_ad} Antardasha) — not just the current running dasha."
                    )

    return issues
