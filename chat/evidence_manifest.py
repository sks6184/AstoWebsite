"""Bounded owner-visible audit metadata; never the model's private deliberation."""
import json


def manifest(result, provider_models=()):
    checked = result.get('validation', result.get('validation_result', {}))
    value = {'schema_version': 1, 'pipeline': 'agent' if 'evidence' in result else 'legacy',
        'status': result.get('status', 'unknown'), 'validated': checked.get('passed') is True,
        'validation_kind': 'tool_claim_validation' if 'claims' in result else result.get('validation_kind', 'not_retained'),
        'model': str(result.get('model', 'unknown'))[:100],
        'provider_models': list(dict.fromkeys(str(m)[:100] for m in provider_models))[:8],
        'exact_replay_available': False,
        'tools': [], 'sources': [], 'claim_ids': []}
    for eid, entry in list(result.get('evidence', {}).items())[:24]:
        response = entry['result']
        method = response.get('method', {})
        provenance = response.get('provenance', {})
        value['tools'].append({'evidence_id': eid, 'tool': entry['tool'], 'status': response['status'],
            'method': {k: str(method[k])[:256] for k in ('version', 'precision', 'interval_convention', 'reference_frame', 'engine') if k in method},
            'fingerprints': {k: str(provenance[k])[:64] for k in ('chart_fingerprint', 'engine_fingerprint', 'request_fingerprint', 'adapter_fingerprint') if k in provenance}})
        if entry['tool'] == 'search_astrology_knowledge':
            for passage in (response.get('data') or {}).get('passages', [])[:5]:
                value['sources'].append({'evidence_id': passage['evidence_id'], 'citation': passage['citation']})
    value['claim_ids'] = [c['id'] for c in result.get('claims', [])[:128]]
    if result.get('pipeline') in ('general_agent', 'planned_consultation'):
        # M3 diagnostics: server-side fields only (no question, answer, query or chart text).
        keep = ('tool', 'status', 'error_code', 'judgement', 'round', 'counted_input_tokens',
                'provider_input_tokens', 'provider_output_tokens', 'requests', 'final', 'question_type', 'domains', 'events',
                'stage', 'supplementary', 'verified_statements', 'soft_notes', 'repair_round', 'after_removal', 'candidates',
                'count', 'calls', 'findings', 'window', 'houses', 'planets', 'vargas', 'dasha_systems', 'rule_categories',
                'unsupported', 'guided_books', 'latency_ms')
        value.update(pipeline=result['pipeline'], stop_reason=str(result.get('stop_reason', ''))[:48],
                     label=result.get('label'), non_answer_states=list(result.get('non_answer_states', []))[:3],
                     published_by=result.get('published_by'), agent_events=[])
        for event in result.get('trace', [])[:60]:
            item = {'event': str(event.get('event'))[:32], **{k: event[k] for k in keep if k in event}}
            if event.get('event') in ('stop', 'fallback', 'invalid_label', 'rejected_request', 'search_ceiling'):
                item['reason'] = str(event.get('reason', ''))[:160]
            if event.get('event') == 'rerank':
                item['searches'] = [{'purpose': str(q.get('purpose'))[:60], 'stance': str(q.get('stance'))[:16]} for q in event.get('queries', [])[:6]]
                item['kept'] = len(event.get('kept', []))
            if event.get('event') == 'plan':
                item['calls'] = [str(c.get('tool'))[:40] for c in event.get('calls', [])[:24]]
            if event.get('event') == 'validation':
                item['issues'] = [str(i)[:120] for i in event.get('issues', [])[:8]]
                item['missing'] = [str(m)[:60] for m in event.get('missing', [])[:8]]
            value['agent_events'].append(item)
    while len(json.dumps(value, ensure_ascii=False).encode()) > 16384:
        value['truncated'] = True
        if value.get('agent_events'): value['agent_events'].pop()
        elif value['sources']: value['sources'].pop()
        elif value['tools']: value['tools'].pop()
        elif value['claim_ids']: value['claim_ids'].pop()
        else: break
    return value
