"""Loader and validator for the M3 domain investigation guidance (domains.v0.yaml).

The file is data (A1, G-6). This module checks its shape and bounds, and hands the model only the
guidance for the domains and events the model itself labelled. It has no per-domain branches, no
tool sequences and no interpretations; ``research_annex`` is never returned (owner instruction).
"""
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
import hashlib
from pathlib import Path
import re

import yaml

PROFILE_PATH = Path(__file__).with_name('domains.v0.yaml')
MAX_DOMAIN_VOCABULARY = 8
MAX_TOTAL_VOCABULARY = 100
MAX_LABELLED_DOMAINS = 3
QUESTION_TYPES = ('factual_lookup', 'concept_explanation', 'natal_assessment', 'predictive_timing',
                  'comparative_decision', 'out_of_scope')
# Question types for which every core factor must be examined or disclosed (A1, M3-AC7).
COVERAGE_TYPES = frozenset(('natal_assessment', 'predictive_timing', 'comparative_decision'))
TIMING_TYPES = frozenset(('predictive_timing', 'comparative_decision'))
PLANET_CODES = frozenset(('Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ra', 'Ke'))
DASHA_SYSTEMS = frozenset(('vimshottari', 'chara', 'yogini'))
REQUIRED_DOMAIN_KEYS = ('label', 'rule_categories', 'houses', 'natural_karakas', 'vargas', 'dasha_systems',
                        'core_factors', 'vocabulary', 'sensitivity', 'known_gaps')
# Guidance must say what to examine, never in what order to call tools (A1) or what a factor means (G-6).
SEQUENCE_MARKERS = re.compile(r'\b(step\s*\d|first,?\s+(call|request|run|use)|then\s+(call|request|run)|'
                              r'after\s+that|followed\s+by|in\s+this\s+order)\b|->|→', re.I)
VERDICT_MARKERS = re.compile(r'\b(will\s+(bring|give|cause|result|deny|deliver)|(?<!no )guarantees?|ensures?|'
                             r'certainly|always\s+(gives|brings|means))\b', re.I)


class ProfileError(ValueError):
    pass


def _strings(value):
    if type(value) is str:
        yield value
    elif type(value) is dict:
        for item in value.values():
            yield from _strings(item)
    elif type(value) is list:
        for item in value:
            yield from _strings(item)


def _houses(value):
    if type(value) is list:
        return list(value)
    if type(value) is dict:
        result = []
        for item in value.values():
            result.extend(_houses(item) if type(item) in (list, dict) else [])
        result.extend(k for k in value if type(k) is int)
        return result
    return []


def _vargas(value):
    """Varga keys from a list, or from a {primary: [...], supplementary: {d16: why}} mapping."""
    if type(value) is list:
        return [v for v in value if type(v) is str]
    result = []
    for item in (value.values() if type(value) is dict else ()):
        result.extend(_vargas(item) if type(item) is list else list(item) if type(item) is dict else [])
    return result


