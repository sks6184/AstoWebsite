"""Server-bound evidence loop; no eval, dynamic imports, writes or model calculations."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
import time

from charts.models import SavedChart
from astrology.tools import invoke_tool
from astrology.tools.contracts import MAX_REQUEST_BYTES, json_bytes, validate_payload
from astrology.calculations.varga import SUPPORTED_VARGAS
from astrology.rag.knowledge import KnowledgeSession, validate_knowledge
from .policy import ScopeError
from .provider import OpenAIProvider
from .continuity import validate_context, plan_with_context
from astrology.synthesis.fact_catalog import build_catalog
from astrology.synthesis.verified_answer import publish_answer, narratives
from accounts.usage_policy import BudgetExceeded
from accounts.pilot_ops import progress

ALLOWLIST = frozenset(('get_chart_facts', 'get_dasha_periods', 'get_transits', 'get_ashtakavarga',
                       'evaluate_astrology_rules', 'get_timing_candidates', 'search_astrology_knowledge'))


@dataclass(frozen=True)
class Limits:
    rounds: int = 4
    calls: int = 24
    tool_bytes: int = 524288
    horizon_days: int = 1097
    model_tokens: int = 100000
    output_tokens: int = 1200
    seconds: float = 60
    tool_seconds: float = 15

    def __post_init__(self):
        # Limits are trusted server configuration; reject invalid values instead of disabling bounds.
        if any(type(v) is not int or v <= 0 for k, v in asdict(self).items() if k not in ('seconds', 'tool_seconds')):
            raise ValueError('Integer budgets must be positive.')
        if any(type(v) not in (int, float) or not 0 < v <= 300 for v in (self.seconds, self.tool_seconds)):
            raise ValueError('Time budgets must be positive and at most 300 seconds.')


class Stop(Exception):
    pass


class Consultation:
    def __init__(self, user, chart_id, question, *, today, provider=None, limits=None, clock=time.monotonic, knowledge_adapter=None, consultation_context=None):
        self.user, self.chart_id, self.question = user, chart_id, question
        self.today, self.provider, self.limits, self.clock = today, provider, limits or Limits(), clock
        self.started = clock()
        self.trace, self.evidence, self.seen = [], {}, {}
        self.usage = {'rounds': 0, 'calls': 0, 'tool_bytes': 0, 'reserved_tokens': 0,
                      'input_tokens': 0, 'output_tokens': 0}
        self.stop_reason = 'complete'
        self.plan = None
        self.knowledge = KnowledgeSession(user, chart_id, knowledge_adapter)
        self.context = consultation_context
        self.draft = None

    def check_time(self):
        if self.clock() - self.started >= self.limits.seconds:
            raise Stop('consultation_timeout')

    def execute(self, name, arguments, reason, *, optional=False):
        self.check_time()
        progress({'get_chart_facts': 'charts', 'get_dasha_periods': 'periods', 'get_transits': 'transits',
            'evaluate_astrology_rules': 'rules', 'search_astrology_knowledge': 'sources'}.get(name, 'answer'))
        if name not in ALLOWLIST or type(arguments) is not dict or type(reason) is not str or not 1 <= len(reason.strip()) <= 400:
            raise Stop('invalid_tool_request')
        args = deepcopy(arguments)
        if 'chart_id' in args and (type(args['chart_id']) is not int or args['chart_id'] != self.chart_id):
            raise Stop('chart_scope_violation')
        args['chart_id'] = self.chart_id
        if len(json_bytes(args)) > MAX_REQUEST_BYTES:
            raise Stop('tool_request_limit')
        if optional:
            if self.plan.kind in ('house_lord', 'current_dasha', 'transit'):
                raise Stop('methodology_scope_violation')
            if name == 'search_astrology_knowledge':
                topics = {self.plan.topic, 'career'} if self.plan.topic == 'job' else {self.plan.topic}
                if args.get('topic') not in topics:
                    raise Stop('topic_scope_violation')
            elif name == 'get_chart_facts':
                if type(args.get('charts')) is not list or not args['charts'] or any(type(c) is not str or c.lower() not in SUPPORTED_VARGAS for c in args['charts']):
                    raise Stop('unsupported_optional_varga')
            elif name == 'get_ashtakavarga':
                pass
            elif name == 'evaluate_astrology_rules':
                if args.get('category') != self.plan.topic or not any(a <= args.get('as_of', '') <= b for a, b in self.plan.windows):
                    raise Stop('calendar_scope_violation')
            else:
                if not any(a <= args.get('start_date', '') <= args.get('end_date', '') <= b for a, b in self.plan.windows):
                    raise Stop('calendar_scope_violation')
                if name == 'get_timing_candidates' and args.get('topic') != self.plan.topic:
                    raise Stop('topic_scope_violation')
        key = json.dumps([name, args], sort_keys=True)
        if key in self.seen:
            self.trace.append({'event': 'deduplicated', 'tool': name, 'evidence_id': self.seen[key], 'reason': reason})
            return self.evidence[self.seen[key]]['result']
        if self.usage['calls'] >= self.limits.calls:
            raise Stop('tool_call_limit')
        self.usage['calls'] += 1
        before = self.clock()
        try:
            if name == 'search_astrology_knowledge':
                reserve = 0
                if self.knowledge.requires_provider(args):
                    if self.usage['rounds'] >= self.limits.rounds:
                        raise Stop('model_round_limit')
                    reserve = self.knowledge.reservation(args)
                    if self.usage['reserved_tokens'] + reserve > self.limits.model_tokens:
                        raise Stop('model_token_limit')
                    self.usage['reserved_tokens'] += reserve
                result = self.knowledge.search(args, token_budget=reserve, timeout=min(self.limits.tool_seconds, self.limits.seconds - (self.clock() - self.started), 60))
                self.usage['rounds'] += self.knowledge.last_usage['provider_rounds']
                self.usage['input_tokens'] += self.knowledge.last_usage['input_tokens']
                self.usage['output_tokens'] += self.knowledge.last_usage['output_tokens']
                if self.usage['input_tokens'] + self.usage['output_tokens'] > self.limits.model_tokens:
                    raise Stop('model_token_limit')
                validate_knowledge(result)
                if (result.get('error') or {}).get('code') == 'knowledge_token_limit':
                    raise Stop('model_token_limit')
                if (result.get('error') or {}).get('code') == 'spending_limit':
                    raise Stop('spending_limit')
            else:
                result = invoke_tool(self.user, name, args)
                validate_payload(name, result)
        except Stop:
            raise
        except TimeoutError:
            raise Stop('tool_timeout') from None
        except Exception:
            raise Stop('tool_failure') from None
        if (result.get('error') or {}).get('code') in ('chart_not_found', 'authentication_required'):
            raise Stop('chart_unavailable')
        if self.clock() - before >= self.limits.tool_seconds:
            raise Stop('tool_timeout')
        self.check_time()
        size = len(json_bytes(result))
        if self.usage['tool_bytes'] + size > self.limits.tool_bytes:
            raise Stop('tool_output_limit')
        self.usage['tool_bytes'] += size
        eid = 'E' + str(len(self.evidence) + 1)
        self.seen[key] = eid
        self.evidence[eid] = {'tool': name, 'arguments': args, 'reason': reason, 'result': result}
        self.trace.append({'event': 'tool_result', 'tool': name, 'evidence_id': eid,
                           'status': result['status'], 'reason': reason})
        return result

    def minimal_evidence(self):
        plan = self.plan
        if plan.kind == 'planet_position':
            self.execute('get_chart_facts', {'charts': [plan.varga]}, 'A stored planetary position requires only its requested chart.')
            return
        if plan.kind == 'ashtakavarga_lookup':
            from .policy import SIGNS
            arguments = {'kind': 'bav', 'planet': plan.planet} if 'bav' in self.question.lower() and plan.planet else {'kind': 'sav'}
            if plan.transit_sign: arguments['sign'] = SIGNS.index(plan.transit_sign) + 1
            self.execute('get_ashtakavarga', arguments, 'Read stored BAV/SAV points; missing values are not zeros.')
            return
        if plan.kind == 'chart_focus':
            self.execute('get_chart_facts', {'charts': ['d10']}, plan.reason)
            return
        if plan.kind == 'house_lord':
            self.execute('get_chart_facts', {'charts': ['d1']}, 'A house ruler is a D1 factual lookup.')
            return
        if plan.kind in ('assessment', 'timing'):
            self.execute('get_chart_facts', {'charts': ['d1', 'd10']}, 'Compare natal promise and professional divisional evidence.')
        for start, end in plan.windows:
            scope = {'start_date': start, 'end_date': end}
            if plan.kind == 'transit':
                self.execute('get_transits', {**scope, 'planets': [plan.planet]},
                             'Focused planet transit in the requested context; no broad forecast.')
                continue
            granularity = 'pratyantardasha' if 'pratyantar' in self.question.lower() else 'antardasha'
            system = ('yogini' if 'yogini' in self.question.lower() else 'chara' if 'chara' in self.question.lower() else 'vimshottari') if plan.kind in ('current_dasha', 'dasha_lookup') else 'vimshottari'
            dasha = self.execute('get_dasha_periods', {**scope, 'system': system, 'granularity': granularity},
                                 'Resolve the actual MD/AD periods for this requested interval.')
            if plan.kind in ('current_dasha', 'dasha_lookup'):
                continue
            self.execute('evaluate_astrology_rules', {'category': plan.topic, 'as_of': start},
                         'Use deterministic rule conclusions as of this window start; not full-window confirmation.')
            if plan.kind == 'timing':
                # P2 source periods are [start,end); requested ranges are inclusive calendar dates.
                for period in (dasha.get('data') or {}).get('periods', []):
                    planets = sorted({period.get('lord'), period.get('mahadasha', {}).get('lord')} - {None})
                    left = max(date.fromisoformat(start), date.fromisoformat(period['start']))
                    right = min(date.fromisoformat(end), date.fromisoformat(period['end']) - timedelta(days=1))
                    if planets and left <= right:
                        self.execute('get_transits', {'planets': planets, 'start_date': left.isoformat(), 'end_date': right.isoformat()},
                                     'Transit only the MD/AD lords active in this source period, clipped at its boundaries.')
                self.execute('get_ashtakavarga', {'kind': 'both'}, 'Map stored BAV/SAV to the scoped transit signs; missing cells remain unknown.')
                self.execute('get_timing_candidates', {**scope, 'topic': plan.topic},
                             'Compare candidate hypotheses and contrary evidence within this window; scores are heuristic, not probabilities.')

    def investigate(self):
        provider = self.provider or OpenAIProvider()
        for _ in range(self.limits.rounds):
            self.check_time()
            if self.usage['rounds'] >= self.limits.rounds:
                raise Stop('model_round_limit')
            payload = {'question': self.question, 'plan': asdict(self.plan), 'evidence': self.evidence,
                       'trace': self.trace, 'remaining_calls': self.limits.calls - self.usage['calls']}
            payload['answer_catalog'] = build_catalog(self.evidence)
            payload['narrative_catalog'] = narratives(self.plan, self.question, self.context, self.evidence)
            if self.context is not None:
                payload['consultation_context'] = self.context
            # Include schemas and instructions; reserve output before dispatch, never after spending.
            reservation = provider.request_size(payload) + self.limits.output_tokens
            if self.usage['reserved_tokens'] + reservation > self.limits.model_tokens:
                raise Stop('model_token_limit')
            self.usage['reserved_tokens'] += reservation
            self.usage['rounds'] += 1
            try:
                reply = provider.complete(deepcopy(payload), max_output_tokens=self.limits.output_tokens,
                                          timeout=min(20, self.limits.seconds - (self.clock() - self.started)))
                if len(json_bytes(reply)) > 32768:
                    raise Stop('provider_output_limit')
                for source, target in (('input_tokens', 'input_tokens'), ('output_tokens', 'output_tokens')):
                    value = reply.get(source)
                    if type(value) is not int or value < 0:
                        raise Stop('invalid_provider_usage')
                    self.usage[target] += value
                if self.usage['input_tokens'] + self.usage['output_tokens'] > self.limits.model_tokens:
                    raise Stop('model_token_limit')
                if reply['output_tokens'] > self.limits.output_tokens:
                    raise Stop('provider_output_token_limit')
                self.check_time()
                calls = reply.get('calls')
                if type(calls) is not list or len(calls) > self.limits.calls:
                    raise Stop('invalid_provider_response')
                if not calls:
                    final = reply.get('final')
                    known = set(self.evidence)
                    for entry in self.evidence.values():
                        if entry['tool'] == 'search_astrology_knowledge':
                            known.update(p['evidence_id'] for p in (entry['result'].get('data') or {}).get('passages', []))
                    if type(final) is not dict or set(final) not in ({'evidence_ids'}, {'evidence_ids', 'draft'}) or type(final['evidence_ids']) is not list or not final['evidence_ids'] or any(type(e) is not str or e not in known for e in final['evidence_ids']):
                        raise Stop('invalid_evidence_references')
                    self.draft = final.get('draft')
                    self.trace.append({'event': 'finish', 'evidence_ids': final['evidence_ids'], 'reason': 'Model finished evidence investigation; server renders all minimum evidence.'})
                    return
                before = self.usage['calls']
                for call in calls:
                    if type(call) is not dict or set(call) != {'name', 'arguments', 'reason'}:
                        raise Stop('invalid_tool_request')
                    self.execute(call['name'], call['arguments'], call['reason'], optional=True)
                if self.usage['calls'] == before:
                    raise Stop('repeated_tool_calls')
            except Stop:
                raise
            except TimeoutError:
                raise Stop('provider_timeout') from None
            except BudgetExceeded:
                raise Stop('spending_limit') from None
            except Exception:
                raise Stop('provider_unavailable') from None
        raise Stop('model_round_limit')

    def run(self):
        try:
            if not getattr(self.user, 'is_authenticated', False) or not getattr(self.user, 'is_active', False) or type(self.chart_id) is not int or not SavedChart.objects.filter(pk=self.chart_id, user_id=self.user.pk).exists():
                raise Stop('chart_unavailable')
            self.context = validate_context(self.context, self.chart_id)
            self.plan = plan_with_context(self.question, self.today, self.limits.horizon_days, self.context)
            self.trace.append({'event': 'plan', **asdict(self.plan)})
            self.minimal_evidence()
            if self.plan.kind in ('assessment', 'timing'):
                self.investigate()
        except ScopeError as exc:
            self.stop_reason = 'scope_clarification'
            self.trace.append({'event': 'clarification', 'reason': str(exc)})
        except Stop as exc:
            self.stop_reason = str(exc)
        # Do not publish retained evidence if ownership changed during this request.
        if self.plan is not None and not SavedChart.objects.filter(pk=self.chart_id, user_id=self.user.pk).exists():
            self.stop_reason = 'chart_unavailable'
        if self.stop_reason == 'chart_unavailable':
            self.evidence.clear()
            self.plan = None
        useful = any(e['result']['status'] in ('ok', 'partial') and e['result'].get('data') for e in self.evidence.values())
        status = 'ok' if useful and self.stop_reason == 'complete' and all(e['result']['status'] == 'ok' for e in self.evidence.values()) else 'partial' if useful else 'error'
        self.trace.append({'event': 'stop', 'reason': self.stop_reason, 'status': status})
        progress('validation')
        published = publish_answer(self.plan, self.question, self.evidence, draft=self.draft, context=self.context,
                                   stop_reason=self.stop_reason, trace=self.trace)
        if not published['validation']['passed']:
            status = 'error'
        elif published['draft_validation'] and not published['draft_validation']['passed'] and status == 'ok':
            status = 'partial'
        self.trace.append({'event': 'publication_validation', 'passed': published['validation']['passed']})
        return {'status': status, 'answer': published['answer'],
                'validation': published['validation'], 'draft_validation': published['draft_validation'], 'claims': published['claims'],
                'model': 'deterministic' if not self.usage['rounds'] else getattr(self.provider, 'name', 'openai-responses'),
                'prompt_tokens': self.usage['input_tokens'], 'completion_tokens': self.usage['output_tokens'],
                'evidence': self.evidence, 'trace': self.trace, 'usage': self.usage, 'stop_reason': self.stop_reason}


def run_consultation(user, chart_id, question, *, today=None, provider=None, limits=None, knowledge_adapter=None, consultation_context=None):
    from django.utils import timezone
    return Consultation(user, chart_id, question, today=today or timezone.localdate(), provider=provider, limits=limits, knowledge_adapter=knowledge_adapter, consultation_context=consultation_context).run()
