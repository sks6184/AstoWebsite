"""Fact check for a written consultation: every astrological statement is compared with the engine's tables.

The writer uses no tags. This module reads each sentence, recognises the common statement forms
(placement, house lordship, aspect, dignity, running period, transit, karaka, pada, dates and Ashtakavarga
numbers) and looks each one up in ``Tables``. A statement that contradicts the tables, names something the
app does not calculate, or cites a source that was not retrieved is a *finding* tied to that one sentence,
so it can be repaired or removed without rejecting the whole answer. Layout and wording are never checked.

It is deliberately conservative in what it calls an error: only recognised statement forms are judged.
Co-mentions it cannot classify are recorded as ``soft`` notes and left alone.
"""
from datetime import date, timedelta
import re

from astrology.validation.prose_validator import (
    CERTAINTY, DEATH, DIAGNOSIS, DURATION, FERTILITY, GENERIC_PHRASES, KARAKA_WORDS, MEDICAL_ADVICE, MONTHS, ORDINAL_WORDS,
    PLANET_WORDS, PROBABILITY, REMEDY, SECOND_PERSON, SIGN_WORDS, SOURCE_TERMS, STRENGTH_LABELS, VARGA_WORDS, YOGA_NAME,
    _title_matches, copied_runs, sentences)
from .tables import planet_name as P, sign_name as S

FIELDS = ('direct_answer', 'natal_promise', 'divisional_confirmation', 'jaimini_view', 'periods', 'transits', 'event_assessment', 'conflicts',
          'classical_support', 'guidance')
MARKER = re.compile(r'\(\s*(P\d{1,2}(?:\s*(?:,|;|and|&)\s*P\d{1,2})*)\s*\)')      # (P1) or (P1, P4)


def markers(text):
    """Passage markers cited in a text, in order."""
    return [m for group in MARKER.findall(text or '') for m in re.findall(r'P\d{1,2}', group)]
INTERNAL_ID = re.compile(r'\[?\b(?:[FK][0-9a-f]{16,20}|E\d{1,3})\b\]?')
_MONTH = '|'.join(sorted(MONTHS, key=len, reverse=True))
DATE = re.compile(rf'(?P<iso>\b\d{{4}}-\d{{2}}-\d{{2}}\b)|(?P<dmy>\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{_MONTH})\.?,?\s+\d{{4}}\b)|'
                  rf'(?P<mdy>\b(?:{_MONTH})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b)|(?P<my>\b(?:{_MONTH})\.?\s+(?:of\s+)?\d{{4}}\b)|'
                  r'(?P<y>\b(?:19|20|21)\d{2}\b)', re.I)
_ORDW = '|'.join(ORDINAL_WORDS)
_NUM = rf'(?:\d{{1,2}}(?:st|nd|rd|th)|{_ORDW})'
_PLANETS = '|'.join(sorted(PLANET_WORDS, key=len, reverse=True))
_SIGNS_EN = 'Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces'
_SIGNS_SA = '|'.join(sorted((w for w in SIGN_WORDS if w not in _SIGNS_EN.casefold().split('|')), key=len, reverse=True))
_KARAKAS = '|'.join(sorted((k for k in KARAKA_WORDS if len(k) > 3), key=len, reverse=True))
_VARGAS = '|'.join(sorted(VARGA_WORDS, key=len, reverse=True))
ENTITY = re.compile(
    rf'(?P<lagl>\b(?:lagna|ascendant)\s+(?:lord|ruler)\b|\blagnesh\b|\b(?:lord|ruler)\s+of\s+(?:the\s+|your\s+)?(?:lagna|ascendant)\b)|'
    rf'(?P<lord1>\b{_NUM})[- ](?:house[- ])?(?:lord|ruler)\b|\b(?:lord|ruler|owner)\s+of\s+(?:the\s+|your\s+)?(?P<lord2>{_NUM})(?:\s+house)?\b|'
    rf'(?P<itslord>\b(?:its|whose)\s+(?:lord|ruler)\b)|'
    rf'(?P<hlist>\b(?:houses?|bhavas?)\s+\d{{1,2}}\b(?:\s*\([^)]{{0,40}}\))?(?:\s*(?:,|and|&|or)\s*\d{{1,2}}\b(?:\s*\([^)]{{0,40}}\))?)*)|'
    rf'(?P<h>\b\d{{1,2}})(?:st|nd|rd|th)\b(?:\s+(?:house|bhava)s?\b)?|(?P<hw>\b(?:{_ORDW}))\s+(?:house|bhava)\b|'
    rf'(?P<karaka>\b(?:{_KARAKAS})\b|\bAmK\b|\bAK\b|\bDK\b|\bPK\b)|'
    rf'(?P<pada>\bArudha\s+Lagna\b|\bUpapada(?:\s+Lagna)?\b|\bDarapada\b|\bKarakams[h]?a\b|\bAL\b|\bUL\b|\bA(?:[1-9]|1[0-2])\b)|'
    rf'(?P<varga>\bD\d{{1,2}}\b|\b(?:{_VARGAS})\b)|'
    rf'(?P<lagna>\b(?:lagna|ascendant|rising\s+sign)\b)|'
    rf"(?P<planet>\b(?:{_PLANETS})\b)(?:'s|’s)?|"
    rf'(?P<sign>\b(?:{_SIGNS_EN})\b|(?i:\b(?:{_SIGNS_SA})\b))|'
    r'(?P<dasha>\b(?:maha\s?dasha|mahadasa|antar\s?dasha|antardasa|dasha|dasa|sub-?periods?|bhukti|periods?)\b)',
    re.I)
PLACE = re.compile(r'\b(in|into|within|occup\w+|sits?|sitting|placed|posited|located|situated|resid\w+|tenant\w*|falls?|falling|'
                   r'positioned|transit\w*|moves?|moving|enter\w*|through|across|over|crosses|crossing)\b', re.I)
RULES = re.compile(r'\b(rules?|ruling|owns?|owning|governs?|governing|lords?\s+over|rulership\s+of|ownership\s+of|as\s+(?:the\s+)?(?:lord|ruler)\s+of)\b', re.I)
ASPECT = re.compile(r'\b(aspect\w*|drishti|glance\w*|gaze\w*)\b', re.I)
TRANSIT = re.compile(r'\btransit\w*|\bgochar\w*', re.I)
FILLER = re.compile(r"^[\s,(:\u2013\u2014-]*(?:(?:is|are|was|being|as|the|your|this|a|an|also|namely|who|which|that|itself|planet|here|i\.e\.)[\s,]*)*[\s,(:\u2013\u2014-]*$", re.I)
CHAIN = re.compile(r"^[\s,(:;\u2013\u2014-]*(?:(?:and|or|in|of|the|your|sign|its|own|which|is|house|as\s+well\s+as|along\s+with|both)[\s,]*)*[\s,(:\u2013\u2014-]*$", re.I)
INFLUENCE = re.compile(r'\b(supports?|supporting|influenc\w+|affect\w*|activat\w+|impact\w*|energi[sz]\w+|strengthen\w*|benefit\w*|'
                       r'bless\w*|afflict\w*|pressur\w+|connect\w*|link\w*|accentuat\w+|touch\w*)\b', re.I)
PRONOUN = re.compile(r'\b(it|its|which|that)\b', re.I)
CONTENT_WORD = re.compile(r'[a-z]{6,}')
COMMON = frozenset('''retrieved source sources passage passages classical though although however because therefore indicates indicate
    suggests suggest during within period periods should would could chart charts planet planets astrology'''.split())
