"""Conversational controlled composition, grounded in exact tool-backed fact slots."""
import json
import re
from .fact_catalog import build_catalog
from astrology.validation.claim_validator import validate_draft, validate_final, result as validation_result

MUHURTA = 'Exact muhurta selection requires tithi, nakshatra, yoga, karana, weekday, lagna, Moon strength, and planetary hour calculation. Based on current available evidence, this is only a preliminary timing recommendation.'


def narratives(plan, question, context=None, evidence=None):
    q = question.lower()
    if any(x in q for x in ('promot', 'professional growth')):
        direct = 'For promotion, the useful question is whether the period supports increased responsibility; a career signal alone cannot establish an offer.'
        guide = 'Ask your manager what evidence of readiness would support a promotion, and document your results before making a decision.'
    elif 'job change' in q or 'leave my job' in q:
        direct = 'A job change remains a conditional possibility; I would compare the timing evidence with an actual offer before deciding to leave.'
        guide = 'Compare responsibilities, compensation and a signed offer before resigning.'
    elif plan.topic == 'business':
        direct = 'For the business question, treat these indications as areas to investigate rather than a verdict on commercial success.'
        guide = 'Use customer interviews and a small private test to check demand before making a large commitment.'
    else:
        direct = 'For your career question, the available evidence supports a cautious assessment rather than a definite forecast.'
        guide = 'Use the evidence to frame a concrete career decision; practical constraints and actual opportunities still matter.'
    allowed = {'direct': direct, 'guidance': guide,
        'method': 'The comparison uses the available natal D1, professional D10 and relevant period evidence.',
        'followup': 'For that follow-up, here is the focused evidence without repeating the full original reading.',
        'uncertainty': 'Preliminary traditional interpretation; confidence is limited. Astrological prediction is not scientifically established.',
        'overlap': 'Rules and timing scores reuse chart and Dasha inputs. They are overlapping signals, not independent confirmations; scores are not probabilities.',
        'citation_role': 'Classical support: these are separately attributed traditional viewpoints, not calculated chart facts or independent confirmation. Agreement between sources is not assumed.',
        'missing_rag': 'No classical support was retrieved for this consultation; none is inferred.',
        'missing_remedy': 'No remedy is supported by the current verified tool evidence, so no mantra or remedy is invented.',
        'muhurta': MUHURTA,
        'limitations': 'Unrequested or unavailable systems cannot be treated as confirmed support.'}
    if plan.kind not in ('assessment', 'timing'):
        return {'followup': allowed['followup']} if plan.kind == 'chart_focus' else {}
    charts = {key for e in (evidence or {}).values() if e['tool'] == 'get_chart_facts' for key in (e['result'].get('data') or {}).get('charts', {})}
    if not {'d1', 'd10'} <= charts:
        allowed['method'] = 'Missing natal or professional-chart evidence prevents a complete comparison.'
    if not any(w in q for w in ('launch', 'auspicious', 'when should i start', 'best time', 'should i start')):
        allowed.pop('muhurta')
    if not any(w in q for w in ('remedy', 'mantra')):
        allowed.pop('missing_remedy')
    return allowed


def select_facts(plan, catalog):
    atoms = list(catalog.values())
    def values(a): return json.loads(a['value'])
    if plan.kind == 'house_lord':
        return [a['id'] for a in atoms if a['kind'] == 'lord' and values(a).get('house') == 10 and '/d1/' in str(a['bindings'])][:1]
    if plan.kind == 'planet_position':
        return [a['id'] for a in atoms if a['kind'] == 'position' and values(a).get('code') == plan.planet and f'/{plan.varga}/' in str(a['bindings'])][:1]
    if plan.kind == 'ashtakavarga_lookup':
        return [a['id'] for a in atoms if a['kind'] == 'ashtakavarga'][:1]
    if plan.kind in ('current_dasha', 'dasha_lookup'):
        return [a['id'] for a in atoms if a['kind'] == 'dasha'][:6]
    if plan.kind == 'transit':
        from astrology.agent.policy import SIGNS
        return [a['id'] for a in atoms if a['kind'] == 'transit' and
                (not plan.transit_sign or values(a).get('transit_sign_number') == SIGNS.index(plan.transit_sign) + 1)][:4]
    if plan.kind == 'chart_focus':
        selected = [a for a in atoms if a['kind'] == 'lord' and values(a).get('house') == 10]
        selected += [a for a in atoms if a['kind'] == 'position' and values(a).get('code') in ('Me', 'Sa')]
        return [a['id'] for a in selected[:3]]
    selected = []
    for chart in ('d1', 'd10'):
        match = next((a for a in atoms if a['kind'] == 'lord' and values(a).get('house') == 10 and f'/{chart}/' in str(a['bindings'])), None)
        if match: selected.append(match['id'])
    if plan.topic == 'business':
        selected.extend(a['id'] for a in atoms if a['kind'] == 'lord' and values(a).get('house') in (2, 7, 11) and '/d1/' in str(a['bindings']))
        selected.extend(a['id'] for a in atoms if a['kind'] == 'position' and values(a).get('code') in ('Me', 'Ra') and '/d1/' in str(a['bindings']))
    for window in plan.windows:
        for kind in ('dasha', 'candidate') if plan.kind == 'timing' else ('dasha',):
            match = next((a for a in atoms if a['kind'] == kind and a['scope'] == list(window)), None)
            if match: selected.append(match['id'])
    if plan.kind == 'timing':
        match = next((a for a in atoms if a['kind'] == 'transit'), None)
        if match: selected.append(match['id'])
    selected.extend([a['id'] for a in atoms if a['kind'] == 'rule'][:2])
    return list(dict.fromkeys(selected))[:12]


