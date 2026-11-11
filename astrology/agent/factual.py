"""Deterministic factual shortcut for the general agent (M3-AC2): zero LLM calls.

Domain-neutral lookups only: any house lord, a planet's placement in a computed varga, and the running
Vimshottari, Yogini or Chara period. Anything with a predictive or evaluative word goes to the agent.
The answer text is the server's own fact-atom wording, so every value is bound to a tool result.
"""
from dataclasses import dataclass
import re

from astrology.calculations.varga import SUPPORTED_VARGAS
from astrology.validation.prose_validator import ORDINAL_WORDS, PLANET_WORDS, VARGA_WORDS

PREDICTIVE = re.compile(r'\b(will|would|should|could|can|when|why|how|mean|means|meaning|effects?|affects?|good|bad|'
                        r'favou?rable|promising|predict\w*|indicat\w*|suggest\w*|brings?|chances?|likely|future|happen\w*|'
                        r'strong|weak|better|worse|help|impact\w*|result\w*|and)\b', re.I)
ORDINAL = r'(1st|2nd|3rd|[4-9]th|1[0-2]th|' + '|'.join(ORDINAL_WORDS) + r')'
DASHA = re.compile(r'\b(maha\s?dasha|mahadasa|dasha|dasa|antar\s?dasha|sub-?period|period)\b', re.I)
NOW = re.compile(r'\b(current|currently|running|now|present|am i in|at the moment|today)\b', re.I)


@dataclass(frozen=True)
class FactualQuery:
    kind: str                # house_lord | placement | current_period
    varga: str = 'd1'
    house: int | None = None
    planet: str | None = None
    system: str = 'vimshottari'


def _ordinal(text):
    text = text.casefold()
    return ORDINAL_WORDS[text] if text in ORDINAL_WORDS else int(re.match(r'\d+', text).group())


def _varga(q):
    found = {'d' + m for m in re.findall(r'\bd(\d{1,2})\b', q)} | {v for w, v in VARGA_WORDS.items() if re.search(r'\b' + w + r'\b', q)}
    if len(found) > 1:
        return None
    key = found.pop() if found else 'd1'
    return key if key in SUPPORTED_VARGAS else None


def match_factual(question):
    """Return a FactualQuery for a plain calculated-fact question, else None (the agent handles it)."""
    if type(question) is not str or len(question) > 300:
        return None
    q = question.casefold().strip()
    if PREDICTIVE.search(q) or q.count('?') > 1 or 'transit' in q:
        return None
    varga = _varga(q)
    if varga is None:
        return None
    lord = (re.search(r'\b(?:lord|ruler)\s+of\s+(?:my\s+|the\s+)?' + ORDINAL + r'(?:\s+house)?\b', q) or
            re.search(r'\b' + ORDINAL + r'[\s-]+(?:house\s+)?(?:lord|ruler)\b', q) or
            re.search(r'\brules?\s+(?:my\s+|the\s+)?' + ORDINAL + r'\s+house\b', q))
    if lord and re.search(r'\b(who|which|what)\b', q):
        house = _ordinal(lord.group(1))
        return FactualQuery('house_lord', varga, house=house) if 1 <= house <= 12 else None
    if re.search(r'\b(lagna|ascendant)\s+(lord|ruler)\b', q) and re.search(r'\b(who|which|what)\b', q):
        return FactualQuery('house_lord', varga, house=1)
    planets = {code for word, code in PLANET_WORDS.items() if re.search(r'\b' + word + r'\b', q)}
    if len(planets) == 1 and re.search(r'\b(where|which (?:sign|house)|what (?:sign|house)|placed|placement|position|located)\b', q):
        return FactualQuery('placement', varga, planet=planets.pop())
    if DASHA.search(q) and NOW.search(q) and not planets and varga == 'd1':
        system = 'yogini' if 'yogini' in q else 'chara' if 'chara' in q else 'vimshottari'
        return FactualQuery('current_period', system=system)
    return None


def factual_arguments(query, today):
    if query.kind == 'current_period':
        return 'get_dasha_periods', {'system': query.system, 'start_date': today.isoformat(), 'end_date': today.isoformat(),
                                     'granularity': 'antardasha'}
    return 'get_chart_facts', {'charts': [query.varga]}


def select_atoms(query, catalog):
    import json
    chosen = []
    for atom in catalog.values():
        value = json.loads(atom['value'])
        path = ' '.join(atom['bindings'].values())
        if query.kind == 'house_lord' and atom['kind'] == 'lord' and value.get('house') == query.house and f'/charts/{query.varga}/' in path:
            chosen.append(atom)
        elif query.kind == 'placement' and atom['kind'] == 'position' and value.get('code') == query.planet and f'/charts/{query.varga}/' in path:
            chosen.append(atom)
        elif query.kind == 'current_period' and atom['kind'] == 'dasha':
            chosen.append(atom)
    return chosen[:2]