def validate_profile(data):
    """Raise ProfileError for any schema, bound or content-policy violation. Returns data."""
    from astrology.calculations.varga import SUPPORTED_VARGAS
    from astrology.tools.adapters import CATEGORIES   # exactly what evaluate_astrology_rules accepts

    def fail(message):
        raise ProfileError(message)

    if type(data) is not dict:
        fail('profile must be a mapping')
    for key in ('schema_version', 'revision', 'status', 'principles', 'question_types', 'timing_principles',
                'transit_sav_principle', 'common_vocabulary', 'domains', 'secondary_domains', 'declared_unavailable'):
        if key not in data:
            fail('missing top-level key: ' + key)
    if data['schema_version'] != 0 or type(data['revision']) is not int:
        fail('unsupported schema version')
    if set(data['question_types']) != set(QUESTION_TYPES):
        fail('question_types must be exactly: ' + ', '.join(QUESTION_TYPES))
    categories = set(CATEGORIES)
    domains, secondary = data['domains'], data['secondary_domains']
    if type(domains) is not dict or type(secondary) is not dict or set(domains) & set(secondary):
        fail('domains and secondary_domains must be disjoint mappings')
    vocabulary_total = len(data['common_vocabulary'])
    for name, entry in {**domains, **secondary}.items():
        if not re.fullmatch(r'[a-z][a-z_]{1,40}', name) or type(entry) is not dict:
            fail('invalid domain id: ' + str(name))
        if name in domains:
            missing = [k for k in REQUIRED_DOMAIN_KEYS if k not in entry]
            if missing:
                fail(f'{name}: missing {missing}')
            if type(entry['core_factors']) is not list or not entry['core_factors'] or not all(type(x) is str and x.strip() for x in entry['core_factors']):
                fail(f'{name}: core_factors must be nonempty strings')
            vocab = entry['vocabulary']
            if type(vocab) is not list or len(vocab) > MAX_DOMAIN_VOCABULARY or not all(type(v) is dict and type(v.get('term')) is str for v in vocab):
                fail(f'{name}: vocabulary must list at most {MAX_DOMAIN_VOCABULARY} terms')
            vocabulary_total += len(vocab)
            for other in entry.get('distinct_from', []):
                if other not in domains:
                    fail(f'{name}: distinct_from names an unknown domain {other}')
            for event, guide in entry.get('event_guides', {}).items():
                if not re.fullmatch(r'[a-z][a-z_]{1,60}', event) or type(guide) is not dict or type(guide.get('focus')) is not str:
                    fail(f'{name}.{event}: an event guide needs a focus')
                if set(guide) - {'focus', 'note', 'basis_note'}:
                    fail(f'{name}.{event}: unknown event-guide keys')
            if 'disclosure' in entry and (type(entry['disclosure']) is not str or not 20 <= len(entry['disclosure']) <= 400):
                fail(f'{name}: disclosure must be 20-400 characters')
        if not set(entry.get('rule_categories', [])) <= categories:
            fail(f'{name}: unknown rule category')
        if not set(_vargas(entry.get('vargas', []))) <= set(SUPPORTED_VARGAS):
            fail(f'{name}: unsupported varga')
        if not set(entry.get('natural_karakas', [])) <= PLANET_CODES:
            fail(f'{name}: unknown planet code')
        if not set(entry.get('dasha_systems', [])) <= DASHA_SYSTEMS:
            fail(f'{name}: unknown dasha system')
        if not all(type(h) is int and 1 <= h <= 12 for h in _houses(entry.get('houses', []))):
            fail(f'{name}: houses must be 1-12')
    if vocabulary_total > MAX_TOTAL_VOCABULARY:
        fail(f'vocabulary total {vocabulary_total} exceeds {MAX_TOTAL_VOCABULARY}')
    unavailable = data['declared_unavailable']
    if type(unavailable) is not dict or not unavailable or not all(
            re.fullmatch(r'[a-z][a-z_]{1,40}', k) and type(v) is dict and type(v.get('name')) is str for k, v in unavailable.items()):
        fail('declared_unavailable must map ids to {name}')
    guidance = {k: v for k, v in data.items() if k != 'research_annex'}
    for text in _strings(guidance):
        if SEQUENCE_MARKERS.search(text):
            fail('guidance contains a tool sequence marker: ' + text[:80])
        if VERDICT_MARKERS.search(text):
            fail('guidance contains a verdict or interpretation marker: ' + text[:80])
    return data


