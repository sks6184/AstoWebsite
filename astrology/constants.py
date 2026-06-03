"""Shared deterministic astrology constants.

Keep raw calculation data here so chart calculations, dasha facts, and rule
evaluation all read from the same source of truth.
"""

PLANET_NAMES = {
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

PLANET_CODES = {name: code for code, name in PLANET_NAMES.items()}

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_LORD_CODES = {
    "Aries": "Ma",
    "Taurus": "Ve",
    "Gemini": "Me",
    "Cancer": "Mo",
    "Leo": "Su",
    "Virgo": "Me",
    "Libra": "Ve",
    "Scorpio": "Ma",
    "Sagittarius": "Ju",
    "Capricorn": "Sa",
    "Aquarius": "Sa",
    "Pisces": "Ju",
}

SIGN_LORDS = {sign: PLANET_NAMES[code] for sign, code in SIGN_LORD_CODES.items()}

JAIMINI_SIGN_LORD_CODES = {
    1: ["Ma"],
    2: ["Ve"],
    3: ["Me"],
    4: ["Mo"],
    5: ["Su"],
    6: ["Me"],
    7: ["Ve"],
    8: ["Ma", "Ke"],
    9: ["Ju"],
    10: ["Sa"],
    11: ["Sa", "Ra"],
    12: ["Ju"],
}

NAKSHATRAS = [
    ("Ashwini", "Ke"),
    ("Bharani", "Ve"),
    ("Krittika", "Su"),
    ("Rohini", "Mo"),
    ("Mrigashira", "Ma"),
    ("Ardra", "Ra"),
    ("Punarvasu", "Ju"),
    ("Pushya", "Sa"),
    ("Ashlesha", "Me"),
    ("Magha", "Ke"),
    ("Purva Phalguni", "Ve"),
    ("Uttara Phalguni", "Su"),
    ("Hasta", "Mo"),
    ("Chitra", "Ma"),
    ("Swati", "Ra"),
    ("Vishakha", "Ju"),
    ("Anuradha", "Sa"),
    ("Jyeshtha", "Me"),
    ("Mula", "Ke"),
    ("Purva Ashadha", "Ve"),
    ("Uttara Ashadha", "Su"),
    ("Shravana", "Mo"),
    ("Dhanishta", "Ma"),
    ("Shatabhisha", "Ra"),
    ("Purva Bhadrapada", "Ju"),
    ("Uttara Bhadrapada", "Sa"),
    ("Revati", "Me"),
]

NAKSHATRA_LORDS = {name: lord for name, lord in NAKSHATRAS}

VIMSHOTTARI_SEQUENCE = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]

VIMSHOTTARI_YEARS = {
    "Ke": 7,
    "Ve": 20,
    "Su": 6,
    "Mo": 10,
    "Ma": 7,
    "Ra": 18,
    "Ju": 16,
    "Sa": 19,
    "Me": 17,
}

NATURAL_BENEFICS = {"Ju", "Ve"}
CONDITIONAL_BENEFICS = {"Me", "Mo"}
NATURAL_MALEFICS = {"Su", "Ma", "Sa", "Ra", "Ke"}

