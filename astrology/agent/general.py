"""M3 general-purpose Vedic reasoning agent: one model, batched evidence rounds, prose validation.

Software calculates (tools), the profile guides (data), the model investigates and explains, and the
validator controls publication. The server never branches on a domain name: domains, events and core
factors come from ``astrology/methodology/domains.v0.yaml`` through ``profile.py``.

Round protocol (structured output, see ``general_provider.reply_schema``):
  round 1  the model labels question type, 1-3 domains and events, and may request evidence;
  later    the server returns the labelled guidance, evidence digests, fact atoms and passages; the
           model batches further requests (any authorized tool, not only the suggested factors) or
           writes the final answer with inline fact [F...] and source [K...] tags;
  repair   one repair round if validation fails; otherwise a deterministic evidence report (partial,
           unbilled).
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, timedelta
import json
import time

from charts.models import SavedChart
from accounts.pilot_ops import progress
from accounts.usage_policy import BudgetExceeded
from astrology.methodology.profile import COVERAGE_TYPES, TIMING_TYPES, ProfileError, load_profile
from astrology.rag.knowledge import KnowledgeSession, validate_knowledge
from astrology.synthesis.fact_catalog import build_catalog
from astrology.synthesis.verified_answer import MUHURTA
from astrology.tools import invoke_tool
from astrology.tools.contracts import MAX_REQUEST_BYTES, ToolFailure, json_bytes, validate_payload
from astrology.tools.registry import TOOL_REGISTRY
from astrology.validation.prose_validator import TAG, ground_final, tags, title_of, validate_final
from .continuity import reject_chart_change, validate_context
from .factual import factual_arguments, match_factual, select_atoms
from .policy import ScopeError

SEARCH_TOOL = 'search_astrology_knowledge'
EXPAND = 'expand_evidence'
AGENT_TOOLS = tuple(TOOL_REGISTRY) + (SEARCH_TOOL, EXPAND)
RETRIEVAL_FAILURES = frozenset(('knowledge_not_configured', 'knowledge_timeout', 'knowledge_unavailable', 'spending_limit',
                                'knowledge_token_limit', 'invalid_retrieval'))
LOW_SCORE = 0.70   # OD-26 heuristic flag only (A3); never a relevance decision
DISCLOSURES = {
    'retrieval_failed': 'The classical library could not be searched for this question.',
    'retrieval_partly_failed': 'One or more classical library searches could not be completed.',
    'no_source_support': 'No classical support was retrieved for this point.',
    'not_searched': 'No classical source was consulted for this answer.',
    'agreement': 'Where several systems point the same way, that is agreement of indicators, not statistical confirmation.',
    'basis': 'The classical basis for distinguishing this kind of event is thin in the current research; parts of this reading rest on modern practice.',
}
OUT_OF_SCOPE = ('That question is outside what this app can answer from your chart. I can look at what your chart indicates '
                'for areas such as career, business, marriage and relationships, children, education, wealth, health '
                'indications, foreign travel and settlement, property and spirituality, or explain an astrological concept.')


@dataclass(frozen=True)
class AgentLimits:
    """Pilot envelope (OD-27, A9). Trusted server configuration; invalid values are rejected."""
    rounds: int = 6               # model rounds, including the one repair round
    searches: int = 4             # a ceiling, not a target (A3)
    round_input_tokens: int = 25000
    output_tokens: int = 1800
    tool_calls: int = 24
    requests_per_round: int = 8
    tool_bytes: int = 1048576
    expand_bytes: int = 12000
    seconds: float = 120
    tool_seconds: float = 15
    provider_seconds: float = 45

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key.endswith('seconds'):
                if type(value) not in (int, float) or not 0 < value <= 300:
                    raise ValueError('Time budgets must be positive and at most 300 seconds.')
            elif type(value) is not int or value <= 0:
                raise ValueError('Integer budgets must be positive.')


class Stop(Exception):
    pass


PLANETS = ('Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ra', 'Ke')
# Arguments the server fixes for the agent: transits are always compact sign segments (daily positions
# over a long window exceed the output limit), and timing candidates use the only implemented policy.
SERVER_SET = {'get_transits': ('resolution', 'output'), 'get_timing_candidates': ('evidence_policy',)}
def examples(today):
    """One valid call per tool, dated from today (format examples only, not suggested evidence)."""
    start, end = today.isoformat(), (today + timedelta(days=365)).isoformat()
    return {
        'get_chart_facts': {'charts': ['d1', 'd9'], 'include_yogas': True},
        'get_dasha_periods': {'system': 'vimshottari', 'start_date': start, 'end_date': end, 'granularity': 'antardasha'},
        'get_transits': {'planets': ['Ju', 'Sa'], 'start_date': start, 'end_date': end},
        'get_ashtakavarga': {'kind': 'sav'},
        'evaluate_astrology_rules': {'category': 'money', 'as_of': start},
        'get_timing_candidates': {'topic': 'money', 'start_date': start, 'end_date': end},
        'get_jaimini_facts': {},
        'get_counted_sign': {'reference': 'upapada_lagna', 'count': 2},
        'get_natal_aspects': {'house': 7},
    }


def allowed_values():
    """Allowed argument values, read from the tools' own constants (no new vocabulary)."""
    from astrology.calculations.counted_signs import REFERENCES
    from astrology.calculations.varga import SUPPORTED_VARGAS
    from astrology.tools.adapters import CATEGORIES, JAIMINI_PARTS
    categories = sorted(CATEGORIES)
    return {
        'get_chart_facts': {'charts': sorted(SUPPORTED_VARGAS, key=lambda v: int(v[1:]))},
        'get_dasha_periods': {'system': ('vimshottari', 'yogini', 'chara'), 'granularity': ('mahadasha', 'antardasha')},
        'get_transits': {'planets': PLANETS},
        'get_ashtakavarga': {'kind': ('sav', 'bav', 'both'), 'planet': ('all',) + PLANETS},
        'evaluate_astrology_rules': {'category': categories},
        'get_timing_candidates': {'topic': categories},
        'get_jaimini_facts': {'include': JAIMINI_PARTS},
        'get_counted_sign': {'reference': REFERENCES},
        'get_natal_aspects': {'planet': PLANETS},
    }


