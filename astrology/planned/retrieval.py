"""Retrieval after calculation: search text built from the actual results, then a pooled re-rank.

The vector store ranks semantically (embeddings plus the provider's own re-ranker). This module adds a
second, local re-rank over the pooled hits: the provider score stays the main signal, and a passage gains a
little when it shares the calculated factors' terms or comes from a book the event matrix names for the
event. Keyword overlap alone never admits or rejects a passage.
"""
from datetime import date
from functools import lru_cache
from pathlib import Path
import re

import yaml

from astrology.validation.prose_validator import title_of
from .brief import ordinal
from .tables import planet_name as P, sign_name as S

GUIDANCE_PATH = Path(__file__).resolve().parent.parent / 'methodology' / 'source_guidance.v0.yaml'
MAX_QUERY_BYTES = 200
KEEP = 6                 # passages given to the writer
PER_PURPOSE = 2
SNIPPET_CHARS = 700
MIN_SCORE = 0.30         # below this a hit needs term overlap to be kept
MALEFICS = ('Sa', 'Ma', 'Ra', 'Ke')
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'}
WORDS = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'eighth',
         9: 'ninth', 10: 'tenth', 11: 'eleventh', 12: 'twelfth'}


@lru_cache(maxsize=1)
def source_guidance():
    return yaml.safe_load(GUIDANCE_PATH.read_text(encoding='utf-8'))


def guided_books(label):
    """Title keywords of the books the event matrix names for the labelled events (or their domains)."""
    data = source_guidance()
    found = {}
    for domain in label['domains']:
        entry = data['events'].get(domain) or {}
        names = [e.partition(':')[2] for e in label['events'] if e.startswith(domain + ':')]
        rows = [entry[n] for n in names if n in entry] or [entry.get('_domain') or {}]
        for row in rows:
            for book, chapters in row.items():
                found.setdefault(book, set()).update(c.strip() for c in str(chapters).split(',') if c.strip())
    return {book: {'keywords': data['books'].get(book, []), 'chapters': sorted(ch)} for book, ch in found.items()}


def _terms(profile, label):
    """Plain book-vocabulary words for the labelled areas (the books' own words, from the profile)."""
    words = []
    for domain in label['domains']:
        vocabulary = profile.entry(domain).get('vocabulary') or []
        plain = [v for v in vocabulary if re.fullmatch(r'[a-z ]{4,}', str(v.get('term', '')))]
        words += [v['term'] for v in sorted(plain, key=lambda v: -int(v.get('mentions') or 0))[:2]]
        if not plain:
            words.append(str(profile.entry(domain).get('label', domain)).split(',')[0].casefold())
    return list(dict.fromkeys(words))


def _clip(text):
    text = ' '.join(text.split())
    while len(text.encode('utf-8')) > MAX_QUERY_BYTES:
        text = text.rsplit(' ', 1)[0]
    return text


