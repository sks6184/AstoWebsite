"""Deterministic calculation plan for a labelled question.

The plan is data-driven: houses, karakas, vargas, Jaimini points, dasha systems and rule categories come
from the domain profile (``domains.v0.yaml``, which carries the owner-approved event-matrix guidance), and
every labelled domain and event is merged. Nothing here interprets a chart or decides a rule.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
import re

from astrology.calculations.counted_signs import REFERENCES
from astrology.calculations.varga import SUPPORTED_VARGAS
from astrology.methodology.profile import TIMING_TYPES, _vargas
from astrology.tools.adapters import CATEGORIES
from astrology.tools.contracts import MAX_DAYS
from astrology.validation.prose_validator import PLANET_WORDS

DEFAULT_DAYS = 365
TRANSIT_PLANETS = ('Ju', 'Sa', 'Ra', 'Ke')      # slow movers used for timing confirmation (AGENTS.md)
MAX_RULE_CATEGORIES = 2
ORDINAL = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)\b')
COUNTED = re.compile(r'^(\d{1,2})(?:st|nd|rd|th)_from_(arudha_lagna|upapada_lagna|karakamsha)$')
# Text in the guidance that names something the app does not calculate (ids from declared_unavailable).
UNAVAILABLE_CUES = {'muhurta': r'\bmuhurta\b|\bpanchanga\b', 'kp': r'\bKP\b', 'shadbala': r'\bshadbala\b',
                    'kundli_matching': r"partner's own chart|child's own chart|two-chart|kundli matching",
                    'strength_conditions': r'\bcombust|neechabhanga|mooltrikona|planetary war|vimshopaka'}


@dataclass
class Plan:
    label: dict
    window: dict                      # {'start', 'end', 'stated'}
    timing: bool
    houses: dict                      # {'primary': [...], 'supporting': [...], 'event': [...]}
    planets: list                     # karakas and planets named by the labelled events
    vargas: list
    jaimini_points: list
    dasha_systems: list
    rule_categories: list
    events: list                      # [{'id', 'focus', 'note'}]
    calls: list = field(default_factory=list)          # [{'tool', 'args', 'reason'}]
    unsupported: list = field(default_factory=list)    # [{'id', 'name', 'why'}]

    @property
    def focus_houses(self):
        return list(dict.fromkeys(self.houses['primary'] + self.houses['event'] + self.houses['supporting']))

    def summary(self):
        return {'window': self.window, 'timing': self.timing, 'houses': self.houses, 'planets': self.planets,
                'vargas': self.vargas, 'jaimini_points': self.jaimini_points, 'dasha_systems': self.dasha_systems,
                'rule_categories': self.rule_categories, 'events': [e['id'] for e in self.events],
                'calls': [{'tool': c['tool'], 'args': c['args']} for c in self.calls],
                'unsupported': [u['id'] for u in self.unsupported]}


MONTH_COUNT = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'nine': 9, 'twelve': 12, 'eighteen': 18}


def stated_window(question, today):
    """The period a question states in plain calendar words, or None. Deterministic, so the same words always
    give the same window: "next year" is the next calendar year, "this year" runs to 31 December."""
    text = str(question).casefold()
    year = re.search(r'\bin\s+(20\d{2})\b', text)
    span = re.search(r'\b(?:next|coming|within|in\s+the\s+next)\s+(\d{1,2}|' + '|'.join(MONTH_COUNT) + r')\s+(months?|years?)\b', text)
    if re.search(r'\bnext\s+year\b', text):
        start, end = date(today.year + 1, 1, 1), date(today.year + 1, 12, 31)
    elif re.search(r'\bthis\s+year\b', text):
        start, end = today, date(today.year, 12, 31)
    elif year and today.year <= int(year.group(1)) <= today.year + 3:
        start, end = max(today, date(int(year.group(1)), 1, 1)), date(int(year.group(1)), 12, 31)
    elif span:
        count = MONTH_COUNT.get(span.group(1)) or int(span.group(1))
        days = count * (365 if span.group(2).startswith('year') else 30)
        start, end = today, today + timedelta(days=min(days, MAX_DAYS - 1))
    else:
        return None
    return {'start': start.isoformat(), 'end': end.isoformat(), 'stated': True}


def clamp_window(window, today):
    """A valid ISO window inside the tools' range; the default is today to twelve months ahead."""
    default = {'start': today.isoformat(), 'end': (today + timedelta(days=DEFAULT_DAYS)).isoformat(), 'stated': False}
    try:
        start, end = date.fromisoformat(window['start']), date.fromisoformat(window['end'])
    except (TypeError, KeyError, ValueError):
        return default
    if end < start or not 1800 <= start.year <= end.year <= 2200:
        return default
    if (end - start).days + 1 > MAX_DAYS:
        end = start + timedelta(days=MAX_DAYS - 1)
    return {'start': start.isoformat(), 'end': end.isoformat(), 'stated': bool(window.get('stated'))}


