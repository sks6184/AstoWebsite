"""M3 offline tests: general agent, profile, wrappers, prose validation, routing and policy.

Offline only: a scripted provider stands in for the model, a synthetic retrieval adapter stands in for
the vector store, and the network and OpenAI client are blocked. Charts are the synthetic sample chart
and the synthetic R1-R5 fixtures; passages are synthetic text written for these tests (no book text).
These tests show the pipeline's behaviour, not astrological correctness or live model capability.
"""
from copy import deepcopy
from datetime import date, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.usage_policy import BudgetExceeded, policy_for
from astrology.agent.factual import match_factual
from astrology.agent.general import AgentLimits, GeneralConsultation, run_general_consultation
from astrology.agent.general_provider import GeneralProvider, reply_schema
from astrology.calculations import jaimini as jaimini_calc
from astrology.calculations.counted_signs import counted_sign
from astrology.methodology.profile import ProfileError, load_profile, validate_profile
from astrology.rag.knowledge_contracts import RetrievalBatch
from astrology.synthesis.fact_catalog import build_catalog
from astrology.tests import sample_chart_data
from astrology.tools import invoke_tool
from astrology.validation.prose_validator import check_prose, copied_runs
from charts.models import SavedChart
from charts.vedic_utils import PLANET_ASPECTS, SIGN_LORDS, aspected_houses
from chat.agent_service import agent_route, generate_question_answer
from chat.models import Conversation

BASE = Path(__file__).resolve().parent.parent
TODAY = date(2026, 11, 7)
WINDOW = {'start_date': TODAY.isoformat(), 'end_date': (TODAY + timedelta(days=365)).isoformat()}
TRACE_DIR = BASE / 'docs' / 'claude_migration' / 'm3_traces'
LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'm3-tests'}}
SYNTHETIC = ('Synthetic test passage written for the AstroGPT offline suite. It discusses how the relevant houses, '
             'their lords and the period rulers are weighed together, and it contains no text from any book. ')


# ── Scripted model and synthetic retrieval ───────────────────────────────────
def req(tool, reason='Examine this factor for the labelled question.', **arguments):
    return {'tool': tool, 'arguments_json': json.dumps(arguments), 'reason': reason}


def reply(label=None, requests=(), judgements=(), final=None):
    return {'label': label, 'requests': list(requests), 'search_judgements': list(judgements), 'final': final}


def label(qtype, *domains, events=()):
    return {'question_type': qtype, 'domains': list(domains), 'events': list(events)}


def fact(payload, kind=None, contains='', where=None):
    for fid, text in payload['facts'].items():
        if contains in text and (where is None or where(text)):
            if kind is None or kind_of(payload, fid) == kind:
                return fid
    raise AssertionError(f'no fact containing {contains!r}')


def kind_of(payload, fid):
    for digest in payload['evidence'].values():
        if fid in digest['fact_ids']:
            return digest['tool']
    return None


def tagged(payload, fid):
    """The server's own fact text with its ID on every sentence (always verifiable)."""
    from astrology.validation.prose_validator import sentences
    return ' '.join(s.rstrip('.') + f' [{fid}].' for s in sentences(payload['facts'][fid]))


def coverage(payload, evidence_id=None):
    ok = [e for e, d in payload['evidence'].items() if d['status'] in ('ok', 'partial')]
    return [{'factor': c['factor'], 'status': 'examined', 'evidence_ids': [evidence_id or ok[0]], 'note': ''}
            for c in payload.get('core_factors', [])]


def final(payload, direct='Here is what the calculated evidence shows for your question, read as indicators rather than a verdict.',
          body=None, conflicts=None, strength='moderate', reason='Several calculated factors were examined and compared for this question.',
          cover=None, unavailable=(), no_source=False, sources=()):
    if body is None:
        lords = [f for f, t in payload['facts'].items() if t.startswith('Your D1 house')][:2]
        body = ' '.join(tagged(payload, f) for f in lords) or 'The question was answered from the retrieved explanation.'
    for k in sources:
        body += f' A retrieved source discusses this theme in its own terms [{k}].'
    if conflicts is None:
        conflicts = [tagged(payload, f) for f, t in payload['facts'].items() if t.startswith('The deterministic conflict')][:1]
    return {'direct_answer': direct, 'body': body, 'conflicts': conflicts,
            'evidence_strength': {'label': strength, 'reason': reason},
            'coverage': coverage(payload) if cover is None else cover,
            'unavailable_calculations': list(unavailable), 'no_source_support': no_source}


class Script:
    """Scripted provider: each step is a reply dict or a function of the round payload."""
    name = 'scripted-offline'

    def __init__(self, *steps):
        self.steps = list(steps)
        self.payloads = []

    def count_tokens(self, payload):
        return GeneralProvider().count_tokens(payload)   # real tiktoken count (M3-AC16)

    def complete(self, payload, *, max_output_tokens, timeout):
        self.payloads.append(deepcopy(payload))
        if not self.steps:
            raise AssertionError('scripted provider has no further steps')
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        value = step(payload) if callable(step) else step
        return {'reply': value, 'input_tokens': 1200, 'output_tokens': 300}


class NoModel:
    name = 'must-not-run'

    def count_tokens(self, payload):
        raise AssertionError('no model round expected')

    def complete(self, *args, **kwargs):
        raise AssertionError('no model call expected')


class FakeLibrary:
    """Synthetic direct-search adapter. ``plan`` maps a query substring to (score, filename) rows."""
    name = 'synthetic-direct'
    configured = True
    fingerprint = 'synthetic-library-v1'

    def __init__(self, plan=None, fail=None):
        self.plan = plan or {}
        self.fail = fail
        self.queries = []

    def retrieve(self, query, request, *, timeout):
        self.queries.append(query)
        if self.fail:
            raise self.fail
        rows = next((rows for key, rows in self.plan.items() if key.casefold() in query.casefold()),
                    [(0.81, 'Synthetic_Parashari_Notes.pdf')])
        results = [{'text': SYNTHETIC + f'Synthetic note {i} for {query[:40]}.', 'filename': name, 'file_id': f'file-syn-{i}',
                    'score': score, 'attributes': {'chapter': str(i + 1)}} for i, (score, name) in enumerate(rows)]
        return RetrievalBatch(results, [query], 0, 0)


def first_search(payload):
    return next(e for e, d in payload['evidence'].items() if d['tool'] == 'search_astrology_knowledge')


