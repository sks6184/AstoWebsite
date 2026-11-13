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


def _links(t, code, focus):
    """How a period lord connects to the houses in focus (ownership, occupation, aspect): lookups only."""
    row = t.place.get('d1', {}).get(code)
    if not row:
        return ''
    parts = []
    ruled = t.ruled(code)
    if ruled:
        parts.append('rules ' + ', '.join(map(str, ruled)))
    parts.append(f"sits in house {row['house']}")
    aspects = [h for h in t.aspects.get(code, {}).get('houses', []) if h in focus]
    if aspects:
        parts.append('aspects ' + ', '.join(map(str, aspects)))
    return f"{P(code)} {'; '.join(parts)}"


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
            periods.append(f"  - {system.title()} sub-period {r['major_name']} / {r['sub_name']}: {r['start']} to {r['end']}.")
        if system != 'chara':
            links = [x for x in (_links(t, c, focus) for c in dict.fromkeys(code for r in rows for code in (r['major'], r['sub']) if code)) if x]
            if links:
                periods.append(f"  - {system.title()} period lords in D1: " + '. '.join(links) + '.')
        else:
            for sign in dict.fromkeys(s for r in rows for s in (r['major_sign'], r['sub_sign']) if s):
                periods.append(f"  - Chara sign {S(sign)} is house {t.sign_house(sign)} from the Lagna; occupants: {_names(t.occupants(t.sign_house(sign)) if t.sign_house(sign) else [])}.")
    if periods:
        sections['PERIODS ' + ('IN THE WINDOW' if plan.timing else 'RUNNING NOW') + ' (period end dates are exclusive; calendar-date precision)'] = periods

    if t.transits:
        sections['TRANSITS IN THE WINDOW (daily noon samples: sign-change dates are approximate)'] = [
            f"- {P(r['planet'])} transits {S(r['sign'])}: house {r['house']} from the Lagna" +
            (f", house {r['moon_house']} from the Moon" if r['moon_house'] else '') + f", {r['start']} to {r['end']}" +
            (f"; SAV of that sign {r['sav']}" if r['sav'] is not None else '') + '.' for r in t.transits[:20]]

    rules = _rules(t, plan)
    if rules:
        sections['TRIGGERED RULES (decided by the deterministic rule engine; heuristic, not probabilities)'] = rules
    if t.candidates:
        sections['TIMING CANDIDATES (heuristic windows where dasha systems agree; possibilities to compare, not predictions)'] = [
            f"- {c['start']} to {c['end']}: {c['label']}" + (f"; systems agreeing: {', '.join(c['systems'])}" if c['systems'] else '') +
            (f"; engine confidence label {c['confidence']}" if c['confidence'] else '') + '.' for c in t.candidates[:4]]

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
    text = '\n\n'.join(heading + '\n' + '\n'.join(lines) for heading, lines in sections.items() if lines)
    return text, sections