def _domain_houses(entry):
    houses = entry.get('houses') or []
    if type(houses) is list:
        return list(houses), []
    primary = list(houses.get('primary') or [])
    supporting = []
    for key in ('supporting', 'retained_from_app'):
        supporting += [int(h) for h in (houses.get(key) or [])]
    return primary, supporting


def _text_focus(text):
    """Houses, planets and vargas named in a guidance sentence (plain text lookup, no interpretation)."""
    houses = [int(m) for m in ORDINAL.findall(text) if 1 <= int(m) <= 12]
    if re.search(r'\bLagna\b(?! lord)', text) and not re.search(r'\bD\d+ Lagna\b', text):
        houses.append(1)
    planets = [code for word, code in PLANET_WORDS.items() if re.search(rf'\b{word}\b', text, re.I)]
    vargas = ['d' + m for m in re.findall(r'\bD(\d{1,2})\b', text)]
    return houses, planets, vargas


def build_plan(profile, label, window, today):
    """Merge every labelled domain and event into one deduplicated list of deterministic calls."""
    window = clamp_window(window, today)
    qtype = label['question_type']
    timing = qtype in TIMING_TYPES
    primary, supporting, event_houses, planets, vargas = [], [], [], [], ['d1', 'd9']
    jaimini, systems, categories, events, guidance_text = [], [], [], [], []
    for domain in label['domains']:
        entry = profile.entry(domain)
        p, s = _domain_houses(entry)
        primary += p
        supporting += s
        planets += list(entry.get('natural_karakas') or [])
        vargas += _vargas(entry.get('vargas') or [])
        jaimini += list(entry.get('jaimini_points') or [])
        systems += list(entry.get('dasha_systems') or ['vimshottari', 'yogini'])
        categories += [c for c in entry.get('rule_categories') or [] if c in CATEGORIES]
        guidance_text += [str(x) for x in entry.get('core_factors') or []] + [str(entry.get('note') or '')]
    for event in label['events']:
        domain, _, name = event.partition(':')
        guide = profile.entry(domain).get('event_guides', {}).get(name) or {}
        focus = str(guide.get('focus') or '')
        h, p, v = _text_focus(focus)
        derived = {int(k): str(text) for k, text in (guide.get('derived_houses') or {}).items()}
        event_houses += h + list(derived)
        planets += p
        vargas += v
        own = list(dict.fromkeys(_domain_houses(profile.entry(domain))[0] + h))
        # Each event keeps its own houses, derived relationships, opposing factors and rule outcomes, so
        # that two events asked together are weighed separately and never merged into one verdict.
        events.append({'id': event, 'focus': focus, 'note': str(guide.get('note') or ''), 'houses': own, 'derived': derived,
                       'opposing': str(guide.get('opposing') or ''), 'rule_outcomes': list(guide.get('rule_outcomes') or [])})
        guidance_text += [focus, str(guide.get('note') or '')]
    order = lambda items: list(dict.fromkeys(items))
    primary = order(primary)
    event_houses = [h for h in order(event_houses) if h not in primary]
    supporting = [h for h in order(supporting) if h not in primary and h not in event_houses]
    vargas = sorted({v for v in vargas if v in SUPPORTED_VARGAS}, key=lambda v: int(v[1:]))
    systems = order(['vimshottari'] + systems)
    plan = Plan(label=label, window=window, timing=timing,
                houses={'primary': primary, 'event': event_houses, 'supporting': supporting},
                planets=order(planets), vargas=vargas, jaimini_points=order(jaimini), dasha_systems=systems,
                rule_categories=order(categories)[:MAX_RULE_CATEGORIES], events=events)
    if qtype == 'concept_explanation':
        return plan                                   # retrieval and explanation only
    add = lambda tool, reason, **args: plan.calls.append({'tool': tool, 'args': args, 'reason': reason})
    add('get_chart_facts', 'Natal and divisional placements and house lords for the labelled areas.',
        charts=vargas, include_yogas=True)
    add('get_natal_aspects', 'Parashari aspects on the houses and planets in focus.')
    add('get_ashtakavarga', 'Ashtakavarga strength of the signs in focus and of transited signs.', kind='both')
    if plan.jaimini_points:
        add('get_jaimini_facts', 'Chara karakas, Karakamsha and house padas for the Jaimini view.')
        for point in plan.jaimini_points:
            m = COUNTED.match(point)
            if m and m.group(2) in REFERENCES and 1 <= int(m.group(1)) <= 12:
                add('get_counted_sign', f'Jaimini point {point}.', reference=m.group(2), count=int(m.group(1)))
    span = {'start_date': window['start'], 'end_date': window['end']} if timing else \
           {'start_date': today.isoformat(), 'end_date': today.isoformat()}
    for system in systems if timing else ['vimshottari']:
        add('get_dasha_periods', f'{system.title()} periods ' + ('across the window.' if timing else 'running now.'),
            system=system, granularity='antardasha', **span)
    if timing:
        add('get_transits', 'Slow-planet transits across the window with Ashtakavarga support.',
            planets=list(TRANSIT_PLANETS), output='segments', **span)
    as_of = window['start'] if timing else today.isoformat()
    for category in plan.rule_categories:
        add('evaluate_astrology_rules', f'Deterministic {category} rules.', category=category, as_of=as_of)
    if timing and plan.rule_categories:
        add('get_timing_candidates', 'Heuristic windows where several dasha systems agree.',
            topic=plan.rule_categories[0], **span)
    text = ' '.join(guidance_text)
    wanted = [key for key, cue in UNAVAILABLE_CUES.items() if re.search(cue, text, re.I)]
    for key in dict.fromkeys(wanted):
        if key in profile.unavailable_ids:
            plan.unsupported.append({'id': key, 'name': profile.unavailable_name(key),
                                     'why': 'named by the guidance for this question; the app does not calculate it'})
    return plan


def supplementary_calls(plan, tables):
    """One bounded follow-up, decided from the results (never by the model): when the window spans several
    sub-periods, or the rule engine reports conflicting signals, re-evaluate the rules at the later
    sub-period starts so the brief can show whether the picture changes inside the window."""
    if not plan.timing or not plan.rule_categories:
        return []
    starts = [p['start'] for p in tables.dashas.get('vimshottari', []) if plan.window['start'] < p['start'] <= plan.window['end']]
    reasons = []
    if starts:
        reasons.append('the window spans more than one Vimshottari sub-period')
    if tables.conflicts and not starts:
        starts = [plan.window['end']]
        reasons.append('the rule engine reports conflicting signals')
    calls = []
    for when in list(dict.fromkeys(starts))[:2]:
        calls.append({'tool': 'evaluate_astrology_rules', 'supplementary': True,
                      'args': {'category': plan.rule_categories[0], 'as_of': when},
                      'reason': f'Supplementary: {" and ".join(reasons)}; rules re-evaluated as of {when}.'})
    return calls