def passage_ids(payload, eid=None):
    eid = eid or first_search(payload)
    return payload['evidence'][eid]['passage_ids']


def vargas_of(profile, domain):
    from astrology.methodology.profile import _vargas
    return _vargas(profile.entry(domain)['vargas'])


def domain_requests(profile, domains, timing=True):
    """Test data standing in for the model's choices (the server prescribes none)."""
    charts = sorted({v for d in domains for v in vargas_of(profile, d)})
    requests = [req('get_chart_facts', charts=charts, include_yogas=True),
                req('get_jaimini_facts'),
                req('evaluate_astrology_rules', category=profile.entry(domains[0])['rule_categories'][0], as_of=TODAY.isoformat())]
    if timing:
        requests += [req('get_dasha_periods', system='vimshottari', **WINDOW),
                     req('get_transits', planets=['Ju', 'Sa'], **WINDOW)]
    return requests


def search_query(profile, domain):
    terms = [v['term'] for v in profile.entry(domain)['vocabulary'][:3]]
    return ' '.join(terms) + ' results in the sub-period'


# ── Test case ────────────────────────────────────────────────────────────────
@override_settings(CACHES=LOCMEM)
class M3Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='m3-pilot', email='pilot@example.test')
        cls.other = User.objects.create_user(username='m3-other', email='other@example.test')
        cls.chart = SavedChart.objects.create(user=cls.owner, name='Synthetic M3 chart', birth_date=date(1990, 5, 17),
            birth_time='10:30:00', birth_place='Synthetic fixture', latitude='28.613900', longitude='77.209000',
            timezone='Asia/Kolkata', chart_data=sample_chart_data())
        cls.profile = load_profile()

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        for target in ('socket.socket.connect', 'openai.OpenAI'):
            block = patch(target, side_effect=AssertionError('Live network/provider forbidden in M3 tests'))
            block.start()
            self.addCleanup(block.stop)
        self.library = FakeLibrary()

    def run_agent(self, question, provider, **kwargs):
        kwargs.setdefault('knowledge_adapter', self.library)
        return run_general_consultation(self.owner, self.chart.pk, question, today=TODAY, provider=provider, **kwargs)

    def standard(self, question, lab, *, requests=None, query=None, finisher=None):
        """Round 1 label + evidence; round 2 one search; round 3 final from the server's own facts."""
        domains = lab['domains']
        timing = lab['question_type'] in ('predictive_timing', 'comparative_decision')
        steps = [reply(lab, requests if requests is not None else domain_requests(self.profile, domains, timing)),
                 reply(requests=[req('search_astrology_knowledge', query=query or search_query(self.profile, domains[0]),
                                     domain=domains[0], reason='Find classical explanation in the books\' terms.')]),
                 lambda p: reply(judgements=[{'evidence_id': first_search(p), 'judgement': 'relevant',
                                              'passage_ids': passage_ids(p)[:1], 'note': 'Discusses the labelled houses.'}],
                                 final=(finisher or (lambda p: final(p, sources=passage_ids(p)[:1])))(p))]
        provider = Script(*steps)
        return self.run_agent(question, provider), provider


def save_trace(name, result, provider=None):
    """Committed synthetic traces (M3 scope item 10). Written only when ASTROGPT_WRITE_M3_TRACES=1."""
    if os.environ.get('ASTROGPT_WRITE_M3_TRACES') != '1':
        return
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    value = {'name': name, 'synthetic': True, 'provider': 'scripted offline (no model call)',
             'status': result['status'], 'stop_reason': result['stop_reason'], 'label': result['label'],
             'non_answer_states': result['non_answer_states'], 'published_by': result['published_by'],
             'answer': result['answer'], 'usage': result['usage'],
             'evidence': {e: {'tool': v['tool'], 'arguments': {k: a for k, a in v['arguments'].items() if k != 'chart_id'},
                              'status': v['result']['status']} for e, v in result['evidence'].items()},
             'trace': result['trace'], 'draft_validation': result['draft_validation']}
    (TRACE_DIR / f'{name}.json').write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')


