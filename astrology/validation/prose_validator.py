"""Prose validation for the M3 general agent (G-1 to G-5, OD-11, A1, A6, A8, R10).

The model writes natural prose. Every sentence that states a chart value carries an inline tag
such as ``[F0123456789abcdef]`` naming a fact atom from ``fact_catalog.build_catalog(full=True)``.
Literature claims carry ``[K...]`` tags naming a retrieved passage. This module checks that:

* G-1: every astrological value in a claim sentence (planet, sign, house, nakshatra, varga, dasha
  lord, date, number, karaka, pada, yoga) is present in the tagged, still-verifiable atoms;
* G-2 / OD-11: every source mention carries a tag of a retrieved hit, the named title matches it,
  and no 12-word run is copied from a retrieved passage (the M2 leak-check rule);
* G-3 to G-5: no event probabilities or certainty claims; evidence strength is a label with a reason;
* A8 / OD-23: no diagnosis, death, longevity or infertility statements; no invented remedies;
* content elements (A6, R10) rather than headings, and core-factor coverage (A1).

It is deliberately conservative. A regex cannot prove arbitrary prose correct; it can only block the
patterns it recognises, so blocked answers are repaired once and otherwise replaced by the
deterministic evidence report.
"""
from datetime import date
import json
import re

from astrology.constants import NAKSHATRAS, PLANET_NAMES, SIGNS
from astrology.synthesis.fact_catalog import verify_atom

STRENGTH_LABELS = ('limited', 'moderate', 'strong')
TAG = re.compile(r'\[\s*((?:[FK][0-9a-f]{16,20})(?:\s*,\s*[FK][0-9a-f]{16,20})*)\s*\]')
LEAK_SHINGLE = 12          # M2 close-out leak rule, applied to answers (M3-AC12)
MIN_ORDINARY_WORDS = 6     # same filter as the M2 leak check (excludes lists of names)

PLANET_WORDS = {name.casefold(): code for code, name in PLANET_NAMES.items()}
PLANET_WORDS.update({'surya': 'Su', 'chandra': 'Mo', 'mangala': 'Ma', 'mangal': 'Ma', 'kuja': 'Ma', 'budha': 'Me',
                     'guru': 'Ju', 'brihaspati': 'Ju', 'shukra': 'Ve', 'shani': 'Sa'})
SIGN_WORDS = {name.casefold(): i for i, name in enumerate(SIGNS, 1)}
SIGN_WORDS.update({'mesha': 1, 'vrishabha': 2, 'mithuna': 3, 'karka': 4, 'karkata': 4, 'simha': 5, 'kanya': 6,
                   'tula': 7, 'vrischika': 8, 'vrishchika': 8, 'dhanu': 9, 'dhanus': 9, 'makara': 10,
                   'kumbha': 11, 'meena': 12, 'mina': 12})
NAKSHATRA_WORDS = {n.casefold(): n for n, _ in NAKSHATRAS}
VARGA_WORDS = {'rasi': 'd1', 'rashi': 'd1', 'drekkana': 'd3', 'chaturthamsha': 'd4', 'chaturthamsa': 'd4',
               'saptamsha': 'd7', 'saptamsa': 'd7', 'navamsha': 'd9', 'navamsa': 'd9', 'dashamsha': 'd10',
               'dasamsa': 'd10', 'dashamsa': 'd10', 'dwadashamsha': 'd12', 'shodashamsha': 'd16', 'vimshamsha': 'd20',
               'chaturvimshamsha': 'd24', 'siddhamsha': 'd24', 'trimshamsha': 'd30'}
KARAKA_WORDS = {'atmakaraka': 'Atmakaraka', 'ak': 'Atmakaraka', 'amatyakaraka': 'Amatyakaraka', 'amk': 'Amatyakaraka',
                'bhratrukaraka': 'Bhratrukaraka', 'bk': 'Bhratrukaraka', 'matrukaraka': 'Matrukaraka', 'mk': 'Matrukaraka',
                'putrakaraka': 'Putrakaraka', 'pk': 'Putrakaraka', 'gnatikaraka': 'Gnatikaraka', 'gk': 'Gnatikaraka',
                'darakaraka': 'Darakaraka', 'dk': 'Darakaraka'}
