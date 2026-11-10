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
    while len(json.dumps(value, ensure_ascii=False).encode()) > 16384:
        value['truncated'] = True
        if value['sources']: value['sources'].pop()
        elif value['tools']: value['tools'].pop()
        elif value['claim_ids']: value['claim_ids'].pop()
        else: break
    return value