class M3ProfileTests(M3Base):
    def test_ac5_profile_schema_bounds_and_research_annex_excluded(self):
        data = self.profile.data
        self.assertEqual(len(self.profile.primary), 12)
        self.assertTrue(all(len(self.profile.entry(d)['vocabulary']) <= 8 for d in self.profile.primary))
        total = len(data['common_vocabulary']) + sum(len(self.profile.entry(d)['vocabulary']) for d in self.profile.primary)
        self.assertLessEqual(total, 100)
        every = label('predictive_timing', 'career', 'marriage', 'health', events=['career:promotion'])
        guidance = json.dumps(self.profile.guidance_for(self.profile.validate_label(every)))
        self.assertNotIn('research_annex', guidance)
        self.assertNotIn('KP 1-5-9', guidance)
        broken = deepcopy(data)
        broken['domains']['career']['core_factors'].append('First call get_chart_facts, then call get_transits')
        with self.assertRaises(ProfileError):
            validate_profile(broken)
        broken = deepcopy(data)
        broken['domains']['marriage']['core_factors'].append('Venus in the 7th will bring an early marriage')
        with self.assertRaises(ProfileError):
            validate_profile(broken)
        broken = deepcopy(data)
        broken['domains']['wealth']['vocabulary'] = [{'term': f't{i}'} for i in range(9)]
        with self.assertRaises(ProfileError):
            validate_profile(broken)

    def test_ac3_labels_are_closed_and_distinction_pairs_differ(self):
        for bad in (label('natal_assessment', 'romance'), label('natal_assessment', 'career', 'marriage', 'health', 'wealth'),
                    label('guess', 'career'), label('natal_assessment', 'career', events=['marriage:remarriage']),
                    label('out_of_scope', 'career')):
            with self.assertRaises(ProfileError):
                self.profile.validate_label(bad)
        rel = self.profile.guidance_for(self.profile.validate_label(label('natal_assessment', 'relationships')))
        mar = self.profile.guidance_for(self.profile.validate_label(label('natal_assessment', 'marriage')))
        self.assertNotEqual(rel['domains']['relationships']['core_factors'], mar['domains']['marriage']['core_factors'])
        self.assertNotIn('marriage', rel['domains'])
        kids = self.profile.core_factors(label('natal_assessment', 'children'))
        conception = self.profile.core_factors(label('natal_assessment', 'conception_childbirth'))
        self.assertNotEqual([t for _, _, t in kids], [t for _, _, t in conception])
        # The strict reply schema enumerates the same closed domain list.
        enum = reply_schema()['schema']['properties']['label']['anyOf'][0]['properties']['domains']['items']['enum']
        self.assertEqual(set(enum), set(self.profile.domain_ids))

    def test_ac3_locked_labelled_set_exercises_every_label(self):
        data = json.loads((BASE / 'astrology/evaluation/fixtures/m3_labelled_questions_v1.json').read_text(encoding='utf-8'))
        questions = data['questions']
        self.assertGreaterEqual(len(questions), 44)
        by_domain = {d: 0 for d in self.profile.primary}
        for q in questions:
            normalized = self.profile.validate_label({'question_type': q['type'], 'domains': q['domains'], 'events': q['events']})
            if len(q['domains']) == 1:
                by_domain[q['domains'][0]] += 1
        self.assertTrue(all(n >= 3 for n in by_domain.values()), by_domain)
        self.assertGreaterEqual(sum(len(q['domains']) > 1 for q in questions), 6)
        self.assertGreaterEqual(sum(q['type'] == 'out_of_scope' for q in questions), 4)
        ids = {q['id']: q for q in questions}
        self.assertGreaterEqual(len(data['distinction_pairs']), 4)
        for pair in data['distinction_pairs']:
            a, b = (ids[x] for x in pair['pair'])
            self.assertNotEqual(a['domains'], b['domains'])
        # A scripted provider labels every question; the server accepts each label and only that label.
        for q in questions[:12] + [q for q in questions if q['type'] == 'out_of_scope']:
            lab = {'question_type': q['type'], 'domains': q['domains'], 'events': q['events']}
            provider = Script(reply(lab, [req('get_chart_facts', charts=['d1'])]), lambda p: reply(final=final(p)))
            result = self.run_agent(q['q'], provider)
            self.assertEqual(result['label']['domains'], q['domains'], q['id'])

    def test_ac5_no_domain_branches_or_synonym_tables_in_python(self):
        sources = [BASE / f for f in ('astrology/agent/general.py', 'astrology/agent/general_provider.py', 'astrology/agent/factual.py',
                                      'astrology/methodology/profile.py', 'astrology/validation/prose_validator.py')]
        for path in sources:
            text = path.read_text(encoding='utf-8')
            for domain in self.profile.domain_ids:
                self.assertNotRegex(text, r"""['"]%s['"]""" % domain, f'{path.name} branches on {domain}')
            self.assertNotIn('minimal_evidence', text)
            self.assertNotRegex(text.casefold(), r'synonym\w*\s*=\s*\{')

    def test_ac4_no_career_boundary_in_general_path(self):
        for path in ('astrology/agent/general.py', 'chat/agent_service.py'):
            text = (BASE / path).read_text(encoding='utf-8')
            self.assertNotIn('supports career/business', text)
            self.assertNotIn('ScopeError(\'P3', text)