MOVING = re.compile(r'transit\w*|moves?|moving|enter\w*|through|across|crosses|crossing', re.I)
RULES_CHAIN = re.compile(r"^[\s,(&]*(?:(?:and|or|the|your|as\s+well\s+as|both)[\s,]*)*(?:house\s*)?$", re.I)
PASSIVE_PLACE = re.compile(r'\b(occupied\s+by|tenanted\s+by|contains?|holds?|hosts?|home\s+to)\b', re.I)
REFERENCE = re.compile(r"\b(?:as\s+)?(?:counted\s+)?from\s+(?:the\s+|your\s+)?(?:natal\s+)?(?:moon|chandra|lagna|ascendant)\b", re.I)
REFERENCE_BEFORE = re.compile(r"\bfrom\s+(?:the\s+|your\s+)?(?:natal\s+)?$", re.I)
ORIGIN = re.compile(r"\bfrom\s+(?:the\s+|its\s+|your\s+|his\s+|her\s+)?(?:natal\s+)?(?:position\s+in\s+(?:the\s+)?)?$", re.I)
APPOSITION = re.compile(r"^[\s,(:–—-]*(?:(?:is|in|of|the|your|sign|which|falls|lies|house|being|namely|i\.e\.)[\s,]*)*[\s,(:–—-]*$", re.I)
GENERAL = re.compile(r"\b(if|when|whenever|generally|in\s+general|traditionally|classically|usually|typically|as\s+a\s+rule)\b", re.I)
PASSIVE_ASPECT = re.compile(r'\baspect\w*\s+(?:by|of|from)\b|\b(?:aspect|drishti|gaze|glance)\s+(?:of|from)\b|\breceiv\w+\b.*\baspect', re.I)
PASSIVE_RULES = re.compile(r'\b(?:ruled|owned|governed|lorded)\s+by\b|\b(?:lord|ruler)\s+(?:is|being)\b|\bunder\s+the\s+(?:lordship|rulership)\s+of\b', re.I)
FROM_REF = re.compile(r"^\s*(?:(?:house|sign)\s+)?(?:as\s+)?(?:counted\s+|reckoned\s+)?from\s+(?:the\s+|your\s+)?(?:natal\s+)?(?P<ref>moon|chandra|lagna|ascendant)?", re.I)
DIGNITY_LABEL = {'exalted': 'exalted', 'debilitated': 'debilitated', 'own_sign': 'in its own sign'}
DIGNITY_WORDS = {'exalted': r'exalt\w+', 'debilitated': r'debilitat\w+', 'own_sign': r'own\s+(?:sign|house)|swakshetra'}
UNCALCULATED = re.compile(r'\b(combust\w*|shadbala|neecha\s?bhanga|vargottama|sub-?lords?|KP|tithi|hora\s+lagna|ghatika|pratyantar\w*|'
                          r'vimshopaka|planetary\s+war|graha\s+yuddha|mool\s?a?trikona|nakshatra\s+pada|bhava\s+chalit)\b', re.I)
DENIED = re.compile(r"\b(not|no|never|without|lacks?|neither|nor|isn't|is\s+not|does\s+not)\b|n't\b", re.I)
VAGUE = re.compile(r'\b((?:planetary|astrological|cosmic|celestial)\s+(?:influences?|energ\w+|alignments?|forces|configurations?|positions))\b', re.I)
NEGATED = re.compile(r"\b(not|n't|never|cannot|unavailable|would\s+(?:need|require)|requires?|beyond|outside|does\s+not|is\s+not)\b", re.I)
SAV_CUE = re.compile(r'\b(SAV|BAV|bindus?|sarvashtakavarga|ashtakavarga)\b', re.I)
BOUNDARY_CUE = re.compile(r'\b(begin\w*|start\w*|end\w*|until|till|from|through|by|after|before|since|on|around|commenc\w+|runs?|lasts?)\b', re.I)
# The words directly before a date that say which end of a period it is: "starts 5 January 2027", "until 26 October 2027".
ROLE_BEFORE = re.compile(r"\b(?:(?P<start>begin\w*|start\w*|commenc\w+|from|since)|(?P<end>end\w*|until|till|(?<!prior\s)to|through|conclud\w+|finish\w*))"
                         r"(?:\s+(?:on|around|about|in|the|approximately|roughly|early|late|mid))*[\s,:-]*$", re.I)
# Between a period's name and the word that says "starts" or "ends": nothing that begins another clause.
TIGHT = re.compile(r"^\s*(?:(?:which|that|it|also|then|now|itself|will|is|was|has|only|actually|period|phase)\s+)*"
                   r"(?:(?:runs?|lasts?|continues?|extends?|operates?)\s+)?$", re.I)
# What a reading cannot do without, by question intent. Anything else that is missing makes it preliminary.
ALWAYS_ESSENTIAL = ('all', 'direct_answer', 'calculated_basis', 'natal_basis', 'primary_house_logic')
SECTION_NAMES = {'direct_answer': 'a direct answer', 'calculated_basis': 'the calculated basis', 'natal_basis': 'the birth-chart basis',
                 'primary_house_logic': 'the main house for this question', 'timing': 'the timing analysis',
                 'period_basis': 'the dasha periods', 'event_comparison': 'a separate assessment of each event',
                 'divisional_basis': 'divisional-chart confirmation', 'jaimini_basis': 'the Jaimini view',
                 'transit_basis': 'the transits', 'conflicting_signals': 'the conflicting indications',
                 'classical_support': 'classical source support', 'evidence_strength_label': 'an evidence-strength assessment',
                 'evidence_strength_reason': 'the reason for the evidence strength', 'all': 'the reading itself'}


def essential_sections(plan):
    """The sections this question cannot be answered without. A timing question needs its timing analysis
    and the dasha periods; a comparison of events needs each event assessed. Divisional, Jaimini, transit,
    classical-source and conflict sections support a reading: without them it is preliminary, not empty."""
    essential = set(ALWAYS_ESSENTIAL)
    if plan.timing:
        essential |= {'timing', 'period_basis'}
    if len(plan.events) > 1 or plan.label.get('question_type') == 'comparative_decision':
        essential.add('event_comparison')
    return essential


def describe_missing(missing):
    return list(dict.fromkeys(SECTION_NAMES.get(m, m.replace('_', ' ')) for m in missing))


DEPENDENT = re.compile(r'^(?:This|That|These|Those|Therefore|Thus|Hence|So|Consequently|As a result|Because of this|For this reason|Accordingly)\b')


def kind_of(path):
    """The body of evidence a verified statement rests on, from where its value sits in the tool results."""
    varga = re.match(r'/data/charts/(d\d+)/', path)
    if varga:
        return 'natal' if varga.group(1) == 'd1' else 'divisional'
    for prefix, kind in (('/data/samples/', 'transit'), ('/data/periods/', 'period'), ('/data/karakas', 'jaimini'), ('/data/padas', 'jaimini'),
                         ('/data/karakamsha', 'jaimini'), ('/data/result', 'jaimini'), ('/data/planets/', 'natal'), ('/data/rows/', 'ashtakavarga')):
        if path.startswith(prefix):
            return kind
    return 'other'


class Entity:
    __slots__ = ('kind', 'value', 'start', 'end', 'ref', 'used')

    def __init__(self, kind, value, start, end, ref=None):
        self.kind, self.value, self.start, self.end, self.ref, self.used = kind, value, start, end, ref, False


def _number(text):
    text = text.casefold()
    if text in ORDINAL_WORDS:
        return ORDINAL_WORDS[text]
    digits = re.match(r'\d{1,2}', text)
    return int(digits.group()) if digits else None


