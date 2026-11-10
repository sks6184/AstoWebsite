"""Finite, source-bound answer atoms. No astrology calculations or rule decisions."""
import hashlib
import json
from charts.vedic_utils import PLANET_NAMES, SIGN_NAMES

MAX_FACTS = 128


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def pointer(value, path):
    for key in path.strip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if type(value) is list else value[key]
    return value


def build_catalog(evidence):
    facts = {}
    def add(kind, eid, bindings, text, scope=None):
        # Reserve slots so long natal/period lists cannot suppress conflicts/citations.
        if len(facts) >= (MAX_FACTS if kind in ('conflict', 'citation') else MAX_FACTS - 16):
            return
        value = {label: pointer(evidence[eid]['result'], path) for label, path in bindings.items()}
        fid = 'F' + hashlib.sha256(canonical([eid, kind, bindings, value]).encode()).hexdigest()[:16]
        facts[fid] = {'id': fid, 'kind': kind, 'evidence_id': eid, 'bindings': bindings,
                      'value': canonical(value), 'text': text, 'scope': scope,
                      'method': evidence[eid]['result'].get('method', {})}
    # First reserve coverage for every scoped period/transit/candidate before large natal/rule lists.
    ordered = sorted(evidence.items(), key=lambda p: {'get_dasha_periods': 0, 'get_transits': 1,
        'get_timing_candidates': 2, 'get_chart_facts': 3, 'get_ashtakavarga': 4,
        'evaluate_astrology_rules': 5, 'search_astrology_knowledge': 6}.get(p[1]['tool'], 9))
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
            for i, row in enumerate(data['samples'][:16]):
                path = f'/data/samples/{i}'
                keys = ('lord', 'start', 'end', 'transit_sign_number', 'transit_house_from_lagna', 'sarvashtakavarga_points')
                bindings = {k: path + '/' + k for k in keys if k in row}
                text = f"{PLANET_NAMES.get(row.get('lord'), 'The selected planet')} is sampled in {SIGN_NAMES.get(row.get('transit_sign_number'), 'an unavailable sign')}, natal house {row.get('transit_house_from_lagna')}, from {row.get('start', row.get('date'))} to {row.get('end', row.get('date'))}; SAV is {row.get('sarvashtakavarga_points') if row.get('sarvashtakavarga_points') is not None else 'unavailable'}. These are daily noon-UTC samples, not exact ingress times."
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
                    if label not in ('2_lord', '7_lord', '10_lord', '11_lord') or not lord.get('lord'):
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
                    add('position', eid, bindings, text + '.')
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
            for i, rule in enumerate(data['triggered_rules'][:6]):
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
                text = '\n'.join('Source excerpt: ' + line for line in p['snippet'].splitlines())
                text += f" [{p['evidence_id']}] Attribution: {attribution if p['citation_available'] else 'Citation unavailable.'}"
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