class M3WrapperParityTests(M3Base):
    """M3-AC6 on the synthetic R1-R5 charts: wrappers equal the existing calculations."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from astrology.test_m1 import fixture_charts
        cls.fixtures = {}
        for key, (spec, data) in fixture_charts().items():
            cls.fixtures[key] = SavedChart.objects.create(user=cls.owner, name=f'Synthetic {key}', birth_date=date.fromisoformat(spec['birth_date']),
                birth_time=spec['birth_time'], birth_place='Synthetic', latitude=str(spec['latitude']), longitude=str(spec['longitude']),
                timezone=spec['timezone'], chart_data=data)

    def test_ac6_jaimini_yogas_lords_counted_signs_and_aspects(self):
        for key, chart in self.fixtures.items():
            data = chart.chart_data
            jai = invoke_tool(self.owner, 'get_jaimini_facts', {'chart_id': chart.pk})['data']
            self.assertEqual(jai['karakas'], json.loads(json.dumps(jaimini_calc.build_karakas(data))), key)
            self.assertEqual(len(jai['karakas']['karakas']), 7)
            self.assertNotIn('Ra', {k['code'] for k in jai['karakas']['karakas'].values()})
            self.assertEqual(jai['padas'], json.loads(json.dumps(jaimini_calc.build_padas(data))))
            self.assertEqual(len(jai['padas']['all_padas']), 12)
            self.assertEqual(jai['karakamsha'], json.loads(json.dumps(jaimini_calc.build_karakamsha(data))))
            self.assertEqual(jai['jaimini_yogas'], json.loads(json.dumps(jaimini_calc.build_jaimini_yogas(data))))
            self.assertTrue(any('planetary_padas' in u for u in jai['unavailable']))
            facts = invoke_tool(self.owner, 'get_chart_facts', {'chart_id': chart.pk, 'charts': ['d1'], 'include_yogas': True})
            stored = [{k: y.get(k) for k in ('name', 'category', 'strength', 'evidence', 'meaning')} for y in data.get('yogas', [])]
            self.assertEqual(facts['data']['yogas'], json.loads(json.dumps(stored)))
            # All 12 house lords in the full catalog, checked against an independent sign-lord count.
            evidence = {'E1': {'tool': 'get_chart_facts', 'arguments': {}, 'reason': 'x', 'result': facts}}
            lords = {json.loads(a['value'])['house']: json.loads(a['value'])['lord']
                     for a in build_catalog(evidence, full=True).values() if a['kind'] == 'lord'}
            lagna = data['ascendant']['sign_number']
            self.assertEqual(lords, {h: SIGN_LORDS[(lagna + h - 2) % 12 + 1] for h in range(1, 13)}, key)
            for reference in ('arudha_lagna', 'upapada_lagna', 'karakamsha'):
                for count in (1, 2, 8, 12):
                    result = invoke_tool(self.owner, 'get_counted_sign', {'chart_id': chart.pk, 'reference': reference, 'count': count})['data']['result']
                    start = result['reference_sign_number']
                    self.assertEqual(result['sign_number'], (start + count - 2) % 12 + 1)     # hand count, inclusive
                    self.assertEqual(result, json.loads(json.dumps(counted_sign(data, reference, count))))
            aspects = invoke_tool(self.owner, 'get_natal_aspects', {'chart_id': chart.pk})['data']
            for row in aspects['planets']:
                self.assertEqual(row['aspected_houses'], aspected_houses(row['code'], row['natal_house']))
                self.assertEqual(row['aspect_offsets'], list(PLANET_ASPECTS.get(row['code'], [7])))

    def test_ac6_unavailable_requests_and_no_calculation_module_changes(self):
        chart = self.fixtures['R1']
        self.assertEqual(invoke_tool(self.owner, 'get_dasha_periods', {'chart_id': chart.pk, 'system': 'vimshottari',
                         'granularity': 'pratyantardasha', **WINDOW})['status'], 'unsupported')
        self.assertEqual(invoke_tool(self.owner, 'get_counted_sign', {'chart_id': chart.pk, 'reference': 'hora_lagna', 'count': 2})['status'], 'unsupported')
        self.assertEqual(invoke_tool(self.owner, 'get_jaimini_facts', {'chart_id': chart.pk, 'include': ['shadbala']})['status'], 'unsupported')
        try:
            changed = subprocess.run(['git', 'diff', '--name-only', 'bf5016c', '--', 'charts/astro_engine.py', 'charts/yogas.py',
                                      'astrology/calculations'], cwd=BASE, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            self.skipTest('git is unavailable; the module diff is reported in M3_REPORT.md instead')
        if changed.returncode != 0:
            self.skipTest('branch base is unavailable in this checkout')
        self.assertEqual([p for p in changed.stdout.split() if p], ['astrology/calculations/counted_signs.py'])   # additive only


class M3ShortcutTests(M3Base):
    def test_ac2_factual_questions_use_zero_model_calls_and_match_stored_values(self):
        data = self.chart.chart_data
        lagna = data['ascendant']['sign_number']
        cases = {'Who is my 7th lord?': ('house_lord', SIGN_LORDS[(lagna + 5) % 12 + 1]),
                 'Who rules my fourth house?': ('house_lord', SIGN_LORDS[(lagna + 2) % 12 + 1]),
                 'Where is Jupiter in D9?': ('placement', next(p for p in data['d9']['planets'] if p['code'] == 'Ju')['sign']),
                 'What is my current mahadasha?': ('current_period', None),
                 'Which Yogini dasha am I running now?': ('current_period', None)}
        from charts.vedic_utils import PLANET_NAMES
        for question, (kind, expected) in cases.items():
            self.assertEqual(match_factual(question).kind, kind, question)
            result = self.run_agent(question, NoModel())
            self.assertEqual(result['usage']['rounds'], 0)
            self.assertEqual(result['model'], 'deterministic')
            self.assertEqual(result['status'], 'ok', question)
            if kind == 'house_lord':
                self.assertIn(PLANET_NAMES[expected], result['answer'])
            elif kind == 'placement':
                self.assertIn(f'In D9, Jupiter is in {expected}', result['answer'])
        vim = self.run_agent('What is my current mahadasha?', NoModel())
        period = vim['evidence']['E1']['result']['data']['periods'][0]
        self.assertIn(period['start'], vim['answer'])
        for question in ('Will my 7th lord bring marriage?', 'Is Jupiter in D9 good for me?', 'When will my mahadasha change?'):
            self.assertIsNone(match_factual(question), question)

    @override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('m3-pilot',))
    def test_ac2_shortcut_through_the_ui_for_an_allowlisted_account(self):
        self.client.force_login(self.owner)
        with patch('chat.llm_engine.generate_answer', side_effect=AssertionError('legacy LLM must not run')):
            response = self.client.post(reverse('ask_question'), {'chart_id': self.chart.pk, 'question': 'Who is my 7th lord?',
                                                                  'answer_language': 'English'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'house 7 ruler is')


class M3DomainMatrixTests(M3Base):
    """M3-AC15 offline: one scripted end-to-end test per primary domain, mixed questions and pairs."""
    QUESTIONS = {
        'career': ('Will I get a promotion in the next year?', 'predictive_timing', ['career:promotion']),
        'business': ('Is this a good period to start my own business?', 'predictive_timing', ['business:starting_a_business']),
        'marriage': ('What kind of spouse does my chart indicate?', 'natal_assessment', ['marriage:nature_of_spouse']),
        'relationships': ('Will I meet someone romantically this year?', 'predictive_timing', ['relationships:meeting_someone']),
        'children': ('How is my relationship with my children shown in my chart?', 'natal_assessment', ['children:parent_child_relationship']),
        'conception_childbirth': ('When might we conceive a child?', 'predictive_timing', ['conception_childbirth:timing_of_conception_or_birth']),
        'education': ('Which field of study suits me?', 'natal_assessment', ['education:field_of_study']),
        'wealth': ('Will my income grow over the next year?', 'predictive_timing', ['wealth:income_growth']),
        'health': ('Is the coming year a sensitive period for my health?', 'predictive_timing', ['health:health_sensitive_periods']),
        'foreign_settlement': ('Will I settle permanently abroad?', 'predictive_timing', ['foreign_settlement:permanent_settlement']),
        'property': ('When is a good time for me to buy a house?', 'predictive_timing', ['property:purchase_timing']),
        'spirituality': ('What kind of spiritual practice suits me?', 'natal_assessment', ['spirituality:suitable_practice']),
    }

    def check_published(self, result, lab):
        self.assertEqual(result['stop_reason'], 'complete', result['draft_validation'])
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['published_by'], 'model')
        self.assertTrue(result['draft_validation']['passed'])
        self.assertEqual(result['label']['domains'], lab['domains'])
        self.assertNotRegex(result['answer'], r'\[F[0-9a-f]{16}\]|\[K[0-9a-f]{20}\]')   # tags rendered, never shown raw
        self.assertIn('(source: Synthetic Parashari Notes', result['answer'])
        self.assertIn('Evidence strength: moderate.', result['answer'])
        self.assertLessEqual(result['usage']['rounds'], 6)
        self.assertLessEqual(result['usage']['searches'], 4)
        self.assertTrue(all(n <= 25000 for n in result['usage']['round_input_tokens']))
        if lab['question_type'] == 'predictive_timing':
            self.assertIn('Exact muhurta selection requires', result['answer'])
        for disclosure in self.profile.disclosures(result['label']):
            self.assertIn(disclosure, result['answer'])

    def test_ac15_every_primary_domain_end_to_end(self):
        self.assertEqual(set(self.QUESTIONS), set(self.profile.primary))
        for domain, (question, qtype, events) in self.QUESTIONS.items():
            with self.subTest(domain=domain):
                lab = label(qtype, domain, events=events)
                result, provider = self.standard(question, lab)
                self.check_published(result, lab)
                guidance = provider.payloads[1]['guidance']
                self.assertEqual(set(guidance['domains']), {domain})
                self.assertEqual(set(guidance['domains'][domain]['event_guides']), {e.split(':')[1] for e in events})
                save_trace(f'offline_{domain}', result)

    def test_ac15_mixed_domain_questions(self):
        mixed = [('Should I move abroad for a better job next year?',
                  label('comparative_decision', 'career', 'foreign_settlement', events=['career:foreign_relocation', 'foreign_settlement:relocation'])),
                 ('Will my business growth let me buy property next year?',
                  label('predictive_timing', 'business', 'property', events=['business:growth_or_expansion', 'property:purchase_timing'])),
                 ('Should I study abroad or start working?',
                  label('comparative_decision', 'education', 'foreign_settlement', 'career', events=['education:study_abroad']))]
        for i, (question, lab) in enumerate(mixed, 1):
            with self.subTest(question=question):
                result, provider = self.standard(question, lab)
                self.check_published(result, lab)
                self.assertEqual(set(provider.payloads[1]['guidance']['domains']), set(lab['domains']))
                required = {c['factor'] for c in provider.payloads[2]['core_factors']}
                self.assertEqual({f.split(':')[0] for f in required}, set(lab['domains']))
                save_trace(f'offline_mixed_{i}', result)

    def test_ac15_distinction_pairs_are_investigated_apart(self):
        for a, b in (('relationships', 'marriage'), ('children', 'conception_childbirth')):
            seen = {}
            for domain in (a, b):
                question, qtype, events = self.QUESTIONS[domain]
                lab = label(qtype, domain, events=events)
                result, provider = self.standard(question, lab)
                self.check_published(result, lab)
                seen[domain] = {c['factor'] for c in provider.payloads[2]['core_factors']}
            self.assertFalse(seen[a] & seen[b])

    def test_ac5_model_may_use_a_tool_outside_the_suggested_factors(self):
        lab = label('natal_assessment', 'marriage', events=['marriage:nature_of_spouse'])
        requests = domain_requests(self.profile, ['marriage'], timing=False) + [
            req('get_ashtakavarga', reason='Not a suggested factor; checking SAV of the 7th sign anyway.', kind='sav', house=7),
            req('get_counted_sign', reason='Second from the Upapada for continuity of marriage.', reference='upapada_lagna', count=2),
            req('get_natal_aspects', reason='Aspects on the 7th house.', house=7)]
        result, _ = self.standard('What kind of spouse does my chart indicate?', lab, requests=requests)
        self.check_published(result, lab)
        self.assertIn('get_ashtakavarga', [e['tool'] for e in result['evidence'].values()])
        save_trace('offline_tool_beyond_suggestions', result)


class M3RetrievalTests(M3Base):
    def test_ac8_ac9a_weak_result_is_refined_with_book_vocabulary(self):
        self.library = FakeLibrary({'chara dasha career': [(0.52, 'Synthetic_Notes.pdf')],
                                    'AmK Pada': [(0.79, 'Synthetic_Jaimini_Notes.pdf')]})
        lab = label('predictive_timing', 'career', events=['career:promotion'])
        provider = Script(
            reply(lab, domain_requests(self.profile, ['career']) + [req('get_dasha_periods', system='chara', **WINDOW)]),
            reply(requests=[req('search_astrology_knowledge', query='chara dasha career promotion timing', domain='career')]),
            lambda p: reply(judgements=[{'evidence_id': first_search(p), 'judgement': 'not_relevant', 'passage_ids': [],
                                         'note': 'General text; nothing on the AmK or the Pada.'}],
                            requests=[req('search_astrology_knowledge', reason='Refine with the book terms Pada and AmK.',
                                          query='Chara Dasha sign of the AmK from the Pada and the 10th sign', domain='career')]),
            lambda p: reply(judgements=[{'evidence_id': 'E8', 'judgement': 'relevant', 'passage_ids': p['evidence']['E8']['passage_ids'][:1],
                                         'note': 'Discusses the AmK sign in Chara Dasha.'}],
                            final=final(p, sources=p['evidence']['E8']['passage_ids'][:1])))
        result = self.run_agent('Will Chara Dasha bring a promotion next year?', provider)
        self.assertEqual(result['status'], 'ok', result['draft_validation'])
        searches = [t for t in result['trace'] if t['event'] == 'search']
        self.assertEqual([s['query'] for s in searches], self.library.queries)          # model-written, not template-joined
        self.assertTrue(searches[0]['low_score_heuristic'])
        self.assertIn('Pada', searches[1]['query'])
        judgements = [t for t in result['trace'] if t['event'] == 'search_judgement']
        self.assertEqual([j['judgement'] for j in judgements], ['not_relevant', 'relevant'])
        save_trace('offline_weak_topic_refined_search', result)

    def test_ac9b_low_score_passage_judged_relevant_is_used_without_research(self):
        self.library = FakeLibrary({'Upapada': [(0.55, 'Synthetic_Upapada_Notes.pdf')]})
        lab = label('natal_assessment', 'marriage', events=['marriage:quality_of_married_life'])
        result, _ = self.standard('How is my married life indicated?', lab, query='Upapada second from it and spouse')
        self.assertEqual(result['status'], 'ok', result['draft_validation'])
        self.assertEqual(result['usage']['searches'], 1)
        search = next(t for t in result['trace'] if t['event'] == 'search')
        self.assertTrue(search['low_score_heuristic'])
        self.assertIn('(source: Synthetic Upapada Notes', result['answer'])

    def test_ac9c_one_good_search_ends_retrieval(self):
        lab = label('natal_assessment', 'wealth', events=['wealth:savings_and_accumulation'])
        result, _ = self.standard('Is my chart good for saving money?', lab)
        self.assertEqual(result['usage']['searches'], 1)
        self.assertEqual(result['usage']['rounds'], 3)

    def test_ac9d_searches_stop_at_the_ceiling(self):
        lab = label('concept_explanation', 'general')
        queries = [f'Upapada meaning variant {i}' for i in range(6)]
        provider = Script(reply(lab, [req('search_astrology_knowledge', query=q) for q in queries]),
                          lambda p: reply(final=final(p, body='The retrieved notes describe the term in their own way [%s].' % p['evidence']['E1']['passage_ids'][0])))
        result = self.run_agent('What is Upapada?', provider)
        self.assertEqual(result['usage']['searches'], 4)
        self.assertEqual(len(self.library.queries), 4)
        self.assertEqual(sum(t['event'] == 'search_ceiling' for t in result['trace']), 2)
        self.assertTrue(all('ceiling' in r['reason'] for r in provider.payloads[1]['rejected_requests']))


class M3NonAnswerTests(M3Base):
    def test_ac10_retrieval_failed(self):
        self.library = FakeLibrary(fail=TimeoutError('upstream'))
        lab = label('natal_assessment', 'education', events=['education:field_of_study'])
        provider = Script(reply(lab, domain_requests(self.profile, ['education'], timing=False) +
                                [req('search_astrology_knowledge', query='education 5th lord Chaturvimshamsha')]),
                          lambda p: reply(final=final(p)))
        result = self.run_agent('Which field of study suits me?', provider)
        self.assertEqual(result['non_answer_states'], ['retrieval_failed'])
        self.assertIn('The classical library could not be searched for this question.', result['answer'])
        self.assertEqual(result['status'], 'partial')                    # unbilled (M3-AC18)
        self.assertNotIn('upstream', result['answer'])
        self.assertNotIn('TimeoutError', result['answer'])
        save_trace('offline_retrieval_failed', result)

    def test_ac10_no_source_support(self):
        lab = label('natal_assessment', 'spirituality', events=['spirituality:inclination'])
        provider = Script(reply(lab, domain_requests(self.profile, ['spirituality'], timing=False) +
                                [req('search_astrology_knowledge', query='Karakamsha 12th moksha')]),
                          lambda p: reply(judgements=[{'evidence_id': first_search(p), 'judgement': 'not_relevant', 'passage_ids': [],
                                                       'note': 'Nothing on the Karakamsha.'}],
                                          requests=[req('search_astrology_knowledge', query='Atmakaraka Navamsha spiritual inclination')]),
                          lambda p: reply(final=final(p, no_source=True)))
        result = self.run_agent('Am I spiritually inclined according to my chart?', provider)
        self.assertEqual(result['status'], 'ok', result['draft_validation'])
        self.assertEqual(result['non_answer_states'], ['no_source_support'])
        self.assertIn('No classical support was retrieved for this point.', result['answer'])
        self.assertNotIn('(source:', result['answer'])
        save_trace('offline_no_source_support', result)

    def test_ac10_calculation_unavailable_for_muhurta_matching_shadbala_and_tools(self):
        lab = label('predictive_timing', 'marriage', events=['marriage:timing_of_marriage'])
        provider = Script(reply(lab, domain_requests(self.profile, ['marriage']) +
                                [req('get_dasha_periods', system='vimshottari', granularity='pratyantardasha', **WINDOW)]),
                          lambda p: reply(final=final(p, unavailable=['muhurta', 'kundli_matching', 'shadbala'])))
        result = self.run_agent('Which exact date should we marry, are we compatible, and how strong is my Venus by shadbala?', provider)
        self.assertEqual(result['status'], 'ok', result['draft_validation'])
        self.assertEqual(result['non_answer_states'], ['calculation_unavailable'])
        for name in ('muhurta', 'kundli_matching', 'shadbala'):
            self.assertIn(f"This needs {self.profile.unavailable_name(name)}, which the app does not yet calculate.", result['answer'])
        self.assertIn('This needs a calculation the app does not yet provide (get_dasha_periods)', result['answer'])
        self.assertNotRegex(result['answer'], r'shadbala (?:score|value|of) \d')
        save_trace('offline_calculation_unavailable', result)

    def test_longevity_is_declined_by_policy(self):
        lab = label('natal_assessment', 'health', events=['health:general_vitality'])
        provider = Script(reply(lab, domain_requests(self.profile, ['health'], timing=False)),
                          lambda p: reply(final=final(p, unavailable=['longevity'])))
        result = self.run_agent('How long will I live?', provider)
        self.assertIn('which the app does not calculate and declines by policy', result['answer'])


class M3ValidationTests(M3Base):
    def marriage(self, *finals):
        lab = label('natal_assessment', 'marriage', events=['marriage:nature_of_spouse'])
        steps = [reply(lab, domain_requests(self.profile, ['marriage'], timing=False))]
        steps += [lambda p, f=f: reply(final=f(p)) for f in finals]
        provider = Script(*steps)
        return self.run_agent('What kind of spouse does my chart indicate?', provider), provider

    def invented(self, p):
        seven = fact(p, contains='D1 house 7 ruler')
        return final(p, body=f'Your 7th lord sits in Scorpio in the 12th house [{seven}]. Your Moon is in Leo.')

    def test_ac11_invented_placements_are_repaired_then_blocked(self):
        result, provider = self.marriage(self.invented, self.invented)
        self.assertEqual(result['stop_reason'], 'validation_failed')
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['published_by'], 'server')
        self.assertIn('repair', provider.payloads[2])
        self.assertTrue(any('unverified_value' in i for i in provider.payloads[2]['repair']['issues']))
        self.assertTrue(any('untagged_chart_claim' in i for i in provider.payloads[2]['repair']['issues']))
        self.assertNotIn('Scorpio in the 12th', result['answer'])
        self.assertIn('I could not complete a verified written interpretation', result['answer'])
        self.assertTrue(result['validation']['passed'])                     # the server's own report is publishable
        save_trace('offline_invented_claim_blocked', result)

    def test_ac11_repair_round_can_fix_the_answer(self):
        result, _ = self.marriage(self.invented, lambda p: final(p))
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(sum(t['event'] == 'repair_requested' for t in result['trace']), 1)

    def test_ac12_citations_need_hits_titles_must_match_and_no_copying(self):
        self.library = FakeLibrary()
        lab = label('natal_assessment', 'marriage')
        def cite(p, text):
            return final(p, body=text)
        steps = [reply(lab, domain_requests(self.profile, ['marriage'], timing=False) + [req('search_astrology_knowledge', query='Darakaraka spouse 7th lord')]),
                 lambda p: reply(final=cite(p, 'According to BPHS the spouse is described by the seventh lord [K0000000000000000000a].'))]
        result = self.run_agent('What kind of spouse is indicated?', Script(*steps, lambda p: reply(final=cite(p, 'According to the Phaladeepika the seventh matters.'))))
        issues = ' '.join(result['draft_validation']['issues'])
        self.assertIn('uncited_source_mention', issues)
        self.assertEqual(result['status'], 'partial')
        catalog, evidence = {}, {}
        kid = 'K' + 'a' * 20
        passages = {kid: {'snippet': SYNTHETIC + 'More synthetic words follow here.', 'citation': {'filename': 'Synthetic_Parashari_Notes.pdf'}}}
        copied = 'It discusses how the relevant houses, their lords and the period rulers are weighed together, as a rule.'
        self.assertTrue(copied_runs(copied, passages))
        found, _, _ = check_prose(f'According to Saravali this is so [{kid}].', catalog, evidence, passages)
        self.assertIn('answer: cited_title_does_not_match_hit', found)
        found, _, _ = check_prose(f'The Synthetic Parashari Notes treat this in their own way [{kid}].', catalog, evidence, passages)
        self.assertEqual(found, [])

    def test_ac13_probability_certainty_health_death_and_fertility_guards(self):
        seven_text = lambda p: tagged(p, fact(p, contains='D1 house 7 ruler'))
        bad = ['There is a 70% chance of marriage by 2027.', 'You will definitely marry next year.',
               'This placement can indicate a heart attack.', 'The maraka period shows the time of death.',
               'You will never conceive a child.', 'Wear a blue sapphire gemstone for luck.']
        for sentence in bad:
            with self.subTest(sentence=sentence):
                found, _, _ = check_prose(sentence, {}, {}, {})
                self.assertTrue(found, sentence)
        for sentence in ('There is no guarantee of any outcome.', 'Your Lagna is Cancer, a water sign.'):
            found, _, _ = check_prose(sentence, {}, {}, {})
            self.assertFalse([f for f in found if 'diagnosis' in f or 'certainty' in f], sentence)
        lab = label('predictive_timing', 'health', events=['health:health_sensitive_periods'])
        result, _ = self.standard('Is the coming year a sensitive period for my health?', lab)
        self.assertIn(self.profile.entry('health')['disclosure'], result['answer'])
        lab = label('predictive_timing', 'conception_childbirth', events=['conception_childbirth:timing_of_conception_or_birth'])
        result, _ = self.standard('When might we conceive?', lab,
                                  finisher=lambda p: final(p, body=seven_text(p) + ' You may be infertile.'))
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(any('fertility_policy' in i for i in result['draft_validation']['issues']))
        self.assertNotIn('infertile', result['answer'])
        self.assertIn(self.profile.entry('conception_childbirth')['disclosure'], result['answer'])

    def test_ac14_heading_free_answer_passes_and_missing_elements_fail(self):
        result, _ = self.marriage(lambda p: final(p))
        self.assertEqual(result['status'], 'ok')
        self.assertNotRegex(result['answer'], r'(?m)^#')
        missing = lambda p: final(p, direct='', reason='short', cover=[])
        result, provider = self.marriage(missing, missing)
        self.assertEqual(result['stop_reason'], 'validation_failed')
        issues = provider.payloads[2]['repair']['issues']
        for element in ('missing direct_answer', 'missing evidence_strength_reason'):
            self.assertIn(element, issues)
        self.assertTrue(any(i.startswith('core_factor_not_covered marriage:') for i in issues))
        heading = lambda p: final(p, body='## Chart basis\n' + tagged(p, fact(p, contains='D1 house 7 ruler')))
        result, _ = self.marriage(heading, heading)
        self.assertTrue(any('headings_not_allowed' in i for i in result['draft_validation']['issues']))

    def test_ac7_core_factor_coverage_examined_or_disclosed(self):
        def partial_cover(p):
            cover = coverage(p)
            cover[0] = {**cover[0], 'status': 'unavailable', 'note': 'Not computed for this chart in this test.'}
            return final(p, cover=cover[:-1])
        result, provider = self.marriage(partial_cover, partial_cover)
        self.assertTrue(any(i.startswith('core_factor_not_covered') for i in result['draft_validation']['issues']))
        unavailable_ok = lambda p: final(p, cover=[{**c, 'status': 'unavailable', 'note': 'Disclosed as unavailable in this test.'} if i == 0 else c
                                                   for i, c in enumerate(coverage(p))])
        result, _ = self.marriage(unavailable_ok)
        self.assertEqual(result['status'], 'ok')


class M3LimitsAndFailureTests(M3Base):
    def test_ac16_round_input_limit_is_checked_before_any_call(self):
        provider = Script(reply(label('natal_assessment', 'career'), [req('get_chart_facts', charts=['d1'])]))
        result = self.run_agent('What does my chart say about my career overall?', provider, limits=AgentLimits(round_input_tokens=1500))
        self.assertEqual(result['stop_reason'], 'round_input_limit')
        self.assertEqual(provider.payloads, [])
        self.assertEqual(result['status'], 'partial')

    def test_ac16_rounds_are_capped_and_tokens_recorded(self):
        lab = label('natal_assessment', 'career')
        loop = lambda p: reply(requests=[req('get_ashtakavarga', kind='sav', house=(len(p['evidence']) % 12) + 1)])
        provider = Script(reply(lab, [req('get_chart_facts', charts=['d1'])]), *([loop] * 10))
        result = self.run_agent('What does my chart say about my career overall?', provider)
        self.assertEqual(result['usage']['rounds'], 6)
        self.assertEqual(result['stop_reason'], 'model_round_limit')
        self.assertTrue(provider.payloads[-1]['final_required'])
        rounds = [t for t in result['trace'] if t['event'] == 'round']
        self.assertEqual(len(rounds), 6)
        self.assertTrue(all(r['provider_input_tokens'] == 1200 and r['counted_input_tokens'] > 0 and 'latency_ms' in r for r in rounds))
        self.assertTrue(any(t['event'] == 'stop' and 'elapsed_ms' in t for t in result['trace']))

    def test_ac18_provider_timeout_and_spending_refusal_are_partial_without_raw_errors(self):
        for error, reason in ((TimeoutError('socket detail 10.0.0.1'), 'provider_timeout'), (BudgetExceeded('cost_or_search_limit'), 'spending_limit'),
                              (RuntimeError('Traceback secret'), 'provider_unavailable')):
            provider = Script(reply(label('natal_assessment', 'career'), [req('get_chart_facts', charts=['d1', 'd10'])]), error)
            result = self.run_agent('What does my chart say about my career overall?', provider)
            self.assertEqual(result['stop_reason'], reason)
            self.assertEqual(result['status'], 'partial')
            self.assertNotIn('10.0.0.1', result['answer'])
            self.assertNotIn('secret', result['answer'])
            self.assertIn('Your D1 house', result['answer'])                # server facts only

    def test_out_of_scope_is_declined_after_one_round(self):
        result = self.run_agent('What will the weather be tomorrow?', Script(reply(label('out_of_scope'))))
        self.assertEqual(result['stop_reason'], 'out_of_scope')
        self.assertEqual(result['usage']['rounds'], 1)
        self.assertEqual(result['evidence'], {})
        self.assertIn('outside what this app can answer', result['answer'])

    def test_invalid_label_and_bad_requests(self):
        result = self.run_agent('Tell me about romance', Script(reply(label('natal_assessment', 'romance'))))
        self.assertEqual(result['stop_reason'], 'invalid_label')
        lab = label('natal_assessment', 'career')
        provider = Script(reply(lab, [req('delete_chart'), {'tool': 'get_chart_facts', 'arguments_json': '[1]', 'reason': 'x'},
                                      req('get_chart_facts', reason='', charts=['d1']), req('get_chart_facts', charts=['d1'])]),
                          lambda p: reply(final=final(p)))
        result = self.run_agent('What does my chart say about my career overall?', provider)
        self.assertEqual(len(provider.payloads[1]['rejected_requests']), 3)
        self.assertEqual(len(result['evidence']), 1)


class M3OwnershipTests(M3Base):
    def test_ac19_forged_chart_id_is_overridden(self):
        foreign = SavedChart.objects.create(user=self.other, name='Other synthetic', birth_date=date(1980, 1, 1), birth_time='12:00:00',
                                            birth_place='Synthetic', timezone='UTC', chart_data=sample_chart_data())
        lab = label('natal_assessment', 'career')
        provider = Script(reply(lab, [req('get_chart_facts', chart_id=foreign.pk, charts=['d1'])]), lambda p: reply(final=final(p)))
        result = self.run_agent('What does my chart say about my career overall?', provider)
        self.assertEqual(result['evidence']['E1']['arguments']['chart_id'], self.chart.pk)
        self.assertTrue(any(t['event'] == 'chart_id_overridden' for t in result['trace']))

    def test_ac19_followup_chart_change_is_rejected(self):
        context = {'schema_version': 1, 'chart_id': self.chart.pk, 'epoch': 1, 'recent_messages': [],
                   'summary': {'schema_version': 1, 'chart_id': self.chart.pk, 'epoch': 1}}
        result = self.run_agent('And what about my wife?', NoModel(), consultation_context=context)
        self.assertEqual(result['stop_reason'], 'scope_clarification')
        self.assertIn('select that person', result['answer'])

    def test_ac19_ownership_change_mid_consultation_publishes_nothing(self):
        def transfer(user, name, args):
            SavedChart.objects.filter(pk=self.chart.pk).update(user=self.other)
            return invoke_tool(user, name, args)
        provider = Script(reply(label('natal_assessment', 'career'), [req('get_chart_facts', charts=['d1']), req('get_jaimini_facts')]))
        with patch('astrology.agent.general.invoke_tool', side_effect=transfer):
            result = self.run_agent('What does my chart say about my career overall?', provider)
        self.assertEqual(result['stop_reason'], 'chart_unavailable')
        self.assertEqual(result['evidence'], {})
        self.assertEqual(result['answer'], 'Chart is unavailable.')


class M3RoutingTests(M3Base):
    @override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('pilot@example.test',))
    def test_ac1_allowlisted_account_uses_agent_and_never_legacy(self):
        self.assertEqual(agent_route(self.owner), 'general')
        self.assertEqual(agent_route(self.other), 'legacy')
        with patch('chat.agent_service.run_general_consultation', return_value={'status': 'ok'}) as agent, \
             patch('chat.agent_service.generate_placeholder_answer') as legacy, \
             patch('chat.llm_engine.generate_answer', side_effect=AssertionError('legacy LLM')):
            self.assertEqual(generate_question_answer(self.owner, self.chart, 'question', Conversation.FULL), {'status': 'ok'})
        agent.assert_called_once_with(self.owner, self.chart.pk, 'question')
        legacy.assert_not_called()
        with patch('chat.agent_service.generate_placeholder_answer', return_value={'answer': 'legacy'}) as legacy, \
             patch('chat.agent_service.run_general_consultation') as agent:
            self.assertEqual(generate_question_answer(self.other, self.chart, 'question', Conversation.FULL), {'answer': 'legacy'})
        agent.assert_not_called()

    def test_ac21_rollback_by_allowlist_or_global_flag(self):
        with override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=()):
            self.assertEqual(agent_route(self.owner), 'legacy')                      # empty by default
        with override_settings(ASTROGPT_AGENT_ENABLED=False, ASTROGPT_AGENT_USERS=('m3-pilot',)):
            self.assertEqual(agent_route(self.owner), 'legacy')
        with override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=(), ASTROGPT_AGENT_P3_COMPAT=True):
            self.assertEqual(agent_route(self.owner), 'p3')
        with override_settings(ASTROGPT_RETRIEVAL_ADAPTER='hosted'):
            from astrology.rag.direct import configured_adapter
            self.assertIn('hosted', configured_adapter().name)

    def test_ac17_pilot_policy_is_reserved_for_allowlisted_accounts(self):
        from accounts.usage import reserve
        from uuid import uuid4
        conversation = Conversation.objects.create(user=self.owner, chart=self.chart)
        with override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('m3-pilot',)):
            row, _ = reserve(self.owner, self.chart, conversation, uuid4(), 'question')
        self.assertEqual(row.policy, policy_for('agent_pilot'))
        self.assertEqual(row.policy['cost'], '0.05')
        self.assertEqual((row.policy['rounds'], row.policy['file_searches']), (6, 4))
        other = Conversation.objects.create(user=self.owner, chart=self.chart)
        with override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=()):
            row, _ = reserve(self.owner, self.chart, other, uuid4(), 'question 2')
        self.assertEqual(row.policy, policy_for('free'))
