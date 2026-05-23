from .specificity_checker import (
    PLANET_CODE_TO_NAME,
    _mahadasha_lord,
    _antardasha_lord,
    _mahadasha_dates,
    _antardasha_dates,
    _yogini_major_lord,
    _yogini_sub_lord,
    _jaimini_active_sign,
    _jaimini_atmakaraka,
    _jaimini_amatyakaraka,
)


def _specificity_mandates(evidence: dict) -> list[str]:
    mandates = []

    mahadasha = _mahadasha_lord(evidence)
    antardasha = _antardasha_lord(evidence)
    if mahadasha:
        md_dates = _mahadasha_dates(evidence)
        ad_dates = _antardasha_dates(evidence)
        ad_part = f" / {antardasha} Antardasha" + (f" ({ad_dates})" if ad_dates else "") if antardasha else ""
        md_dates_part = f" ({md_dates})" if md_dates else ""
        mandates.append(
            f"Write '{mahadasha} Mahadasha{md_dates_part}{ad_part}' — "
            f"do NOT write 'current Mahadasha', 'Vimshottari period', or 'Parashari timing' without this lord name."
        )

    yogini_major = _yogini_major_lord(evidence)
    yogini_sub = _yogini_sub_lord(evidence)
    if yogini_major:
        sub_part = f" with {yogini_sub} sub-period" if yogini_sub and yogini_sub != yogini_major else ""
        mandates.append(
            f"Write '{yogini_major} Yogini major period{sub_part}' — "
            f"do NOT write 'Yogini indicates' without this lord name."
        )

    jaimini_sign = _jaimini_active_sign(evidence)
    if jaimini_sign:
        mandates.append(
            f"Write '{jaimini_sign} Chara Dasha' — "
            f"do NOT write 'Jaimini indicates' without this sign name."
        )

    atmakaraka = _jaimini_atmakaraka(evidence)
    if atmakaraka:
        mandates.append(f"Name '{atmakaraka}' as the Atmakaraka planet.")

    amatyakaraka = _jaimini_amatyakaraka(evidence)
    if amatyakaraka:
        mandates.append(f"Name '{amatyakaraka}' as the Amatyakaraka planet.")

    return mandates


def build_repair_instruction(result: dict, evidence: dict) -> str:
    question = evidence.get("question", {}).get("text", "")
    category = evidence.get("question", {}).get("category", "general")
    pieces = [
        "Regenerate the answer using only calculated chart facts, dasha facts, triggered rules, and RAG context.",
        f"Question category: {category}.",
    ]
    if question:
        pieces.append(f"User question: {question}")
    if result.get("missing_sections"):
        pieces.append("Add missing sections: " + ", ".join(result["missing_sections"]) + ".")
    if result.get("missing_evidence"):
        pieces.append("Add missing evidence: " + ", ".join(result["missing_evidence"]) + ".")
    if result.get("unsupported_claims"):
        pieces.append("Repair unsupported claims: " + ", ".join(result["unsupported_claims"]) + ".")
    if result.get("generic_phrases_detected"):
        pieces.append("Replace generic wording with specific deterministic facts.")

    specificity_mandates = _specificity_mandates(evidence)
    if specificity_mandates:
        pieces.append(
            "SPECIFICITY REQUIRED — use these exact names from the payload: "
            + " | ".join(specificity_mandates)
        )

    pieces.append(
        "For timing/startup questions include a direct recommendation, better date or window, "
        "launch mode such as soft launch/private beta/payment launch/public marketing, "
        "muhurta limitation if exact muhurta is unavailable, and confidence level."
    )
    return " ".join(pieces)
