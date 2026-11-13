"""Lookup tables over the tool results of one consultation.

Pure re-indexing of values the deterministic tools already returned: nothing is calculated here except
whole-sign counting from the stored Lagna (house <-> sign), which is the tools' own stated convention.
Every row keeps a ``ref`` (evidence ID and JSON pointer) so a published sentence can be traced to its source.
"""
from datetime import date

from astrology.constants import PLANET_NAMES, SIGNS

OK = ('ok', 'partial')


def sign_name(number):
    return SIGNS[number - 1] if type(number) is int and 1 <= number <= 12 else 'an unavailable sign'


def planet_name(code):
    return PLANET_NAMES.get(code, str(code))


def _day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class Tables:
    def __init__(self, evidence):
        self.lagna, self.place, self.lords = {}, {}, {}
        self.aspects, self.sav, self.karakas, self.padas = {}, {}, {}, {}
        self.karakamsha, self.counted, self.jaimini_yogas, self.yogas = None, [], [], []
        self.dashas, self.transits, self.rules, self.conflicts, self.candidates = {}, [], {}, [], []
        self.transit_planets, self.failed = set(), []
        for eid, entry in evidence.items():
            result, tool = entry['result'], entry['tool']
            if result.get('status') not in OK or not result.get('data'):
                if tool != 'search_astrology_knowledge':
                    error = result.get('error') or {}
                    self.failed.append({'evidence_id': eid, 'tool': tool, 'status': result.get('status'),
                                        'code': error.get('code'), 'message': error.get('message')})
                continue
            handler = getattr(self, '_' + tool, None)
            if handler:
                handler(eid, result['data'], entry['arguments'])

    # ── Loading ──────────────────────────────────────────────────────────
    def _get_chart_facts(self, eid, data, args):
        for varga, chart in data['charts'].items():
            lagna = (chart.get('lagna') or {}).get('sign_number')
            if type(lagna) is int:
                self.lagna[varga] = lagna
            for i, p in enumerate(chart.get('planets') or []):
                if p.get('code') in PLANET_NAMES:
                    self.place.setdefault(varga, {})[p['code']] = {
                        'sign': p.get('sign_number'), 'house': p.get('house'), 'nakshatra': p.get('nakshatra'),
                        'dignity': p.get('dignity'), 'retrograde': bool(p.get('retrograde')),
                        'ref': {'evidence_id': eid, 'path': f'/data/charts/{varga}/planets/{i}'}}
            for key, row in (chart.get('all_lord_placements') or {}).items():
                if row.get('lord') in PLANET_NAMES and type(row.get('house')) is int:
                    self.lords.setdefault(varga, {})[row['house']] = {
                        'lord': row['lord'], 'placed_house': row.get('placed_house'), 'placed_sign': row.get('placed_sign_number'),
                        'dignity': row.get('dignity'),
                        'ref': {'evidence_id': eid, 'path': f'/data/charts/{varga}/all_lord_placements/{key}'}}
        for i, yoga in enumerate(data.get('yogas') or []):
            if type(yoga.get('name')) is str:
                self.yogas.append({'name': yoga['name'], 'strength': yoga.get('strength'),
                                   'evidence': [str(e) for e in yoga.get('evidence') or []][:2],
                                   'ref': {'evidence_id': eid, 'path': f'/data/yogas/{i}'}})

    def _get_natal_aspects(self, eid, data, args):
        for i, row in enumerate(data['planets']):
            self.aspects[row['code']] = {'from': row.get('natal_house'), 'houses': list(row.get('aspected_houses') or []),
                                         'ref': {'evidence_id': eid, 'path': f'/data/planets/{i}'}}

    def _get_ashtakavarga(self, eid, data, args):
        for i, row in enumerate(data['rows']):
            self.sav[row['sign_number']] = {'sav': row.get('sav'), 'bav': dict(row.get('bav') or {}), 'house': row.get('house'),
                                            'ref': {'evidence_id': eid, 'path': f'/data/rows/{i}'}}

    def _get_jaimini_facts(self, eid, data, args):
        for key, k in ((data.get('karakas') or {}).get('karakas') or {}).items():
            if type(k) is dict and k.get('code') in PLANET_NAMES:
                self.karakas[k.get('karaka') or key.title()] = {
                    'code': k['code'], 'sign': k.get('sign_number'), 'house': k.get('house'),
                    'ref': {'evidence_id': eid, 'path': f'/data/karakas/karakas/{key}'}}
        km = data.get('karakamsha') or {}
        if km.get('sign_number'):
            self.karakamsha = {'sign': km['sign_number'], 'atmakaraka': (km.get('atmakaraka') or {}).get('code'),
                               'ref': {'evidence_id': eid, 'path': '/data/karakamsha'}}
        for house, pada in ((data.get('padas') or {}).get('all_padas') or {}).items():
            if type(pada) is dict and pada.get('pada_sign_number'):
                self.padas[int(house)] = {'sign': pada['pada_sign_number'], 'house': pada.get('pada_house_from_lagna'),
                                          'ref': {'evidence_id': eid, 'path': f'/data/padas/all_padas/{house}'}}
        for i, yoga in enumerate(data.get('jaimini_yogas') or []):
            if type(yoga) is dict and type(yoga.get('name')) is str:
                self.jaimini_yogas.append({'name': yoga['name'], 'finding': str(yoga.get('finding') or ''),
                                           'ref': {'evidence_id': eid, 'path': f'/data/jaimini_yogas/{i}'}})

    def _get_counted_sign(self, eid, data, args):
        r = data['result']
        self.counted.append({'reference': r['reference'], 'reference_sign': r.get('reference_sign_number'), 'count': r['count'],
                             'sign': r.get('sign_number'), 'house': r.get('house_from_lagna'),
                             'occupants': [o.get('code') for o in r.get('occupants') or []],
                             'influences': [o.get('code') for o in r.get('influencing_planets') or []],
                             'ref': {'evidence_id': eid, 'path': '/data/result'}})

    def _get_dasha_periods(self, eid, data, args):
        rows = self.dashas.setdefault(data['system'], [])
        for i, p in enumerate(data['periods']):
            major = p.get('mahadasha') or {}
            if not p.get('start') or not p.get('end'):
                continue
            row = {'system': data['system'], 'start': p['start'], 'end': p['end'],
                   'major_start': major.get('start'), 'major_end': major.get('end'),
                   'ref': {'evidence_id': eid, 'path': f'/data/periods/{i}'}}
            for key, obj in (('major', major), ('sub', p)):
                row[key] = obj.get('lord') if obj.get('lord') in PLANET_NAMES else None
                row[key + '_sign'] = obj.get('sign_number') if type(obj.get('sign_number')) is int else None
                row[key + '_yogini'] = obj.get('yogini')
                row[key + '_name'] = (sign_name(row[key + '_sign']) if row[key + '_sign'] else
                                      (f"{obj['yogini']} ({planet_name(row[key])})" if obj.get('yogini') else planet_name(row[key])))
            if not any(r['start'] == row['start'] and r['sub_name'] == row['sub_name'] for r in rows):
                rows.append(row)

    def _get_transits(self, eid, data, args):
        self.transit_planets.update(data.get('planets') or [])
        for i, s in enumerate(data['samples']):
            if s.get('lord') in PLANET_NAMES and s.get('start'):
                self.transits.append({'planet': s['lord'], 'sign': s.get('transit_sign_number'), 'house': s.get('transit_house_from_lagna'),
                                      'moon_house': s.get('transit_house_from_moon'), 'start': s['start'], 'end': s.get('end') or s['start'],
                                      'sav': s.get('sarvashtakavarga_points'),
                                      'aspects': [h for h in s.get('transit_aspected_houses_from_lagna') or [] if type(h) is int],
                                      'ref': {'evidence_id': eid, 'path': f'/data/samples/{i}'}})

    def _evaluate_astrology_rules(self, eid, data, args):
        rows = self.rules.setdefault((data['category'], data['as_of']), [])
        for i, rule in enumerate(data['triggered_rules']):
            text = next((rule[k] for k in ('interpretation', 'finding', 'description', 'reason') if type(rule.get(k)) is str and rule[k].strip()), None)
            if text:
                rows.append({'id': rule.get('rule_id') or rule.get('id'), 'system': rule.get('system') or '', 'text': text.strip(),
                             'polarity': rule.get('polarity') or 'mixed', 'weight': rule.get('weight') if type(rule.get('weight')) is int else 0,
                             'ref': {'evidence_id': eid, 'path': f'/data/triggered_rules/{i}'}})
        conflicts = data.get('conflicts') or {}
        for issue in conflicts.get('issues') or []:
            if type(issue) is dict and issue.get('issue'):
                self.conflicts.append({'text': issue['issue'], 'as_of': data['as_of'],
                                       'ref': {'evidence_id': eid, 'path': '/data/conflicts'}})

    def _get_timing_candidates(self, eid, data, args):
        for i, c in enumerate(data['candidates']):
            if c.get('start') and c.get('end'):
                self.candidates.append({'start': c['start'], 'end': c['end'], 'label': c.get('vimshottari_display') or c.get('label') or '',
                                        'confidence': c.get('confidence'), 'systems': list(c.get('confirmed_systems') or []),
                                        'ref': {'evidence_id': eid, 'path': f'/data/candidates/{i}'}})

    # ── Lookups ──────────────────────────────────────────────────────────
    def house_sign(self, house, varga='d1'):
        lagna = self.lagna.get(varga)
        return (lagna + house - 2) % 12 + 1 if lagna else None

    def sign_house(self, sign, varga='d1'):
        lagna = self.lagna.get(varga)
        return (sign - lagna) % 12 + 1 if lagna and sign else None

    def occupants(self, house, varga='d1'):
        return [code for code, row in self.place.get(varga, {}).items() if row['house'] == house]

    def ruled(self, code, varga='d1'):
        return sorted(h for h, row in self.lords.get(varga, {}).items() if row['lord'] == code)

    def aspecting(self, house):
        return [code for code, row in self.aspects.items() if house in row['houses']]

    def period_lords(self):
        """Planet codes that rule a Mahadasha or sub-period in the fetched periods."""
        return list(dict.fromkeys(code for rows in self.dashas.values() for r in rows for code in (r['major'], r['sub']) if code))

    def boundaries(self, scope=None):
        """Calculated start and end dates: of the periods, of the transit segments, or of both (and the candidates)."""
        days = set()
        if scope in (None, 'periods'):
            for rows in self.dashas.values():
                for r in rows:
                    days.update(d for d in map(_day, (r['start'], r['end'], r['major_start'], r['major_end'])) if d)
        for r in (self.transits if scope in (None, 'transits') else []) + self.candidates:
            days.update(d for d in map(_day, (r['start'], r['end'])) if d)
        return days
