"""Small explicit English policy. No model calculates dates or astrology."""
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
import re


class ScopeError(ValueError):
    pass


@dataclass(frozen=True)
class Plan:
    kind: str
    topic: str
    windows: tuple[tuple[str, str], ...]
    reason: str
    planet: str | None = None
    transit_sign: str | None = None
    varga: str | None = None


MONTHS = {name: i for i, name in enumerate(
    ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'), 1)}
PLANETS = {'sun': 'Su', 'moon': 'Mo', 'mars': 'Ma', 'mercury': 'Me', 'jupiter': 'Ju',
           'venus': 'Ve', 'saturn': 'Sa', 'rahu': 'Ra', 'ketu': 'Ke'}
SIGNS = ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio',
         'sagittarius', 'capricorn', 'aquarius', 'pisces')


def make_plan(question, today, max_days=1097):
    if type(question) is not str or not question.strip() or len(question.encode('utf-8')) > 4096:
        raise ScopeError('Please provide a question of at most 4096 UTF-8 bytes.')
    q = question.lower()
    selected_planet = next((code for name, code in PLANETS.items() if re.search(r'\b' + name + r'\b', q)), None)
    selected_varga = re.search(r'\bd(?:1|2|3|4|7|9|10|12|16|20|24|27|30|40|45|60)\b', q)
    if re.search(r'(who|which|what).*(rules?|lord|ruler).*(10th|tenth)', q) or re.search(r'(10th|tenth).*(lord|ruler)', q):
        kind = 'house_lord'
    elif ('dasha' in q or 'dasa' in q) and any(s in q for s in ('now', 'current', 'am i in')):
        kind = 'current_dasha'
    elif ('dasha' in q or 'dasa' in q) and any(s in q for s in ('which', 'what', 'show')):
        kind = 'dasha_lookup'
    elif selected_planet and any(s in q for s in ('where', 'longitude', 'position')) and 'transit' not in q:
        kind = 'planet_position'
    elif any(s in q for s in ('sav points', 'bav points', 'ashtakavarga points')):
        kind = 'ashtakavarga_lookup'
    elif 'transit' in q or re.search(r'\b(' + '|'.join(PLANETS) + r') in \w+', q):
        kind = 'transit'
    elif any(s in q for s in ('when', 'next year', 'next month', 'next week', 'last year', 'tomorrow', 'yesterday', 'compare', 'promot', 'job change')) or re.search(r'\b(?:18|19|20|21|22)\d{2}\b', q):
        kind = 'timing'
    else:
        kind = 'assessment'
    topic = 'business' if any(s in q for s in ('business', 'startup')) else 'job' if any(s in q for s in ('career', 'job', 'promot', 'professional growth')) else 'general'
    if kind in ('house_lord', 'current_dasha', 'assessment', 'planet_position', 'ashtakavarga_lookup'):
        windows = [(today, today)]
    else:
        iso = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', q)
        years = re.findall(r'\b(?:18|19|20|21|22)\d{2}\b', q)
        months = list(re.finditer(r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b', q))
        if iso:
            if len(iso) > 2:
                raise ScopeError('Please specify at most two ISO dates.')
            try:
                windows = [(date.fromisoformat(iso[0]), date.fromisoformat(iso[-1]))]
            except ValueError as exc:
                raise ScopeError('The requested date is invalid.') from exc
        elif months:
            if not years or len(set(years)) != 1 or len(months) > 2:
                raise ScopeError('Specify one common year for up to two named months, or use ISO dates.')
            year = int(years[0])
            values = [MONTHS[m.group()[:3]] for m in months]
            if len(values) == 2 and any(s in q for s in (' to ', ' through ', ' until ')):
                windows = [(date(year, values[0], 1), date(year, values[1], monthrange(year, values[1])[1]))]
            else:
                windows = [(date(year, m, 1), date(year, m, monthrange(year, m)[1])) for m in values]
        elif 'next year' in q or years:
            if len(set(years)) > 1:
                raise ScopeError('Please specify an explicit ISO start and end for a multi-year range.')
            year = today.year + 1 if 'next year' in q else int(years[0])
            windows = [(date(year, 1, 1), date(year, 12, 31))]
        elif any(s in q for s in ('next month', 'next week', 'tomorrow', 'yesterday', 'last year', 'years', 'months', 'weeks')):
            raise ScopeError('Please specify named months with a year or ISO start/end dates.')
        else:
            windows = [(today, today + timedelta(days=1095))]
    if any(b < a or a.year < 1800 or b.year > 2200 for a, b in windows):
        raise ScopeError('Invalid or unsupported calendar range.')
    if (max(b for _, b in windows) - min(a for a, _ in windows)).days + 1 > max_days:
        raise ScopeError('Requested horizon exceeds the server calendar limit; narrow the dates.')
    planet = selected_planet
    if kind == 'transit' and planet is None:
        raise ScopeError('Please name the planet for this focused transit lookup.')
    if kind in ('assessment', 'timing') and topic == 'general':
        raise ScopeError('P3 supports career/business assessments; please specify that topic or a factual lookup.')
    transit_sign = next((sign for sign in SIGNS if re.search(r'\b' + sign + r'\b', q)), None) if kind in ('transit', 'ashtakavarga_lookup') else None
    return Plan(kind, topic, tuple((a.isoformat(), b.isoformat()) for a, b in windows),
                'Narrow factual evidence' if kind in ('house_lord', 'current_dasha', 'dasha_lookup', 'planet_position', 'ashtakavarga_lookup', 'transit') else
                'Career evidence: natal D1, professional D10, scoped Vimshottari and deterministic rules; transits confirm timing.', planet, transit_sign,
                selected_varga.group() if selected_varga else 'd1' if kind == 'planet_position' else None)