def publish_answer(plan, question, evidence, *, draft=None, context=None, stop_reason='complete', trace=(), postprocess=None):
    if plan is None:
        answer = next((x['reason'] for x in trace if x['event'] == 'clarification'), 'Chart is unavailable.')
        return {'answer': answer, 'validation': validation_result(stage='final_post_processing'), 'draft_validation': None, 'claims': []}
    catalog = build_catalog(evidence)
    prose = narratives(plan, question, context, evidence)
    checked = validate_draft(draft, catalog, prose, evidence) if draft is not None else None
    blocks, chosen = [], []
    if checked and checked['passed']:
        for paragraph in draft['paragraphs']:
            text = []
            for segment in paragraph['segments']:
                if segment['kind'] == 'fact':
                    chosen.append(segment['ref'])
                    text.append(catalog[segment['ref']]['text'])
                else:
                    text.append(prose[segment['ref']])
            blocks.append(' '.join(text))
    else:
        chosen = select_facts(plan, catalog)
        if plan.kind in ('assessment', 'timing'):
            blocks.append(prose['direct'])
            if context is None:
                blocks.append(prose['method'])
        elif plan.kind == 'chart_focus':
            blocks.append(prose['followup'])
        elif plan.kind == 'transit' and plan.transit_sign:
            blocks.append('Focus: ' + plan.transit_sign.title() + ' within the requested scope; no exact ingress time is inferred.')
        distinct = list(dict.fromkeys(catalog[fid]['text'] for fid in chosen))
        blocks.extend(' '.join(distinct[i:i + 2]) for i in range(0, len(distinct), 2))
    # Minimum coverage/counter-evidence cannot be hidden by a model-selected subset.
    required = select_facts(plan, catalog)
    if checked and checked['passed']:
        missing = [fid for fid in required if fid not in chosen]
        blocks.extend(catalog[fid]['text'] for fid in missing)
        chosen.extend(missing)
    for atom in catalog.values():
        if atom['kind'] in ('conflict', 'citation') and atom['id'] not in chosen:
            chosen.append(atom['id'])
            if atom['kind'] == 'citation' and prose['citation_role'] not in blocks:
                blocks.append(prose['citation_role'])
            blocks.append(atom['text'])
    serious = plan.kind in ('assessment', 'timing')
    if serious:
        if any(e['tool'] == 'evaluate_astrology_rules' for e in evidence.values()): blocks.append(prose['overlap'])
        if not any(a['kind'] == 'citation' for a in catalog.values()): blocks.append(prose['missing_rag'])
        blocks.extend([prose['uncertainty'], prose['guidance']])
    if any(w in question.lower() for w in ('launch', 'auspicious', 'when should i start', 'best time', 'should i start')):
        blocks.append(MUHURTA)
    if any(w in question.lower() for w in ('remedy', 'mantra')):
        blocks.append('No remedy is supported by the current verified tool evidence, so no mantra or remedy is invented.')
    if not chosen:
        blocks.append('No supported calculated facts are available for this request.')
    if re.search(r'\blate\s+\d{4}\b', question.lower()):
        blocks.append('The requested late-year comparison uses October through December; specify dates to narrow it.')
    # User corrections and source warnings remain explicitly non-calculation context.
    if context:
        corrections = context['summary'].get('corrections', [])[-1:]
        current = context.get('current_user') or {}
        if current.get('kind') == 'correction': corrections = [{'text': current.get('content', '')}]
        if corrections: blocks.insert(0, 'User-provided correction (not a verified chart fact): ' + corrections[-1]['text'])
    for entry in evidence.values():
        response = entry['result']
        if response.get('error'):
            blocks.append('Calculation unsupported or unavailable: ' + response['error']['message'])
        for warning in response.get('warnings', []):
            if 'Legacy lookup helpers disagree' not in warning:
                blocks.append(warning)
    if stop_reason != 'complete': blocks.append('Investigation stopped: ' + stop_reason + '. Results above are partial.')
    expected = '\n\n'.join(dict.fromkeys(b for b in blocks if b))
    final = postprocess(expected) if postprocess else expected
    validated = validate_final(final, expected, catalog, chosen, evidence)
    return {'answer': final if validated['passed'] else '', 'validation': validated,
            'draft_validation': checked, 'claims': [catalog[fid] for fid in dict.fromkeys(chosen)]}
