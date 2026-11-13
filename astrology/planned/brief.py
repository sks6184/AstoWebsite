"""The astrologer's brief: the calculated evidence for one question, laid out the way an astrologer reads a chart.

Server wording only. Each line restates values from ``Tables`` (tool results); no line judges an outcome.
Rule texts are the deterministic engine's own paraphrased interpretations, and passages are untrusted
source excerpts for paraphrase.
"""
from astrology.validation.prose_validator import DEATH, DIAGNOSIS, FERTILITY
from .tables import planet_name as P, sign_name as S

ORD = {1: '1st', 2: '2nd', 3: '3rd'}
MAX_RULES_EACH = 5
DIGNITY = {'exalted': 'exalted', 'debilitated': 'debilitated', 'own_sign': 'in its own sign'}


def ordinal(n):
    return ORD.get(n, f'{n}th')


def _names(codes):
    return ', '.join(P(c) for c in codes) or 'none'


def _placement(t, code, varga='d1', detail=True):
    row = t.place.get(varga, {}).get(code)
    if not row:
        return None
    text = f"{S(row['sign'])}, house {row['house']}"
    if detail:
        if row.get('nakshatra'):
            text += f", {row['nakshatra']} nakshatra"
        if row.get('retrograde'):
            text += ', retrograde'
        if DIGNITY.get(row.get('dignity')):
            text += ', ' + DIGNITY[row['dignity']]
    return text


def _house_line(t, house, role):
    sign = t.house_sign(house)
    lord = t.lords.get('d1', {}).get(house)
    if not sign or not lord:
        return None
    line = f"- {ordinal(house)} house ({role}): sign {S(sign)}. Its lord {P(lord['lord'])} is placed in {S(lord['placed_sign'])}, house {lord['placed_house']}"
    if DIGNITY.get(lord.get('dignity')):
        line += f" ({DIGNITY[lord['dignity']]})"
    line += f". Occupants: {_names(t.occupants(house))}. Aspected by (Parashari): {_names(t.aspecting(house))}."
    sav = t.sav.get(sign, {}).get('sav')
    if sav is not None:
        line += f' SAV {sav}.'
    return line


def _planet_line(t, code, vargas, why):
    d1 = _placement(t, code)
    if not d1:
        return None
    ruled = t.ruled(code)
    line = f"- {P(code)} ({why}): D1 {d1}."
    if ruled:
        line += f" Rules house{'s' if len(ruled) > 1 else ''} {', '.join(map(str, ruled))}."
    aspects = t.aspects.get(code, {}).get('houses')
    if aspects:
        line += f" Aspects house{'s' if len(aspects) > 1 else ''} {', '.join(map(str, aspects))}."
    for varga in vargas:
        if varga != 'd1' and _placement(t, code, varga, False):
            line += f" {varga.upper()}: {_placement(t, code, varga, False)}."
    return line


def _links(t, code, focus, plan=None):
    """How a period lord connects to the houses in focus (ownership, occupation, aspect): lookups only.
    A house that is the primary house for the question is marked, so the connection is not overlooked."""
    row = t.place.get('d1', {}).get(code)
    if not row:
        return ''
    primary = set(plan.houses['primary']) if plan else set()
    mark = lambda h: f'{h} (the primary house for this question)' if h in primary else str(h)
    parts = []
    ruled = t.ruled(code)
    if ruled:
        parts.append(f"rules house{'s' if len(ruled) > 1 else ''} " + ', '.join(mark(h) for h in ruled))
    parts.append(f"sits in house {mark(row['house'])}")
    aspects = [h for h in t.aspects.get(code, {}).get('houses', []) if h in focus]
    if aspects:
        parts.append(f"aspects house{'s' if len(aspects) > 1 else ''} " + ', '.join(mark(h) for h in aspects))
    return f"{P(code)} {'; '.join(parts)}"