def build_queries(question, plan, tables, profile, limit):
    """Up to ``limit`` searches, most important first: [{'query', 'purpose', 'stance', 'keys'}].

    Each search states ONE principle that the calculations make applicable, in the books' own way of
    stating it ("results of the 10th lord in the 12th house"), instead of a string of this chart's
    factors: a factor list mostly retrieves worked examples of other people's charts.
    """
    t, label = tables, plan.label
    if label['question_type'] == 'concept_explanation' or not t.lagna.get('d1'):
        return [{'query': _clip(question), 'purpose': 'the concept asked about', 'stance': 'neutral', 'keys': {}}][:limit]
    terms = _terms(profile, label)
    topic = terms[0] if terms else ''
    queries = []

    def add(purpose, stance, text, planets=(), houses=()):
        if text and not any(q['query'] == _clip(text) for q in queries):
            queries.append({'query': _clip(text), 'purpose': purpose, 'stance': stance,
                            'keys': {'planets': list(dict.fromkeys(planets)), 'houses': list(dict.fromkeys(houses))}})

    primary = [h for h in plan.houses['primary'] if h in t.lords.get('d1', {})]
    if primary:
        h = primary[0]
        lord = t.lords['d1'][h]
        add(f"the {ordinal(h)} lord in the {ordinal(lord['placed_house'])} house", 'supporting',
            f"Results of the lord of the {ordinal(h)} house placed in the {ordinal(lord['placed_house'])} house; effect on {topic}",
            [], [h, lord['placed_house']])

    rows = t.dashas.get('vimshottari') or []
    if rows:
        span = lambda r: (min(date.fromisoformat(r['end']), date.fromisoformat(plan.window['end'])) -
                          max(date.fromisoformat(r['start']), date.fromisoformat(plan.window['start']))).days
        main = max(rows, key=span) if plan.timing else rows[0]          # the sub-period that covers most of the window
        if main['major'] and main['sub']:
            add(f"the {P(main['sub'])} sub-period in the {P(main['major'])} Mahadasha", 'supporting',
                f"Effects of the sub-period (antardasha) of {P(main['sub'])} in the Mahadasha of {P(main['major'])}",
                [main['major'], main['sub']], [])

    if plan.timing and t.transits:
        segs = [r for r in t.transits if r['planet'] == 'Sa'] or [r for r in t.transits if r['planet'] == 'Ju']
        if segs:
            seg = max(segs, key=lambda r: (date.fromisoformat(r['end']) - date.fromisoformat(r['start'])).days)   # the longest stay
            house = seg['moon_house'] or seg['house']
            add(f"{P(seg['planet'])}'s transit through the {ordinal(house)} from the {'Moon' if seg['moon_house'] else 'Lagna'}", 'supporting',
                f"Results of the transit of {P(seg['planet'])} through the {ordinal(house)} house from the natal {'Moon' if seg['moon_house'] else 'Lagna'} (gochara)",
                [seg['planet']], [house])

    # A contrary principle: the engine's strongest cautionary rule, else an affliction the tables show.
    caution = sorted((r for rules in t.rules.values() for r in rules if r['polarity'] != 'positive' and r['weight'] > 0),
                     key=lambda r: -r['weight'])
    if caution:
        text = re.sub(r'[^\w ,/-]+', ' ', caution[0]['text'].split(';')[0])[:130]
        add('a cautionary principle from the rule engine', 'contrary', text,
            [], [int(x) for x in re.findall(r'\b(\d{1,2})(?:st|nd|rd|th)\b', text) if 1 <= int(x) <= 12])
    elif primary:
        h = primary[0]
        afflicting = [c for c in MALEFICS if c in t.occupants(h) or c in t.aspecting(h)]
        if afflicting:
            add(f"{P(afflicting[0])}'s influence on the {ordinal(h)} house", 'contrary',
                f"Effects of {P(afflicting[0])} occupying or aspecting the {ordinal(h)} house: obstacles and delay in {topic}", afflicting[:1], [h])

    # A derived relationship named for an asked event (for example the 5th as the 12th from the 6th).
    for event in plan.events:
        for house, text in event['derived'].items():
            add(f"the {ordinal(house)} house as {text.split(':')[0]}", 'neutral',
                f"The {ordinal(house)} house as {text.split(':')[0]} (bhavat bhavam): leaving or change of service and position", [], [house])
    amk = t.karakas.get('Amatyakaraka')
    if amk and plan.jaimini_points:
        add('the Amatyakaraka', 'supporting', f"Amatyakaraka in the {ordinal(amk['house'])} house: results for {topic} (Jaimini)", [amk['code']], [amk['house']])
    ordered = queries[:limit]
    contrary = next((q for q in queries if q['stance'] == 'contrary'), None)
    if contrary and contrary not in ordered and limit >= 2:
        ordered[-1] = contrary                                          # a contrary search is moved up, never dropped
    return ordered


def display_title(citation):
    """The stored source name made readable (upload prefixes and file suffixes removed); nothing is added."""
    title = re.sub(r'^\d{5,}[-_ ]+', '', title_of(citation))
    title = re.sub(r'[-_ ]+pdf$', '', title, flags=re.I)
    title = re.sub(r'[-_]+', ' ', title).strip()
    return title if any(c.isupper() for c in title) else title.title()


EXAMPLE_PENALTY = 0.25
EXAMPLE_MARKS = re.compile(r"\bChart\s+(?:No\.?\s*)?\d+|\bCase\s+Stud(?:y|ies)\b|\bnative(?:'s)?\b|\b(?:he|she|his|her)\b|"
                           r"\b(?:19|20)\d{2}\b|\bAnalysis\s+of\b|\bwas\s+born\b|\bthis\s+person\b", re.I)