PADA_WORDS = {'al': 'AL', 'arudha': 'AL', 'ul': 'UL', 'upapada': 'UL', 'darapada': 'A7', 'karakamsha': 'Karakamsha',
              'karakamsa': 'Karakamsha'}
ORDINAL_WORDS = {w: i for i, w in enumerate(('first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh',
                                             'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth'), 1)}
MONTHS = {m: i for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                      'september', 'october', 'november', 'december'), 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
DASHA_TERMS = re.compile(r'\b(maha\s?dasha|mahadasa|antar\s?dasha|antardasa|dasha|dasa|sub-?period|bhukti|pratyantar\w*)\b', re.I)
STATE_TERMS = re.compile(r'\b(retrograde|exalted|debilitated|combust|own sign|lagna|ascendant|lord|ruler|aspects?|occup\w+|placed|transit\w*)\b', re.I)
SOURCE_TERMS = re.compile(r'\b(BPHS|Brihat Parashara|Parashara Hora|Phaladeepika|Phala Deepika|Saravali|Jataka Parijata|'
                          r'Brihat Jataka|Uttara Kalamrita|Jaimini Sutras?|Bhrigu Samhita|Hora Sara|Sarvartha Chintamani|'
                          r'Prasna Marga|K\.\s?N\.\s?Rao|Sanjay Rath|Narasimha Rao|Varahamihira|'
                          r'according to (?:the |a |one |this )?(?:book|text|source|classic\w*|tradition)|'
                          r'classical (?:texts?|sources?|authorit\w+) (?:say|state|describe|hold|teach)\w*|'
                          r'the (?:book|text|source) (?:says|states|describes|explains|notes))\b', re.I)
SECOND_PERSON = re.compile(r'\b(your|you|you\'re|yours|chart|natal|running|current)\b', re.I)
YOGA_NAME = re.compile(r"\b([A-Z][a-z]+(?:[- ][A-Z][a-z]+)?)\s+[Yy]oga\b")
GENERIC_PHRASES = re.compile(r'\b(planetary movements|cosmic energ\w*|the stars (?:say|suggest|indicate|favou?r)|'
                             r'the universe|celestial influences?|stars are aligned)\b', re.I)
PROBABILITY = re.compile(r'\b\d{1,3}(?:\.\d+)?\s?(?:%|per\s?cent\b|percent\b)|\bprobabilit(?:y|ies)\b|\bodds\b|'
                         r'\blikelihood\b|\bchances?\s+(?:of|that|are|is)\b|\b\d+\s+in\s+\d+\b', re.I)
CERTAINTY = re.compile(r'\b(?<!no )(?<!not )(?:guarantee[sd]?|definitely will|will definitely|certainly will|'
                       r'will certainly|will surely|is certain to|are certain to|without (?:a )?doubt|inevitabl[ey])\b', re.I)
DEATH = re.compile(r'\b(die|dies|dying|death|deaths|lifespan|life span|longevity|fatal|maraka|pass(?:ing)? away)\b', re.I)
# Case-insensitive except "cancer": only the lower-case illness word is caught, never the sign Cancer.
DIAGNOSIS = re.compile(r'(?i:\b(?:diagnos\w*|tumou?rs?|diabetes|heart attack|kidney (?:failure|disease)|chronic illness|'
                       r'you (?:have|will (?:develop|get|suffer from|contract)) (?:a |an )?(?:disease|illness|disorder|condition))\b)|'
                       r'\bcancer\b')
MEDICAL_ADVICE = re.compile(r'\b(medication|dosage|prescri\w+|treatment plan|stop (?:taking|your) \w+)\b', re.I)
FERTILITY = re.compile(r'\b(infertil\w*|barren|sterile|childless|miscarriage|(?:cannot|can\'t|unable to|will not|won\'t|never) '
                       r'(?:conceive|have (?:a )?(?:child|children|baby)))\b', re.I)
