from typing import Any


PLANET_CODE_TO_NAME: dict[str, str] = {
    "Su": "Sun",
    "Mo": "Moon",
    "Ma": "Mars",
    "Me": "Mercury",
    "Ju": "Jupiter",
    "Ve": "Venus",
    "Sa": "Saturn",
    "Ra": "Rahu",
    "Ke": "Ketu",
}


def _resolve_planet_name(value: str | None) -> str | None:
    if not value:
        return None
    return PLANET_CODE_TO_NAME.get(value, value)


def _mahadasha_lord(evidence: dict[str, Any]) -> str | None:
    vimshottari = evidence.get("parashari_vimshottari", {}) or {}
    mahadasha = vimshottari.get("current_mahadasha") or {}
    name = mahadasha.get("lord_name") or mahadasha.get("name")
    code = mahadasha.get("lord")
    return name or _resolve_planet_name(code)


def _antardasha_lord(evidence: dict[str, Any]) -> str | None:
    vimshottari = evidence.get("parashari_vimshottari", {}) or {}
    antardasha = vimshottari.get("current_antardasha") or {}
    name = antardasha.get("lord_name") or antardasha.get("name")
    code = antardasha.get("lord")
    return name or _resolve_planet_name(code)


def _mahadasha_dates(evidence: dict[str, Any]) -> str:
    vimshottari = evidence.get("parashari_vimshottari", {}) or {}
    mahadasha = vimshottari.get("current_mahadasha") or {}
    start = mahadasha.get("start_display") or mahadasha.get("start", "")
    end = mahadasha.get("end_display") or mahadasha.get("end", "")
    if start and end:
        return f"{start} to {end}"
    return ""


def _antardasha_dates(evidence: dict[str, Any]) -> str:
    vimshottari = evidence.get("parashari_vimshottari", {}) or {}
    antardasha = vimshottari.get("current_antardasha") or {}
    start = antardasha.get("start_display") or antardasha.get("start", "")
    end = antardasha.get("end_display") or antardasha.get("end", "")
    if start and end:
        return f"{start} to {end}"
    return ""


def _yogini_major_lord(evidence: dict[str, Any]) -> str | None:
    yogini = evidence.get("yogini", {}) or {}
    if yogini.get("calculation_status") != "active":
        return None
    dasha = yogini.get("current_yogini_dasha") or {}
    return dasha.get("yogini") or dasha.get("lord_name") or _resolve_planet_name(dasha.get("lord"))


def _yogini_sub_lord(evidence: dict[str, Any]) -> str | None:
    yogini = evidence.get("yogini", {}) or {}
    if yogini.get("calculation_status") != "active":
        return None
    sub = yogini.get("current_yogini_subperiod") or {}
    return sub.get("yogini") or sub.get("lord_name") or _resolve_planet_name(sub.get("lord"))


def _jaimini_active_sign(evidence: dict[str, Any]) -> str | None:
    jaimini = evidence.get("jaimini", {}) or {}
    if jaimini.get("calculation_status") != "active":
        return None
    chara = jaimini.get("chara_dasha") or {}
    current = chara.get("current_period") or chara.get("active_period") or {}
    return current.get("sign") or current.get("rashi")


def _jaimini_atmakaraka(evidence: dict[str, Any]) -> str | None:
    jaimini = evidence.get("jaimini", {}) or {}
    if jaimini.get("calculation_status") != "active":
        return None
    karakas = jaimini.get("karakas") or {}
    atma = karakas.get("atmakaraka") or {}
    return atma.get("name") or _resolve_planet_name(atma.get("code"))


def _jaimini_amatyakaraka(evidence: dict[str, Any]) -> str | None:
    jaimini = evidence.get("jaimini", {}) or {}
    if jaimini.get("calculation_status") != "active":
        return None
    karakas = jaimini.get("karakas") or {}
    amatya = karakas.get("amatyakaraka") or {}
    return amatya.get("name") or _resolve_planet_name(amatya.get("code"))