def _dates(text):
    """(tokens, text with the dates blanked out). Tokens are ('day'|'month'|'year', value, start)."""
    found = []

    def take(m):
        kind = m.lastgroup
        raw = m.group()
        try:
            if kind == 'iso':
                found.append(('day', date.fromisoformat(raw), m.start()))
            elif kind in ('dmy', 'mdy'):
                month = MONTHS[re.search(_MONTH, raw, re.I).group().casefold()[:3]]
                numbers = [int(n) for n in re.findall(r'\d+', raw)]
                found.append(('day', date(max(numbers), month, min(numbers)), m.start()))
            elif kind == 'my':
                found.append(('month', (int(re.search(r'\d{4}', raw).group()), MONTHS[re.search(_MONTH, raw, re.I).group().casefold()[:3]]), m.start()))
            else:
                found.append(('year', int(raw), m.start()))
        except (ValueError, AttributeError):
            found.append(('invalid', raw, m.start()))
        return ' ' * len(raw)
    return found, DATE.sub(take, text)


def entities(text):
    """Astrological mentions in order of appearance (dates must already be blanked out)."""
    found = []
    for m in ENTITY.finditer(text):
        kind = m.lastgroup
        raw = m.group(kind)
        if kind == 'lagl':
            found.append(Entity('L', 1, m.start(), m.end()))
        elif kind in ('lord1', 'lord2'):
            n = _number(raw)
            if n and 1 <= n <= 12:
                found.append(Entity('L', n, m.start(), m.end()))
        elif kind == 'itslord':
            found.append(Entity('L', None, m.start(), m.end()))
        elif kind == 'hlist':
            for n in re.findall(r'\d{1,2}', re.sub(r'\([^)]*\)', ' ', raw)):
                if 1 <= int(n) <= 12:
                    found.append(Entity('H', int(n), m.start(), m.end()))
        elif kind in ('h', 'hw'):
            n = _number(raw)
            if n and 1 <= n <= 12:
                ref = FROM_REF.match(text[m.end():])
                entity = Entity('H', n, m.start(), m.end())
                if ref:
                    name = (ref.group('ref') or '').casefold()
                    entity.ref = 'moon' if name in ('moon', 'chandra') else 'lagna' if name in ('lagna', 'ascendant') else 'other'
                found.append(entity)
        elif kind == 'karaka':
            key = raw.casefold()
            if key in KARAKA_WORDS and (len(key) > 3 or raw.isupper() or raw == 'AmK'):
                found.append(Entity('K', KARAKA_WORDS[key], m.start(), m.end()))
        elif kind == 'pada':
            key = raw.casefold()
            house = 1 if key in ('al', 'arudha lagna') else 12 if key.startswith(('ul', 'upapada')) else 7 if key == 'darapada' else \
                    0 if key.startswith('karakams') else int(key[1:]) if raw[0] == 'A' and raw[1:].isdigit() else None
            if house is not None and (len(raw) > 2 or raw.isupper() or raw[1:].isdigit()):
                found.append(Entity('A', house, m.start(), m.end()))
        elif kind == 'varga':
            key = raw.casefold()
            found.append(Entity('V', VARGA_WORDS.get(key, key if key.startswith('d') else None), m.start(), m.end()))
        elif kind == 'lagna':
            found.append(Entity('G', None, m.start(), m.end()))
        elif kind == 'planet':
            found.append(Entity('P', PLANET_WORDS[raw.casefold()], m.start(), m.start() + len(raw)))
        elif kind == 'sign':
            if raw.casefold() != 'cancer' or raw[0].isupper():
                found.append(Entity('S', SIGN_WORDS[raw.casefold()], m.start(), m.end()))
        elif kind == 'dasha':
            found.append(Entity('D', raw.casefold(), m.start(), m.end()))
    return found