def _event_evidence(t, plan):
    """For each event asked about: which period lords and transits touch its houses, and which triggered
    rules speak to it. Lookups and counts only; the weighing is the astrologer's."""
    lines = []
    rules = {}
    first = min((as_of for _, as_of in t.rules), default=None)
    for (category, as_of), rows in t.rules.items():
        if as_of == first:
            for r in rows:
                rules.setdefault(r['id'] or r['text'], r)
    usable = [r for r in rules.values() if not (DEATH.search(r['text']) or DIAGNOSIS.search(r['text']) or FERTILITY.search(r['text']))]
    for event in plan.events:
        name = event['id'].split(':')[1].replace('_', ' ')
        houses, derived = event['houses'], event['derived']
        every = set(houses) | set(derived)
        tag = lambda h: f"{h} (derived: {derived[h]})" if h in derived and h not in houses else str(h)
        lines.append(f"Event: {name}. Houses read for it: {', '.join(map(str, houses))}." +
                     (' Derived relationships (indicators to combine with the period lords, aspects and D10; never a rule on their own): ' +
                      '; '.join(f'the {ordinal(h)} is {text}' for h, text in derived.items()) + '.' if derived else ''))
        for r in t.dashas.get('vimshottari', [])[:6]:
            parts = []
            for code in dict.fromkeys(c for c in (r['major'], r['sub']) if c):
                row = t.place.get('d1', {}).get(code)
                if not row:
                    continue
                bits = []
                ruled = [h for h in t.ruled(code) if h in every]
                if ruled:
                    bits.append('rules ' + ', '.join(tag(h) for h in ruled))
                if row['house'] in every:
                    bits.append('sits in ' + tag(row['house']))
                aspects = [h for h in t.aspects.get(code, {}).get('houses', []) if h in every]
                if aspects:
                    bits.append('aspects ' + ', '.join(tag(h) for h in aspects))
                if bits:
                    parts.append(f"{P(code)} {'; '.join(bits)}")
            lines.append(f"- Period {r['major_name']} / {r['sub_name']} ({r['start']} to {r['end']}): " +
                         ('. '.join(parts) + '.' if parts else 'neither lord rules, occupies or aspects these houses.'))
        for s in t.transits:
            if s['planet'] not in ('Sa', 'Ju'):
                continue
            bits = ([f"occupies {tag(s['house'])}"] if s['house'] in every else []) + \
                   ([f"aspects {', '.join(tag(h) for h in s['aspects'] if h in every)}"] if every & set(s['aspects']) else [])
            if bits:
                lines.append(f"- Transit {P(s['planet'])} in {S(s['sign'])} ({s['start']} to {s['end']}): {'; '.join(bits)} (houses from the Lagna).")
        keys = event['rule_outcomes']
        if keys and usable:
            score = lambda r: sum(r['outcomes'].get(k, 0) for k in keys)
            support = sorted((r for r in usable if r['weight'] > 0 and score(r) > 0), key=lambda r: -r['weight'] * score(r))
            oppose = sorted((r for r in usable if r['weight'] > 0 and score(r) < 0), key=lambda r: r['weight'] * score(r))
            lines.append(f"- Triggered rules that speak to this event (a count of rules, not a probability): {len(support)} for, {len(oppose)} against." +
                         (f" Strongest for: {support[0]['text']}" if support else '') + (f" Strongest against: {oppose[0]['text']}" if oppose else ''))
        if event['opposing']:
            lines.append(f"- Would argue against it, if found in the chart above: {event['opposing']}.")
    return lines


