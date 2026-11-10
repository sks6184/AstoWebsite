"""Evidence-only text for the existing escaping Markdown template filter."""
import json
from .policy import SIGNS


def render_evidence(plan, evidence, stop_reason, trace):
    if plan is None:
        return next((e['reason'] for e in trace if e['event'] == 'clarification'), 'Chart is unavailable.')
    parts = [plan.reason]
    if plan.kind in ('assessment', 'timing'):
        parts.extend(['## Preliminary evidence report',
            'A substantive forecast is not yet established. Timing scores are heuristic support, not probabilities or mandates.',
            'Classical support is limited to explicitly retrieved excerpts below. Full answer-quality validation is not enabled. Confidence: limited; conflicting signals require review.'])
    labels = {'get_chart_facts': 'Chart basis', 'get_dasha_periods': 'Dasha basis',
              'get_transits': 'Scoped transits', 'get_ashtakavarga': 'BAV/SAV basis',
              'evaluate_astrology_rules': 'Deterministic rules', 'get_timing_candidates': 'Candidate windows',
              'search_astrology_knowledge': 'Classical support and source viewpoints'}
    if plan.kind in ('assessment', 'timing') and not any(e['tool'] == 'search_astrology_knowledge' for e in evidence.values()):
        parts.append('No classical support was retrieved for this consultation; none is inferred.')
    for eid, item in evidence.items():
        result, tool, args = item['result'], item['tool'], item['arguments']
        data = result.get('data') or {}
        parts.extend([f"## {labels[tool]} [{eid}]", item['reason']])
        if 'start_date' in args:
            parts.append(f"Requested: {args['start_date']} through {args['end_date']} (inclusive).")
        if tool == 'get_chart_facts':
            for key, chart in data.get('charts', {}).items():
                if plan.kind == 'house_lord':
                    ruler = chart.get('all_lord_placements', {}).get('10_lord', {})
                    name = ruler.get('lord_name') or ruler.get('lord')
                    parts.append(f"Your D1 tenth-house ruler is {name}." if name else 'The stored D1 tenth-house ruler is unavailable.')
                    continue
                for label in ('2_lord', '7_lord', '10_lord', '11_lord'):
                    lord = chart.get('all_lord_placements', {}).get(label, {})
                    if lord:
                        parts.append(f"- {key.upper()} house {lord.get('house')} lord {lord.get('lord_name') or lord.get('lord')}: {lord.get('placed_sign')}, house {lord.get('placed_house')}; dignity {lord.get('dignity')}.")
        elif tool == 'get_dasha_periods':
            for p in data.get('periods', []):
                major = p.get('mahadasha', {})
                parts.append(f"- {major.get('lord_name') or major.get('lord', 'Unknown')} Mahadasha / {p.get('lord_name') or p.get('lord', 'Unknown')} Antardasha: {p.get('start')} to {p.get('end')} (source end exclusive).")
            if not data.get('periods'):
                parts.append('No supported periods are available for these dates.')
        elif tool == 'get_transits':
            samples = data.get('samples', [])
            if plan.transit_sign:
                samples = [s for s in samples if s.get('transit_sign_number') == SIGNS.index(plan.transit_sign) + 1]
                parts.append(f"Focus: {plan.transit_sign.title()}. {len(samples)} sampled sign segment(s) in this scope; no exact ingress time is inferred.")
            for s in samples:
                parts.append(f"- {s.get('lord_name') or s.get('lord')}: {s.get('start')} to {s.get('end')}; sign {s.get('transit_sign_number')}, natal house {s.get('transit_house_from_lagna')}, SAV {s.get('sarvashtakavarga_points')}.")
        elif tool == 'get_ashtakavarga':
            for row in data.get('rows', []):
                parts.append(f"- {row['sign']}, natal house {row['house']}: SAV {row['sav']}; BAV {json.dumps(row['bav'], ensure_ascii=False)}.")
        elif tool == 'evaluate_astrology_rules':
            if not data.get('triggered_rules'):
                parts.append('No deterministic rules matched the available evidence.')
            for rule in data.get('triggered_rules', []):
                parts.append('- ' + json.dumps(rule, ensure_ascii=False))
            parts.append('Conflicting evidence: ' + json.dumps(data.get('conflicts', {}), ensure_ascii=False))
        elif tool == 'get_timing_candidates':
            if not data.get('candidates'):
                parts.append('No supported timing candidates are available.')
            for candidate in data.get('candidates', []):
                parts.append('- ' + json.dumps({k: v for k, v in candidate.items() if k not in ('transit_segments', 'transit_convergence')}, ensure_ascii=False))
        elif tool == 'search_astrology_knowledge':
            parts.append('These are separately attributed traditional interpretations, not calculated chart facts or independent confirmation. Agreement between sources is not assumed.')
            if not data.get('passages'):
                parts.append('Insufficient retrieved support.')
            for passage in data.get('passages', []):
                citation = passage['citation']
                parts.append('### Retrieved viewpoint [' + passage['evidence_id'] + ']')
                # Prefix every line to avoid source text masquerading as an answer heading.
                parts.extend('Source excerpt: ' + line for line in passage['snippet'].splitlines())
                available = [f'{key}: {value}' for key, value in citation.items() if value is not None]
                parts.append('Attribution: ' + ('; '.join(available) if passage['citation_available'] else 'Citation unavailable.'))
                missing = [key for key, value in citation.items() if value is None]
                if missing:
                    parts.append('Unavailable citation metadata: ' + ', '.join(missing) + '.')
                if passage['truncated']:
                    parts.append('Excerpt shortened to the snippet budget.')
        parts.extend(result.get('warnings', []))
        if result.get('error'):
            parts.append('Limitation: ' + result['error']['message'])
        method = result.get('method', {})
        parts.extend(str(method[k]) for k in ('precision', 'interval') if k in method)
    if not evidence:
        parts.append('No deterministic evidence was retrieved.')
    if stop_reason != 'complete':
        parts.append('Investigation stopped: ' + stop_reason + '. Results above are partial.')
    return '\n\n'.join(parts)
