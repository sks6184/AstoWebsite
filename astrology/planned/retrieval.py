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
PER_PURPOSE = 3
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
    """Up to ``limit`` searches: [{'query', 'purpose', 'stance', 'keys'}], most important first."""
    t, label = tables, plan.label
    if label['question_type'] == 'concept_explanation' or not t.lagna.get('d1'):
        return [{'query': _clip(question), 'purpose': 'the concept asked about', 'stance': 'neutral', 'keys': []}][:limit]
    terms = _terms(profile, label)
    topic = terms[0] if terms else ''
    events = ' '.join(e['id'].split(':')[1].replace('_', ' ') for e in plan.events[:1])
    queries = []

    def add(purpose, stance, text, planets=(), houses=()):
        if text:
            queries.append({'query': _clip(text), 'purpose': purpose, 'stance': stance,
                            'keys': {'planets': list(dict.fromkeys(planets)), 'houses': list(dict.fromkeys(houses))}})

    primary = [h for h in plan.houses['primary'] if h in t.lords.get('d1', {})]
    if primary:
        h = primary[0]
        lord = t.lords['d1'][h]
        occupants = t.occupants(h)
        text = f"{ordinal(h)} lord {P(lord['lord'])} in the {ordinal(lord['placed_house'])} house results for {topic}"
        if occupants:
            text += f"; {' and '.join(P(c) for c in occupants[:2])} in the {ordinal(h)} house"
        add('the natal promise', 'supporting', text + (f'; {events}' if events else ''),
            [lord['lord'], *occupants[:2]], [h, lord['placed_house']])

    if plan.timing and t.dashas.get('vimshottari'):
        rows = t.dashas['vimshottari']
        major = rows[0]['major']
        subs = list(dict.fromkeys(r['sub'] for r in rows if r['sub']))[:2]
        text = f"{P(major)} Mahadasha " + ' and '.join(f'{P(s)} sub-period' for s in subs) + ' results'
        ruled = t.ruled(major)
        if ruled and t.place.get('d1', {}).get(major):
            text += f"; dasha of the lord of the {ordinal(ruled[0])} placed in the {ordinal(t.place['d1'][major]['house'])} house"
        add('the running periods', 'supporting', text + f'; {topic}', [major, *subs],
            ruled[:1] + ([t.place['d1'][major]['house']] if t.place.get('d1', {}).get(major) else []))

    if plan.timing and t.transits:
        parts, planets, houses = [], [], []
        for code in ('Sa', 'Ju'):
            segs = [r for r in t.transits if r['planet'] == code]
            if segs:
                seg = max(segs, key=lambda r: (date.fromisoformat(r['end']) - date.fromisoformat(r['start'])).days)   # the longest stay
                parts.append(f"{P(code)} transit through the {ordinal(seg['house'])} house from Lagna" +
                             (f" and {ordinal(seg['moon_house'])} from the Moon" if seg['moon_house'] else ''))
                planets.append(code)
                houses += [seg['house']] + ([seg['moon_house']] if seg['moon_house'] else [])
        add('the transits in the window', 'supporting', '; '.join(parts) + f'; effects on {topic}; ashtakavarga bindus', planets, houses)

    # Contrary principles: the engine's strongest cautionary rule, else an affliction that the tables show.
    caution = sorted((r for rules in t.rules.values() for r in rules if r['polarity'] != 'positive' and r['weight'] > 0),
                     key=lambda r: -r['weight'])
    if caution:
        text = re.sub(r'[^\w ,/-]+', ' ', caution[0]['text'].split(';')[0])[:120]
        add('contrary or cautionary indications', 'contrary', f'{text} {topic} obstacles',
            [], [int(x) for x in re.findall(r'\b(\d{1,2})(?:st|nd|rd|th)\b', text) if 1 <= int(x) <= 12])
    elif primary:
        h = primary[0]
        afflicting = [c for c in MALEFICS if c in t.occupants(h) or c in t.aspecting(h)]
        lord = t.lords['d1'][h]
        if afflicting:
            add('contrary or cautionary indications', 'contrary',
                f"{P(afflicting[0])} influence on the {ordinal(h)} house obstacles delay loss in {topic}", afflicting[:1], [h])
        elif lord['placed_house'] in (6, 8, 12):
            add('contrary or cautionary indications', 'contrary',
                f"{ordinal(h)} lord in the {ordinal(lord['placed_house'])} house difficulties loss obstacles {topic}", [lord['lord']], [h, lord['placed_house']])

    amk = t.karakas.get('Amatyakaraka')
    counted = t.counted[0] if t.counted else None
    if amk and plan.jaimini_points:
        text = f"Amatyakaraka {P(amk['code'])} in the {ordinal(amk['house'])} house"
        if counted:
            text += f"; {ordinal(counted['count'])} from {counted['reference'].replace('_', ' ')} " + \
                    (f"occupied by {P(counted['occupants'][0])}" if counted['occupants'] else 'unoccupied')
        add('the Jaimini view', 'supporting', text + f'; {topic}', [amk['code']], [amk['house']])
    for varga in plan.vargas:
        if varga not in ('d1', 'd9') and primary and t.lords.get(varga, {}).get(primary[0]):
            row = t.lords[varga][primary[0]]
            add('the divisional chart', 'supporting',
                f"{varga.upper()} {ordinal(primary[0])} lord {P(row['lord'])} in {S(row['placed_sign'])} in the {ordinal(row['placed_house'])} house of {varga.upper()} {topic}",
                [row['lord']], [primary[0], row['placed_house']])
            break
    # Keep a contrary search within the limit: it is moved up rather than dropped.
    ordered = queries[:limit]
    contrary = next((q for q in queries if q['stance'] == 'contrary'), None)
    if contrary and contrary not in ordered and limit >= 2:
        ordered[-1] = contrary
    return ordered


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
            title = title_of(p['citation'])
            haystack = ' '.join(str(v) for v in p['citation'].values() if v).casefold().replace('_', ' ')
            guided = next((b for b, row in books.items() if any(k in haystack for k in row['keywords'])), None)
            overlap = _overlap(p['snippet'], query['keys'])
            semantic = p['score'] if p['score'] is not None else 0.5
            score = round(semantic + 0.15 * overlap + (0.10 if guided else 0.0), 4)
            row = {'id': p['evidence_id'], 'title': title, 'chapter': p['citation'].get('chapter'), 'page': p['citation'].get('page'),
                   'purpose': query['purpose'], 'stance': query['stance'], 'semantic': p['score'], 'overlap': round(overlap, 2),
                   'guided_book': guided, 'score': score, 'snippet': p['snippet'][:SNIPPET_CHARS], 'citation': p['citation']}
            if row['id'] not in pool or score > pool[row['id']]['score']:
                pool[row['id']] = row
    ranked = sorted(pool.values(), key=lambda r: -r['score'])
    kept, per = [], {}
    eligible = [r for r in ranked if r['semantic'] is None or r['semantic'] >= MIN_SCORE or r['overlap'] >= 0.5]
    contrary = next((r for r in eligible if r['stance'] == 'contrary'), None)
    for row in ([contrary] if contrary else []) + eligible:
        if row in kept or len(kept) >= KEEP or per.get(row['purpose'], 0) >= PER_PURPOSE:
            continue
        kept.append(row)
        per[row['purpose']] = per.get(row['purpose'], 0) + 1
    kept.sort(key=lambda r: -r['score'])
    for i, row in enumerate(kept, 1):
        row['marker'] = f'P{i}'
    report = [{'id': r['id'], 'title': r['title'], 'purpose': r['purpose'], 'stance': r['stance'], 'semantic': r['semantic'],
               'overlap': r['overlap'], 'guided_book': r['guided_book'], 'score': r['score'], 'kept': r in kept} for r in ranked]
    return kept, report
