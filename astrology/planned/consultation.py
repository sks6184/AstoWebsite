"""Planned consultation (M3, second design).

    question
    -> intent            one model call: question type, domains, events, window
    -> plan              deterministic: merged profile and event-matrix requirements -> tool calls
    -> engine            every call once (deduplicated, cached); failures and unsupported items tracked
    -> supplementary     at most one deterministic follow-up when the results call for it
    -> retrieval         searches built from the actual results; pooled re-rank; supporting and contrary
    -> brief             the astrologer's brief (server text)
    -> writer            one model call: the interpretation, no tags
    -> fact check        each statement against the tables; one targeted repair call only if needed;
                         statements still wrong are removed, never the whole answer for a formatting reason
    -> answer            with internal provenance (sentence -> evidence), never shown to the reader

The model never chooses a tool, never calculates and never decides a rule. The multi-round agent loop this
replaces is kept in ``astrology/agent/general.py`` (git tag ``m3-agent-loop-v1``).
"""
from copy import deepcopy
import json
import time

from accounts.pilot_ops import progress
from accounts.usage_policy import BudgetExceeded
from astrology.agent.general import DISCLOSURES, SEARCH_TOOL, GeneralConsultation, Stop
from astrology.tools import invoke_tool
from astrology.tools.contracts import validate_payload
from .brief import build_brief
from .checker import FIELDS, check_answer, clean_text, markers, prune
from .plan import build_plan, stated_window, supplementary_calls
from .retrieval import build_queries, guided_books, rerank
from .tables import Tables

PROGRESS = {'get_chart_facts': 'charts', 'get_dasha_periods': 'periods', 'get_transits': 'transits', 'evaluate_astrology_rules': 'rules'}
NOT_CITED = 'Classical passages were retrieved for these factors, but this reading does not cite them.'
REMOVED_NOTE = 'One or more statements that could not be verified against the calculations were removed from this reading.'
REPORT_SECTIONS = ('NATAL CHART', 'PERIODS', 'TRANSITS', 'TRIGGERED RULES', 'TIMING CANDIDATES')