@dataclass(frozen=True)
class Profile:
    data: dict
    fingerprint: str

    @property
    def primary(self):
        return tuple(self.data['domains'])

    @property
    def domain_ids(self):
        return tuple(self.data['domains']) + tuple(self.data['secondary_domains'])

    @property
    def unavailable_ids(self):
        return tuple(self.data['declared_unavailable'])

    def entry(self, domain):
        return self.data['domains'].get(domain) or self.data['secondary_domains'][domain]

    def event_ids(self, domain):
        return tuple(self.entry(domain).get('event_guides', {}))

    def catalog(self):
        """Round-1 menu: closed labels only, no guidance (the model labels before it is guided)."""
        return {
            'question_types': {k: v['description'] for k, v in self.data['question_types'].items()},
            'domains': {d: {'label': self.entry(d).get('label', d.replace('_', ' ')),
                            'distinct_from': list(self.entry(d).get('distinct_from', [])),
                            'events': list(self.event_ids(d))} for d in self.domain_ids},
            'declared_unavailable': {k: v['name'] for k, v in self.data['declared_unavailable'].items()},
            'principles': list(self.data['principles']),
        }

    def validate_label(self, label):
        """Return a normalized label or raise ProfileError. Unknown labels are rejected, never guessed."""
        if type(label) is not dict or set(label) != {'question_type', 'domains', 'events'}:
            raise ProfileError('label must have question_type, domains and events')
        qtype, domains, events = label['question_type'], label['domains'], label['events']
        if qtype not in QUESTION_TYPES:
            raise ProfileError('unknown question type')
        if type(domains) is not list or not all(type(d) is str for d in domains) or len(set(domains)) != len(domains):
            raise ProfileError('domains must be a list of unique ids')
        if qtype == 'out_of_scope':
            if domains or events:
                raise ProfileError('an out-of-scope question has no domains or events')
            return {'question_type': qtype, 'domains': [], 'events': []}
        if not 1 <= len(domains) <= MAX_LABELLED_DOMAINS or not set(domains) <= set(self.domain_ids):
            raise ProfileError('domains must be 1-3 known domain ids')
        if type(events) is not list or len(events) > 6 or not all(type(e) is str for e in events):
            raise ProfileError('events must be a list of at most 6 ids')
        for event in events:
            domain, _, name = event.partition(':')
            if domain not in domains or name not in self.event_ids(domain):
                raise ProfileError('unknown event for the labelled domains: ' + event[:80])
        return {'question_type': qtype, 'domains': list(domains), 'events': list(dict.fromkeys(events))}

    def guidance_for(self, label):
        """Guidance for the labelled domains and events only. Never includes research_annex."""
        qtype = label['question_type']
        result = {'principles': list(self.data['principles']),
                  'question_type': {qtype: deepcopy(self.data['question_types'][qtype])},
                  'common_vocabulary': deepcopy(self.data['common_vocabulary']), 'domains': {}}
        if qtype in TIMING_TYPES:
            result['timing_principles'] = list(self.data['timing_principles'])
            result['transit_sav_principle'] = list(self.data['transit_sav_principle'])
        selected = set(label['events'])
        for domain in label['domains']:
            entry = deepcopy(self.entry(domain))
            guides = entry.pop('event_guides', {})
            entry['event_guides'] = {k: v for k, v in guides.items() if f'{domain}:{k}' in selected}
            entry['other_events'] = [k for k in guides if f'{domain}:{k}' not in selected]
            if entry.get('jaimini_points') and 'jaimini_conventions' not in result:
                result['jaimini_conventions'] = deepcopy(self.data.get('jaimini_conventions', {}))
            result['domains'][domain] = entry
        result['declared_unavailable'] = {k: v['name'] for k, v in self.data['declared_unavailable'].items()}
        return result

    def core_factors(self, label):
        """(factor_id, domain, text) for every core factor the label requires, else ()."""
        if label['question_type'] not in COVERAGE_TYPES:
            return ()
        return tuple((f'{d}:{i + 1}', d, text) for d in label['domains'] if d in self.data['domains']
                     for i, text in enumerate(self.data['domains'][d]['core_factors']))

    def disclosures(self, label):
        return [self.data['domains'][d]['disclosure'] for d in label['domains']
                if d in self.data['domains'] and self.data['domains'][d].get('disclosure')]

    def has_basis_note(self, label):
        for event in label['events']:
            domain, _, name = event.partition(':')
            if self.entry(domain).get('event_guides', {}).get(name, {}).get('basis_note'):
                return True
        return any(self.entry(d).get('basis_note') for d in label['domains'])

    def unavailable_name(self, key):
        return self.data['declared_unavailable'][key]['name']

    def declined_by_policy(self, key):
        return bool(self.data['declared_unavailable'][key].get('declined_by_policy'))


def _load(path):
    raw = Path(path).read_bytes()
    data = yaml.safe_load(raw.decode('utf-8'))
    return Profile(validate_profile(data), hashlib.sha256(raw).hexdigest()[:16])


@lru_cache(maxsize=4)
def _cached(path, mtime_ns):
    return _load(path)


def load_profile(path=PROFILE_PATH):
    path = Path(path)
    return _cached(str(path), path.stat().st_mtime_ns)