REMEDY = re.compile(r'\b(gemstones?|wear (?:a|an) \w+|mantras?|puja|pooja|yantras?|remed(?:y|ies)|donat\w+)\b', re.I)
NUMBER = re.compile(r'(?<![\w.-])(\d+(?:\.\d+)?)(?![\w-])')
DURATION = re.compile(r'\b\d+(?:\.\d+)?\s*-?\s*(?:months?|years?|days?|weeks?|searches|rounds|systems?)\b', re.I)
ISO = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b')
MONTH_YEAR = re.compile(r'\b(' + '|'.join(sorted(MONTHS, key=len, reverse=True)) + r')\.?\s+(\d{4})\b', re.I)
YEAR = re.compile(r'\b(1[89]\d{2}|2[0-2]\d{2})\b')


def _words(text):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)


def extract(text):
    """Astrological value tokens in a text: planets, signs, houses, vargas, dates, numbers and terms."""
    tokens = {'planets': set(), 'signs': set(), 'nakshatras': set(), 'houses': set(), 'vargas': set(),
              'karakas': set(), 'padas': set(), 'yogas': set(), 'numbers': set(), 'dates': []}
    for word in _words(text):
        key = word.casefold().strip("'")
        key = key[:-2] if key.endswith("'s") else key
        if key in PLANET_WORDS:
            tokens['planets'].add(PLANET_WORDS[key])
        if key in SIGN_WORDS and (word[0].isupper() or key not in ('cancer',)):
            tokens['signs'].add(SIGN_WORDS[key])
        if key in NAKSHATRA_WORDS:
            tokens['nakshatras'].add(NAKSHATRA_WORDS[key])
        if key in VARGA_WORDS:
            tokens['vargas'].add(VARGA_WORDS[key])
        if key in KARAKA_WORDS and (len(key) > 3 or word.isupper() or word in ('AmK',)):
            tokens['karakas'].add(KARAKA_WORDS[key])
        if key in PADA_WORDS and (len(key) > 2 or word.isupper()):
            tokens['padas'].add(PADA_WORDS[key])
    tokens['padas'].update('A' + m for m in re.findall(r'\bA(\d{1,2})\b', text) if 1 <= int(m) <= 12)
    tokens['vargas'].update('d' + m for m in re.findall(r'\b[Dd](\d{1,2})\b', text))
    tokens['yogas'].update(m.casefold() for m in YOGA_NAME.findall(text))
    stripped = text
    for m in ISO.finditer(text):
        try:
            tokens['dates'].append(('day', date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
        except ValueError:
            tokens['dates'].append(('invalid', m.group()))
    stripped = ISO.sub(' ', stripped)
    for m in MONTH_YEAR.finditer(stripped):
        tokens['dates'].append(('month', (int(m.group(2)), MONTHS[m.group(1).casefold()[:3]])))
    stripped = MONTH_YEAR.sub(' ', stripped)
    for m in YEAR.finditer(stripped):
        tokens['dates'].append(('year', int(m.group())))
    stripped = YEAR.sub(' ', stripped)
    for m in re.finditer(r'\b(\d{1,2})(?:st|nd|rd|th)\b', stripped):
        if 1 <= int(m.group(1)) <= 12:
            tokens['houses'].add(int(m.group(1)))
    for m in re.finditer(r'\b(' + '|'.join(ORDINAL_WORDS) + r')\s+(?:house|lord|bhava|sign|from)\b', stripped, re.I):
        tokens['houses'].add(ORDINAL_WORDS[m.group(1).casefold()])
    for m in re.finditer(r'\b(?:houses?|bhavas?)\s*\(?s?\)?\s+((?:\d{1,2}(?:\s*(?:,|and|&|or)\s*)?)+)', stripped, re.I):
        tokens['houses'].update(int(x) for x in re.findall(r'\d{1,2}', m.group(1)) if 1 <= int(x) <= 12)
    stripped = re.sub(r'\b(?:houses?|bhavas?)\s*\(?s?\)?\s+(?:\d{1,2}(?:\s*(?:,|and|&|or)\s*)?)+', ' ', stripped, flags=re.I)
    stripped = re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b|\b[Dd]\d{1,2}\b|\bA\d{1,2}\b', ' ', stripped)
    stripped = DURATION.sub(' ', stripped)
    tokens['numbers'].update(float(n) for n in NUMBER.findall(stripped))
    return tokens


def is_claim(text, tokens):
    planet, sign = bool(tokens['planets']), bool(tokens['signs'])
    detail = bool(tokens['houses'] or tokens['nakshatras'] or tokens['karakas'] or tokens['padas'])
    dasha = bool(DASHA_TERMS.search(text))
    state = bool(STATE_TERMS.search(text))
    numeric = bool(tokens['numbers']) and bool(re.search(r'\b(SAV|BAV|bindus?|points?|degrees?|score)\b', text, re.I))
    return bool((planet and (sign or detail or dasha or state)) or (sign and (detail or dasha or state)) or
                tokens['nakshatras'] or (tokens['karakas'] and (planet or sign)) or (tokens['padas'] and (sign or planet or detail)) or
                ((dasha or planet) and tokens['dates']) or numeric or tokens['yogas'])


def _support(atoms):
    """Union of value tokens from tagged atoms (server text and bound values)."""
    support = extract(' '.join(a['text'] for a in atoms))
    support['text'] = ' '.join(a['text'] for a in atoms).casefold()
    support['dates'] = []
    spans = []
    for atom in atoms:
        try:
            value = json.loads(atom['value'])
        except (TypeError, ValueError):
            value = {}
        days = [d for kind, d in extract(atom['text'])['dates'] if kind == 'day']
        for key, item in value.items():
            items = item if type(item) is list else [item]
            for v in items:
                if type(v) is int and ('house' in key or key in ('count',)) and 1 <= v <= 12:
                    support['houses'].add(v)
                if type(v) is int and 'sign_number' in key:
                    support['signs'].add(v)
                if type(v) is str and v in PLANET_NAMES:
                    support['planets'].add(v)
                if type(v) in (int, float) and not isinstance(v, bool):
                    support['numbers'].add(float(v))
                if type(v) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
                    days.append(date.fromisoformat(v))
        for path in atom['bindings'].values():
            m = re.search(r'/charts/(d\d{1,2})/', path)
            if m:
                support['vargas'].add(m.group(1))
        if days:
            spans.append((min(days), max(days)))
    support['spans'] = spans
    return support


def _has(term, text):
    return re.search(r'(?<![a-z0-9])' + re.escape(term.casefold()) + r'(?![a-z0-9])', text) is not None


def _date_supported(token, spans):
    kind, value = token
    if kind == 'invalid':
        return False
    for left, right in spans:
        if kind == 'day' and left <= value <= right:
            return True
        if kind == 'month' and (left.year, left.month) <= value <= (right.year, right.month):
            return True
        if kind == 'year' and left.year <= value <= right.year:
            return True
    return False


def sentences(text):
    """Split prose into sentences, keeping a trailing tag group with the sentence it follows."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip()) if text and text.strip() else []
    merged = []
    for part in parts:
        if merged and re.fullmatch(r'(?:\s*' + TAG.pattern + r')+[.!?]?', part):
            merged[-1] += ' ' + part
        else:
            merged.append(part)
    return merged


def tags(text):
    found = []
    for m in TAG.finditer(text):
        found.extend(x.strip() for x in m.group(1).split(','))
    return found


def _shingles(text, size):
    tokens = re.sub(r'[^a-z0-9]+', ' ', text.casefold()).split()
    return {' '.join(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))}


def _vocabulary():
    names = list(PLANET_NAMES.values()) + list(PLANET_NAMES) + [n for n, _ in NAKSHATRAS] + list(SIGNS)
    return {w for name in names for w in re.sub(r'[^a-z0-9]+', ' ', str(name).casefold()).split()}


def copied_runs(text, passages):
    """12-word runs shared with any retrieved snippet, ignoring runs that are mostly names."""
    vocabulary = _vocabulary()
    answer = _shingles(text, LEAK_SHINGLE)
    runs = set()
    for passage in passages.values():
        for gram in answer & _shingles(passage['snippet'], LEAK_SHINGLE):
            if sum(1 for w in gram.split() if w not in vocabulary and not w.isdigit()) >= MIN_ORDINARY_WORDS:
                runs.add(gram)
    return sorted(runs)


def title_of(citation):
    for key in ('book', 'document', 'filename', 'file_id'):
        value = citation.get(key)
        if value:
            return re.sub(r'\.(pdf|txt|md|docx?)$', '', value, flags=re.I).replace('_', ' ').strip()
    return 'unattributed retrieved source'


def _title_matches(mention, citations):
    words = set(re.sub(r'[^a-z0-9]+', ' ', mention.casefold()).split()) - {'the', 'of', 'a', 'according', 'to', 'book', 'text', 'source'}
    if not words:
        return True
    for citation in citations:
        title = set(re.sub(r'[^a-z0-9]+', ' ', ' '.join(v for v in citation.values() if v).casefold()).split())
        if len(words & title) >= max(1, round(0.6 * len(words))):
            return True
    return False


def _missing(tokens, facts, sourced=False):
    """Values in the sentence that the given fact atoms do not contain (empty list = fully supported)."""
    support = _support(facts)
    missing = []
    missing += [PLANET_NAMES[p] for p in tokens['planets'] - support['planets']]
    missing += [SIGNS[s - 1] for s in tokens['signs'] - support['signs']]
    missing += [f'house {h}' for h in tokens['houses'] - support['houses']]
    missing += [n for n in tokens['nakshatras'] if not _has(n, support['text'])]
    missing += [v.upper() for v in tokens['vargas'] - support['vargas']]
    missing += [k for k in tokens['karakas'] if not _has(k, support['text'])]
    missing += [p for p in tokens['padas'] if not _has(p, support['text'])]
    missing += [y + ' yoga' for y in tokens['yogas'] if not _has(y, support['text']) and not sourced]
    missing += [str(n).rstrip('0').rstrip('.') for n in tokens['numbers'] - support['numbers']]
    missing += [str(d[1]) for d in tokens['dates'] if not _date_supported(d, support['spans'])]
    return missing


TRANSIT_CUE = re.compile(r'\btransit\w*|\bgochar\b', re.I)
# Only atoms with a single role per value: lord, aspect, pada, counted-sign and Moon/Lagna transit-house atoms
# hold two different house roles, so a value bag could ground a false sentence; those need the model's own tag.
NATAL_KINDS = ('position', 'karaka', 'karakamsha', 'yoga', 'jaimini_yoga')


def ground(text, catalog, evidence):
    """Attach a fact tag to an untagged chart-claim sentence when exactly one kind-compatible atom
    contains every value it states (G-1 still holds: each value matches a tool fact). Sentences that
    cannot be grounded this way are left untouched and will fail validation. Returns (text, count)."""
    if not text:
        return text, 0
    count, paragraphs = 0, []
    for paragraph in text.split('\n'):
        out = []
        for sentence in sentences(paragraph):
            bare = TAG.sub(' ', sentence)
            tokens = extract(bare)
            if tags(sentence) or not is_claim(bare, tokens) or SOURCE_TERMS.search(bare):
                out.append(sentence)
                continue
            if TRANSIT_CUE.search(bare):
                kinds = ('transit',) if not tokens['houses'] else ()
            elif DASHA_TERMS.search(bare):
                kinds = ('dasha',) if not tokens['houses'] else ()
            else:
                kinds = NATAL_KINDS
            def compatible(atom):
                path = ' '.join(atom['bindings'].values())
                # With no varga named, a placement claim reads as natal (D1).
                return atom['kind'] != 'position' or tokens['vargas'] or '/charts/d1/' in path
            match = next((a for a in catalog.values() if a['kind'] in kinds and compatible(a)
                          and not _missing(tokens, [a]) and verify_atom(a, evidence)), None)
            if match is None:
                out.append(sentence)
                continue
            end = re.search(r'[.!?]+$', sentence)
            out.append(sentence[:end.start()] + f' [{match["id"]}]' + end.group() if end else sentence + f' [{match["id"]}]')
            count += 1
        paragraphs.append(' '.join(out))
    return '\n'.join(paragraphs), count


def ground_final(final, catalog, evidence):
    """Apply ``ground`` to every model-written text field of a final answer object."""
    if type(final) is not dict:
        return final, 0
    grounded, total = dict(final), 0
    for key in ('direct_answer', 'body'):
        if type(final.get(key)) is str:
            grounded[key], n = ground(final[key], catalog, evidence)
            total += n
    if type(final.get('conflicts')) is list:
        grounded['conflicts'] = []
        for item in final['conflicts']:
            value, n = ground(item, catalog, evidence) if type(item) is str else (item, 0)
            grounded['conflicts'].append(value)
            total += n
    return grounded, total


def check_prose(text, catalog, evidence, passages, *, label='answer'):
    """G-1, G-2 and policy guards over one model-written text. Returns (issues, unsupported, generic)."""
    issues, unsupported, generic = [], [], []
    if not text:
        return issues, unsupported, generic
    if re.search(r'(?m)^\s{0,3}#{1,6}\s', text):
        issues.append(f'{label}: headings_not_allowed')
    for sentence in sentences(text):
        ids = tags(sentence)
        bare = TAG.sub(' ', sentence)
        short = re.sub(r'\s+', ' ', bare).strip()[:90]
        facts, sources = [], []
        for tag in ids:
            if tag.startswith('F'):
                atom = catalog.get(tag)
                if atom is None or not verify_atom(atom, evidence):
                    issues.append(f'{label}: unknown_or_changed_fact_tag {tag[:17]}')
                else:
                    facts.append(atom)
            elif tag in passages:
                sources.append(passages[tag])
            else:
                issues.append(f'{label}: citation_without_retrieved_hit {tag[:21]}')
        tokens = extract(bare)
        if is_claim(bare, tokens):
            viewpoint = sources and not SECOND_PERSON.search(bare)
            if not facts and not viewpoint:
                issues.append(f'{label}: untagged_chart_claim')
                unsupported.append(short)
            elif facts:
                missing = _missing(tokens, facts, bool(sources))
                if missing:
                    issues.append(f'{label}: unverified_value ' + ', '.join(missing[:6]))
                    unsupported.append(short)
        mention = SOURCE_TERMS.search(bare)
        if mention and not sources:
            issues.append(f'{label}: uncited_source_mention')
            unsupported.append(short)
        elif mention and sources and not _title_matches(mention.group(), [s['citation'] for s in sources]):
            issues.append(f'{label}: cited_title_does_not_match_hit')
        if GENERIC_PHRASES.search(bare) and not ids:
            generic.append(GENERIC_PHRASES.search(bare).group())
        for name, pattern in (('event_probability', PROBABILITY), ('certainty_claim', CERTAINTY),
                              ('longevity_or_death_content', DEATH), ('diagnosis_or_illness_prediction', DIAGNOSIS),
                              ('medical_advice', MEDICAL_ADVICE), ('fertility_policy', FERTILITY)):
            if pattern.search(bare):
                issues.append(f'{label}: {name}')
        if REMEDY.search(bare) and not sources:
            issues.append(f'{label}: unsupported_remedy')
    if generic:
        issues.append(f'{label}: generic_phrasing')
    return issues, unsupported, generic


def validate_final(final, *, label, profile, catalog, evidence, passages, conflicts_present):
    """Validate the model's final answer object. Returns the AGENTS.md validation shape plus details."""
    issues, missing, unsupported, generic = [], [], [], []
    keys = {'direct_answer', 'body', 'conflicts', 'evidence_strength', 'coverage', 'unavailable_calculations', 'no_source_support'}
    if type(final) is not dict or set(final) != keys:
        return _result(['invalid_final_structure'], ['all'], [], [])
    direct, body, conflicts = final['direct_answer'], final['body'], final['conflicts']
    strength, coverage = final['evidence_strength'], final['coverage']
    if type(direct) is not str or not 1 <= len(direct.strip()) <= 700:
        missing.append('direct_answer')
    if type(body) is not str or len(body) > 6000:
        issues.append('body_size_or_type')
        body = ''
    if type(conflicts) is not list or len(conflicts) > 6 or not all(type(c) is str and 0 < len(c) <= 600 for c in conflicts):
        issues.append('conflicts_invalid')
        conflicts = []
    if type(strength) is not dict or set(strength) != {'label', 'reason'} or strength.get('label') not in STRENGTH_LABELS:
        missing.append('evidence_strength_label')
        strength = {'label': None, 'reason': ''}
    if type(strength.get('reason')) is not str or len(strength['reason'].strip()) < 20:
        missing.append('evidence_strength_reason')
    texts = [('direct_answer', direct if type(direct) is str else ''), ('body', body),
             *((f'conflict_{i + 1}', c) for i, c in enumerate(conflicts)),
             ('evidence_strength_reason', strength.get('reason') or '')]
    for name, text in texts:
        found, claims, phrases = check_prose(text, catalog, evidence, passages, label=name)
        issues.extend(found)
        unsupported.extend(claims)
        generic.extend(phrases)
    used = {t for _, text in texts for t in tags(text)}
    qtype = label['question_type']
    if qtype not in ('concept_explanation', 'out_of_scope') and not any(t.startswith('F') and t in catalog for t in used):
        missing.append('calculated_factors_used')
    if conflicts_present and not conflicts:
        missing.append('conflicting_signals')
    if type(final['no_source_support']) is not bool:
        issues.append('no_source_support_invalid')
    elif final['no_source_support'] and any(t.startswith('K') for t in used):
        issues.append('no_source_support_contradicts_citations')
    unavailable = final['unavailable_calculations']
    if type(unavailable) is not list or not all(type(u) is str and u in profile.unavailable_ids for u in unavailable):
        issues.append('unknown_unavailable_calculation')
    copied = copied_runs(' '.join(t for _, t in texts), passages)
    if copied:
        issues.append('verbatim_source_copy')
    issues.extend(_coverage(coverage, profile.core_factors(label), evidence))
    return _result(issues, missing, unsupported, generic)


def _coverage(coverage, required, evidence):
    issues = []
    if type(coverage) is not list or len(coverage) > 48:
        return ['coverage_invalid']
    seen = {}
    for item in coverage:
        if type(item) is not dict or set(item) != {'factor', 'status', 'evidence_ids', 'note'}:
            return ['coverage_invalid']
        seen[item['factor']] = item
    for factor_id, _, _ in required:
        item = seen.get(factor_id)
        if item is None:
            issues.append('core_factor_not_covered ' + factor_id)
        elif item['status'] == 'examined':
            ids = item['evidence_ids']
            if type(ids) is not list or not ids or not all(type(e) is str and e in evidence and
                                                           evidence[e]['result']['status'] in ('ok', 'partial') for e in ids):
                issues.append('core_factor_without_evidence ' + factor_id)
        elif item['status'] == 'unavailable':
            if type(item['note']) is not str or len(item['note'].strip()) < 10:
                issues.append('core_factor_unavailable_without_reason ' + factor_id)
        else:
            issues.append('core_factor_status_invalid ' + factor_id)
    return issues


def _result(issues, missing, unsupported, generic):
    issues = list(dict.fromkeys(issues))
    missing = list(dict.fromkeys(missing))
    problems = issues + ['missing_' + m for m in missing]
    instruction = ''
    if problems:
        instruction = ('Rewrite the final answer. Tag every sentence that states a chart value with the fact IDs that '
                       'contain every value it mentions, or remove the value. Cite sources only with retrieved K IDs and '
                       'paraphrase them. No probabilities, certainty, diagnosis, death, longevity or infertility statements, '
                       'and no remedies without a retrieved source. Provide a direct answer, conflicting signals where they '
                       'exist, an evidence-strength label with a reason, and cover every core factor. Issues: '
                       + '; '.join(problems[:12]))
    return {'passed': not problems, 'score': max(0, 100 - 10 * len(problems)), 'issues': issues,
            'missing_sections': missing, 'generic_phrases_detected': list(dict.fromkeys(generic)),
            'unsupported_claims': list(dict.fromkeys(unsupported))[:12], 'repair_instruction': instruction}