class SentenceCheck:
    """Findings, soft notes and provenance for one sentence."""

    def __init__(self, text, tables, plan, passages, today, field=None):
        self.text, self.t, self.plan, self.passages, self.today = text, tables, plan, passages, today
        self.findings, self.soft, self.refs, self.verified = [], [], [], 0
        self.kinds = set()             # which bodies of evidence this sentence's verified statements rest on
        self.period_rows = []          # the period rows this sentence names (its dates must be theirs)
        self.period_mentions = []      # (where the name ends, its rows, True for a Mahadasha) for the start/end check
        self.dates, blank = _dates(text)
        self.blank = blank
        self.ents = entities(blank)
        self.transit = bool(TRANSIT.search(blank)) or field == 'transits'
        self.moving = False            # the statement being checked uses a transit verb
        self.scope = {}                # planet -> transit signs this sentence has placed it in ("Jupiter transits Cancer ...")
        self.vargas = list(dict.fromkeys(['d1'] + [e.value for e in self.ents if e.kind == 'V' and e.value in tables.lagna]))
        self.named_varga = len(self.vargas) > 1

    def fail(self, code, detail, correction=''):
        self.findings.append({'code': code, 'detail': detail, 'correction': correction})

    def ok(self, *refs):
        self.verified += 1
        for ref in refs:
            if ref:
                self.refs.append(ref)
                self.kinds.add(kind_of(ref.get('path', '')))

    # ── Truth lookups ────────────────────────────────────────────────────
    def placement(self, code, target):
        t = self.t
        for varga in () if self.moving else self.vargas:
            row = t.place.get(varga, {}).get(code)
            if not row:
                continue
            if target.kind == 'S' and row['sign'] == target.value:
                return row['ref']
            if target.kind == 'H':
                if target.ref == 'moon':
                    moon = t.place.get(varga, {}).get('Mo')
                    if moon and (row['sign'] - moon['sign']) % 12 + 1 == target.value:
                        return row['ref']
                elif row['house'] == target.value:
                    return row['ref']
        if self.transit:
            for seg in self.segments(code):
                hit = (target.kind == 'S' and seg['sign'] == target.value) or \
                      (target.kind == 'H' and (seg['moon_house'] if target.ref == 'moon' else seg['house']) == target.value)
                if hit:
                    if self.moving:
                        # Once the sentence has put the planet in a transit sign, its other claims about
                        # that planet are judged from that sign, not from anywhere it goes in the window.
                        self.scope.setdefault(code, set()).add(seg['sign'])
                    return seg['ref']
        return None

    def segments(self, code):
        signs = self.scope.get(code)
        return [s for s in self.t.transits if s['planet'] == code and (not signs or s['sign'] in signs)]

    def placement_fact(self, code):
        t = self.t
        parts = []
        for varga in self.vargas:
            row = t.place.get(varga, {}).get(code)
            if row:
                parts.append(f"{P(code)} is in {S(row['sign'])}, house {row['house']} in {varga.upper()}")
        if self.transit:
            segs = [s for s in t.transits if s['planet'] == code]
            if segs:
                parts.append('in transit ' + '; '.join(f"{S(s['sign'])} (house {s['house']} from the Lagna" +
                             (f", {s['moon_house']} from the Moon" if s['moon_house'] else '') + f") {s['start']} to {s['end']}" for s in segs[:4]))
            elif code not in t.transit_planets:
                parts.append(f'the transit of {P(code)} was not calculated')
        return '; '.join(parts) or f'no placement of {P(code)} is available'

    def lord_of(self, house):
        for varga in (self.vargas[1:] + ['d1']) if self.named_varga else ['d1']:
            row = self.t.lords.get(varga, {}).get(house)
            if row:
                yield varga, row

    def lordship(self, code, house):
        for _, row in self.lord_of(house):
            if row['lord'] == code:
                return row['ref']
        return None

    # ── Statement forms ──────────────────────────────────────────────────
    def check_lordship(self, code, house):
        ref = self.lordship(code, house)
        if ref:
            return self.ok(ref)
        actual = next((row for _, row in self.lord_of(house)), None)
        if actual is None:
            return self.soft.append(f'lord of house {house} unavailable')
        ruled = self.t.ruled(code)
        self.fail('wrong_house_lord', f'{P(code)} is stated as lord of house {house}',
                  f"The lord of house {house} is {P(actual['lord'])}." + (f" {P(code)} rules house{'s' if len(ruled) > 1 else ''} {', '.join(map(str, ruled))}." if ruled else ''))

    def check_placement(self, subject, target):
        if target.kind == 'H' and target.ref == 'other':
            return self.soft.append('house counted from another reference point: not verified')
        if subject['kind'] == 'A':
            row = subject['row']
            good = (target.kind == 'S' and row['sign'] == target.value) or (target.kind == 'H' and row.get('house') == target.value)
            if good:
                return self.ok(row['ref'])
            return self.fail('wrong_pada_or_karakamsha', f"{subject['name']} is stated in {self.describe(target)}",
                             f"{subject['name']} is in {S(row['sign'])}" + (f", house {row['house']} from the Lagna." if row.get('house') else '.'))
        code = subject['code']
        ref = self.placement(code, target)
        if ref:
            return self.ok(ref, subject.get('ref'))
        if self.transit and code not in self.t.transit_planets and not any(self.t.place.get(v, {}).get(code) for v in self.vargas):
            return self.fail('uncalculated_transit', f'a transit of {P(code)} is stated', f'The transit of {P(code)} was not calculated.')
        self.fail('wrong_placement', f"{subject['name']} is stated in {self.describe(target)}", self.placement_fact(code) + '.')

    def check_aspect(self, code, house):
        row = self.t.aspects.get(code)
        segments = self.segments(code) if self.transit else []
        if row is None and not segments:
            return self.soft.append('aspects unavailable')
        if row and house in row['houses'] and code not in self.scope:
            return self.ok(row['ref'])
        hit = next((s for s in segments if house in s['aspects']), None)
        if hit:
            return self.ok(hit['ref'])
        fact = f"By Parashari aspect {P(code)}, in house {row['from']} at birth, aspects house(s) {', '.join(map(str, row['houses']))}." if row else ''
        if segments:
            fact += ' In transit: ' + '; '.join(f"from {S(s['sign'])} (house {s['house']}) it aspects {', '.join(map(str, s['aspects']))}"
                                                 for s in {s['sign']: s for s in segments}.values()) + '.'
        self.fail('wrong_aspect', f'{P(code)} is stated to aspect house {house}', fact.strip())

    def describe(self, target):
        if target.kind == 'S':
            return S(target.value)
        return f"house {target.value}" + (' from the Moon' if target.ref == 'moon' else '')

    def subject_of(self, entity, last_house):
        """Resolve a planet, house-lord, karaka, pada or Lagna mention to what the tables say it is."""
        t = self.t
        if entity.kind == 'P':
            return {'kind': 'P', 'code': entity.value, 'name': P(entity.value)}
        if entity.kind == 'L':
            house = entity.value if entity.value else last_house
            row = next((row for _, row in self.lord_of(house)), None) if house else None
            if row:
                return {'kind': 'P', 'code': row['lord'], 'name': f"the lord of house {house} ({P(row['lord'])})", 'ref': row['ref'], 'house': house}
            return None
        if entity.kind == 'K':
            row = t.karakas.get(entity.value)
            return {'kind': 'P', 'code': row['code'], 'name': f"the {entity.value} ({P(row['code'])})", 'ref': row['ref']} if row else None
        if entity.kind == 'A':
            if entity.value == 0:
                km = t.karakamsha
                return {'kind': 'A', 'name': 'The Karakamsha', 'row': {'sign': km['sign'], 'house': t.sign_house(km['sign']), 'ref': km['ref']}} if km else None
            row = t.padas.get(entity.value)
            return {'kind': 'A', 'name': f'The pada of house {entity.value}', 'row': row} if row else None
        if entity.kind == 'G':
            varga = self.vargas[-1] if self.named_varga else 'd1'
            if t.lagna.get(varga):
                return {'kind': 'A', 'name': f'The {varga.upper()} Lagna', 'row': {'sign': t.lagna[varga], 'house': 1, 'ref': None}, 'lagna': True}
        return None

    def run(self):
        text, ents = self.blank, self.ents
        # A source's own general statement, or a conditional principle, is not a statement about this chart.
        general = (MARKER.search(self.text) or GENERAL.search(self.text)) and not SECOND_PERSON.search(self.text)
        if not general:
            self.forms(text, ents)
            self.periods()
            self.calendar()
            self.numbers()
            self.yogas()
        self.policy()
        return self

    def forms(self, text, ents):
        subject, subject_end, relation, last_house, last_target = None, 0, None, None, None
        planet = lambda e: {'kind': 'P', 'code': e.value, 'name': P(e.value)}
        for i, e in enumerate(ents):
            prev = ents[i - 1] if i else None
            gap = text[prev.end:e.start] if prev else ''
            if e.kind in ('V', 'D'):
                continue
            if e.kind in ('P', 'G') and REFERENCE_BEFORE.search(text[:e.start]):
                continue                                          # "... from the Moon": a reference point, not a subject
            if e.kind == 'A' and REFERENCE_BEFORE.search(text[:e.start]):
                counted = self.counted_subject(prev, e)
                subject, subject_end, relation = counted, e.end, None
                continue
            if e.kind in ('P', 'L', 'K', 'A', 'G'):
                self.moving = False
                resolved = self.subject_of(e, last_house)
                # "10th lord Venus", "Venus, the 10th lord", "the Amatyakaraka Moon": an identity statement.
                if prev and prev.kind != e.kind and {prev.kind, e.kind} in ({'P', 'L'}, {'P', 'K'}) and FILLER.match(gap):
                    who, other = (e, prev) if e.kind == 'P' else (prev, e)
                    relation = None
                    if other.kind == 'L':
                        house = other.value or last_house
                        if house:
                            self.check_lordship(who.value, house)
                            target = Entity('H', house, other.start, other.end)
                            relation, last_target, last_house = ('rules', target), target, house
                    else:
                        row = self.t.karakas.get(other.value)
                        if row and row['code'] == who.value:
                            self.ok(row['ref'])
                        elif row:
                            self.fail('wrong_karaka', f'{P(who.value)} is stated as the {other.value}', f"The {other.value} is {P(row['code'])}.")
                    subject, subject_end = planet(who), e.end
                    if e.kind == 'P':
                        self.dignity(e)
                    continue
                if e.kind == 'P' and prev and prev.kind in ('H', 'S') and last_target is not None and last_target is prev:
                    passive = ('rules' if PASSIVE_RULES.search(gap) else 'passive_aspect' if PASSIVE_ASPECT.search(gap) else
                               'passive_place' if PASSIVE_PLACE.search(gap) and not RULES.search(gap) else None)
                    if passive == 'rules':
                        house = prev.value if prev.kind == 'H' else self.t.sign_house(prev.value)
                        if house:
                            self.check_lordship(e.value, house)
                    elif passive == 'passive_aspect' and prev.kind == 'H':
                        self.check_aspect(e.value, prev.value)
                    elif passive == 'passive_place':
                        self.check_placement(planet(e), prev)
                    if passive:
                        subject, subject_end = planet(e), e.end
                        relation = (passive, prev) if passive.startswith('passive') else None
                        self.dignity(e)
                        continue
                if e.kind == 'P' and prev and prev.kind == 'P' and relation and relation[0].startswith('passive') and CHAIN.match(gap):
                    if relation[0] == 'passive_place':                # "... occupied by the Sun and Mars"
                        self.check_placement(planet(e), relation[1])
                    else:
                        self.check_aspect(e.value, relation[1].value)
                    subject, subject_end = planet(e), e.end
                    continue
                if e.kind == 'G' and prev and prev.kind == 'S' and FILLER.match(gap) and resolved:
                    self.check_placement(resolved, prev)              # "Leo Lagna"
                subject, subject_end, relation = resolved, e.end, None
                if e.kind == 'P':
                    self.dignity(e)
                continue
            # A house or a sign: decide what the sentence says about the current subject.
            if e.kind == 'H':
                last_house = e.value
            before = text[:e.start]
            if subject is None:
                if prev and {prev.kind, e.kind} == {'H', 'S'} and APPOSITION.match(gap) and not self.transit:
                    self.check_house_sign(prev if prev.kind == 'H' else e, e if e.kind == 'S' else prev)
                last_target = e
                continue
            pronoun = [m.end() for m in PRONOUN.finditer(text, subject_end, e.start)]
            span = text[max([subject_end] + pronoun):e.start]
            between = REFERENCE.sub(' ', text[last_target.end:e.start]) if last_target is not None else ''
            # "rules the 2nd and 11th" continues a lordship; "the 10th lord in the 6th" does not.
            chained = relation and last_target is relation[1] and (RULES_CHAIN if relation[0] == 'rules' else CHAIN).match(between)
            if ORIGIN.search(before) and not (e.kind == 'H' and e.ref):
                kind = None                                       # "aspects the 10th from the 4th": origin, not verified here
            elif chained and relation[0] in ('place', 'rules', 'aspect', 'influence'):
                kind = relation[0]                                # "in the 12th house, in Cancer" / "rules the 2nd and 11th"
            elif len(span.split()) > 14 and not (last_target is not None and last_target.end >= subject_end
                                                 and (ASPECT.search(between) or INFLUENCE.search(between)) and len(between.split()) <= 14):
                kind = None
            else:
                if len(span.split()) > 14:
                    span = between                                # "... occupying your 1st house and aspecting your career (10th house)"
                cues = [(m.start(), name) for name, pattern in (('rules', RULES), ('aspect', ASPECT), ('place', PLACE), ('influence', INFLUENCE))
                        for m in pattern.finditer(span)]
                kind = max(cues)[1] if cues else None             # the cue nearest to the house or sign decides
            if subject.get('lagna') and kind is None and FILLER.match(span):
                kind = 'place'                                    # "Lagna is Leo"
            if kind == 'place':
                if not chained:
                    verbs = [m for m in PLACE.finditer(span)]
                    self.moving = bool(verbs and MOVING.fullmatch(verbs[-1].group()))
                self.check_placement(subject, e)
            elif kind == 'rules' and subject['kind'] == 'P':
                house = e.value if e.kind == 'H' else self.t.sign_house(e.value)
                if house:
                    self.check_lordship(subject['code'], house)
            elif kind == 'aspect' and subject['kind'] == 'P' and e.kind == 'H':
                self.check_aspect(subject['code'], e.value)
            elif kind == 'influence' and subject['kind'] == 'P':
                self.check_relation(subject, e)                   # "supports", "activates", "connects": some real relation is needed
            else:
                if prev and {prev.kind, e.kind} == {'H', 'S'} and APPOSITION.match(gap) and not self.transit and not (relation and last_target is prev):
                    self.check_house_sign(prev if prev.kind == 'H' else e, e if e.kind == 'S' else prev)
                elif subject['kind'] == 'P' and kind is None and len(span.split()) <= 14 and not (e.kind == 'H' and e.ref == 'other') \
                        and not ORIGIN.search(before):
                    # The wording is not one of the known forms. It still links a planet with a house or sign:
                    # that needs some relation in the calculations, otherwise it is an unsupported chart claim.
                    self.check_relation(subject, e, known_form=False)
                else:
                    self.soft.append(f"{subject['name']} with {self.describe(e)}: statement form not recognised, not verified")
                kind = None
            relation = (kind, e) if kind else None
            last_target = e

    def relation_of(self, code, target):
        """Any calculated relation between a planet and a house or sign: occupation, lordship or aspect, at
        birth (in the charts named) or, in a transit statement, in transit. Returns its reference or None."""
        t = self.t
        scoped = code in self.scope                       # a transit statement: birth-chart placement and aspects do not answer it
        moving, self.moving = self.moving, scoped
        ref = self.placement(code, target)
        self.moving = moving
        if ref:
            return ref
        house = target.value if target.kind == 'H' else t.sign_house(target.value)
        if target.kind == 'H' and target.ref == 'moon':
            return None                                   # a count from the Moon is a position only
        if house:
            if self.lordship(code, house):
                return self.lordship(code, house)
            if not scoped and house in (t.aspects.get(code) or {}).get('houses', []):
                return t.aspects[code]['ref']
            if self.transit:
                hit = next((s for s in self.segments(code) if house in s['aspects']), None)
                if hit:
                    return hit['ref']
        return None

    def check_relation(self, subject, target, known_form=True):
        code = subject['code']
        ref = self.relation_of(code, target)
        if ref:
            if known_form:
                return self.ok(ref, subject.get('ref'))
            return self.soft.append(f"{subject['name']} with {self.describe(target)}: wording not recognised; a calculated relation exists")
        if not self.t.place.get('d1', {}).get(code):
            return self.soft.append('planet unavailable')
        ruled = self.t.ruled(code)
        aspects = (self.t.aspects.get(code) or {}).get('houses', [])
        fact = self.placement_fact(code) + '.' + (f" It rules house{'s' if len(ruled) > 1 else ''} {', '.join(map(str, ruled))}." if ruled else '') + \
               (f" At birth it aspects house{'s' if len(aspects) > 1 else ''} {', '.join(map(str, aspects))}." if aspects else '')
        if self.transit:
            seen = {s['sign']: s for s in self.segments(code)}
            if seen:
                fact += ' In transit it aspects ' + '; '.join(f"{', '.join(map(str, s['aspects']))} from {S(s['sign'])}" for s in seen.values()) + \
                        ' (houses from the Lagna). A count from the Moon is a position, not an aspect.'
        self.fail('unsupported_relation', f"{subject['name']} is linked with {self.describe(target)}, but it does not occupy, rule or aspect it", fact)

    def counted_subject(self, count, reference):
        """The n-th sign from the Arudha Lagna, Upapada Lagna or Karakamsha, if the engine counted it."""
        names = {1: 'arudha_lagna', 12: 'upapada_lagna', 0: 'karakamsha'}
        if count is None or count.kind != 'H' or reference.value not in names:
            return None
        row = next((c for c in self.t.counted if c['reference'] == names[reference.value] and c['count'] == count.value), None)
        if row is None:
            self.soft.append(f"sign {count.value} from the {names[reference.value].replace('_', ' ')} was not calculated: not verified")
            return None
        return {'kind': 'A', 'name': f"Sign {count.value} from the {names[reference.value].replace('_', ' ').title()}",
                'row': {'sign': row['sign'], 'house': row['house'], 'ref': row['ref']}}

    def check_house_sign(self, house, sign):
        """"your 10th house, Taurus": the sign on a house, by whole-sign counting from the stored Lagna."""
        if house.ref:
            return
        varga = self.vargas[-1] if self.named_varga else 'd1'
        actual = self.t.house_sign(house.value, varga)
        if actual is None:
            return
        if actual == sign.value:
            return self.ok()
        self.fail('wrong_house_sign', f'house {house.value} is stated as {S(sign.value)}', f'House {house.value} is {S(actual)} in {varga.upper()}.')

    def dignity(self, entity):
        """A dignity or retrograde word attached to this planet, stated or denied, against the stored chart."""
        if entity.kind != 'P' or self.transit:
            return
        before = self.blank[max(0, entity.start - 24):entity.start]
        nxt = next((e for e in self.ents if e.start >= entity.end and e.kind == 'P'), None)
        after = self.blank[entity.end:min(entity.end + 110, nxt.start if nxt else len(self.blank))]
        words = '|'.join(DIGNITY_WORDS.values()) + '|retrograde'
        after = re.sub(rf'(?:{words})\s+$', '', after, flags=re.I)       # "... aspects exalted Venus": that word belongs to Venus
        rows = [self.t.place.get(v, {}).get(entity.value) for v in self.vargas]
        if not any(rows):
            return
        for name, pattern in list(DIGNITY_WORDS.items()) + [('retrograde', 'retrograde')]:
            leading = re.search(rf'(?:{pattern})\s+$', before, re.I)
            trailing = re.search(rf'(?:{pattern})', after, re.I)
            if not leading and not trailing:
                continue
            denied = bool(trailing and not leading and DENIED.search(after[max(0, trailing.start() - 28):trailing.start()]))
            holds = [r for r in rows if r and (r['retrograde'] if name == 'retrograde' else r.get('dignity') == name)]
            label = name.replace('_', ' ')
            if bool(holds) != denied:
                self.ok((holds or [r for r in rows if r])[0]['ref'])
                continue
            actual = next(r for r in rows if r)
            if name == 'retrograde':
                self.fail('wrong_retrograde', f"{P(entity.value)} is stated as {'not ' if denied else ''}retrograde",
                          f"{P(entity.value)} is {'' if actual['retrograde'] else 'not '}retrograde in the stored chart.")
            else:
                true = DIGNITY_LABEL.get(actual.get('dignity'))
                self.fail('wrong_dignity', f"{P(entity.value)} is stated as {'not ' if denied else ''}{label}",
                          f"{P(entity.value)} is in {S(actual['sign'])}" + (f' and is {true} there.' if true else
                          f'; it is not exalted, debilitated or in its own sign there, so say nothing about its dignity.'))

    def periods(self):
        t = self.t
        rows = [r for system in t.dashas.values() for r in system]
        if not rows:
            return
        for i, e in enumerate(self.ents):
            if e.kind != 'D' or e.value.startswith('period') and not any(x.kind == 'P' and 0 <= e.start - x.end <= 3 for x in self.ents):
                continue
            level = 'major' if e.value.startswith(('maha',)) else 'sub' if e.value.startswith(('antar', 'sub', 'bhukti')) else None
            named, strict = [], False
            j = i - 1
            while j >= 0 and self.ents[j].kind == 'P':
                between = self.blank[self.ents[j].end:self.ents[j + 1].start]
                if not re.fullmatch(r"(?:'s|\u2019s)?[\s/\u2013\u2014,&-]*(?:and\s+)?", between, re.I):
                    break
                if named and re.search(r'[/\u2013\u2014-]', between):
                    strict = True                                 # "Jupiter/Mars period": a Mahadasha / sub-period pair
                named.insert(0, self.ents[j])
                j -= 1
            after = self.ents[i + 1] if i + 1 < len(self.ents) else None
            if not named and after and after.kind == 'P' and re.fullmatch(r'\s*(?:of|lord|ruled\s+by|run\s+by|:)?\s*(?:the\s+)?', self.blank[e.end:after.start], re.I):
                named = [after]
            if not named:
                continue
            codes = [n.value for n in named]
            if len(codes) >= 2 and not strict:
                for code in codes:                                # "the Moon and Mars sub-periods"
                    match = next((r for r in rows if code in (r['major'], r['sub'])), None)
                    if match:
                        self.period_rows += [r for r in rows if code in (r['major'], r['sub'])]
                        self.ok(match['ref'])
                    else:
                        self.fail('wrong_period', f'a {P(code)} period is stated', self.period_fact())
                continue
            if len(codes) >= 2:
                match = next((r for r in rows if r['major'] == codes[0] and r['sub'] == codes[1]), None)
                if match:
                    self.period_rows.append(match)
                    self.period_mentions.append((e.end, [match], False))
                    self.ok(match['ref'])
                else:
                    self.fail('wrong_period', f'a {P(codes[0])}/{P(codes[1])} period is stated', self.period_fact())
                continue
            code = codes[0]
            keys = ('major',) if level == 'major' else ('sub',) if level == 'sub' else ('major', 'sub')
            match = next((r for r in rows if any(r[k] == code for k in keys)), None)
            if match:
                self.period_rows += [r for r in rows if any(r[k] == code for k in keys)] if level == 'sub' else [match]
                if level:
                    self.period_mentions.append((max(e.end, named[-1].end), [r for r in rows if r['sub'] == code] if level == 'sub' else [match],
                                                 level == 'major'))
                self.ok(match['ref'])
            else:
                kind = {'major': 'Mahadasha', 'sub': 'sub-period'}.get(level, 'period')
                self.fail('wrong_period', f'a {P(code)} {kind} is stated', self.period_fact())

    def period_fact(self):
        parts = []
        for system, rows in self.t.dashas.items():
            if system == 'chara' or not rows:
                continue
            parts.append(f"{system.title()}: " + '; '.join(f"{r['major_name']} / {r['sub_name']} {r['start']} to {r['end']}" for r in rows[:4]))
        return 'The calculated periods are: ' + '. '.join(parts) + '.'

    def calendar(self):
        if not self.dates:
            return
        t, window = self.t, self.plan.window
        # A date in a period sentence must be a period date; in a transit sentence, a transit date.
        named_period = any(e.kind == 'D' and not e.value.startswith('period') for e in self.ents)
        scope = 'transits' if self.transit and not named_period else 'periods' if named_period and not self.transit else None
        boundaries = t.boundaries(scope)
        if scope == 'periods' and self.period_rows:
            boundaries = {date.fromisoformat(r[k]) for r in self.period_rows for k in ('start', 'end', 'major_start', 'major_end') if r.get(k)}
        boundaries |= {date.fromisoformat(window['start']), date.fromisoformat(window['end']), self.today}
        low, high = min(self.today, date.fromisoformat(window['start'])), date.fromisoformat(window['end'])
        for kind, value, position in self.dates:
            if kind == 'invalid':
                self.fail('invalid_date', f'{value} is not a valid date')
            elif kind == 'day':
                if not any(abs((value - b).days) <= 1 for b in boundaries):
                    self.fail('unsupported_date', f'{value.isoformat()} is not a calculated period, transit or window date',
                              'Use only the dates given for the periods, transits and candidate windows.')
                elif self.swapped(position, lambda b: abs((value - b).days) <= 1):
                    self.boundary_failure(value.isoformat(), *self.swapped(position, lambda b: abs((value - b).days) <= 1))
                else:
                    self.verified += 1
            elif kind == 'month':
                inside = (low.year, low.month) <= value <= (high.year, high.month)
                edge = any((b.year, b.month) == value for b in boundaries)
                cue = BOUNDARY_CUE.search(self.text[max(0, position - 28):position])
                if not (edge or (inside and not (cue and cue.group().casefold().startswith(('begin', 'start', 'end', 'commenc'))))):
                    self.fail('unsupported_date', f'{value[1]:02d}/{value[0]} is not supported by a calculated period or transit date',
                              'Use only the dates given for the periods, transits and candidate windows.')
                elif self.swapped(position, lambda b: (b.year, b.month) == value):
                    self.boundary_failure(f'{value[1]:02d}/{value[0]}', *self.swapped(position, lambda b: (b.year, b.month) == value))
            elif kind == 'year':
                years = {b.year for b in boundaries} | set(range(low.year, high.year + 1))
                if value not in years and value > self.today.year:
                    self.fail('unsupported_date', f'the year {value} is outside the calculated periods and window')

    def swapped(self, position, same):
        """(role, row, is a Mahadasha) when the sentence gives a named period's END as its start, or its START as
        its end. Only a true swap counts: the date must be the other end of that same period, and the period's
        name must lead straight into the word "starts" or "ends". A sentence that names one period and then
        gives the date on which the next one begins is left alone."""
        cue = ROLE_BEFORE.search(self.text[:position])
        if not cue or self.transit:
            return None
        role = cue.lastgroup
        other = 'end' if role == 'start' else 'start'
        day = lambda r, k: date.fromisoformat(r[k]) if r.get(k) else None
        for end, rows, major in self.period_mentions:
            if end > cue.start() or not TIGHT.match(self.text[end:cue.start()]):
                continue
            stated = [day(r, k) for r in rows for k in (role, 'major_' + role)]
            if any(d and same(d) for d in stated):
                continue                                      # it is that end of the period, as stated
            key = 'major_' + other if major else other
            hit = next((r for r in rows if day(r, key) and same(day(r, key))), None)
            if hit:
                return role, hit, major
        return None

    def boundary_failure(self, shown, role, row, major):
        other = 'end' if role == 'start' else 'start'
        if major:
            fact = f"The {row['major_name']} Mahadasha starts on {row['major_start']} and ends on {row['major_end']}."
        else:
            fact = f"{row['major_name']} / {row['sub_name']} starts on {row['start']} and ends on {row['end']}."
            nxt = next((r for rows in self.t.dashas.values() for r in rows if r is not row and r.get(role) == row[other]), None)
            if nxt:
                fact += f" The period that {role}s on {nxt[role]} is {nxt['major_name']} / {nxt['sub_name']}."
        self.fail('wrong_period_boundary', f'{shown} is stated as the {role} of the named period, but it is its {other}', fact)

    def numbers(self):
        if not SAV_CUE.search(self.blank):
            return
        t = self.t
        allowed = {row['sav'] for row in t.sav.values() if row['sav'] is not None} | {s['sav'] for s in t.transits if s['sav'] is not None}
        allowed |= {v for row in t.sav.values() for v in row['bav'].values() if v is not None} | {28, 8}
        if not allowed:
            return
        text = DURATION.sub(lambda m: ' ' * len(m.group()), self.blank)
        for m in re.finditer(r'(?<![\w.-])(\d{1,2})(?![\w-]|\s*(?:st|nd|rd|th)\b)', text):
            if any(e.start <= m.start() < e.end for e in self.ents):
                continue
            if int(m.group(1)) not in allowed:
                self.fail('wrong_ashtakavarga_value', f'the Ashtakavarga figure {m.group(1)} is not in the calculated table',
                          'Use only the SAV and BAV figures given.')
            else:
                self.verified += 1

    def yogas(self):
        detected = ' | '.join(y['name'].casefold() for y in self.t.yogas + self.t.jaimini_yogas)
        for name in YOGA_NAME.findall(self.text):
            key = name.casefold()
            if key in ('this', 'that', 'the', 'a', 'such', 'each', 'no', 'any', 'which', 'these', 'detected', 'stored'):
                continue
            if key in detected:
                self.verified += 1
            elif SECOND_PERSON.search(self.text) and not MARKER.search(self.text) and not NEGATED.search(self.text):
                self.fail('yoga_not_detected', f'{name} Yoga is stated for this chart', "It is not among the app's detected yogas.")

    def passage_supports(self, passage):
        """A cited passage must share the sentence's subject: a planet or house the sentence names, or at
        least two of its content words. (A wording test: it shows the citation is on topic, not that the
        book proves the point.)"""
        snippet = str(passage.get('snippet') or '').casefold()
        if not snippet:
            return True
        from .retrieval import _overlap
        planets = [e.value for e in self.ents if e.kind == 'P']
        houses = [e.value for e in self.ents if e.kind in ('H', 'L') and e.value]
        if (planets or houses) and _overlap(snippet, {'planets': planets, 'houses': houses}) > 0:
            return True
        words = set(CONTENT_WORD.findall(MARKER.sub(' ', self.text).casefold())) - COMMON
        return len({w for w in words if w in snippet}) >= 2

    def policy(self):
        text = self.text
        uncalculated = UNCALCULATED.search(text)
        if uncalculated and not NEGATED.search(text):
            self.fail('uncalculated_factor', f"'{uncalculated.group()}' is not calculated by this app", 'Remove it, or say plainly that the app does not calculate it.')
        for marker in markers(text):
            if marker not in self.passages:
                self.fail('unknown_source_marker', f'({marker}) is not a retrieved passage')
            else:
                self.refs.append({'passage_id': self.passages[marker]['id'], 'marker': marker})
                if not self.passage_supports(self.passages[marker]):
                    self.fail('citation_not_supported', f'({marker}) does not discuss what this sentence says',
                              'Cite a passage only for what it actually says about a factor; otherwise drop the citation or the sentence.')
        mention = SOURCE_TERMS.search(text)
        if mention and not MARKER.search(text):
            if not self.passages or not _title_matches(mention.group(), [p['citation'] for p in self.passages.values()]):
                self.fail('uncited_source', f"'{mention.group()}' is named but no such passage was retrieved",
                          'Name a source only when citing one of the retrieved passages with its (P) marker.')
        for name, pattern in (('event_probability', PROBABILITY), ('certainty_claim', CERTAINTY), ('longevity_or_death_content', DEATH),
                              ('diagnosis_or_illness_prediction', DIAGNOSIS), ('medical_advice', MEDICAL_ADVICE), ('fertility_policy', FERTILITY)):
            found = pattern.search(text)
            if found:
                self.fail(name, f"'{found.group()}' is not allowed", 'Describe the strength and direction of the indications in words; no odds, guarantees or medical statements.')
        if REMEDY.search(text) and not MARKER.search(text):
            self.fail('unsupported_remedy', f"'{REMEDY.search(text).group()}': remedies need a retrieved source")
        vague = GENERIC_PHRASES.search(text) or VAGUE.search(text)
        if vague:
            self.fail('generic_phrase', f"'{vague.group()}' names no actual factor", 'Name the planet, house, period or transit you mean.')


