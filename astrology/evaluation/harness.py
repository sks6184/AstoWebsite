"""Paired, blinded evaluation with explicit unknowns; no model judges as humans."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

LOCK_SHA256 = '03049e821e46f75027ef84b855d0d619c7a899f98927f577e7e38e500ffd9b9e'
FIXTURE = Path(__file__).parent / 'fixtures' / 'p6_cases_v1.json'
SYSTEMS = {'legacy', 'agent'}


def load_cases():
    raw = FIXTURE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LOCK_SHA256 or FIXTURE.with_suffix('.sha256').read_text().strip() != LOCK_SHA256:
        raise ValueError('Locked evaluation fixture changed; create a reviewed new version instead.')
    payload = json.loads(raw)
    if len({c['id'] for c in payload['cases']}) != len(payload['cases']):
        raise ValueError('Duplicate locked case ID')
    return payload['cases']


def collect_responses(runners):
    """Runners are trusted injected callables. This module never imports/executes a named runner."""
    if set(runners) != SYSTEMS or not all(callable(r) for r in runners.values()):
        raise ValueError('Supply explicit legacy and agent runners.')
    records = []
    for case in load_cases():
        for system in sorted(SYSTEMS):
            start = time.perf_counter()
            output = runners[system](deepcopy(case))
            records.append({'case_id': case['id'], 'system': system, 'answer': output['answer'],
                'metrics': {'latency_ms': (time.perf_counter() - start) * 1000,
                            'input_tokens': output.get('prompt_tokens'), 'output_tokens': output.get('completion_tokens'),
                            'cost_amount': output.get('cost_amount'), 'currency': output.get('currency'),
                            'measurement': output.get('measurement', 'unverified_runner')},
                'objective': output.get('objective', {'critical_calculation_errors': None, 'privacy_errors': None,
                                                     'validation_passed': None})})
    return records


def validate_records(records):
    cases = {c['id'] for c in load_cases()}
    if type(records) is not list or len(records) > 2 * len(cases):
        raise ValueError('Response artifact exceeds locked set.')
    seen = set()
    for record in records:
        if type(record) is not dict or set(record) != {'case_id', 'system', 'answer', 'metrics', 'objective'}:
            raise ValueError('Invalid response record; do not include prompts/private chart data.')
        identity = (record['case_id'], record['system'])
        if type(record['case_id']) is not str or type(record['system']) is not str or record['case_id'] not in cases or record['system'] not in SYSTEMS or identity in seen:
            raise ValueError('Invalid/duplicate system-case identity')
        seen.add(identity)
        if type(record['answer']) is not str or len(record['answer'].encode('utf-8')) > 32768:
            raise ValueError('Answer size/type invalid')
        metrics = record['metrics']
        if type(metrics) is not dict or set(metrics) != {'latency_ms', 'input_tokens', 'output_tokens', 'cost_amount', 'currency', 'measurement'}:
            raise ValueError('Metrics must remain separate and explicit.')
        for key in ('latency_ms', 'input_tokens', 'output_tokens', 'cost_amount'):
            value = metrics[key]
            if value is not None and (type(value) not in (int, float) or value < 0 or not math.isfinite(value)):
                raise ValueError('Invalid metric; use null for unknown, never fabricated zero.')
        if metrics['currency'] is not None and metrics['currency'] not in ('USD', 'EUR', 'GBP', 'THB', 'INR'):
            raise ValueError('Explicit supported currency required.')
        if type(metrics['measurement']) is not str:
            raise ValueError('Measurement provenance required.')
        objective = record['objective']
        if type(objective) is not dict or set(objective) != {'critical_calculation_errors', 'privacy_errors', 'validation_passed'}:
            raise ValueError('Invalid objective metrics')
        for key in ('critical_calculation_errors', 'privacy_errors'):
            if objective[key] is not None and (type(objective[key]) is not int or objective[key] < 0):
                raise ValueError('Unknown errors are null, not automatic zero.')
        if objective['validation_passed'] is not None and type(objective['validation_passed']) is not bool:
            raise ValueError('Invalid validation metric')
    return records


def blinded_packet(records, *, seed):
    validate_records(records)
    if type(seed) is not str or not seed:
        raise ValueError('Use a private randomization seed; do not send it to graders.')
    lookup = {(r['case_id'], r['system']): r for r in records}
    packet, key = [], {}
    for case in load_cases():
        if any((case['id'], s) not in lookup for s in SYSTEMS):
            continue
        swap = hashlib.sha256((seed + case['id']).encode()).digest()[0] % 2
        a, b = ('legacy', 'agent') if swap else ('agent', 'legacy')
        pair_id = hashlib.sha256((case['id'] + seed).encode()).hexdigest()[:20]
        parent = next((c for c in load_cases() if c['id'] == case['parent_id']), None)
        packet.append({'pair_id': pair_id, 'question': case['question'], 'parent_question': parent['question'] if parent else None,
                       'parent_A': lookup.get((case['parent_id'], a), {}).get('answer'),
                       'parent_B': lookup.get((case['parent_id'], b), {}).get('answer'),
                       'A': lookup[(case['id'], a)]['answer'], 'B': lookup[(case['id'], b)]['answer']})
        key[pair_id] = {'case_id': case['id'], 'A': a, 'B': b}
    return packet, key


def summarize(records, key, human_scores=(), *, preference_target=0.6, threshold_agreed=False,
              latency_ratio_limit=None, cost_ratio_limit=None):
    validate_records(records)
    if type(preference_target) not in (int, float) or not 0 <= preference_target <= 1:
        raise ValueError('Invalid pilot preference target')
    if type(threshold_agreed) is not bool:
        raise ValueError('Agreement must be explicit.')
    for limit in (latency_ratio_limit, cost_ratio_limit):
        if limit is not None and (type(limit) not in (int, float) or not math.isfinite(limit) or limit <= 0):
            raise ValueError('Invalid approved performance limit')
    votes, seen, ratings = Counter(), set(), {'agent': [], 'legacy': []}
    human_errors = Counter()
    covered = set()
    known_cases = {c['id'] for c in load_cases()}
    if any(type(v) is not dict or set(v) != {'case_id', 'A', 'B'} or v['case_id'] not in known_cases or {v['A'], v['B']} != SYSTEMS for v in key.values()):
        raise ValueError('Invalid private unblinding key')
    for score in human_scores:
        if type(score) is not dict or set(score) != {'pair_id', 'assessor', 'source', 'preference', 'quality', 'errors'}:
            raise ValueError('Invalid human score shape')
        pid = score['pair_id']
        if type(pid) is not str or type(score['quality']) is not dict or set(score['quality']) != {'A', 'B'} or type(score['errors']) is not dict or set(score['errors']) != {'A', 'B'}:
            raise ValueError('Invalid scoring dimensions')
        if pid not in key or score['source'] != 'human' or type(score['assessor']) is not str or not score['assessor'] or (pid, score['assessor']) in seen:
            raise ValueError('Only distinct attested human scores for known pairs are accepted.')
        seen.add((pid, score['assessor']))
        covered.add(key[pid]['case_id'])
        if score['preference'] not in ('A', 'B', 'tie'):
            raise ValueError('Preference must be A, B or tie.')
        votes['tie' if score['preference'] == 'tie' else key[pid][score['preference']]] += 1
        for side in ('A', 'B'):
            q = score['quality'].get(side)
            if type(q) is not dict or set(q) != {'accuracy', 'grounding', 'responsiveness', 'clarity', 'concision'} or any(type(v) is not int or not 1 <= v <= 5 for v in q.values()):
                raise ValueError('Rate quality dimensions separately from preference and performance.')
            if type(score['errors'].get(side)) is not int or score['errors'][side] < 0:
                raise ValueError('Record human-observed errors separately.')
            ratings[key[pid][side]].append(q)
            human_errors[key[pid][side]] += score['errors'][side]
    performance, objective = {}, {}
    for system in sorted(SYSTEMS):
        rows = [r for r in records if r['system'] == system]
        performance[system] = {}
        for metric in ('latency_ms', 'input_tokens', 'output_tokens', 'cost_amount'):
            values = [r['metrics'][metric] for r in rows if r['metrics'][metric] is not None]
            performance[system][metric] = {'count': len(values), 'median': statistics.median(values) if values else None,
                                         'total': sum(values) if values else None}
        performance[system]['currencies'] = sorted({r['metrics']['currency'] for r in rows if r['metrics']['currency']})
        performance[system]['measurement_sources'] = sorted({r['metrics']['measurement'] for r in rows})
        objective[system] = {'case_count': len(rows), 'critical_errors': sum(r['objective']['critical_calculation_errors'] or 0 for r in rows),
            'unknown_critical_cases': sum(r['objective']['critical_calculation_errors'] is None for r in rows),
            'privacy_errors': sum(r['objective']['privacy_errors'] or 0 for r in rows),
            'unknown_privacy_cases': sum(r['objective']['privacy_errors'] is None for r in rows),
            'validation_failures': sum(r['objective']['validation_passed'] is False for r in rows),
            'unknown_validation_cases': sum(r['objective']['validation_passed'] is None for r in rows)}
        if len(performance[system]['currencies']) > 1:
            performance[system]['cost_amount']['median'] = None
            performance[system]['cost_amount']['total'] = None
    non_ties = votes['agent'] + votes['legacy']
    preference = votes['agent'] / non_ties if non_ties else None
    reasons = []
    expected = len(load_cases())
    if any(objective[s]['case_count'] != expected for s in SYSTEMS): reasons.append('paired_response_coverage_incomplete')
    new = objective['agent']
    if new['critical_errors'] or new['privacy_errors'] or new['validation_failures']: reasons.append('automatic_safety_gate_failed')
    if new['unknown_critical_cases'] or new['unknown_privacy_cases'] or new['unknown_validation_cases']: reasons.append('automatic_safety_unknown')
    if human_errors['agent']: reasons.append('human_observed_errors_require_review')
    if len(covered) != expected or not non_ties: reasons.append('human_evaluation_incomplete')
    if not threshold_agreed: reasons.append('human_threshold_not_agreed')
    if preference is not None and preference < preference_target: reasons.append('human_preference_below_pilot_target')
    if latency_ratio_limit is None or cost_ratio_limit is None: reasons.append('performance_limits_not_approved')
    if any(performance[s]['measurement_sources'] != ['live_verified'] for s in SYSTEMS): reasons.append('live_performance_unverified')
    if any(len(performance[s]['currencies']) != 1 for s in SYSTEMS) or performance['agent']['currencies'] != performance['legacy']['currencies']:
        reasons.append('cost_currency_comparison_unverified')
    for metric, limit in [('latency_ms', latency_ratio_limit), ('cost_amount', cost_ratio_limit)]:
        old, new_value = performance['legacy'][metric]['median'], performance['agent'][metric]['median']
        complete = all(performance[s][metric]['count'] == expected for s in SYSTEMS)
        if limit is not None:
            if not complete or old is None or old <= 0 or new_value is None: reasons.append(metric + '_comparison_unverified')
            elif new_value / old > limit: reasons.append(metric + '_regression')
    return {'schema_version': '1.0', 'locked_set_sha256': LOCK_SHA256,
            'objective': objective, 'human': {'scored_case_count': len(covered), 'votes': dict(votes),
                'agent_preference_non_tied': preference, 'pilot_target': preference_target,
                'threshold_agreed': threshold_agreed, 'quality_ratings': ratings, 'observed_errors': dict(human_errors)},
            'performance': performance, 'gate': 'PASS' if not reasons else 'FAIL' if any('failed' in r or 'below' in r or 'regression' in r for r in reasons) else 'BLOCKED',
            'reasons': reasons, 'interpretation': 'Preference is a pilot UX measure, not evidence of predictive effectiveness.'}
