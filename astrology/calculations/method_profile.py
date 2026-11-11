"""Named, versioned calculation method profile (M1).

Records the conventions the engine actually used, so tools and answers can
disclose them. The ephemeris entry is detected from Swiss Ephemeris return
flags, never assumed: when the requested data files are absent, Swiss
Ephemeris falls back to its built-in Moshier ephemeris, and that fallback is
recorded here rather than hidden.
"""

import swisseph as swe

METHOD_PROFILE_ID = "lahiri.geometric.truenode.wholesign.v2"
SIDEREAL_MODE = swe.SIDM_LAHIRI
# M1b (owner decision): geometric positions (FLG_TRUEPOS: no light-time or
# aberration correction). With Lahiri this reproduces the owner's Jagannatha
# Hora "Traditional Lahiri" planet longitudes to within 0.4 arcseconds.
POSITION_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_TRUEPOS
# Yogini and Chara dashas keep a fixed year by owner decision (M1b).
FIXED_DASHA_YEAR_DAYS = 365.2425

EPHEMERIS_LABELS = {
    "swiss_ephemeris_files": "Swiss Ephemeris data files (.se1)",
    "moshier": "Moshier analytical ephemeris built into Swiss Ephemeris (data files not found)",
    "jpl": "JPL ephemeris file",
    "mixed": "Mixed: some bodies used a fallback ephemeris",
    "unknown": "Not detected",
}


def ephemeris_from_flags(return_flags) -> str:
    """Classify the ephemeris that Swiss Ephemeris actually used, from ``calc_ut`` return flags."""
    kinds = set()
    for flag in return_flags:
        if flag & swe.FLG_JPLEPH:
            kinds.add("jpl")
        elif flag & swe.FLG_SWIEPH:
            kinds.add("swiss_ephemeris_files")
        elif flag & swe.FLG_MOSEPH:
            kinds.add("moshier")
        else:
            kinds.add("unknown")
    if not kinds:
        return "unknown"
    return kinds.pop() if len(kinds) == 1 else "mixed"


def build_method_profile(ephemeris: str) -> dict:
    return {
        "profile": METHOD_PROFILE_ID,
        "ayanamsa": "Lahiri (swe.SIDM_LAHIRI)",
        "zodiac": "sidereal",
        "planet_positions": "geometric (swe.FLG_TRUEPOS: no light-time or aberration correction)",
        "lunar_node": "true node (swe.TRUE_NODE); Ketu = Rahu + 180 degrees",
        "houses": "whole-sign from the sidereal ascendant",
        "ephemeris_requested": "Swiss Ephemeris data files (FLG_SWIEPH)",
        "ephemeris_used": ephemeris,
        "ephemeris_used_label": EPHEMERIS_LABELS.get(ephemeris, ephemeris),
        "swiss_ephemeris_version": swe.version,
        "vimshottari_year": "true sidereal solar year (Sun's sidereal advance of 360 degrees per year)",
        "vimshottari_birth_mahadasha": "full period starting before birth; elapsed part from the Moon's position in its nakshatra",
        "yogini_chara_year_days": FIXED_DASHA_YEAR_DAYS,
        "dasha_interval_convention": "[start, end)",
        "transit_sampling": "daily at 12:00 UTC (agent tools)",
    }