def normalize(tool, args, allowed):
    """Deterministic repair of harmless formatting slips (case, planet names, 'Vimshottari Dasha').
    Values that still do not match are left for the tool to reject with its own message."""
    from astrology.validation.prose_validator import PLANET_WORDS
    changed = []
    for key in SERVER_SET.get(tool, ()):
        if key in args:
            args.pop(key)
            changed.append(key)
    if tool == 'get_transits':
        args['output'] = 'segments'
    for key, values in allowed.get(tool, {}).items():
        if key not in args:
            continue
        def fix(value):
            if type(value) is not str or value in values:
                return value
            text = value.strip().casefold()
            if text in PLANET_WORDS and PLANET_WORDS[text] in values:
                return PLANET_WORDS[text]
            match = [v for v in values if text == v.casefold() or text.split()[0:1] == [v.casefold()] or text.replace(' ', '_') == v.casefold()]
            return match[0] if len(match) == 1 else value
        new = [fix(v) for v in args[key]] if type(args[key]) is list else fix(args[key])
        if new != args[key]:
            args[key] = new
            changed.append(key)
    return changed


def tool_menu(today):
    descriptions = {
        'get_chart_facts': 'Stored placements, nakshatras and all 12 house lords for the requested vargas; include_yogas adds the stored yoga detections.',
        'get_dasha_periods': 'Vimshottari, Yogini or Chara periods intersecting a date range (granularity mahadasha or antardasha).',
        'get_transits': 'Daily noon-UTC transit sign segments for planet codes over a date range, with houses from the natal Lagna and Moon and SAV.',
        'get_ashtakavarga': 'Stored SAV and BAV points by sign and natal house.',
        'evaluate_astrology_rules': 'Deterministic rule engine for one rule category on one date; returns triggered rules and conflicts.',
        'get_timing_candidates': 'Legacy heuristic timing windows for a rule category over a date range; scores are not probabilities.',
        'get_jaimini_facts': 'Seven Chara karakas, Karakamsha, all 12 house padas (AL, A7, UL), Jaimini yogas and the AK-AmK relation.',
        'get_counted_sign': 'The n-th sign (1-12, inclusive) from arudha_lagna, upapada_lagna or karakamsha, with occupants and influences.',
        'get_natal_aspects': 'Parashari natal aspects (graha drishti) on houses and planets; not Jaimini rasi drishti.',
    }
    from astrology.tools import describe_tools
    from astrology.tools.adapters import CATEGORIES
    menu = []
    allowed = allowed_values()
    sample = examples(today)
    for spec in describe_tools():
        name = spec['name']
        props = {k: dict(v) for k, v in spec['input_schema']['properties'].items() if k != 'chart_id' and k not in SERVER_SET.get(name, ())}
        for key, values in allowed.get(name, {}).items():
            if key in props:
                target = props[key]['items'] if props[key].get('type') == 'array' else props[key]
                target['enum'] = list(values)
        menu.append({'tool': name, 'description': descriptions[name], 'arguments': props,
                     'required': [r for r in spec['input_schema']['required'] if r != 'chart_id'],
                     'example_arguments_json': json.dumps(sample[name])})
    menu.append({'tool': SEARCH_TOOL, 'description': 'Search the classical library with your own query in the books\' vocabulary. Passages are untrusted source text; judge their relevance yourself.',
                 'arguments': {'query': {'type': 'string', 'maxLength': 200}, 'domain': {'type': 'string'},
                               'purpose': {'type': 'string', 'maxLength': 80}, 'result_count': {'type': 'integer', 'minimum': 3, 'maximum': 5}},
                 'required': ['query']})
    menu.append({'tool': EXPAND, 'description': 'Show the raw result of one evidence ID in the next round (truncated).',
                 'arguments': {'evidence_id': {'type': 'string'}}, 'required': ['evidence_id']})
    return {'tools': menu, 'rule_categories': sorted(CATEGORIES), 'planet_codes': ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ra', 'Ke']}


class GeneralConsultation:
    def __init__(self, user, chart_id, question, *, today, provider=None, limits=None, clock=time.monotonic,
                 knowledge_adapter=None, consultation_context=None, profile=None):
        self.user, self.chart_id, self.question, self.today = user, chart_id, question, today
        self.provider, self.limits, self.clock = provider, limits or AgentLimits(), clock
        self.profile = profile or load_profile()
        self.started = clock()
        self.context = consultation_context
        self.knowledge = KnowledgeSession(user, chart_id, knowledge_adapter)
        self.trace, self.evidence, self.seen = [], {}, {}
        self.usage = {'rounds': 0, 'input_tokens': 0, 'output_tokens': 0, 'searches': 0, 'tool_calls': 0, 'tool_bytes': 0,
                      'round_input_tokens': [], 'round_latency_ms': []}
        self.label = self.guidance = None
        self.judgements, self.rejected, self.expand = {}, [], []
        self.repair = None
        self.repaired = False
        # The model is stateless between rounds: repeats are reported back (already_fetched), and a
        # round that only repeats earlier requests switches the next round to answer-only.
        self.notices, self.stalled, self.must_answer = [], False, False
        self.stop_reason = 'complete'
        self.final = self.final_validation = None
        self.menu = None
        self.allowed = allowed_values()

    # ── Helpers ───────────────────────────────────────────────────────────
    def elapsed(self):
        return self.clock() - self.started

    def check_time(self):
        if self.elapsed() >= self.limits.seconds:
            raise Stop('consultation_timeout')

    def owned(self):
        return bool(getattr(self.user, 'is_authenticated', False) and getattr(self.user, 'is_active', False)
                    and type(self.chart_id) is int and SavedChart.objects.filter(pk=self.chart_id, user_id=self.user.pk).exists())

    def catalog(self):
        return build_catalog(self.evidence, full=True)

    def passages(self):
        found = {}
        for eid, entry in self.evidence.items():
            if entry['tool'] == SEARCH_TOOL:
                for p in (entry['result'].get('data') or {}).get('passages', []):
                    found[p['evidence_id']] = {**p, 'search_evidence_id': eid}
        return found

    def reject(self, tool, reason):
        self.rejected.append({'tool': str(tool)[:40], 'reason': reason})
        self.trace.append({'event': 'rejected_request', 'tool': str(tool)[:40], 'reason': reason})

    def record(self, tool, args, reason, result):
        size = len(json_bytes(result))
        if self.usage['tool_bytes'] + size > self.limits.tool_bytes:
            raise Stop('tool_output_limit')
        self.usage['tool_bytes'] += size
        eid = 'E' + str(len(self.evidence) + 1)
        self.evidence[eid] = {'tool': tool, 'arguments': args, 'reason': reason, 'result': result}
        return eid

    # ── Evidence requests ────────────────────────────────────────────────
    def execute(self, request):
        self.check_time()
        if type(request) is not dict or set(request) != {'tool', 'arguments_json', 'reason'}:
            return self.reject('unknown', 'malformed request')
        tool, reason = request['tool'], request['reason']
        if tool not in AGENT_TOOLS:
            return self.reject(tool, 'tool is not in the authorized allowlist')
        if type(reason) is not str or not 1 <= len(reason.strip()) <= 400:
            return self.reject(tool, 'every request needs a short reason')
        try:
            args = json.loads(request['arguments_json']) if type(request['arguments_json']) is str else None
        except ValueError:
            args = None
        if type(args) is not dict or len(json_bytes(args)) > MAX_REQUEST_BYTES:
            return self.reject(tool, 'arguments_json must be a JSON object within the size limit')
        if 'chart_id' in args:
            if args['chart_id'] != self.chart_id:
                self.trace.append({'event': 'chart_id_overridden', 'tool': tool})
            args.pop('chart_id')
        if tool == EXPAND:
            if set(args) != {'evidence_id'} or args['evidence_id'] not in self.evidence:
                return self.reject(tool, 'unknown evidence ID')
            self.expand.append(args['evidence_id'])
            return None
        if tool in TOOL_REGISTRY:
            changed = normalize(tool, args, self.allowed)
            if changed:
                self.trace.append({'event': 'arguments_normalized', 'tool': tool, 'keys': changed})
        key = json.dumps([tool, args], sort_keys=True)
        if key in self.seen:
            eid = self.seen[key]
            self.trace.append({'event': 'deduplicated', 'tool': tool, 'evidence_id': eid})
            self.notices.append({'tool': tool, 'evidence_id': eid,
                                 'note': f'You already requested this in an earlier round. Its result is evidence {eid} and its '
                                         'fact IDs are listed there. Do not request it again: use those facts.'})
            return eid
        if self.usage['tool_calls'] >= self.limits.tool_calls:
            return self.reject(tool, 'tool call limit reached')
        if tool == SEARCH_TOOL:
            eid = self.search(args, reason)
        else:
            self.usage['tool_calls'] += 1
            progress({'get_chart_facts': 'charts', 'get_dasha_periods': 'periods', 'get_transits': 'transits',
                      'evaluate_astrology_rules': 'rules'}.get(tool, 'charts'))
            before = self.clock()
            try:
                result = invoke_tool(self.user, tool, {**args, 'chart_id': self.chart_id})
                validate_payload(tool, result)
            except Exception:
                raise Stop('tool_failure') from None
            if (result.get('error') or {}).get('code') in ('chart_not_found', 'authentication_required'):
                raise Stop('chart_unavailable')
            if self.clock() - before >= self.limits.tool_seconds:
                raise Stop('tool_timeout')
            eid = self.record(tool, {**args, 'chart_id': self.chart_id}, reason, result)
            self.trace.append({'event': 'tool_result', 'tool': tool, 'evidence_id': eid, 'status': result['status'],
                               'reason': reason, 'error_code': (result.get('error') or {}).get('code')})
        if eid:
            self.seen[key] = eid
        return eid

    def search(self, args, reason):
        if not set(args) <= {'query', 'domain', 'purpose', 'result_count'} or type(args.get('query')) is not str:
            return self.reject(SEARCH_TOOL, 'a search needs a query written by you (and optionally domain, purpose, result_count)')
        if self.usage['searches'] >= self.limits.searches:
            self.trace.append({'event': 'search_ceiling', 'query': args['query'][:200], 'limit': self.limits.searches})
            return self.reject(SEARCH_TOOL, f'the {self.limits.searches}-search ceiling is reached; answer from the evidence you have')
        # The topic is trace metadata only; the model's own query is what is searched.
        domain = args.get('domain') or ((self.label or {}).get('domains') or ['consultation'])[0]
        arguments = {'chart_id': self.chart_id, 'topic': str(domain)[:80], 'concepts': [str(args.get('purpose') or args['query'])[:80]],
                     'query': args['query'], 'result_count': args.get('result_count', 3)}
        try:
            reserve = self.knowledge.reservation(arguments)
        except ToolFailure:
            return self.reject(SEARCH_TOOL, 'the query must be 1-200 bytes of plain text')
        except Exception:
            return self.reject(SEARCH_TOOL, 'invalid search arguments')
        self.usage['searches'] += 1
        self.usage['tool_calls'] += 1
        progress('sources')
        timeout = max(1, min(self.limits.tool_seconds, self.limits.seconds - self.elapsed(), 60))
        result = self.knowledge.search(arguments, token_budget=reserve, timeout=timeout)
        validate_knowledge(result)
        if (result.get('error') or {}).get('code') == 'chart_not_found':
            raise Stop('chart_unavailable')
        eid = self.record(SEARCH_TOOL, arguments, reason, result)
        passages = (result.get('data') or {}).get('passages', [])
        scores = [p['score'] for p in passages]
        known = [s for s in scores if s is not None]
        best = max(known) if known else None
        self.trace.append({'event': 'search', 'evidence_id': eid, 'query': arguments['query'], 'reason': reason,
                           'status': result['status'], 'error_code': (result.get('error') or {}).get('code'),
                           'scores': scores, 'best_score': best, 'low_score_heuristic': None if best is None else best < LOW_SCORE,
                           'passage_ids': [p['evidence_id'] for p in passages]})
        return eid

    # ── Model rounds ─────────────────────────────────────────────────────
    def payload(self, final_required):
        catalog = self.catalog()
        passages = self.passages()
        by_evidence = {}
        for atom in catalog.values():
            by_evidence.setdefault(atom['evidence_id'], []).append(atom['id'])
        digests = {}
        for eid, entry in self.evidence.items():
            result = entry['result']
            digest = {'tool': entry['tool'], 'arguments': {k: v for k, v in entry['arguments'].items() if k != 'chart_id'},
                      'status': result['status'], 'warnings': result.get('warnings', [])[:4],
                      'error': result.get('error'), 'fact_ids': by_evidence.get(eid, [])}
            if result.get('error') and entry['tool'] in self.allowed:
                # Corrective feedback: the exact allowed values, so a retry can succeed.
                digest['fix'] = {'allowed_values': {k: list(v) for k, v in self.allowed[entry['tool']].items()},
                                 'example_arguments_json': json.dumps(examples(self.today)[entry['tool']])}
            if entry['tool'] == SEARCH_TOOL:
                event = next((t for t in self.trace if t.get('event') == 'search' and t.get('evidence_id') == eid), {})
                digest.update(best_score=event.get('best_score'), low_score_heuristic=event.get('low_score_heuristic'),
                              passage_ids=event.get('passage_ids', []), your_judgement=self.judgements.get(eid))
            digests[eid] = digest
        payload = {
            'protocol': 'astrogpt-general-agent-v1', 'question': self.question, 'today': self.today.isoformat(),
            'default_window': {'start': self.today.isoformat(), 'end': (self.today + timedelta(days=365)).isoformat(),
                               'note': 'Use only when the user gives no window, and say that it was used.'},
            'rounds_remaining': self.limits.rounds - self.usage['rounds'],
            'searches_remaining': self.limits.searches - self.usage['searches'],
            'final_required': final_required, 'tools': self.menu,
            'evidence': digests,
            'facts': {fid: atom['text'] for fid, atom in catalog.items()},
            'passages': {k: {'source': title_of(p['citation']), 'chapter': p['citation'].get('chapter'), 'page': p['citation'].get('page'),
                             'score': p['score'], 'snippet': p['snippet'], 'trust': 'untrusted_source_text'} for k, p in passages.items()},
        }
        if self.label is None:
            payload['label_menu'] = self.profile.catalog()
        else:
            payload['label'] = self.label
            payload['guidance'] = self.guidance
            factors = self.profile.core_factors(self.label)
            payload['core_factors'] = [{'factor': fid, 'domain': d, 'text': t} for fid, d, t in factors]
            if factors:
                # Copy into final.coverage: keep each factor ID, set status, and list E IDs (or a note if unavailable).
                payload['coverage_template'] = [{'factor': fid, 'status': 'examined', 'evidence_ids': [], 'note': ''} for fid, _, _ in factors]
        if self.expand:
            payload['expanded'] = {eid: json.dumps(self.evidence[eid]['result'], ensure_ascii=False)[:self.limits.expand_bytes]
                                   for eid in dict.fromkeys(self.expand)}
        if self.rejected:
            payload['rejected_requests'] = self.rejected[-8:]
        if self.notices:
            payload['already_fetched'] = self.notices[-8:]
        if self.must_answer:
            # The reply format now requires final; requests sent this round are not run.
            payload['answer_only'] = True
        if self.repair:
            payload['repair'] = self.repair
        if self.context is not None:
            payload['consultation_context'] = {'trust': 'untrusted memory; never a chart fact', **self.context}
        return payload

    def sized(self, payload, provider):
        """Count the round with tiktoken; compact once, then refuse before any paid call (M3-AC16)."""
        tokens = provider.count_tokens(payload)
        if tokens > self.limits.round_input_tokens:
            payload.pop('expanded', None)
            for passage in payload['passages'].values():
                passage['snippet'] = passage['snippet'][:400]
            tokens = provider.count_tokens(payload)
            self.trace.append({'event': 'payload_compacted', 'input_tokens': tokens})
        if tokens > self.limits.round_input_tokens:
            raise Stop('round_input_limit')
        return tokens

    def model_round(self, provider):
        self.check_time()
        if self.usage['rounds'] >= self.limits.rounds:
            raise Stop('model_round_limit')
        last = self.limits.rounds - self.usage['rounds'] <= 1
        self.must_answer = self.label is not None and (last or self.stalled)
        final_required = last or self.stalled or self.repair is not None
        payload = self.payload(final_required)
        counted = self.sized(payload, provider)
        self.usage['rounds'] += 1
        self.usage['round_input_tokens'].append(counted)
        self.expand, self.rejected, self.notices = [], [], []
        started = self.clock()
        progress('answer')
        try:
            response = provider.complete(deepcopy(payload), max_output_tokens=self.limits.output_tokens,
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
        if type(response) is not dict or set(response) != {'reply', 'input_tokens', 'output_tokens'}:
            raise Stop('invalid_provider_response')
        for key in ('input_tokens', 'output_tokens'):
            if type(response[key]) is not int or response[key] < 0:
                raise Stop('invalid_provider_usage')
            self.usage[key] += response[key]
        if response['output_tokens'] > self.limits.output_tokens:
            raise Stop('provider_output_token_limit')
        self.usage['round_latency_ms'].append(latency)
        reply = response['reply']
        if type(reply) is not dict or set(reply) != {'label', 'requests', 'search_judgements', 'final'} or len(json_bytes(reply)) > 65536:
            raise Stop('invalid_provider_response')
        self.trace.append({'event': 'round', 'round': self.usage['rounds'], 'counted_input_tokens': counted,
                           'provider_input_tokens': response['input_tokens'], 'provider_output_tokens': response['output_tokens'],
                           'latency_ms': latency, 'requests': len(reply['requests'] or []), 'final': reply['final'] is not None,
                           'repair': self.repair is not None})
        return reply

    def apply_label(self, label):
        try:
            self.label = self.profile.validate_label(label)
        except ProfileError as exc:
            self.trace.append({'event': 'invalid_label', 'reason': str(exc)[:200]})
            raise Stop('invalid_label') from None
        self.guidance = self.profile.guidance_for(self.label)
        self.trace.append({'event': 'label', **self.label, 'profile_revision': self.profile.data['revision'],
                           'profile_fingerprint': self.profile.fingerprint})

    def apply_judgements(self, judgements):
        if type(judgements) is not list:
            raise Stop('invalid_provider_response')
        passages = self.passages()
        searches = [e for e, v in self.evidence.items() if v['tool'] == SEARCH_TOOL]
        for item in judgements[:8]:
            if type(item) is not dict or item.get('judgement') not in ('relevant', 'partly_relevant', 'not_relevant'):
                self.reject(SEARCH_TOOL, 'a search judgement needs evidence_id (a search E ID), judgement '
                                         '(relevant, partly_relevant or not_relevant), passage_ids and a note')
                continue
            eid = item.get('evidence_id')
            if eid in passages:                           # a passage ID given instead of its search's E ID
                eid = passages[eid]['search_evidence_id']
            if eid not in searches:
                # Nothing to judge (for example, no search has run yet): ignore rather than penalize.
                self.trace.append({'event': 'search_judgement_ignored', 'reason': 'no matching search'})
                continue
            ids = [p for p in item.get('passage_ids') or [] if type(p) is str and p in passages]
            self.judgements[eid] = item['judgement']
            self.trace.append({'event': 'search_judgement', 'evidence_id': eid, 'judgement': item['judgement'],
                               'passage_ids': ids, 'note': str(item.get('note') or '')[:300]})

    def investigate(self, provider):
        while True:
            reply = self.model_round(provider)
            labelled_now = False
            if self.label is None:
                if reply['label'] is None:
                    raise Stop('missing_label')
                self.apply_label(reply['label'])
                labelled_now = True
                if self.label['question_type'] == 'out_of_scope':
                    return 'out_of_scope'
            self.apply_judgements(reply['search_judgements'])
            pending = type(reply['requests']) is list and len(reply['requests']) > 0
            if self.must_answer and reply['final'] is None:
                raise Stop('missing_final')
            if reply['final'] is not None and pending and not self.must_answer and self.usage['rounds'] < self.limits.rounds:
                # A draft written before its own requests ran cannot cite their results: run the
                # requests and set the draft aside (it is neither validated nor counted as a repair).
                self.trace.append({'event': 'premature_final_set_aside', 'requests': len(reply['requests'])})
            elif reply['final'] is not None:
                self.final, grounded = ground_final(reply['final'], self.catalog(), self.evidence)
                if grounded:
                    self.trace.append({'event': 'auto_grounded', 'sentences': grounded})
                self.final_validation = self.validate(self.final)
                self.trace.append({'event': 'validation', 'passed': self.final_validation['passed'],
                                   'issues': self.final_validation['issues'][:12],
                                   'missing': self.final_validation['missing_sections'], 'repair_round': self.repair is not None})
                if self.final_validation['passed']:
                    return 'published'
                if self.repaired or self.usage['rounds'] >= self.limits.rounds:
                    raise Stop('validation_failed')
                self.repaired = True
                factors = {fid: text for fid, _, text in self.profile.core_factors(self.label)}
                uncovered = [i.split(' ', 1)[1] for i in self.final_validation['issues'] if i.startswith('core_factor_')]
                self.repair = {'issues': self.final_validation['issues'] + ['missing ' + m for m in self.final_validation['missing_sections']],
                               'failing_sentences': self.final_validation['unsupported_claims'],
                               'core_factors_to_fix': {f: factors.get(f, '') for f in uncovered},
                               'how_to_fix': ('End each failing sentence with the fact ID whose text contains every value it states, '
                                              'e.g. "Your 10th lord Venus is in the 12th house [F0123456789abcdef]." If no fact has the '
                                              'value, delete the value or request the tool that calculates it this round. Copy '
                                              'coverage_template into coverage and give E IDs for each factor, or status '
                                              'unavailable with a note.'),
                               'instruction': self.final_validation['repair_instruction'], 'previous_final': self.final}
                self.trace.append({'event': 'repair_requested'})
                continue
            requests = reply['requests']
            if self.repair is not None and not requests:
                raise Stop('validation_failed')
            if type(requests) is not list:
                raise Stop('invalid_provider_response')
            if not requests:
                if labelled_now:
                    # Label-only first round: the model receives its guidance next round.
                    self.trace.append({'event': 'label_only_round'})
                    continue
                raise Stop('empty_round')
            if len(requests) > self.limits.requests_per_round:
                self.reject('batch', f'only the first {self.limits.requests_per_round} requests in a round are run')
            before, repeats = len(self.evidence), len(self.notices)
            for request in requests[:self.limits.requests_per_round]:
                self.execute(request)
            if len(self.evidence) == before and len(self.notices) > repeats:
                # Nothing new, only repeats: the next round must answer from the evidence already held.
                self.stalled = True
                self.trace.append({'event': 'stalled_round', 'repeats': len(self.notices) - repeats})

    def conflicts_present(self):
        for entry in self.evidence.values():
            if entry['tool'] == 'evaluate_astrology_rules':
                conflicts = (entry['result'].get('data') or {}).get('conflicts') or {}
                if conflicts.get('has_contradictions') or conflicts.get('issues'):
                    return True
        return False

    def validate(self, final):
        return validate_final(final, label=self.label, profile=self.profile, catalog=self.catalog(), evidence=self.evidence,
                              passages=self.passages(), conflicts_present=self.conflicts_present())

    # ── Publication ──────────────────────────────────────────────────────
    def states(self, cited=()):
        searches = [e for e in self.evidence.values() if e['tool'] == SEARCH_TOOL]
        failed = [e for e in searches if e['result']['status'] == 'error']
        succeeded = [e for e in searches if e['result']['status'] in ('ok', 'partial')]
        states, calculations = [], []
        if failed:
            states.append('retrieval_failed')
        if succeeded and not any(c.startswith('K') for c in cited):
            states.append('no_source_support')
        for entry in self.evidence.values():
            if entry['result']['status'] == 'unsupported':
                calculations.append({'source': 'tool', 'tool': entry['tool'], 'message': entry['result']['error']['message']})
        declared = self.final.get('unavailable_calculations') if type(self.final) is dict else None
        for key in declared if type(declared) is list else []:
            if type(key) is str and key in self.profile.unavailable_ids:
                calculations.append({'source': 'declared', 'id': key, 'name': self.profile.unavailable_name(key),
                                     'declined_by_policy': self.profile.declined_by_policy(key)})
        if calculations:
            states.append('calculation_unavailable')
        return states, calculations, bool(succeeded), bool(failed)

    def disclosures(self, states, calculations, succeeded, failed):
        lines = []
        if 'retrieval_failed' in states:
            lines.append(DISCLOSURES['retrieval_partly_failed' if succeeded else 'retrieval_failed'])
        if 'no_source_support' in states:
            lines.append(DISCLOSURES['no_source_support'])
        if self.label and self.label['question_type'] in COVERAGE_TYPES and not succeeded and not failed:
            lines.append(DISCLOSURES['not_searched'])
        seen = set()
        for item in calculations:
            if item['source'] == 'declared':
                text = (f"This needs {item['name']}, which the app does not calculate and declines by policy." if item['declined_by_policy']
                        else f"This needs {item['name']}, which the app does not yet calculate.")
            else:
                text = f"This needs a calculation the app does not yet provide ({item['tool']}): {item['message']}"
            if text not in seen:
                seen.add(text)
                lines.append(text)
        if self.label:
            if self.label['question_type'] in TIMING_TYPES:
                lines.append(MUHURTA)
            if self.label['question_type'] in COVERAGE_TYPES:
                lines.append(DISCLOSURES['agreement'])
            if self.profile.has_basis_note(self.label):
                lines.append(DISCLOSURES['basis'])
            lines.extend(self.profile.disclosures(self.label))
        return list(dict.fromkeys(lines))

    def render(self, final):
        catalog, passages = self.catalog(), self.passages()
        order = []

        def replace(match):
            out = []
            for tag in (t.strip() for t in match.group(1).split(',')):
                if tag.startswith('F'):
                    if tag not in order:
                        order.append(tag)
                    out.append(f'[{order.index(tag) + 1}]')
                else:
                    citation = passages[tag]['citation']
                    detail = ', '.join(f'{k} {citation[k]}' for k in ('chapter', 'page') if citation.get(k))
                    out.append(f"(source: {title_of(citation)}{', ' + detail if detail else ''})")
            return ' '.join(out)

        def clean(text):
            return TAG.sub(replace, text).replace(' .', '.').strip()

        blocks = [clean(final['direct_answer'])]
        if final['body'].strip():
            blocks.append(clean(final['body']))
        if final['conflicts']:
            blocks.append('Conflicting indications: ' + ' '.join(clean(c) for c in final['conflicts']))
        blocks.append(f"Evidence strength: {final['evidence_strength']['label']}. {clean(final['evidence_strength']['reason'])}")
        cited = {t for text in (final['direct_answer'], final['body'], final['evidence_strength']['reason'], *final['conflicts']) for t in tags(text)}
        states, calculations, succeeded, failed = self.states(cited)
        notes = self.disclosures(states, calculations, succeeded, failed)
        if notes:
            blocks.append(' '.join(notes))
        if order:
            blocks.append('Calculated facts referenced: ' + ' '.join(f'[{i + 1}] {catalog[f]["text"]}' for i, f in enumerate(order)))
        return '\n\n'.join(blocks), [catalog[f] for f in order], states, calculations

    def fallback(self, reason):
        """Deterministic evidence report: server wording only, marked partial and unbilled (M3-AC18)."""
        catalog = self.catalog()
        states, calculations, succeeded, failed = self.states()
        preferred = ('lord', 'position', 'dasha', 'karaka', 'pada', 'transit', 'aspect', 'rule', 'conflict', 'counted_sign', 'karakamsha')
        atoms = sorted((a for a in catalog.values() if a['kind'] in preferred), key=lambda a: preferred.index(a['kind']))[:12]
        blocks = ['I could not complete a verified written interpretation for this question, so here is the calculated '
                  'evidence that was gathered, without interpretation.']
        if atoms:
            blocks.append(' '.join(a['text'] for a in atoms))
        else:
            blocks.append('No calculated evidence was gathered before the consultation stopped.')
        blocks.append('Evidence strength: limited, because no interpretation could be verified.')
        notes = self.disclosures(states, calculations, succeeded, failed)
        if notes:
            blocks.append(' '.join(notes))
        self.trace.append({'event': 'fallback', 'reason': reason})
        return '\n\n'.join(blocks), atoms, states, calculations

    def shortcut(self, query):
        tool, args = factual_arguments(query, self.today)
        result = invoke_tool(self.user, tool, {**args, 'chart_id': self.chart_id})
        validate_payload(tool, result)
        if (result.get('error') or {}).get('code') in ('chart_not_found', 'authentication_required'):
            raise Stop('chart_unavailable')
        eid = self.record(tool, {**args, 'chart_id': self.chart_id}, 'Deterministic factual lookup; no model call.', result)
        self.trace.append({'event': 'factual_shortcut', 'kind': query.kind, 'tool': tool, 'evidence_id': eid, 'status': result['status']})
        atoms = select_atoms(query, self.catalog())
        if not atoms:
            text = 'That value is not available in the stored chart; nothing was calculated or inferred.'
            if result.get('error'):
                text += ' ' + result['error']['message']
            return text, [], 'partial'
        return ' '.join(a['text'] for a in atoms), atoms, 'ok' if result['status'] == 'ok' else 'partial'

    def run(self):
        answer, atoms, states, calculations, status = '', [], [], [], 'error'
        try:
            if not self.owned():
                raise Stop('chart_unavailable')
            self.context = validate_context(self.context, self.chart_id)
            if self.context is not None:
                reject_chart_change(self.question)
            if type(self.question) is not str or not self.question.strip() or len(self.question.encode('utf-8')) > 4096:
                raise ScopeError('Please provide a question of at most 4096 UTF-8 bytes.')
            query = match_factual(self.question)
            if query is not None:
                answer, atoms, status = self.shortcut(query)
            else:
                from .general_provider import GeneralProvider
                provider = self.provider or GeneralProvider()
                self.menu = tool_menu(self.today)
                outcome = self.investigate(provider)
                if outcome == 'out_of_scope':
                    answer, status = OUT_OF_SCOPE, 'partial'
                    self.stop_reason = 'out_of_scope'
                else:
                    answer, atoms, states, calculations = self.render(self.final)
                    status = 'partial' if 'retrieval_failed' in states else 'ok'
        except ScopeError as exc:
            self.stop_reason = 'scope_clarification'
            answer = str(exc)
            self.trace.append({'event': 'clarification', 'reason': answer})
        except Stop as exc:
            self.stop_reason = str(exc)
        if self.stop_reason not in ('complete', 'scope_clarification', 'out_of_scope') and self.stop_reason != 'chart_unavailable':
            answer, atoms, states, calculations = self.fallback(self.stop_reason)
            status = 'partial'
        # Never publish retained evidence if ownership changed during the request (M3-AC19).
        if self.stop_reason == 'chart_unavailable' or not self.owned():
            self.stop_reason = 'chart_unavailable'
            self.evidence.clear()
            answer, atoms, states, calculations, status = 'Chart is unavailable.', [], [], [], 'error'
        self.trace.append({'event': 'stop', 'reason': self.stop_reason, 'status': status, 'non_answer_states': states,
                           'elapsed_ms': int(self.elapsed() * 1000)})
        progress('validation')
        published_by = 'model' if self.final_validation and self.final_validation['passed'] and self.stop_reason == 'complete' else 'server'
        validation = {'passed': status != 'error', 'score': 100 if status != 'error' else 0, 'issues': [], 'missing_sections': [],
                      'generic_phrases_detected': [], 'unsupported_claims': [], 'repair_instruction': '',
                      'stage': 'prose_validation' if published_by == 'model' else 'deterministic_server_text'}
        return {'status': status, 'answer': answer, 'validation': validation, 'draft_validation': self.final_validation,
                'claims': [{'id': a['id'], 'kind': a['kind'], 'text': a['text']} for a in atoms],
                'model': getattr(self.provider, 'name', 'openai-responses-general') if self.usage['rounds'] else 'deterministic',
                'prompt_tokens': self.usage['input_tokens'], 'completion_tokens': self.usage['output_tokens'],
                'evidence': self.evidence, 'trace': self.trace, 'usage': self.usage, 'stop_reason': self.stop_reason,
                'label': self.label, 'non_answer_states': states, 'unavailable_calculations': calculations,
                'pipeline': 'general_agent', 'published_by': published_by}


def run_general_consultation(user, chart_id, question, *, today=None, provider=None, limits=None, knowledge_adapter=None,
                             consultation_context=None, profile=None):
    from django.utils import timezone
    return GeneralConsultation(user, chart_id, question, today=today or timezone.localdate(), provider=provider, limits=limits,
                               knowledge_adapter=knowledge_adapter, consultation_context=consultation_context, profile=profile).run()