def check_answer(answer, tables, plan, passages, *, today, conflicts_present):
    """Check a written answer. Returns the AGENTS.md validation shape plus per-sentence findings and provenance."""
    passages = {p['marker']: p for p in passages}
    findings, soft, provenance, missing, verified, kinds = [], [], [], [], 0, set()
    if type(answer) is not dict:
        return _report([{'field': 'answer', 'sentence': '', 'code': 'invalid_answer', 'detail': 'the writer returned no answer object', 'correction': ''}],
                       [], [], ['all'], 0, {})
    for field in FIELDS:
        text = answer.get(field)
        if type(text) is not str:
            continue
        for index, sentence in enumerate(sentences(text)):
            result = SentenceCheck(sentence, tables, plan, passages, today, field).run()
            verified += result.verified
            kinds |= result.kinds
            findings += [{'field': field, 'index': index, 'sentence': sentence, **f} for f in result.findings]
            soft += [{'field': field, 'sentence': sentence[:120], 'note': note} for note in result.soft]
            if result.refs:
                provenance.append({'field': field, 'index': index, 'sentence': sentence, 'refs': result.refs})
    copied = copied_runs(' '.join(str(answer.get(f) or '') for f in FIELDS), {p['id']: p for p in passages.values()})
    for run in copied:
        for field in FIELDS:
            for index, sentence in enumerate(sentences(str(answer.get(field) or ''))):
                if run in re.sub(r'[^a-z0-9]+', ' ', sentence.casefold()):
                    findings.append({'field': field, 'index': index, 'sentence': sentence, 'code': 'verbatim_source_copy',
                                     'detail': 'twelve or more consecutive words are copied from a passage', 'correction': 'Paraphrase the source.'})
    qtype = plan.label['question_type']
    if not str(answer.get('direct_answer') or '').strip():
        missing.append('direct_answer')
    if qtype != 'concept_explanation':
        if verified < 3:
            missing.append('calculated_basis')
        # Every body of evidence the plan gathered must be used with at least one specific, verified statement
        # (AGENTS.md: no Jaimini, divisional or timing talk without the actual factors).
        t = tables
        required = [('natal', bool(t.lagna.get('d1'))), ('divisional', any(v != 'd1' for v in t.lagna)),
                    ('jaimini', bool(plan.jaimini_points and t.karakas)), ('period', bool(plan.timing and t.dashas)),
                    ('transit', bool(plan.timing and t.transits))]
        missing += [f'{kind}_basis' for kind, wanted in required if wanted and kind not in kinds and verified >= 3]
        if plan.timing and not str(answer.get('periods') or '').strip():
            missing.append('timing')
        if conflicts_present and not str(answer.get('conflicts') or '').strip():
            missing.append('conflicting_signals')
        if len(plan.events) > 1 and len(sentences(str(answer.get('event_assessment') or ''))) < len(plan.events):
            missing.append('event_comparison')
    if passages and not markers(' '.join(str(answer.get(f) or '') for f in FIELDS)):
        missing.append('classical_support')
    strength = answer.get('evidence_strength')
    if type(strength) is not dict or strength.get('label') not in STRENGTH_LABELS:
        missing.append('evidence_strength_label')
    elif len(str(strength.get('reason') or '').strip()) < 20:
        missing.append('evidence_strength_reason')
    full = ' '.join(str(answer.get(f) or '') for f in FIELDS)
    _, blank = _dates(full)
    mentioned = {e.value for e in entities(blank) if e.kind in ('H', 'L') and e.value}
    coverage = {'primary_houses_discussed': [h for h in plan.houses['primary'] if h in mentioned],
                'primary_houses_not_discussed': [h for h in plan.houses['primary'] if h not in mentioned],
                'other_focus_houses_discussed': [h for h in plan.focus_houses if h in mentioned and h not in plan.houses['primary']]}
    if qtype != 'concept_explanation' and plan.houses['primary'] and not coverage['primary_houses_discussed']:
        missing.append('primary_house_logic')
    coverage['evidence_used'] = sorted(kinds)
    return _report(findings, soft, provenance, missing, verified, coverage, essential_sections(plan))


