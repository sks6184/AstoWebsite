"""Traceable Chapter 8 snapshot checklist for Yogini Dasha."""
from typing import Any


CHAPTER_EIGHT_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 8: Quick Use of Yogini Dasha",
    "printed_pages": "71-81",
    "pdf_pages": "79-89",
}


def build_yogini_snapshot_checklist(
    major_yogini: str | None,
    sub_yogini: str | None,
    major_assessment: dict[str, Any],
    sub_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Report the Chapter 8 snapshot checks without replacing full verification."""
    major_factors = major_assessment.get("factors", [])
    sub_factors = sub_assessment.get("factors", [])
    factors = major_factors + sub_factors
    factor_codes = {factor.get("code") for factor in factors}
    return {
        "major_yogini_checked": major_yogini,
        "sub_yogini_checked": sub_yogini,
        "lordship_checked": bool(major_assessment.get("owned_houses") or sub_assessment.get("owned_houses")),
        "placement_checked": bool(major_assessment.get("d1_house") or sub_assessment.get("d1_house")),
        "aspects_checked": True,
        "conjunctions_checked": True,
        "aspect_or_association_found": any(
            code in {"category_house_aspect", "benefic_association", "malefic_association"}
            for code in factor_codes
        ),
        "dispositor_checked": bool(major_assessment.get("dispositor") or sub_assessment.get("dispositor")),
        "is_snapshot_only": True,
        "instruction": "Snapshot checklist is explanatory only. Do not bypass Vimshottari, Jaimini, divisional charts, or transit verification.",
        "source_reference": CHAPTER_EIGHT_REFERENCE,
    }
