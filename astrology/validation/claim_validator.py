"""Closed claim-slot validation; deliberately no claim that regex proves arbitrary prose."""
from astrology.synthesis.fact_catalog import verify_atom, canonical


def result(issues=(), *, stage='draft'):
    return {'passed': not issues, 'score': 100 if not issues else 0, 'issues': list(issues),
            'missing_sections': [], 'generic_phrases_detected': [],
            'unsupported_claims': [x for x in issues if 'claim' in x or 'reference' in x],
            'repair_instruction': '' if not issues else 'Use only verified catalog claims and allowed narrative IDs; otherwise use the server fallback.',
            'stage': stage}


def validate_draft(draft, catalog, narratives, evidence):
    issues = []
    if type(draft) is not dict or set(draft) != {'paragraphs'} or type(draft['paragraphs']) is not list or not 1 <= len(draft['paragraphs']) <= 6:
        return result(['invalid_draft_structure'])
    total, used = 0, set()
    for paragraph in draft['paragraphs']:
        if type(paragraph) is not dict or set(paragraph) != {'segments'} or type(paragraph['segments']) is not list or not 1 <= len(paragraph['segments']) <= 12:
            issues.append('invalid_paragraph_structure')
            continue
        for segment in paragraph['segments']:
            total += 1
            if type(segment) is not dict or set(segment) != {'kind', 'ref', 'value'} or type(segment['ref']) is not str or type(segment['kind']) is not str:
                issues.append('unsupported_free_text_claim')
                continue
            kind, ref, value = segment['kind'], segment['ref'], segment['value']
            if (kind, ref) in used:
                issues.append('repeated_claim')
            used.add((kind, ref))
            if kind == 'fact':
                atom = catalog.get(ref)
                if atom is None or type(value) is not str or value != atom['value'] or not verify_atom(atom, evidence):
                    issues.append('unsupported_or_mismatched_claim:' + ref[:40])
            elif kind == 'narrative':
                if ref not in narratives or value is not None:
                    issues.append('unsupported_narrative_reference')
            else:
                issues.append('unsupported_claim_kind')
    if total > 24:
        issues.append('draft_size_limit')
    return result(tuple(dict.fromkeys(issues)))


def validate_final(answer, expected, catalog, selected_ids, evidence):
    issues = []
    if type(answer) is not str or answer != expected:
        issues.append('post_processing_changed_verified_answer')
    if type(answer) is str and len(answer.encode('utf-8')) > 24576:
        issues.append('final_answer_size_limit')
    if any(fid not in catalog or not verify_atom(catalog[fid], evidence) for fid in selected_ids):
        issues.append('final_claim_source_changed')
    return result(issues, stage='final_post_processing')


def final_schema():
    segment = {'type': 'object', 'additionalProperties': False,
        'properties': {'kind': {'type': 'string', 'enum': ['fact', 'narrative']},
                       'ref': {'type': 'string'}, 'value': {'type': ['string', 'null']}},
        'required': ['kind', 'ref', 'value']}
    draft = {'type': 'object', 'additionalProperties': False,
        'properties': {'paragraphs': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
            'properties': {'segments': {'type': 'array', 'items': segment}}, 'required': ['segments']}}}, 'required': ['paragraphs']}
    return {'type': 'json_schema', 'name': 'grounded_consultation', 'strict': True,
        'schema': {'type': 'object', 'additionalProperties': False,
            'properties': {'evidence_ids': {'type': 'array', 'items': {'type': 'string'}},
                           'draft': {'anyOf': [draft, {'type': 'null'}]}}, 'required': ['evidence_ids', 'draft']}}