def _report(findings, soft, provenance, missing, verified, coverage, essential=ALWAYS_ESSENTIAL):
    issues = list(dict.fromkeys(f"{f['field']}: {f['code']}" for f in findings))
    problems = issues + ['missing_' + m for m in missing]
    lines = []
    for f in findings[:12]:
        lines.append(f"- In {f['field']}: \"{f['sentence'][:220]}\" -> {f['detail']}. {f['correction']}".strip())
    for m in missing:
        lines.append({'direct_answer': '- Start with a direct answer to the question.',
                      'calculated_basis': '- Ground the reading in the calculated placements, lords and periods given in the brief.',
                      'timing': '- Explain the timing from the periods and transits in the window.',
                      'conflicting_signals': '- State the conflicting indications; the brief contains cautionary rules.',
                      'primary_house_logic': '- Discuss the primary house for this question and its lord.',
                      'event_comparison': '- In event_assessment, take each event in EVENT EVIDENCE in turn: what supports it, what opposes it; then say which the evidence supports more strongly, or that it does not separate them.',
                      'classical_support': '- In classical_support, say what the CLASSICAL PASSAGES add for this chart (supporting and contrary), paraphrased, and cite each one you use as (P1), (P2).',
                      'natal_basis': '- Add the natal basis: the house, its lord and where that lord sits, from NATAL CHART.',
                      'divisional_basis': '- Add the divisional confirmation with actual placements from DIVISIONAL CHARTS (for example where the 10th lord sits in D10 or D9).',
                      'jaimini_basis': '- Add the Jaimini view with actual factors from JAIMINI (for example which planet is the Amatyakaraka and where it sits, or the 10th from the Arudha Lagna).',
                      'period_basis': '- Add the running periods by name with their dates from PERIODS, and say how each period lord connects to the houses in question.',
                      'transit_basis': '- Add the transits from TRANSITS: which house Saturn and Jupiter transit, when, and the SAV of that sign.',
                      'evidence_strength_label': '- Give evidence_strength a label (limited, moderate or strong).',
                      'evidence_strength_reason': '- Give a reason for the evidence strength.'}.get(m, f'- Provide {m}.'))
    instruction = ''
    if problems:
        instruction = ('Correct only the statements listed below and keep everything else as it is. Each correction gives the '
                       'calculated value; restate the sentence with it, or delete the sentence, and adjust any conclusion that '
                       'depended on it so the reading stays coherent.\n' + '\n'.join(lines))
    # passed: complete. publishable: nothing wrong remains and nothing essential is missing (a preliminary reading).
    return {'passed': not problems, 'publishable': not findings and not any(m in essential for m in missing),
            'essential_missing': [m for m in missing if m in essential], 'supplementary_missing': [m for m in missing if m not in essential],
            'score': max(0, 100 - 10 * len(problems)), 'issues': issues, 'missing_sections': list(missing),
            'generic_phrases_detected': [f['detail'] for f in findings if f['code'] == 'generic_phrase'],
            'unsupported_claims': list(dict.fromkeys(f['sentence'][:160] for f in findings))[:12], 'repair_instruction': instruction,
            'findings': findings, 'soft': soft[:40], 'provenance': provenance, 'verified_statements': verified, 'coverage': coverage}


