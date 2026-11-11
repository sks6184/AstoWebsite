"""Finite, source-bound answer atoms. No astrology calculations or rule decisions."""
import hashlib
import json
from charts.vedic_utils import PLANET_NAMES, SIGN_NAMES

MAX_FACTS = 128
FULL_MAX_FACTS = 320
PADA_NAMES = {1: 'Arudha Lagna, AL', 7: 'Darapada, A7', 12: 'Upapada Lagna, UL'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def pointer(value, path):
    for key in path.strip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if type(value) is list else value[key]
    return value


def build_catalog(evidence, *, full=False):
    """Fact atoms bound to tool results. ``full`` (M3 general agent, opt-in) publishes all 12 house
    lords, nakshatras and the M3 fact kinds; the default output is unchanged for the P3 slice."""
    facts = {}
    cap = FULL_MAX_FACTS if full else MAX_FACTS
    def add(kind, eid, bindings, text, scope=None):
        # Reserve slots so long natal/period lists cannot suppress conflicts/citations.
        if len(facts) >= (cap if kind in ('conflict', 'citation') else cap - 16):
            return
        value = {label: pointer(evidence[eid]['result'], path) for label, path in bindings.items()}
        fid = 'F' + hashlib.sha256(canonical([eid, kind, bindings, value]).encode()).hexdigest()[:16]
        facts[fid] = {'id': fid, 'kind': kind, 'evidence_id': eid, 'bindings': bindings,
                      'value': canonical(value), 'text': text, 'scope': scope,
                      'method': evidence[eid]['result'].get('method', {})}
    # First reserve coverage for every scoped period/transit/candidate before large natal/rule lists.
    ordered = sorted(evidence.items(), key=lambda p: {'get_dasha_periods': 0, 'get_transits': 1,
        'get_timing_candidates': 2, 'get_chart_facts': 3, 'get_ashtakavarga': 4,
        'evaluate_astrology_rules': 5, 'search_astrology_knowledge': 6, 'get_jaimini_facts': 7,
        'get_counted_sign': 7, 'get_natal_aspects': 8}.get(p[1]['tool'], 9))
    for eid, entry in ordered:
        result, tool, args = entry['result'], entry['tool'], entry['arguments']
        if result.get('status') not in ('ok', 'partial') or not result.get('data'):
            continue
        data = result['data']
        scope = [args['start_date'], args['end_date']] if 'start_date' in args else [args['as_of'], args['as_of']] if 'as_of' in args else None
        if tool == 'get_dasha_periods':
            for i, p in enumerate(data['periods'][:12]):
                path = f'/data/periods/{i}'
                if not all(k in p for k in ('start', 'end')):
                    continue
                bindings = {'start': path + '/start', 'end': path + '/end'}
                major = p.get('mahadasha', {})
                for key, obj, sub in [('major', major, '/mahadasha'), ('sub', p, '')]:
                    field = next((k for k in ('lord', 'sign_name', 'sign', 'name') if k in obj), None)
                    if field:
                        bindings[key] = path + sub + '/' + field
                v = {k: pointer(result, x) for k, x in bindings.items()}
                major_name = PLANET_NAMES.get(v.get('major'), v.get('major', 'unavailable'))
                sub_name = PLANET_NAMES.get(v.get('sub'), v.get('sub', 'unavailable'))
                text = f"{data['system'].title()}: {major_name} Mahadasha / {sub_name} Antardasha runs from {p['start']} to {p['end']} (source end exclusive; calendar-date precision)."
                add('dasha', eid, bindings, text, scope)
        elif tool == 'get_transits':
            for i, row in enumerate(data['samples'][:32 if full else 16]):
                path = f'/data/samples/{i}'
                keys = ('lord', 'start', 'end', 'transit_sign_number', 'transit_house_from_lagna', 'sarvashtakavarga_points')
                if full:
                    keys += ('transit_house_from_moon', 'date')
                bindings = {k: path + '/' + k for k in keys if k in row}
                text = f"{PLANET_NAMES.get(row.get('lord'), 'The selected planet')} is sampled in {SIGN_NAMES.get(row.get('transit_sign_number'), 'an unavailable sign')}, natal house {row.get('transit_house_from_lagna')}, from {row.get('start', row.get('date'))} to {row.get('end', row.get('date'))}; SAV is {row.get('sarvashtakavarga_points') if row.get('sarvashtakavarga_points') is not None else 'unavailable'}. These are daily noon-UTC samples, not exact ingress times."
                if full and row.get('transit_house_from_moon') is not None:
                    text = text.replace(' These are daily', f" Counted from the natal Moon it is house {row['transit_house_from_moon']}. These are daily")
                add('transit', eid, bindings, text, scope)
        elif tool == 'get_timing_candidates':
            for i, c in enumerate(data['candidates'][:4]):
                bindings = {k: f'/data/candidates/{i}/{k}' for k in ('start', 'end', 'score', 'composite_score') if k in c}
                if not all(k in bindings for k in ('start', 'end')):
                    continue
                text = f"A heuristic candidate spans {c['start']} to {c['end']}; this is a possibility to compare, not a probability or a guaranteed event."
                add('candidate', eid, bindings, text, scope)
        elif tool == 'get_chart_facts':
            for chart_key, chart in data['charts'].items():
                for label, lord in chart.get('all_lord_placements', {}).items():
                    if (not full and label not in ('2_lord', '7_lord', '10_lord', '11_lord')) or not lord.get('lord'):
                        continue
                    base = f'/data/charts/{chart_key}/all_lord_placements/{label}'
                    bindings = {k: base + '/' + k for k in ('house', 'lord', 'placed_house', 'placed_sign_number', 'dignity') if k in lord}
                    name = PLANET_NAMES.get(lord['lord'], lord['lord'])
                    text = f"Your {chart_key.upper()} house {lord['house']} ruler is {name}"
                    if lord.get('placed_house') is not None:
                        text += f", placed in {SIGN_NAMES.get(lord.get('placed_sign_number'), 'an unavailable sign')}, house {lord['placed_house']}"
                    text += '.'
                    # Retain the established short factual wording.
                    if chart_key == 'd1' and label == '10_lord':
                        text = f"Your D1 tenth-house ruler is {name}." + (f" It is placed in house {lord['placed_house']}." if lord.get('placed_house') is not None else '')
                    add('lord', eid, bindings, text)
                for i, p in enumerate(chart.get('planets', [])):
                    code = p.get('code')
                    if code not in PLANET_NAMES:
                        continue
                    base = f'/data/charts/{chart_key}/planets/{i}'
                    bindings = {k: base + '/' + k for k in ('code', 'house', 'sign_number') if k in p}
                    longitude = data.get('longitudes', {}).get(chart_key, {}).get(code)
                    if longitude is not None:
                        bindings['longitude'] = f'/data/longitudes/{chart_key}/{code}'
                    text = f"In {chart_key.upper()}, {PLANET_NAMES[code]} is in {SIGN_NAMES.get(p.get('sign_number'), 'an unavailable sign')}, house {p.get('house')}"
                    if longitude is not None:
                        text += f", at {longitude} degrees ecliptic longitude"
                    if full:
                        for key in ('nakshatra', 'retrograde', 'dignity'):
                            if p.get(key) is not None:
                                bindings[key] = base + '/' + key
                        if p.get('nakshatra'):
                            text += f", in {p['nakshatra']} nakshatra"
                        if p.get('retrograde'):
                            text += ', retrograde'
                        if p.get('dignity') not in (None, '', 'ordinary'):
                            text += f", dignity {p['dignity']}"
                    add('position', eid, bindings, text + '.')
            for i, yoga in enumerate((data.get('yogas') or [])[:24] if full else []):
                bindings = {'name': f'/data/yogas/{i}/name', 'strength': f'/data/yogas/{i}/strength'}
                add('yoga', eid, bindings, f"The app's stored yoga detection lists {yoga['name']} (strength: {yoga.get('strength') or 'unstated'}). This is a detection, not an outcome.")
        elif full and tool == 'get_jaimini_facts':
            for name, k in sorted(((data.get('karakas') or {}).get('karakas') or {}).items()):
                if type(k) is not dict or k.get('code') not in PLANET_NAMES:
                    continue
                base = f'/data/karakas/karakas/{name}'
                add('karaka', eid, {f: base + '/' + f for f in ('karaka', 'code', 'sign_number', 'house') if f in k},
                    f"Your Chara {k.get('karaka') or name.title()} (7-karaka scheme) is {PLANET_NAMES[k['code']]}, in {SIGN_NAMES.get(k.get('sign_number'), 'an unavailable sign')}, house {k.get('house')}.")
            km = data.get('karakamsha') or {}
            if km.get('sign_number'):
                ak = PLANET_NAMES.get((km.get('atmakaraka') or {}).get('code'), 'the Atmakaraka')
                add('karakamsha', eid, {'sign_number': '/data/karakamsha/sign_number', 'atmakaraka': '/data/karakamsha/atmakaraka/code'},
                    f"Your Karakamsha (the D9 sign of the Atmakaraka, {ak}) is {SIGN_NAMES.get(km['sign_number'])}.")
            for house, pada in sorted(((data.get('padas') or {}).get('all_padas') or {}).items(), key=lambda x: int(x[0])):
                if type(pada) is not dict or not pada.get('pada_sign_number'):
                    continue
                base = f'/data/padas/all_padas/{house}'
                named = PADA_NAMES.get(int(house))
                add('pada', eid, {f: base + '/' + f for f in ('house', 'pada_sign_number', 'pada_house_from_lagna') if f in pada},
                    f"The pada of house {int(house)}{' (' + named + ')' if named else ''} falls in {SIGN_NAMES.get(pada['pada_sign_number'])}, house {pada.get('pada_house_from_lagna')} from the Lagna.")
            for i, yoga in enumerate((data.get('jaimini_yogas') or [])[:12]):
                if type(yoga) is dict and type(yoga.get('name')) is str:
                    add('jaimini_yoga', eid, {'name': f'/data/jaimini_yogas/{i}/name'},
                        f"The app's Jaimini check lists the combination {yoga['name']}. This is a detection, not an outcome.")
        elif full and tool == 'get_counted_sign':
            r = data['result']
            occupants = ', '.join(PLANET_NAMES.get(o.get('code'), '?') for o in r.get('occupants', [])) or 'none'
            influences = ', '.join(PLANET_NAMES.get(o.get('code'), '?') for o in r.get('influencing_planets', [])) or 'none'
            label = {'arudha_lagna': 'Arudha Lagna (AL)', 'upapada_lagna': 'Upapada Lagna (UL)', 'karakamsha': 'Karakamsha'}.get(r['reference'], r['reference'])
            add('counted_sign', eid, {f: '/data/result/' + f for f in ('reference', 'reference_sign_number', 'count', 'sign_number', 'house_from_lagna')},
                f"Counting inclusively, sign {r['count']} from the {label} in {r.get('reference_sign')} is {r.get('sign')}, house {r.get('house_from_lagna')} from the Lagna. Occupants: {occupants}. Influencing planets (occupation or Jaimini rasi drishti): {influences}.")
        elif full and tool == 'get_natal_aspects':
            for i, row in enumerate(data['planets']):
                houses = ', '.join(str(h) for h in row['aspected_houses'])
                add('aspect', eid, {f: f'/data/planets/{i}/{f}' for f in ('code', 'natal_house', 'aspected_houses')},
                    f"By Parashari aspect, {row['name']} in house {row['natal_house']} aspects house(s) {houses}.")
        elif tool == 'get_ashtakavarga':
            for i, row in enumerate(data['rows']):
                path = f'/data/rows/{i}'
                bindings = {'sign_number': path + '/sign_number', 'house': path + '/house'}
                parts = []
                if data['kind'] != 'bav':
                    bindings['sav'] = path + '/sav'
                    parts.append(f"SAV {row['sav']}" if row['sav'] is not None else 'SAV unavailable')
                for code, points in row['bav'].items():
                    bindings[f'bav_{code}'] = path + '/bav/' + code
                    parts.append(f"{PLANET_NAMES.get(code, code)} BAV {points}" if points is not None else f"{PLANET_NAMES.get(code, code)} BAV unavailable")
                add('ashtakavarga', eid, bindings, f"{row['sign']} (natal house {row['house']}): " + '; '.join(parts) + '.')
        elif tool == 'evaluate_astrology_rules':
            for i, rule in enumerate(data['triggered_rules'][:10 if full else 6]):
                rid = rule.get('rule_id') or rule.get('id')
                if not rid:
                    continue
                field = 'rule_id' if 'rule_id' in rule else 'id'
                bindings = {'rule_id': f'/data/triggered_rules/{i}/{field}', 'as_of': '/data/as_of'}
                description_field = next((k for k in ('finding', 'interpretation', 'description', 'reason') if type(rule.get(k)) is str), None)
                detail = ''
                if description_field:
                    bindings['description'] = f'/data/triggered_rules/{i}/{description_field}'
                    detail = ' ' + rule[description_field][:500]
                add('rule', eid, bindings, f"A triggered traditional rule, evaluated as of {data['as_of']}, reports:{detail or ' a conditional signal requiring context.'}", scope)
            if data.get('conflicts', {}).get('has_contradictions') or data.get('conflicts', {}).get('issues'):
                issues = data['conflicts'].get('issues', [])
                detail = ' '.join(i.get('issue', '') for i in issues[:2] if type(i) is dict)
                add('conflict', eid, {'conflicts': '/data/conflicts'},
                    'The deterministic conflict assessment contains differing signals. ' + detail + ' Conflicting evidence limits the conclusion rather than cancelling the contrary signal.', scope)
        elif tool == 'search_astrology_knowledge':
            for i, p in enumerate(data['passages']):
                cite = p['citation']
                attribution = '; '.join(f'{k}: {v}' for k, v in cite.items() if v is not None)
                missing = ', '.join(k for k, v in cite.items() if v is None)
                # OD-11 (owner, 2026-11-11): cite by title and paraphrase only. The excerpt
                # stays bound for verification but is never published verbatim.
                text = (f"A retrieved traditional source was consulted [{p['evidence_id']}]; its text is not quoted. "
                        f"Attribution: {attribution if p['citation_available'] else 'Citation unavailable.'}")
                if missing:
                    text += f' Unavailable citation metadata: {missing}.'
                add('citation', eid, {'passage_id': f'/data/passages/{i}/evidence_id',
                    'snippet': f'/data/passages/{i}/snippet', 'citation': f'/data/passages/{i}/citation'}, text)
    return facts


def verify_atom(atom, evidence):
    try:
        values = {k: pointer(evidence[atom['evidence_id']]['result'], path) for k, path in atom['bindings'].items()}
        return canonical(values) == atom['value']
    except (KeyError, ValueError, TypeError, IndexError):
        return False
