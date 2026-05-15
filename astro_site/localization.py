SUPPORTED_LANGUAGES = [
    ("English", "English"),
    ("Hindi", "Hindi"),
    ("Telugu", "Telugu"),
    ("Marathi", "Marathi"),
    ("Kannada", "Kannada"),
    ("Tamil", "Tamil"),
    ("Bengali", "Bengali"),
    ("Vietnamese", "Vietnamese"),
    ("Mandarin", "Mandarin"),
    ("Malay", "Malay"),
]

SUPPORTED_LANGUAGE_VALUES = {value for value, _ in SUPPORTED_LANGUAGES}


def normalize_language(language):
    return language if language in SUPPORTED_LANGUAGE_VALUES else "English"


def remedy_devotion_note(language):
    from charts.remedies import DEVOTION_NOTES, normalize_language as normalize_remedy_language

    return DEVOTION_NOTES[normalize_remedy_language(language)]