def worked_example(snippet):
    """True when a passage reads as the analysis of a particular person's chart rather than a statement of
    principle (chart numbers, "the native", he/she, calendar years). Such text shares planets and houses
    with any chart, which is exactly why it must not pass for support."""
    return len(EXAMPLE_MARKS.findall(snippet or '')) >= 3


def _overlap(snippet, keys):
    """Share of the query's calculated factors (planets and houses) that the passage mentions, in any spelling."""
    if not keys:
        return 0.0
    text = snippet.casefold()
    wanted, hit = 0, 0
    for code in keys.get('planets', []):
        wanted += 1
        hit += P(code).casefold() in text
    for h in keys.get('houses', []):
        wanted += 1
        hit += bool(re.search(rf'\b(?:{h}(?:st|nd|rd|th)|{WORDS[h]}|{ROMAN[h].casefold()}th)\b', text))
    return hit / wanted if wanted else 0.0


def rerank(searches, label):
    """Pool every search's passages, score them, and keep a small, balanced set for the writer.

    ``searches`` is [(query, passages)]. Returns (kept, report): kept passages carry a ``marker`` (P1...),
    and the report lists every hit with its scores and whether it was kept (for the trace).
    """
    books = guided_books(label)
    pool = {}
    for query, passages in searches:
        for p in passages:
            title = display_title(p['citation'])
            haystack = ' '.join(str(v) for v in p['citation'].values() if v).casefold().replace('_', ' ')
            guided = next((b for b, row in books.items() if any(k in haystack for k in row['keywords'])), None)
            overlap = _overlap(p['snippet'], query['keys'])
            semantic = p['score'] if p['score'] is not None else 0.5
            example = worked_example(p['snippet'])
            score = round(semantic + 0.10 * overlap + (0.10 if guided else 0.0) - (EXAMPLE_PENALTY if example else 0.0), 4)
            row = {'id': p['evidence_id'], 'title': title, 'chapter': p['citation'].get('chapter'), 'page': p['citation'].get('page'),
                   'purpose': query['purpose'], 'stance': query['stance'], 'semantic': p['score'], 'overlap': round(overlap, 2),
                   'guided_book': guided, 'worked_example': example, 'score': score, 'snippet': p['snippet'][:SNIPPET_CHARS],
                   'citation': p['citation']}
            if row['id'] not in pool or score > pool[row['id']]['score']:
                pool[row['id']] = row
    ranked = sorted(pool.values(), key=lambda r: -r['score'])
    kept, per = [], {}
    eligible = [r for r in ranked if r['semantic'] is None or r['semantic'] >= MIN_SCORE or r['overlap'] >= 0.5]
    # A worked example of someone else's chart is given to the writer only when its search found no
    # statement of principle at all, and then it is labelled as an example.
    principled = {r['purpose'] for r in eligible if not r['worked_example']}
    eligible = [r for r in eligible if not r['worked_example'] or r['purpose'] not in principled]
    contrary = next((r for r in eligible if r['stance'] == 'contrary'), None)
    # The best passage for each search first, so every searched factor is represented (the contrary one
    # included), then the next best overall.
    first = []
    for row in eligible:
        if row['purpose'] not in {r['purpose'] for r in first}:
            first.append(row)
    for row in ([contrary] if contrary else []) + first + eligible:
        if row in kept or len(kept) >= KEEP or per.get(row['purpose'], 0) >= PER_PURPOSE:
            continue
        kept.append(row)
        per[row['purpose']] = per.get(row['purpose'], 0) + 1
    kept.sort(key=lambda r: -r['score'])
    for i, row in enumerate(kept, 1):
        row['marker'] = f'P{i}'
    report = [{'id': r['id'], 'title': r['title'], 'purpose': r['purpose'], 'stance': r['stance'], 'semantic': r['semantic'],
               'overlap': r['overlap'], 'guided_book': r['guided_book'], 'worked_example': r['worked_example'], 'score': r['score'],
               'kept': r in kept} for r in ranked]
    return kept, report