def _rules(t, plan):
    lines, seen = [], set()
    for (category, as_of), rules in sorted(t.rules.items(), key=lambda x: x[0][1]):
        # Rule wording that touches the app's policy limits (death, illness, fertility) is not passed to the writer.
        usable = [r for r in rules if not (DEATH.search(r['text']) or DIAGNOSIS.search(r['text']) or FERTILITY.search(r['text']))]
        fresh = [r for r in sorted(usable, key=lambda r: -r['weight']) if r['text'] not in seen]
        support = [r for r in fresh if r['polarity'] == 'positive'][:MAX_RULES_EACH]
        caution = [r for r in fresh if r['polarity'] != 'positive' and r['weight'] > 0][:MAX_RULES_EACH]
        if not support and not caution:
            if rules:
                lines.append(f'Rules for {category} as of {as_of}: the same rules as above apply; no new rule is triggered.')
            continue
        lines.append(f'Rules for {category} as of {as_of} ({len(rules)} returned by the engine; strongest shown):')
        for title, group in (('Supportive', support), ('Cautionary or mixed', caution)):
            for r in group:
                seen.add(r['text'])
                lines.append(f"- {title} [{r['system'] or 'rule'}]: {r['text']}".replace('�', '-'))
    for text in list(dict.fromkeys(c['text'] for c in t.conflicts))[:2]:
        lines.append(f"- Engine conflict note: {text}")
    return lines