def check_specificity(answer: str, evidence: dict[str, Any]) -> list[str]:
    """
    Fails answers that mention dasha systems by name (Vimshottari, Jaimini, Yogini)
    without naming the actual active lords, signs, and periods from the evidence payload.
    """
    issues = []
    lowered = answer.lower()

    # --- Vimshottari / Parashari specificity ---
    mahadasha_name = _mahadasha_lord(evidence)
    antardasha_name = _antardasha_lord(evidence)

    vimshottari_referenced = any(
        term in lowered for term in ["vimshottari", "mahadasha", "antardasha", "parashari", "dasha lord"]
    )
    if vimshottari_referenced and mahadasha_name:
        if mahadasha_name.lower() not in lowered:
            dates = _mahadasha_dates(evidence)
            ad_hint = f" / {antardasha_name} Antardasha" if antardasha_name else ""
            date_hint = f" ({dates})" if dates else ""
            issues.append(
                f"Answer references Vimshottari/Parashari timing without naming the active Mahadasha lord. "
                f"Write '{mahadasha_name} Mahadasha{ad_hint}{date_hint}' — "
                f"do NOT write 'current Mahadasha' or 'Vimshottari period' without the lord name."
            )
        elif antardasha_name and antardasha_name.lower() not in lowered:
            dates = _antardasha_dates(evidence)
            date_hint = f" ({dates})" if dates else ""
            issues.append(
                f"Answer names the Mahadasha lord but omits the Antardasha lord. "
                f"Write '{mahadasha_name} Mahadasha / {antardasha_name} Antardasha{date_hint}'."
            )

    # --- Yogini specificity ---
    yogini_major = _yogini_major_lord(evidence)
    yogini_sub = _yogini_sub_lord(evidence)

    if "yogini" in lowered and yogini_major:
        if yogini_major.lower() not in lowered:
            sub_hint = f" with {yogini_sub} sub-period" if yogini_sub else ""
            issues.append(
                f"Answer mentions Yogini but does not name the active Yogini lord '{yogini_major}'. "
                f"Write 'current {yogini_major} Yogini major period{sub_hint}' — "
                f"do NOT write 'Yogini indicates' without the lord name."
            )
        elif yogini_sub and yogini_sub.lower() not in lowered and yogini_sub.lower() != yogini_major.lower():
            issues.append(
                f"Answer names the Yogini major lord but omits the sub-period lord '{yogini_sub}'. "
                f"Write '{yogini_major} Yogini / {yogini_sub} sub-period'."
            )

    # --- Jaimini specificity ---
    jaimini_referenced = any(
        term in lowered for term in ["jaimini", "chara", "chara dasha", "karaka"]
    )
    if jaimini_referenced:
        jaimini_sign = _jaimini_active_sign(evidence)
        if jaimini_sign and jaimini_sign.lower() not in lowered:
            issues.append(
                f"Answer mentions Jaimini/Chara without naming the active Chara Dasha sign '{jaimini_sign}'. "
                f"Write '{jaimini_sign} Chara Dasha' — do NOT write 'Jaimini indicates' without the sign."
            )

        atmakaraka = _jaimini_atmakaraka(evidence)
        if "atmakaraka" in lowered and atmakaraka and atmakaraka.lower() not in lowered:
            issues.append(
                f"Atmakaraka is mentioned but the planet '{atmakaraka}' is not named. "
                f"Write '{atmakaraka} as Atmakaraka'."
            )

        amatyakaraka = _jaimini_amatyakaraka(evidence)
        if "amatyakaraka" in lowered and amatyakaraka and amatyakaraka.lower() not in lowered:
            issues.append(
                f"Amatyakaraka is mentioned but the planet '{amatyakaraka}' is not named. "
                f"Write '{amatyakaraka} as Amatyakaraka'."
            )

    return issues
