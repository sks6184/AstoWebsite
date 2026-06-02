"""Derived reference-frame facts from Yogini Dasha Chapter 10."""
from typing import Any

from .vedic_utils import PLANET_NAMES, SIGN_LORDS, SIGN_NAMES, get_planet, normalize_sign_number


CHAPTER_TEN_REFERENCE = {
    "book": "Applications of Yogini Dasha for Brilliant Predictions",
    "chapter": "Chapter 10: Successful Predictive Techniques",
    "printed_pages": "98-129",
    "pdf_pages": "106-137",
}

_CATEGORY_PRIMARY_VARGA = {
    "job": "d10",
    "career": "d10",
    "business": "d10",
    "marriage": "d9",
    "children": "d7",
    "family": "d12",
    "education": "d24",
    "property": "d4",
    "health": "d30",
    "general": "d9",
}
_CATEGORY_KARAKAS = {
    "job": ["Sa", "Me"],
    "career": ["Su", "Sa", "Me"],
    "business": ["Me", "Ju", "Ra"],
    "marriage": ["Ve", "Ju"],
    "children": ["Ju"],
    "family": ["Su", "Mo"],
    "education": ["Me", "Ju"],
    "property": ["Ma", "Mo"],
    "health": ["Su", "Ma"],
}


def _frame(label: str, chart_data: dict[str, Any], chart_key: str, anchor: dict[str, Any], category_houses: list[int]) -> dict[str, Any]:
    sign_number = anchor.get("sign_number")
    houses = []
    for house in category_houses:
        house_sign = normalize_sign_number(sign_number + house - 1) if sign_number else None
        houses.append(
            {
                "house_from_frame": house,
                "sign_number": house_sign,
                "sign": SIGN_NAMES.get(house_sign),
                "lord": SIGN_LORDS.get(house_sign),
                "lord_name": PLANET_NAMES.get(SIGN_LORDS.get(house_sign), SIGN_LORDS.get(house_sign)),
            }
        )
    return {
        "label": label,
        "chart": chart_key,
        "anchor_sign_number": sign_number,
        "anchor_sign": SIGN_NAMES.get(sign_number),
        "topic_houses": houses,
    }


def build_reference_frames(
    chart_data: dict[str, Any],
    category: str,
    category_houses: list[int],
) -> dict[str, Any]:
    """Expose topic houses from Lagna, Moon, karakas, and the primary varga Lagna."""
    primary_varga = _CATEGORY_PRIMARY_VARGA.get(category, "d9")
    frames = []
    ascendant = get_planet(chart_data, "Asc", "d1") or chart_data.get("ascendant", {})
    if ascendant:
        frames.append(_frame("D1 Lagna", chart_data, "d1", ascendant, category_houses))
    moon = get_planet(chart_data, "Mo", "d1")
    if moon:
        frames.append(_frame("Moon as Lagna", chart_data, "d1", moon, category_houses))
    for karaka in _CATEGORY_KARAKAS.get(category, []):
        planet = get_planet(chart_data, karaka, "d1")
        if planet:
            frames.append(
                _frame(
                    f"{PLANET_NAMES.get(karaka, karaka)} as karaka Lagna",
                    chart_data,
                    "d1",
                    planet,
                    category_houses,
                )
            )
    varga_ascendant = get_planet(chart_data, "Asc", primary_varga)
    if varga_ascendant:
        frames.append(
            _frame(
                f"{primary_varga.upper()} Lagna",
                chart_data,
                primary_varga,
                varga_ascendant,
                category_houses,
            )
        )
    return {
        "calculation_status": "active" if frames else "unavailable",
        "category": category,
        "primary_varga": primary_varga,
        "frames": frames,
        "instruction": "Use these calculated frames as evidence. Do not infer derived houses in the LLM.",
        "source_reference": CHAPTER_TEN_REFERENCE,
    }