class PlannedConsultation(GeneralConsultation):
    pipeline = 'planned_consultation'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plan = self.tables = None
        self.brief, self.sections, self.kept, self.retrieval, self.removed, self.intent = '', {}, [], [], [], None
        self.models, self.attempts = [], []

    def default_provider(self):
        from .provider import PlannedProvider
        return PlannedProvider()

    # ── One metered model call ───────────────────────────────────────────
    def call(self, provider, stage, payload):
        self.check_time()
        if self.usage['rounds'] >= self.limits.rounds:
            raise Stop('model_round_limit')
        counted = provider.count_tokens(stage, payload)
        if counted > self.limits.round_input_tokens:
            raise Stop('round_input_limit')
        self.usage['rounds'] += 1
        self.usage['round_input_tokens'].append(counted)
        started = self.clock()
        progress('answer')
        try:
            response = provider.complete(stage, deepcopy(payload), max_output_tokens=self.limits.output_tokens,
                                         timeout=max(1, min(self.limits.provider_seconds, self.limits.seconds - self.elapsed())))
        except Stop:
            raise
        except TimeoutError:
            raise Stop('provider_timeout') from None
        except BudgetExceeded:
            raise Stop('spending_limit') from None
        except Exception:
            raise Stop('provider_unavailable') from None
        latency = int((self.clock() - started) * 1000)
        if type(response) is not dict or not {'reply', 'input_tokens', 'output_tokens'} <= set(response) or type(response['reply']) is not dict:
            raise Stop('invalid_provider_response')
        for key in ('input_tokens', 'output_tokens'):
            if type(response[key]) is not int or response[key] < 0:
                raise Stop('invalid_provider_usage')
            self.usage[key] += response[key]
        self.usage['round_latency_ms'].append(latency)
        if response.get('model'):
            self.models.append(str(response['model']))
        self.trace.append({'event': 'round', 'round': self.usage['rounds'], 'stage': stage, 'counted_input_tokens': counted,
                           'provider_input_tokens': response['input_tokens'], 'provider_output_tokens': response['output_tokens'],
                           'latency_ms': latency})
        return response['reply']

    # ── Engine ───────────────────────────────────────────────────────────
    def calculate(self, call):
        """Run one planned call once. Identical calls are never repeated within a consultation."""
        tool, args = call['tool'], call['args']
        key = json.dumps([tool, args], sort_keys=True)
        if key in self.seen:
            self.trace.append({'event': 'deduplicated', 'tool': tool, 'evidence_id': self.seen[key]})
            return self.seen[key]
        self.check_time()
        self.usage['tool_calls'] += 1
        progress(PROGRESS.get(tool, 'charts'))
        try:
            result = invoke_tool(self.user, tool, {**args, 'chart_id': self.chart_id})
            validate_payload(tool, result)
        except Exception:
            raise Stop('tool_failure') from None
        error = (result.get('error') or {}).get('code')
        if error in ('chart_not_found', 'authentication_required'):
            raise Stop('chart_unavailable')
        eid = self.record(tool, {**args, 'chart_id': self.chart_id}, call['reason'], result)
        self.seen[key] = eid
        self.trace.append({'event': 'tool_result', 'tool': tool, 'evidence_id': eid, 'status': result['status'], 'error_code': error,
                           'arguments': args, 'supplementary': bool(call.get('supplementary'))})
        return eid

    def retrieve(self):
        queries = build_queries(self.question, self.plan, self.tables, self.profile, self.limits.searches)
        searches = []
        for query in queries:
            eid = self.search({'query': query['query'], 'domain': (self.label['domains'] or ['consultation'])[0],
                               'purpose': query['purpose'][:80], 'result_count': 5},
                              f"Classical principles for {query['purpose']} ({query['stance']}).")
            if eid:
                data = self.evidence[eid]['result'].get('data') or {}
                searches.append((query, data.get('passages', [])))
        self.kept, self.retrieval = rerank(searches, self.label)
        self.trace.append({'event': 'rerank', 'queries': [{'purpose': q['purpose'], 'stance': q['stance'], 'query': q['query']} for q in queries],
                           'candidates': len(self.retrieval), 'kept': [p['id'] for p in self.kept],
                           'guided_books': sorted(guided_books(self.label))})

    # ── The flow ─────────────────────────────────────────────────────────
    def investigate(self, provider):
        intent = self.call(provider, 'intent', {'question': self.question, 'today': self.today.isoformat(),
                                                'label_menu': self.profile.catalog(),
                                                **({'consultation_context': {'trust': 'untrusted memory; never a chart fact', **self.context}}
                                                   if self.context is not None else {})})
        self.intent = intent
        self.apply_label(self.normalize_label(intent))
        if self.label['question_type'] == 'out_of_scope':
            return 'out_of_scope'
        window = stated_window(self.question, self.today)
        if window:
            self.trace.append({'event': 'window_from_question', 'window': window})
        self.plan = build_plan(self.profile, self.label, window or intent.get('window'), self.today)
        self.trace.append({'event': 'plan', **self.plan.summary()})
        for call in self.plan.calls:
            self.calculate(call)
        self.tables = Tables(self.evidence)
        extra = supplementary_calls(self.plan, self.tables)
        if extra:
            for call in extra:
                self.calculate(call)
            self.trace.append({'event': 'supplementary', 'calls': len(extra), 'reason': extra[0]['reason']})
            self.tables = Tables(self.evidence)
        self.retrieve()
        self.brief, self.sections = build_brief(self.question, self.plan, self.tables, self.kept, self.profile, self.today)
        answer = self.call(provider, 'writer', {'brief': self.brief})
        report = self.check(answer)
        if not report['passed'] and self.usage['rounds'] < self.limits.rounds:
            # A targeted repair: only the statements the fact check names, with the calculated values.
            self.trace.append({'event': 'repair_requested', 'findings': len(report['findings']), 'missing': report['missing_sections']})
            try:
                answer = self.call(provider, 'repair', {'brief': self.brief, 'previous_answer': answer,
                                                        'corrections': report['repair_instruction']})
                report = self.check(answer, repair=True)
            except Stop as exc:
                self.trace.append({'event': 'repair_unavailable', 'reason': str(exc)})
        if report['findings']:
            answer, self.removed = prune(answer, report['findings'])
            self.trace.append({'event': 'statements_removed', 'count': len(self.removed)})
            report = self.check(answer, pruned=True)
        self.final_validation = report
        self.final = {**answer, 'unavailable_calculations': [u['id'] for u in self.plan.unsupported]}
        concept = self.label['question_type'] == 'concept_explanation'
        if report['findings'] or not str(answer.get('direct_answer') or '').strip() or (not concept and report['verified_statements'] < 2):
            raise Stop('validation_failed')
        return 'published'

    def normalize_label(self, intent):
        """The label fields only; an event of an unlabelled domain is dropped (and traced), never guessed."""
        domains = list(intent.get('domains') or []) if type(intent.get('domains')) is list else []
        events = [e for e in intent.get('events') or [] if type(e) is str] if type(intent.get('events')) is list else []
        kept = [e for e in events if e.partition(':')[0] in domains]
        if len(kept) != len(events):
            self.trace.append({'event': 'events_dropped', 'count': len(events) - len(kept)})
        return {'question_type': intent.get('question_type'), 'domains': domains[:3], 'events': kept[:6]}

    def check(self, answer, repair=False, pruned=False):
        report = check_answer(answer, self.tables, self.plan, self.kept, today=self.today, conflicts_present=bool(self.tables.conflicts))
        self.attempts.append({'stage': 'after_removal' if pruned else 'repair' if repair else 'writer', 'answer': answer,
                              'findings': [{k: f[k] for k in ('field', 'sentence', 'code', 'detail', 'correction')} for f in report['findings']],
                              'missing': report['missing_sections'], 'soft': report['soft']})
        self.trace.append({'event': 'validation', 'passed': report['passed'], 'issues': report['issues'][:12],
                           'missing': report['missing_sections'], 'verified_statements': report['verified_statements'],
                           'soft_notes': len(report['soft']), 'repair_round': repair, 'after_removal': pruned})
        return report

    # ── Publication ──────────────────────────────────────────────────────
    def render(self, final):
        blocks = []
        for field in FIELDS:
            text = clean_text(final.get(field) or '', self.kept)
            if text:
                blocks.append(('Conflicting indications: ' if field == 'conflicts' else '') + text)
        strength = final.get('evidence_strength') or {}
        if strength.get('label'):
            blocks.append(f"Evidence strength: {strength['label']}. {clean_text(strength.get('reason') or '', self.kept)}")
        used = {m for field in FIELDS for m in markers(final.get(field))}
        cited = [p['id'] for p in self.kept if p['marker'] in used]
        states, calculations, succeeded, failed = self.states(cited)
        notes = self.disclosures(states, calculations, succeeded, failed)
        if self.kept and not cited:
            # Passages were retrieved, but the reading cites none: say that, not that nothing was found.
            notes = [NOT_CITED if n == DISCLOSURES['no_source_support'] else n for n in notes]
        if self.removed:
            notes.append(REMOVED_NOTE)
        if notes:
            blocks.append(' '.join(notes))
        return '\n\n'.join(blocks), self.atoms(), states, calculations

    def atoms(self):
        """Fact atoms behind the verified statements (internal provenance; never printed in the answer)."""
        catalog = self.catalog()
        index = {}
        for atom in catalog.values():
            for path in atom['bindings'].values():
                index.setdefault((atom['evidence_id'], path.rsplit('/', 1)[0]), atom)
        found = {}
        for row in (self.final_validation or {}).get('provenance', []):
            for ref in row['refs']:
                atom = index.get((ref.get('evidence_id'), ref.get('path')))
                if atom:
                    found[atom['id']] = atom
        return list(found.values())[:128]

    def fallback(self, reason):
        """Deterministic evidence report from the brief (server text only), marked partial and unbilled."""
        if not self.sections:
            return super().fallback(reason)
        states, calculations, succeeded, failed = self.states()
        blocks = ['I could not complete a verified written interpretation for this question, so here is the calculated '
                  'evidence that was gathered, without interpretation.']
        for heading, lines in self.sections.items():
            if heading.startswith(REPORT_SECTIONS):
                blocks.append(heading.split(' (')[0].title() + '\n' + '\n'.join(lines[:14]))
        blocks.append('Evidence strength: limited, because no interpretation could be verified.')
        notes = self.disclosures(states, calculations, succeeded, failed)
        if notes:
            blocks.append(' '.join(notes))
        self.trace.append({'event': 'fallback', 'reason': reason})
        return '\n\n'.join(blocks), [], states, calculations

    def extra(self):
        report = self.final_validation or {}
        published = {}
        if self.stop_reason == 'complete' and self.final is not None:
            # The fact check's own report is the published validation (AGENTS.md shape).
            published = {'published_by': 'model',
                         'validation': {**{k: report[k] for k in ('passed', 'score', 'issues', 'missing_sections', 'generic_phrases_detected',
                                                                 'unsupported_claims', 'repair_instruction')},
                                        'stage': 'fact_check', 'verified_statements': report['verified_statements'],
                                        'removed_statements': len(self.removed), 'coverage': report['coverage']}}
            if report['missing_sections']:
                published['status'] = 'partial'
        return {**published, 'intent': self.intent, 'plan': self.plan.summary() if self.plan else None, 'brief': self.brief,
                'retrieval': self.retrieval, 'passages': [{k: p[k] for k in ('marker', 'id', 'title', 'chapter', 'page', 'purpose', 'stance', 'score')} for p in self.kept],
                'provenance': report.get('provenance', []), 'removed_statements': self.removed, 'attempts': self.attempts,
                'provider_models': list(dict.fromkeys(self.models)),
                'unsupported': ([{'id': u['id'], 'name': u['name']} for u in self.plan.unsupported] if self.plan else []) +
                               ([{'tool': f['tool'], 'code': f['code']} for f in self.tables.failed] if self.tables else [])}


def run_planned_consultation(user, chart_id, question, *, today=None, provider=None, limits=None, knowledge_adapter=None,
                             consultation_context=None, profile=None, clock=time.monotonic):
    from django.utils import timezone
    return PlannedConsultation(user, chart_id, question, today=today or timezone.localdate(), provider=provider, limits=limits,
                               clock=clock, knowledge_adapter=knowledge_adapter, consultation_context=consultation_context,
                               profile=profile).run()