def build_brief(question, plan, tables, passages, profile, today):
    """Return (text, sections) where sections maps a heading to its lines (for tracing)."""
    t = tables
    label = plan.label
    sections = {}
    head = [f'Question: {question}', f'Today: {today.isoformat()}.',
            f"Question type: {label['question_type']}. Areas: " +
            ', '.join(profile.entry(d).get('label', d.replace('_', ' ')) for d in label['domains']) + '.']
    if plan.timing:
        head.append(f"Window examined: {plan.window['start']} to {plan.window['end']} "
                    f"({'stated in the question' if plan.window['stated'] else 'default: the user gave none, so say that the next twelve months were used'}).")
    for event in plan.events:
        head.append(f"Event in question: {event['id'].split(':')[1].replace('_', ' ')}. Examine: {event['focus']}" +
                    (f" Note: {event['note']}" if event['note'] else ''))
    for domain in label['domains']:
        note = profile.entry(domain).get('sensitivity')
        if note:
            head.append(f'Sensitivity: {note}')
    sections['QUESTION'] = head

    if t.lagna.get('d1'):
        natal = [f"Lagna (Ascendant): {S(t.lagna['d1'])}. Whole-sign houses, Lahiri sidereal zodiac."]
        moon = _placement(t, 'Mo')
        if moon:
            natal.append(f'Moon: {moon}.')
        roles = [(h, 'primary') for h in plan.houses['primary']] + [(h, 'named for this event') for h in plan.houses['event']] + \
                [(h, 'supporting') for h in plan.houses['supporting']]
        natal += [line for h, role in roles if (line := _house_line(t, h, role))]
        sections['NATAL CHART (D1)'] = natal

        lords = t.period_lords() if plan.timing else []
        planets = [(c, 'natural significator for this area') for c in plan.planets]
        planets += [(c, 'period lord in the window') for c in lords if c not in plan.planets]
        lines = [line for c, why in planets if (line := _planet_line(t, c, plan.vargas, why))]
        if lines:
            sections['PLANETS OF INTEREST'] = lines

        div = []
        for varga in plan.vargas:
            if varga == 'd1' or varga not in t.lagna:
                continue
            row = f"- {varga.upper()}: Lagna {S(t.lagna[varga])}."
            for house in plan.houses['primary']:
                lord = t.lords.get(varga, {}).get(house)
                if lord:
                    row += (f" Its {ordinal(house)} lord {P(lord['lord'])} is in {S(lord['placed_sign'])}, {varga.upper()} house {lord['placed_house']}"
                            + (f" ({DIGNITY[lord['dignity']]})" if DIGNITY.get(lord.get('dignity')) else '') + '.')
                d1 = t.lords.get('d1', {}).get(house)
                if d1 and _placement(t, d1['lord'], varga, False):
                    row += f" The D1 {ordinal(house)} lord {P(d1['lord'])} is in {_placement(t, d1['lord'], varga, False).replace('house', varga.upper() + ' house')}."
            div.append(row)
        if div:
            sections['DIVISIONAL CHARTS'] = div
        if t.yogas:
            sections['YOGAS DETECTED BY THE APP (detections, not outcomes)'] = [
                f"- {y['name']} (strength {y['strength'] or 'unstated'})" + (f": {y['evidence'][0]}" if y['evidence'] else '') for y in t.yogas[:10]]

    jaimini = []
    for name in ('Atmakaraka', 'Amatyakaraka', 'Darakaraka', 'Putrakaraka'):
        k = t.karakas.get(name)
        if k and (name in ('Atmakaraka', 'Amatyakaraka') or any(name.casefold() in p for p in plan.jaimini_points)):
            jaimini.append(f"- {name}: {P(k['code'])}, in {S(k['sign'])}, house {k['house']}.")
    if t.karakamsha:
        jaimini.append(f"- Karakamsha (D9 sign of the Atmakaraka): {S(t.karakamsha['sign'])}.")
    for house, name in ((1, 'Arudha Lagna (AL)'), (7, 'Darapada (A7)'), (12, 'Upapada Lagna (UL)')):
        pada = t.padas.get(house)
        if pada and (house == 1 or any(k in ' '.join(plan.jaimini_points) for k in (('darapada', 'a7') if house == 7 else ('upapada',)))):
            jaimini.append(f"- {name}: {S(pada['sign'])}, house {pada['house']} from the Lagna.")
    names = {'arudha_lagna': 'Arudha Lagna', 'upapada_lagna': 'Upapada Lagna', 'karakamsha': 'Karakamsha'}
    for c in t.counted:
        jaimini.append(f"- {ordinal(c['count'])} from the {names.get(c['reference'], c['reference'])}: {S(c['sign'])}, house {c['house']} from the Lagna. "
                       f"Occupants: {_names(c['occupants'])}. Influenced by (occupation or rasi drishti): {_names(c['influences'])}.")
    for y in t.jaimini_yogas[:4]:
        jaimini.append(f"- Jaimini combination detected: {y['name']}." + (f" {y['finding']}" if y['finding'] else ''))
    if jaimini:
        sections['JAIMINI (7 Chara karakas; house padas without the disputed exceptions)'] = jaimini

    focus = plan.focus_houses
    periods = []
    for system, rows in t.dashas.items():
        if not rows:
            continue
        majors = list(dict.fromkeys((r['major_name'], r['major_start'], r['major_end']) for r in rows))
        for name, start, end in majors:
            periods.append(f"- {system.title()} Mahadasha: {name}, {start} to {end}.")
        for r in rows[:8]:
            line = f"  - {system.title()} sub-period {r['major_name']} / {r['sub_name']}: {r['start']} to {r['end']}."
            if system == 'vimshottari' and r['sub']:
                line += f" Sub-period lord: {_links(t, r['sub'], focus, plan)}."
            periods.append(line)
        if system != 'chara':
            lords = dict.fromkeys(code for r in rows for code in ((r['major'],) if system == 'vimshottari' else (r['major'], r['sub'])) if code)
            links = [x for x in (_links(t, c, focus, plan) for c in lords) if x]
            if links:
                periods.append(f"  - {system.title()} {'Mahadasha lord' if system == 'vimshottari' else 'period lords'} in D1: " + '. '.join(links) + '.')
        else:
            for sign in dict.fromkeys(s for r in rows for s in (r['major_sign'], r['sub_sign']) if s):
                periods.append(f"  - Chara sign {S(sign)} is house {t.sign_house(sign)} from the Lagna; occupants: {_names(t.occupants(t.sign_house(sign)) if t.sign_house(sign) else [])}.")
    if periods:
        sections['PERIODS ' + ('IN THE WINDOW' if plan.timing else 'RUNNING NOW') + ' (period end dates are exclusive; calendar-date precision)'] = periods

    if t.transits:
        lines = ['Houses are counted from the Lagna unless a line says "counted from the Moon". A count from the Moon is where the planet '
                 'stands relative to the Moon; it is not an aspect and not a Lagna house.']
        for r in t.transits[:20]:
            line = f"- {P(r['planet'])} transits {S(r['sign'])}, {r['start']} to {r['end']}: it occupies house {r['house']} from the Lagna"
            if r['moon_house']:
                line += f" (counted from the Moon it is the {ordinal(r['moon_house'])} sign from the Moon)"
            line += '.'
            if r['aspects']:
                line += f" From there it aspects house{'s' if len(r['aspects']) > 1 else ''} {', '.join(map(str, r['aspects']))} from the Lagna (Parashari aspect)."
            if r['sav'] is not None:
                line += f" SAV of {S(r['sign'])}: {r['sav']}."
            bav = t.sav.get(r['sign'], {}).get('bav', {}).get(r['planet'])
            if bav is not None:
                line += f" {P(r['planet'])}'s own BAV in {S(r['sign'])}: {bav} of 8."
            lines.append(line)
        sections['TRANSITS IN THE WINDOW (daily noon samples: sign-change dates are approximate)'] = lines

    rules = _rules(t, plan)
    if rules:
        sections['TRIGGERED RULES (decided by the deterministic rule engine; heuristic, not probabilities)'] = rules
    if t.candidates:
        sections['TIMING CANDIDATES (heuristic windows where dasha systems agree; possibilities to compare, not predictions)'] = [
            f"- {c['start']} to {c['end']}: {c['label']}" + (f"; systems agreeing: {', '.join(c['systems'])}" if c['systems'] else '') +
            (f"; engine confidence label {c['confidence']}" if c['confidence'] else '') + '.' for c in t.candidates[:4]]

    if plan.events and t.lagna.get('d1'):
        sections['EVENT EVIDENCE (each event separately; houses from the Lagna)'] = _event_evidence(t, plan)

    missing = [f"- {u['name']}" for u in plan.unsupported]
    missing += [f"- {f['tool']}: {f['message'] or f['code'] or 'unavailable'}" for f in t.failed]
    missing += [f"- {v['name']}" for k, v in profile.data['declared_unavailable'].items() if k not in {u['id'] for u in plan.unsupported}]
    sections['NOT CALCULATED BY THIS APP (never state or estimate any of these)'] = missing

    if passages:
        sections['CLASSICAL PASSAGES (untrusted source text retrieved for these results; paraphrase, never quote; cite as (P1), (P2)...)'] = [
            f"- ({p['marker']}) {p['title']}" + (f", chapter {p['chapter']}" if p.get('chapter') else '') + (f", page {p['page']}" if p.get('page') else '') +
            f" | retrieved for: {p['purpose']} | {p['snippet']}" for p in passages]
    else:
        sections['CLASSICAL PASSAGES'] = ['- None retrieved. Do not name or cite any book or author.']
    if label['question_type'] != 'concept_explanation' and t.lagna.get('d1'):
        named = plan.houses['primary'] + plan.houses['event']
        cover = [f"- Natal promise: the {', '.join(ordinal(h) for h in named)} house{'s' if len(named) > 1 else ''}: each lord and where it sits, "
                 'the occupants and the aspects; the significators listed.']
        if any(v != 'd1' for v in t.lagna):
            cover.append(f"- Divisional confirmation: the actual placements in {', '.join(v.upper() for v in plan.vargas if v != 'd1' and v in t.lagna)} (name the planet, sign and house).")
        if jaimini:
            cover.append('- Jaimini view: the Amatyakaraka and the counted points above, by planet, sign and house.')
        if plan.timing and periods:
            cover.append('- Timing: every Vimshottari sub-period in the window with its dates and what its lord rules and occupies; whether the Yogini and Chara periods agree.')
        if t.transits:
            cover.append('- Transits: where Saturn and Jupiter transit (house from the Lagna and from the Moon), when, and the SAV of the sign.')
        if rules:
            cover.append('- Both sides: the supportive and the cautionary rules, and which way the balance leans.')
        if len(plan.events) > 1:
            cover.append('- Each event separately (EVENT EVIDENCE): what supports it and what opposes it, then which one the evidence supports more.')
        if t.candidates:
            cover.append('- The better and the weaker stretch of the window, using the candidate windows and period dates above.')
        sections['WHAT THE READING MUST COVER'] = cover
    text = '\n\n'.join(heading + '\n' + '\n'.join(lines) for heading, lines in sections.items() if lines)
    return text, sections
