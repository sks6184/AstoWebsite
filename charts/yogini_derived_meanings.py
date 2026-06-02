"""Experimental, unscored Yogini themes from Chapters 13 and 14."""
from typing import Any


CHAPTER_THIRTEEN_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 13: Derived Meanings of the Yoginis",
    "printed_pages": "192-203",
    "pdf_pages": "200-211",
}
CHAPTER_FOURTEEN_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 14: Conclusion",
    "printed_pages": "204-205",
    "pdf_pages": "212-213",
}

# Short paraphrases only. Medical, danger, and highly speculative symbolic
# claims are intentionally excluded from automated output.
EXPERIMENTAL_YOGINI_THEMES: dict[str, list[str]] = {
    "Mangala": ["auspicious occasions", "recognition", "tradition", "support from others"],
    "Pingala": ["authority", "vigilance", "mobility", "wise decisions", "mixed outcomes"],
    "Dhanya": ["prosperity", "family happiness", "commercial opportunities", "restoration"],
    "Bhramari": ["movement", "complex situations", "attachment", "resource gathering"],
    "Bhadrika": ["protection", "good contacts", "communication talent", "resilience"],
    "Ulka": ["discipline", "technical learning", "astrology interest", "pressure requiring care"],
    "Siddha": ["achievement", "skill", "recognition", "settlement", "completion"],
    "Sankata": ["difficulty", "risk awareness", "independence", "reconnection", "technical themes"],
}


def get_experimental_yogini_themes(yogini: str | None) -> dict[str, Any]:
    """Return explanation metadata without changing deterministic scores."""
    return {
        "yogini": yogini,
        "themes": EXPERIMENTAL_YOGINI_THEMES.get(yogini or "", []),
        "experimental": True,
        "scored": False,
        "excluded_from_automated_output": [
            "medical claims",
            "danger claims",
            "fatality claims",
            "highly speculative symbolic meanings",
        ],
        "instruction": (
            "Use only as optional explanatory metadata after calculated evidence. "
            "Do not treat any Yogini as automatically positive or negative."
        ),
        "source_references": [CHAPTER_THIRTEEN_REFERENCE, CHAPTER_FOURTEEN_REFERENCE],
    }
