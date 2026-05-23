"""
Detect whether a user's question is a periodic rashifal (horoscope reading)
and which time horizon it targets: weekly, monthly, or annual.

Strong Hindi/Urdu periodic terms alone are enough to trigger rashifal mode.
English terms (weekly, monthly, yearly) only trigger rashifal when paired with
a rashifal/horoscope trigger word, because those words also appear in regular
prediction questions ("when will I get a job this month?").
"""

# Trigger words that indicate a periodic reading request
_RASHIFAL_TRIGGERS = {
    "rashifal", "raashifal", "horoscope", "bhavishya", "bhavishyafal",
    "kundali reading", "reading", "forecast", "prediction",
}

# Strong Hindi/Urdu terms — alone imply a periodic reading
_STRONG_WEEKLY = {
    "saptahik", "saptahik rashifal", "hafte ka", "hafte ki", "hafte hafta",
    "saptah ka", "saptah ki", "7 din ka", "saat din ka",
}
_STRONG_MONTHLY = {
    "masik", "maasik", "mahine ka", "mahine ki", "is mahine",
    "masic", "masik rashifal",
}
_STRONG_ANNUAL = {
    "varshik", "saalik", "varsh ka", "varsh ki", "is saal ka",
    "pura saal",
}

# Horizon modifiers — need a rashifal trigger to activate
_WEAK_WEEKLY = {"weekly", "this week", "week's", "weekly reading", "weekly forecast"}
_WEAK_MONTHLY = {"monthly", "this month", "month's", "monthly reading", "monthly forecast"}
_WEAK_ANNUAL = {"yearly", "annual", "this year", "year's", "annual reading", "yearly forecast"}


def detect_rashifal(text: str) -> dict:
    """
    Returns {'is_rashifal': True, 'horizon': 'weekly'|'monthly'|'annual'}
    or      {'is_rashifal': False}.

    Horizon precedence: weekly > monthly > annual.
    'rashifal' alone (no horizon modifier) defaults to annual.
    """
    lowered = text.lower()

    has_trigger = any(kw in lowered for kw in _RASHIFAL_TRIGGERS)
    strong_weekly = any(kw in lowered for kw in _STRONG_WEEKLY)
    strong_monthly = any(kw in lowered for kw in _STRONG_MONTHLY)
    strong_annual = any(kw in lowered for kw in _STRONG_ANNUAL)
    weak_weekly = any(kw in lowered for kw in _WEAK_WEEKLY)
    weak_monthly = any(kw in lowered for kw in _WEAK_MONTHLY)
    weak_annual = any(kw in lowered for kw in _WEAK_ANNUAL)

    is_weekly = strong_weekly or (has_trigger and weak_weekly)
    is_monthly = strong_monthly or (has_trigger and weak_monthly)
    is_annual = strong_annual or (has_trigger and weak_annual)

    if not (has_trigger or strong_weekly or strong_monthly or strong_annual):
        return {"is_rashifal": False}

    # Horizon resolution: weekly beats monthly beats annual
    if is_weekly:
        return {"is_rashifal": True, "horizon": "weekly"}
    if is_monthly:
        return {"is_rashifal": True, "horizon": "monthly"}
    if is_annual or has_trigger:
        return {"is_rashifal": True, "horizon": "annual"}

    return {"is_rashifal": False}
