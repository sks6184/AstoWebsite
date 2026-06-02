"""Low-weight classical Yogini modifiers from Chapter 7."""
from typing import Any

from .yogini_derived_meanings import get_experimental_yogini_themes

CHAPTER_SEVEN_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 7: The Meaning in Psychology of Yoginis",
    "printed_pages": "60-70",
    "pdf_pages": "68-78",
}

# These are small modifiers, not verdicts. Chapters 3, 4, and 7 require the
# literal baseline to be modified by the actual condition of the Yogini lord.
YOGINI_BASELINES: dict[str, dict[str, Any]] = {
    "Mangala": {"tone": "supportive", "score": 2, "themes": ["comforts", "learning", "auspicious events"]},
    "Pingala": {"tone": "pressured", "score": -2, "themes": ["worry", "physical pressure", "loss of ease"]},
    "Dhanya": {"tone": "supportive", "score": 2, "themes": ["wealth", "business growth", "learning", "recognition"]},
    "Bhramari": {"tone": "pressured", "score": -2, "themes": ["movement", "disruption", "hard work"]},
    "Bhadrika": {"tone": "supportive", "score": 2, "themes": ["business", "communication", "family comforts"]},
    "Ulka": {"tone": "pressured", "score": -2, "themes": ["loss", "delay", "family or health pressure"]},
    "Siddha": {"tone": "supportive", "score": 2, "themes": ["accomplishment", "prosperity", "authority"]},
    "Sankata": {"tone": "pressured", "score": -2, "themes": ["disruption", "separation", "instability"]},
}


def _pair(tone: str, score: int) -> dict[str, Any]:
    return {"tone": tone, "score": score}


# Reviewed from the major/subperiod descriptions on printed pages 62-70.
# Scores remain deliberately small so calculated lord condition dominates.
YOGINI_PAIR_BASELINES: dict[tuple[str, str], dict[str, Any]] = {
    ("Mangala", "Mangala"): _pair("supportive", 2),
    ("Mangala", "Pingala"): _pair("pressured", -2),
    ("Mangala", "Dhanya"): _pair("supportive", 2),
    ("Mangala", "Bhramari"): _pair("pressured", -2),
    ("Mangala", "Bhadrika"): _pair("supportive", 2),
    ("Mangala", "Ulka"): _pair("pressured", -2),
    ("Mangala", "Siddha"): _pair("supportive", 2),
    ("Mangala", "Sankata"): _pair("pressured", -2),
    ("Pingala", "Mangala"): _pair("pressured", -2),
    ("Pingala", "Pingala"): _pair("pressured", -2),
    ("Pingala", "Dhanya"): _pair("supportive", 2),
    ("Pingala", "Bhramari"): _pair("pressured", -2),
    ("Pingala", "Bhadrika"): _pair("supportive", 2),
    ("Pingala", "Ulka"): _pair("pressured", -2),
    ("Pingala", "Siddha"): _pair("mixed", 0),
    ("Pingala", "Sankata"): _pair("pressured", -2),
    ("Dhanya", "Mangala"): _pair("supportive", 2),
    ("Dhanya", "Pingala"): _pair("pressured", -2),
    ("Dhanya", "Dhanya"): _pair("supportive", 2),
    ("Dhanya", "Bhramari"): _pair("pressured", -2),
    ("Dhanya", "Bhadrika"): _pair("supportive", 2),
    ("Dhanya", "Ulka"): _pair("pressured", -2),
    ("Dhanya", "Siddha"): _pair("supportive", 2),
    ("Dhanya", "Sankata"): _pair("pressured", -2),
    ("Bhramari", "Mangala"): _pair("supportive", 2),
    ("Bhramari", "Pingala"): _pair("pressured", -2),
    ("Bhramari", "Dhanya"): _pair("supportive", 2),
    ("Bhramari", "Bhramari"): _pair("pressured", -2),
    ("Bhramari", "Bhadrika"): _pair("supportive", 2),
    ("Bhramari", "Ulka"): _pair("pressured", -2),
    ("Bhramari", "Siddha"): _pair("supportive", 2),
    ("Bhramari", "Sankata"): _pair("pressured", -2),
    ("Bhadrika", "Mangala"): _pair("supportive", 2),
    ("Bhadrika", "Pingala"): _pair("mixed", 0),
    ("Bhadrika", "Dhanya"): _pair("supportive", 2),
    ("Bhadrika", "Bhramari"): _pair("pressured", -2),
    ("Bhadrika", "Bhadrika"): _pair("supportive", 2),
    ("Bhadrika", "Ulka"): _pair("pressured", -2),
    ("Bhadrika", "Siddha"): _pair("supportive", 2),
    ("Bhadrika", "Sankata"): _pair("pressured", -2),
    ("Ulka", "Mangala"): _pair("supportive", 2),
    ("Ulka", "Pingala"): _pair("pressured", -2),
    ("Ulka", "Dhanya"): _pair("mixed", 0),
    ("Ulka", "Bhramari"): _pair("pressured", -2),
    ("Ulka", "Bhadrika"): _pair("supportive", 2),
    ("Ulka", "Ulka"): _pair("pressured", -2),
    ("Ulka", "Siddha"): _pair("pressured", -2),
    ("Ulka", "Sankata"): _pair("pressured", -2),
    ("Siddha", "Mangala"): _pair("supportive", 2),
    ("Siddha", "Pingala"): _pair("pressured", -2),
    ("Siddha", "Dhanya"): _pair("supportive", 2),
    ("Siddha", "Bhramari"): _pair("pressured", -2),
    ("Siddha", "Bhadrika"): _pair("supportive", 2),
    ("Siddha", "Ulka"): _pair("pressured", -2),
    ("Siddha", "Siddha"): _pair("supportive", 2),
    ("Siddha", "Sankata"): _pair("pressured", -2),
    ("Sankata", "Mangala"): _pair("pressured", -2),
    ("Sankata", "Pingala"): _pair("pressured", -2),
    ("Sankata", "Dhanya"): _pair("mixed", 1),
    ("Sankata", "Bhramari"): _pair("pressured", -2),
    ("Sankata", "Bhadrika"): _pair("mixed", 1),
    ("Sankata", "Ulka"): _pair("pressured", -2),
    ("Sankata", "Siddha"): _pair("supportive", 2),
    ("Sankata", "Sankata"): _pair("pressured", -2),
}


def evaluate_yogini_baseline(major_yogini: str | None, sub_yogini: str | None) -> dict[str, Any]:
    major = YOGINI_BASELINES.get(major_yogini or "", {"tone": "unknown", "score": 0, "themes": []})
    pair = YOGINI_PAIR_BASELINES.get((major_yogini or "", sub_yogini or ""), {"tone": "unknown", "score": 0})
    return {
        "major_yogini": major_yogini,
        "sub_yogini": sub_yogini,
        "major_baseline": major,
        "pair_baseline": pair,
        "score": major["score"] + pair["score"],
        "is_low_weight_modifier": True,
        "instruction": "Use as a minor modifier only; calculated lord condition and full cross-system evidence dominate.",
        "experimental_derived_themes": get_experimental_yogini_themes(major_yogini),
        "source_reference": CHAPTER_SEVEN_REFERENCE,
    }
