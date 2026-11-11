"""M2 offline tests: retrieval adapters, metering, citation fidelity, source policy.

All provider traffic is mocked; network connects are blocked. Passages are synthetic.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from accounts.models import ProviderUsage, UsageRequest
from accounts.provider_meter import Budget, SEARCH_MODEL, request_budget, vector_store_search
from accounts.usage_policy import BudgetExceeded
from astrology.agent.orchestrator import run_consultation
from astrology.agent.provider import INSTRUCTIONS
from astrology.rag.direct import DirectVectorStoreSearch, StaticRetrieval, configured_adapter, plain_query, result_row
from astrology.rag.hosted import HostedFileSearch
from astrology.rag.knowledge import KnowledgeSession
from astrology.rag.knowledge_contracts import SearchRequest
from astrology.rag.policy import SOURCE_TEXT_POLICY
from astrology.test_agent import ScriptedProvider, call
from astrology.test_knowledge import FakeRetrieval, passage
from astrology.tests import sample_chart_data
from charts.models import SavedChart

LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'm2-tests'}}
STORE = {'OPENAI_API_KEY': 'offline-test-key', 'OPENAI_VECTOR_STORE_ID': 'vs-offline'}


def sdk_hit(text='Synthetic tenth-lord viewpoint.', page=None, **changes):
    attributes = {'book': 'Synthetic Book A'}
    if page is not None:
        attributes['page'] = page
    data = {'file_id': 'file-a', 'filename': 'synthetic-a.pdf', 'score': 0.71, 'attributes': attributes,
            'content': [{'type': 'text', 'text': text}], **changes}
    return SimpleNamespace(model_dump=lambda: data)


class DirectAdapterTests(SimpleTestCase):
    def setUp(self):
        block = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        block.start()
        self.addCleanup(block.stop)

    def test_plain_query_flattens_the_knowledge_tool_json(self):
        self.assertEqual(plain_query('{"topic": "career", "concepts": ["d10", "tenth lord"], "tradition": null, "source": null}'),
                         'career d10 tenth lord')
        self.assertEqual(plain_query('Amatyakaraka and profession'), 'Amatyakaraka and profession')

    def test_result_row_keeps_only_returned_metadata(self):
        row = result_row(sdk_hit(page='7'))
        self.assertEqual(row, {'file_id': 'file-a', 'filename': 'synthetic-a.pdf', 'score': 0.71,
                               'attributes': {'book': 'Synthetic Book A', 'page': '7'}, 'text': 'Synthetic tenth-lord viewpoint.'})

    @override_settings(**STORE)
    def test_direct_search_is_bounded_unretried_and_closed(self):
        api = Mock()
        api.vector_stores.search.return_value = SimpleNamespace(data=[sdk_hit(), sdk_hit('Second.'), sdk_hit('Third.')])
        with patch('openai.OpenAI', return_value=api) as factory:
            batch = DirectVectorStoreSearch().retrieve('{"topic": "career", "concepts": ["d10"]}',
                SearchRequest(1, 'career', ('d10',), result_count=2), timeout=9)
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
        self.assertEqual(factory.call_args.kwargs['timeout'], 9)
        api.vector_stores.search.assert_called_once_with('vs-offline', query='career d10', max_num_results=2)
        api.close.assert_called_once()
        self.assertEqual(len(batch.results), 2)
        self.assertEqual((batch.input_tokens, batch.output_tokens, batch.complete), (0, 0, True))

    def test_static_adapter_never_contacts_a_provider(self):
        adapter = StaticRetrieval([passage()])
        with patch('openai.OpenAI', side_effect=AssertionError('forbidden')):
            batch = adapter.retrieve('q', SearchRequest(1, 'career', ('d10',)), timeout=1)
        self.assertEqual(len(batch.results), 1)

    def test_adapter_setting_selects_and_rejects(self):
        with override_settings(ASTROGPT_RETRIEVAL_ADAPTER='hosted'):
            self.assertIsInstance(configured_adapter(), HostedFileSearch)
        with override_settings(ASTROGPT_RETRIEVAL_ADAPTER='direct'):
            self.assertIsInstance(configured_adapter(), DirectVectorStoreSearch)
        with override_settings(ASTROGPT_RETRIEVAL_ADAPTER='qdrant'), self.assertRaises(ValueError):
            configured_adapter()


class SearchMeteringTests(TestCase):
    def setUp(self):
        block = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        block.start()
        self.addCleanup(block.stop)

    def test_unaccounted_search_still_counts_against_the_conservative_cap(self):
        budget = Budget()  # free policy: one search
        client = Mock()
        with patch('accounts.provider_meter.CURRENT') as current:
            current.get.return_value = budget
            vector_store_search(client, 'vs', query='q', max_num_results=1)
            with self.assertRaisesRegex(BudgetExceeded, 'cost_or_search_limit'):
                vector_store_search(client, 'vs', query='q', max_num_results=1)
        client.vector_stores.search.assert_called_once()
        self.assertEqual(budget.reserved, Decimal('0.0025'))

    def test_accounted_search_is_written_to_the_ledger_before_and_after(self):
        from accounts.test_usage import owned_chart
        user = get_user_model().objects.create_user(username='m2-meter')
        chart = owned_chart(user)
        from accounts.models import CreditAccount
        CreditAccount.objects.get_or_create(user=user)
        row = UsageRequest.objects.create(user=user, chart=chart, request_id=uuid4(), status='running', policy={
            'rounds': 2, 'tokens': 160000, 'output': 1200, 'file_searches': 1, 'cost': '0.05'})
        client = Mock()
        with request_budget(row):
            vector_store_search(client, 'vs', query='q', max_num_results=1)
        call_row = ProviderUsage.objects.get(request=row)
        self.assertEqual(call_row.model, SEARCH_MODEL)
        self.assertEqual((call_row.status, call_row.file_searches, call_row.reported_file_searches), ('estimated', 1, 1))
        self.assertEqual(call_row.rated_cost, Decimal('0.0025'))

    def test_failed_search_is_recorded_and_blocks_further_calls(self):
        budget = Budget()
        client = Mock()
        client.vector_stores.search.side_effect = RuntimeError('provider down')
        with patch('accounts.provider_meter.CURRENT') as current:
            current.get.return_value = budget
            with self.assertRaises(RuntimeError):
                vector_store_search(client, 'vs', query='q')
        self.assertTrue(budget.failed)


@override_settings(CACHES=LOCMEM, **STORE)
class AdapterSwapAndCitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='m2-owner')
        cls.chart = SavedChart.objects.create(user=cls.owner, name='Synthetic M2 chart',
            birth_date=date(1990, 5, 17), birth_time='10:30:00', birth_place='Synthetic fixture',
            latitude='28.613900', longitude='77.209000', timezone='Asia/Kolkata', chart_data=sample_chart_data())

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)
        block = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        block.start()
        self.addCleanup(block.stop)

    def args(self):
        return {'chart_id': self.chart.pk, 'topic': 'career', 'concepts': ['tenth lord', 'D10'], 'result_count': 3}

    def direct_adapter(self, hits):
        api = Mock()
        api.vector_stores.search.return_value = SimpleNamespace(data=hits)
        patcher = patch('openai.OpenAI', return_value=api)
        patcher.start()
        self.addCleanup(patcher.stop)
        return DirectVectorStoreSearch()

    def hosted_adapter(self, rows):
        api = Mock()
        item = SimpleNamespace(type='file_search_call', status='completed', queries=['career d10'],
                               results=[SimpleNamespace(model_dump=lambda r=r: r) for r in rows])
        api.responses.create.return_value = SimpleNamespace(output=[item], usage=SimpleNamespace(input_tokens=900, output_tokens=12))
        patcher = patch('openai.OpenAI', return_value=api)
        patcher.start()
        self.addCleanup(patcher.stop)
        return HostedFileSearch()

    def consult(self, adapter):
        return run_consultation(self.owner, self.chart.pk, 'Is my career generally promising?', today=date(2026, 11, 7),
            provider=ScriptedProvider([call('search_astrology_knowledge', {'topic': 'career', 'concepts': ['tenth lord', 'D10']},
                                            'Explain calculated D10 evidence with classical references.')]),
            knowledge_adapter=adapter)

    def test_m2_ac6_agent_runs_unchanged_against_hosted_direct_and_offline_adapters(self):
        row = passage()
        adapters = {'hosted': lambda: self.hosted_adapter([row]),
                    'direct': lambda: self.direct_adapter([sdk_hit(row['text'], page='12')]),
                    'static': lambda: StaticRetrieval([row])}
        for name, build in adapters.items():
            with self.subTest(adapter=name):
                result = self.consult(build())
                self.assertTrue(result['validation']['passed'])
                self.assertIn('its text is not quoted', result['answer'])
                self.assertNotIn(row['text'], result['answer'])
                knowledge = [e for e in result['evidence'].values() if e['tool'] == 'search_astrology_knowledge']
                self.assertEqual(knowledge[0]['result']['data']['support_status'], 'retrieved')

    def test_m2_ac4_every_locator_comes_from_a_returned_hit_and_pages_only_when_returned(self):
        adapter = self.direct_adapter([sdk_hit('With page.', page='44'), sdk_hit('No page.', file_id='file-b', filename='b.pdf')])
        result = KnowledgeSession(self.owner, self.chart.pk, adapter).search(self.args())
        passages = result['data']['passages']
        returned = {('file-a', 'synthetic-a.pdf'), ('file-b', 'b.pdf')}
        self.assertTrue(all((p['citation']['file_id'], p['citation']['filename']) in returned for p in passages))
        self.assertEqual([p['citation']['page'] for p in passages], ['44', None])
        self.assertIn('no missing attribution was inferred', ' '.join(result['warnings']))

    def test_m2_ac8_no_hits_states_that_no_classical_support_was_retrieved(self):
        for adapter in (StaticRetrieval([]), FakeRetrieval([])):
            with self.subTest(adapter=adapter.name):
                result = self.consult(adapter)
                self.assertTrue(result['validation']['passed'])
                self.assertIn('No classical support was retrieved', result['answer'])
                self.assertNotIn('Attribution:', result['answer'])

    def test_unconfigured_store_never_calls_the_provider(self):
        with override_settings(OPENAI_VECTOR_STORE_ID=''), patch('openai.OpenAI', side_effect=AssertionError('forbidden')):
            result = KnowledgeSession(self.owner, self.chart.pk, DirectVectorStoreSearch()).search(self.args())
        self.assertEqual(result['error']['code'], 'knowledge_not_configured')


class SourcePolicyTests(SimpleTestCase):
    """M2-AC7 (S-6) and OD-11 in every prompt that can see retrieved text."""

    def test_policy_text(self):
        self.assertIn('untrusted', SOURCE_TEXT_POLICY)
        self.assertIn('never quote', SOURCE_TEXT_POLICY)
        self.assertIn('no classical support was retrieved', SOURCE_TEXT_POLICY)

    def test_legacy_prompts_carry_the_policy(self):
        from chat.llm_engine import _rashifal_system_instructions, _system_instructions
        for depth in (1, 2, 3):
            self.assertIn(SOURCE_TEXT_POLICY, _system_instructions(depth))
        for horizon in ('weekly', 'monthly', 'yearly'):
            self.assertIn(SOURCE_TEXT_POLICY, _rashifal_system_instructions(horizon))

    def test_agent_prompt_carries_the_policy(self):
        self.assertIn(SOURCE_TEXT_POLICY, INSTRUCTIONS)


class M2CloseOutTests(SimpleTestCase):
    """Owner approval 2026-11-11: direct by default, hosted as rollback, at least 3 passages."""

    def test_default_adapter_is_direct_and_hosted_remains_selectable(self):
        from django.conf import settings
        self.assertEqual(settings.ASTROGPT_RETRIEVAL_ADAPTER, 'direct')
        self.assertIsInstance(configured_adapter(), DirectVectorStoreSearch)
        with override_settings(ASTROGPT_RETRIEVAL_ADAPTER='hosted'):
            self.assertIsInstance(configured_adapter(), HostedFileSearch)

    def test_requests_for_fewer_than_three_passages_are_raised_to_three(self):
        from astrology.rag.knowledge import prepare
        from astrology.rag.knowledge_contracts import MIN_RESULTS
        self.assertEqual(MIN_RESULTS, 3)
        for asked, expected in ((1, 3), (2, 3), (3, 3), (5, 5)):
            request, _ = prepare({'chart_id': 1, 'topic': 'career', 'concepts': ['d10'], 'result_count': asked})
            self.assertEqual(request.result_count, expected)
        request, _ = prepare({'chart_id': 1, 'topic': 'career', 'concepts': ['d10']})
        self.assertEqual(request.result_count, 3)

    def test_session_cap_refuses_before_the_call(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        import tempfile
        from pathlib import Path
        from charts.management.commands import m2_retrieval_eval as cmd
        with tempfile.TemporaryDirectory() as tmp, patch.object(cmd, 'PRIVATE', Path(tmp)), \
                patch('astrology.rag.direct.DirectVectorStoreSearch.retrieve', side_effect=AssertionError('no call')):
            with self.assertRaisesRegex(CommandError, 'session cap'):
                call_command('m2_retrieval_eval', run='Q1', adapters='direct', label='t', session_cap='0.001', confirm_paid=True)
