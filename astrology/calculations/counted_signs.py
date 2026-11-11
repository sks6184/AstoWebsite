"""Counted signs from Jaimini reference points (OD-31) and Moon-based houses (OD-33).

Additive module (M3). It reuses the existing conventions in astrology/calculations/jaimini.py:
house padas by direct counting without exceptions, Karakamsha = the D9 sign of the Atmakaraka, and
inclusive sign counting (the reference sign itself is the 1st), exactly as the existing
"10th from Karakamsha" and "10th from Arudha" points are computed. Occupants and influences are read
in the D1 chart, and influence means occupation or Jaimini rasi drishti, as in the existing helpers.
"""
from typing import Any

from charts.vedic_utils import SIGN_NAMES, get_planet, get_planets_in_sign, normalize_sign_number, sign_distance

from .jaimini import _compact_planet, _planets_influencing_sign, build_karakamsha, build_padas

REFERENCES = ("arudha_lagna", "upapada_lagna", "karakamsha")
COUNTING = "inclusive: the reference sign itself is the 1st (same convention as the existing 10th-from points)"


class CountedSignError(ValueError):
    """Invalid reference or count, or a reference point that cannot be determined."""


def reference_sign(chart_data: dict[str, Any], reference: str) -> tuple[int | None, dict[str, Any]]:
    if reference not in REFERENCES:
        raise CountedSignError("unknown_reference")
    if reference == "karakamsha":
        karakamsha = build_karakamsha(chart_data)
        return karakamsha.get("sign_number"), {
            "definition": "Navamsha (D9) sign occupied by the Atmakaraka",
            "atmakaraka": (karakamsha.get("atmakaraka") or {}).get("code"),
            "source": "astrology/calculations/jaimini.py::build_karakamsha",
        }
    padas = build_padas(chart_data)
    pada = padas["arudha_lagna" if reference == "arudha_lagna" else "upapada_lagna"]
    return pada.get("pada_sign_number"), {
        "definition": "Pada of the 1st house (AL)" if reference == "arudha_lagna" else "Pada of the 12th house (UL)",
        "house": pada.get("house"),
        "exceptions_applied": padas.get("exceptions_applied"),
        "source": "astrology/calculations/jaimini.py::build_padas",
    }


def counted_sign(chart_data: dict[str, Any], reference: str, count: int) -> dict[str, Any]:
    if type(count) is not int or not 1 <= count <= 12:
        raise CountedSignError("count_out_of_range")
    start, provenance = reference_sign(chart_data, reference)
    start = normalize_sign_number(start)
    if not start:
        raise CountedSignError("reference_unavailable")
    sign_number = normalize_sign_number(start + count - 1)
    return {
        "reference": reference,
        "reference_sign_number": start,
        "reference_sign": SIGN_NAMES.get(start),
        "reference_provenance": provenance,
        "count": count,
        "counting": COUNTING,
        "sign_number": sign_number,
        "sign": SIGN_NAMES.get(sign_number),
        "house_from_lagna": sign_distance(chart_data.get("ascendant", {}).get("sign_number"), sign_number),
        "occupants": [_compact_planet(p) for p in get_planets_in_sign(chart_data, sign_number, "d1")],
        "influencing_planets": _planets_influencing_sign(chart_data, sign_number),
        "influence_rule": "occupation or Jaimini rasi drishti (astrology/calculations/jaimini.py)",
    }


def house_from_moon(chart_data: dict[str, Any], sign_number: int | None) -> int | None:
    """Whole-sign house of sign_number counted from the natal Moon's D1 sign (inclusive)."""
    moon_sign = get_planet(chart_data, "Mo", "d1").get("sign_number")
    return sign_distance(moon_sign, sign_number) if moon_sign and sign_number else None