def prune(answer, findings):
    """Remove the sentences that still carry findings, and a following sentence that leans on a removed one.
    Returns (answer, removed sentences)."""
    bad = {}
    for f in findings:
        bad.setdefault(f['field'], set()).add(f['index'])
    cleaned, removed = dict(answer), []
    for field, indexes in bad.items():
        if field not in FIELDS or type(answer.get(field)) is not str:
            continue
        kept, dropped_previous = [], False
        for index, sentence in enumerate(sentences(answer[field])):
            if index in indexes or (dropped_previous and DEPENDENT.match(sentence.strip())):
                removed.append({'field': field, 'sentence': sentence})
                dropped_previous = True
            else:
                kept.append(sentence)
                dropped_previous = False
        cleaned[field] = ' '.join(kept)
    return cleaned, removed


def clean_text(text, passages):
    """Reader-facing text: (P1) markers become source names; internal IDs never appear."""
    by_marker = {p['marker']: p for p in passages}

    def cite(match):
        names = []
        for marker in re.findall(r'P\d{1,2}', match.group(1)):
            p = by_marker.get(marker)
            if p:
                detail = ', '.join(f'{k} {p[k]}' for k in ('chapter', 'page') if p.get(k))
                names.append(f"{p['title']}{', ' + detail if detail else ''}")
        return f"({'; '.join(dict.fromkeys(names))})" if names else ''
    text = MARKER.sub(cite, text or '')
    text = INTERNAL_ID.sub('', text)
    return re.sub(r'\s+([.,;:])', r'\1', re.sub(r'[ \t]{2,}', ' ', text)).strip()
