"""P7 offline billing/resilience checks. Synthetic tariffs/usage are not live costs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import json
import io
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import close_old_connections, connection, OperationalError
from django.test import TestCase, TransactionTestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from astrology.tests import sample_chart_data
from astrology.tools import invoke_tool
from astrology.rag.knowledge import KnowledgeSession
from astrology.test_knowledge import FakeRetrieval
from charts.models import SavedChart
from chat.models import Conversation, Message
from chat.consultation_service import append_turn, change_memory
from .models import CreditAccount, UsageRequest, ProviderUsage, UserProfile
from .usage import reserve, settle, refund
from .usage_policy import policy_for, tariff_for, cost_for, BudgetExceeded
from .provider_meter import Budget, request_budget, responses_create, usage_counts
from .credits import question_credit_status
from .reporting import contribution_report


def reply(incoming=100, outgoing=20, cached=0):
    return SimpleNamespace(usage=SimpleNamespace(input_tokens=incoming, output_tokens=outgoing,
        input_tokens_details=SimpleNamespace(cached_tokens=cached)))


def owned_chart(user):
    return SavedChart.objects.create(user=user, name='Synthetic billing chart', birth_date=date(1990, 5, 17),
        birth_time='10:30', birth_place='Synthetic', latitude='28.6139', longitude='77.2090',
        timezone='Asia/Kolkata', chart_data=sample_chart_data())


@override_settings(ENFORCE_QUESTION_LIMITS=True, FREE_QUESTION_CREDITS=2,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'p7-tests'}})
class UsageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='usage-owner')
        cls.other = get_user_model().objects.create_user(username='usage-other')
        cls.chart = owned_chart(cls.user)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.provider = Mock()
        self.provider.responses.create.return_value = reply()
        block = patch('socket.socket.connect', side_effect=AssertionError('No live network in P7 tests'))
        block.start()
        self.addCleanup(block.stop)

    def conversation(self, **kwargs):
        return Conversation.objects.create(user=self.user, chart=self.chart, **kwargs)

    def reserve(self, conversation=None, request_id=None, question='Who rules my 10th house?'):
        return reserve(self.user, self.chart, conversation or self.conversation(), request_id or uuid4(), question)[0]

    def generate(self, user, chart, question, depth, **kwargs):
        responses_create(self.provider, model='gpt-4o-mini', input='Synthetic request')
        return {'status': 'ok', 'answer': 'Verified synthetic answer.', 'model': 'gpt-4o-mini', 'validation': {'passed': True}}

    def test_p7_01_simple_request_reserves_and_consumes_once(self):
        conversation = self.conversation()
        result = append_turn(self.user, conversation.pk, 'Who rules my 10th house?', request_id=uuid4(), expected_revision=0, generator=self.generate)
        self.assertEqual(result.state, 'complete')
        row = UsageRequest.objects.get()
        account = CreditAccount.objects.get(user=self.user)
        self.assertEqual((account.consumed, account.reserved), (1, 0))
        self.assertEqual(row.status, 'succeeded')
        self.assertLess(row.estimated_cost, Decimal(row.policy['cost']))
        self.assertIsNone(row.actual_cost)
        call = row.provider_calls.get()
        self.assertEqual((call.input_tokens, call.output_tokens), (100, 20))
        self.assertEqual(self.provider.responses.create.call_args.kwargs['max_tool_calls'], 1)

    def test_p7_02_round_token_search_cost_and_model_limits_block_before_dispatch(self):
        for policy, kwargs in [({**policy_for('free'), 'rounds': 1}, {}),
                               ({**policy_for('free'), 'tokens': 1}, {}),
                               ({**policy_for('free'), 'cost': '0.000001'}, {}),
                               (policy_for('free'), {'model': 'unpriced-model'}),
                               (policy_for('free'), {'tools': [{'type': 'web_search'}]})]:
            row = self.reserve()
            row.policy = policy
            row.save(update_fields=['policy'])
            self.provider.reset_mock()
            with request_budget(row):
                if policy['rounds'] == 1:
                    responses_create(self.provider, model='gpt-4o-mini', input='x')
                before = self.provider.responses.create.call_count
                with self.assertRaises(BudgetExceeded):
                    responses_create(self.provider, **{'model': 'gpt-4o-mini', 'input': 'x', **kwargs})
                self.assertEqual(self.provider.responses.create.call_count, before)
            settle(row.pk, reason='failed')
        row = self.reserve()
        with request_budget(row):
            responses_create(self.provider, model='gpt-4o-mini', input='x', tools=[{'type': 'file_search'}])
            with self.assertRaises(BudgetExceeded):
                responses_create(self.provider, model='gpt-4o-mini', input='x', tools=[{'type': 'file_search'}])

    def test_p7_03_timeout_has_estimated_liability_and_releases_credit(self):
        self.provider.responses.create.side_effect = TimeoutError('private provider details')
        result = append_turn(self.user, self.conversation().pk, 'Career?', request_id=uuid4(), expected_revision=0, generator=self.generate)
        self.assertEqual(result.state, 'failed')
        row = UsageRequest.objects.get()
        self.assertEqual((row.credits_consumed, row.credits_released), (0, 1))
        call = row.provider_calls.get()
        self.assertEqual(call.status, 'error')
        self.assertIsNone(call.input_tokens)
        self.assertGreater(row.estimated_cost, 0)
        self.assertNotIn('private provider', call.error_code)
        self.assertEqual(CreditAccount.objects.get().reserved, 0)

    def test_p7_04_followup_duplicate_has_single_charge_and_call(self):
        conversation = self.conversation()
        identity = uuid4()
        first = append_turn(self.user, conversation.pk, 'Career?', request_id=identity, expected_revision=0, generator=self.generate)
        second = append_turn(self.user, conversation.pk, 'Career?', request_id=identity, expected_revision=0, generator=self.generate)
        self.assertEqual((first.state, second.state), ('complete', 'complete'))
        self.assertEqual(self.provider.responses.create.call_count, 1)
        self.assertEqual(UsageRequest.objects.count(), 1)
        self.assertEqual(CreditAccount.objects.get().consumed, 1)

    def test_initial_http_reused_id_with_changed_body_is_conflict(self):
        self.client.force_login(self.user)
        identity = uuid4()
        payload = {'request_id': str(identity), 'chart_id': self.chart.pk, 'question': 'Career?', 'answer_language': 'English'}
        with patch('chat.views.generate_question_answer', side_effect=self.generate):
            self.client.post(reverse('ask_question'), payload)
            payload['question'] = 'Different business question'
            response = self.client.post(reverse('ask_question'), payload)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.provider.responses.create.call_count, 1)
        self.assertEqual(UsageRequest.objects.count(), 1)
        self.assertEqual(CreditAccount.objects.get().consumed, 1)

    def test_p7_04_initial_http_duplicate_reuses_conversation(self):
        self.client.force_login(self.user)
        identity = uuid4()
        payload = {'request_id': str(identity), 'chart_id': self.chart.pk, 'question': 'Career?', 'answer_language': 'English'}
        with patch('chat.views.generate_question_answer', side_effect=self.generate):
            first = self.client.post(reverse('ask_question'), payload)
            second = self.client.post(reverse('ask_question'), payload)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first.url, second.url)
        self.assertEqual(UsageRequest.objects.count(), 1)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(self.provider.responses.create.call_count, 1)

    @override_settings(FREE_QUESTION_CREDITS=1)
    def test_p7_05_last_credit_is_reserved_before_provider(self):
        first = self.reserve()
        with self.assertRaises(BudgetExceeded): self.reserve()
        self.assertEqual(CreditAccount.objects.get().reserved, 1)
        settle(first.pk, reason='failed')
        self.assertEqual(question_credit_status(self.user)['remaining'], 1)

    def test_p7_06_deterministic_cache_reuses_then_invalidates_changed_chart(self):
        from astrology.tools import registry
        original = registry.TOOL_REGISTRY['get_chart_facts'].adapter
        with patch.object(registry, 'TOOL_REGISTRY', {**registry.TOOL_REGISTRY,
            'get_chart_facts': SimpleNamespace(request_type=registry.TOOL_REGISTRY['get_chart_facts'].request_type,
                requires_natal=False, adapter=Mock(wraps=original))}):
            adapter = registry.TOOL_REGISTRY['get_chart_facts'].adapter
            args = {'chart_id': self.chart.pk, 'charts': ['d1']}
            a = invoke_tool(self.user, 'get_chart_facts', args)
            b = invoke_tool(self.user, 'get_chart_facts', args)
            self.assertEqual(a, b)
            self.assertEqual(adapter.call_count, 1)
            self.chart.chart_data = deepcopy(self.chart.chart_data)
            self.chart.chart_data['ayanamsa'] = 'Synthetic changed method'
            self.chart.save(update_fields=['chart_data'])
            c = invoke_tool(self.user, 'get_chart_facts', args)
            self.assertNotEqual(a['provenance']['chart_fingerprint'], c['provenance']['chart_fingerprint'])
            self.assertEqual(adapter.call_count, 2)
            self.assertEqual(invoke_tool(self.other, 'get_chart_facts', args)['status'], 'error')

    def test_p7_07_conversation_retrieval_reuses_and_invalidates_source_and_epoch(self):
        conversation = self.conversation(memory_enabled=True, memory_consent_at=timezone.now())
        row = self.reserve(conversation)
        adapter = FakeRetrieval()
        arguments = {'chart_id': self.chart.pk, 'topic': 'career', 'concepts': ['tenth lord']}
        with request_budget(row):
            first = KnowledgeSession(self.user, self.chart.pk, adapter).search(arguments)
            second = KnowledgeSession(self.user, self.chart.pk, adapter).search(arguments)
            self.assertEqual(len(adapter.calls), 1)
            self.assertTrue(second['provenance']['cache_hit'])
            self.assertEqual(second['data']['usage']['provider_rounds'], 0)
            adapter.fingerprint = 'changed-source-generation'
            KnowledgeSession(self.user, self.chart.pk, adapter).search(arguments)
            self.assertEqual(len(adapter.calls), 2)
            Conversation.objects.filter(pk=conversation.pk).update(memory_epoch=1)
            KnowledgeSession(self.user, self.chart.pk, adapter).search(arguments)
            self.assertEqual(len(adapter.calls), 3)

    def test_p7_08_unknown_usage_is_conservative_not_free(self):
        row = self.reserve()
        self.provider.responses.create.return_value = SimpleNamespace(usage=None)
        with request_budget(row):
            result = responses_create(self.provider, model='gpt-4o-mini', input='x')
            self.assertGreater(sum(usage_counts(result)), 0)
        call = row.provider_calls.get()
        self.assertIsNone(call.input_tokens)
        self.assertEqual(call.status, 'estimated')
        self.assertEqual(call.rated_cost, call.reserved_cost)

    def test_p7_09_cached_discount_and_published_tariff_fixture(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/p7_tariff_v1.json').read_text())
        tariff = tariff_for(fixture['model'])
        for case in fixture['cases']:
            self.assertEqual(cost_for(tariff, case['input_tokens'], case['output_tokens'], case['cached_tokens'], case['file_searches']), Decimal(case['expected_usd']))
        row = self.reserve()
        self.provider.responses.create.return_value = reply(100, 20, 50)
        with request_budget(row): responses_create(self.provider, model='gpt-4o-mini', input='x')
        self.assertGreater(row.provider_calls.get().cached_discount, 0)

    def test_p7_10_refund_idempotent_and_cancel_stops_future_calls(self):
        row = self.reserve()
        settle(row.pk, delivered=True)
        refund(self.user, row.request_id)
        refund(self.user, row.request_id)
        self.assertEqual(CreditAccount.objects.get().consumed, 0)
        pending = self.reserve()
        refund(self.user, pending.request_id)
        with request_budget(pending), self.assertRaises(BudgetExceeded):
            responses_create(self.provider, model='gpt-4o-mini', input='x')
        self.provider.responses.create.assert_not_called()

    def test_cancel_during_generation_blocks_late_answer(self):
        conversation = self.conversation()
        identity = uuid4()
        def cancel(*args, **kwargs):
            refund(self.user, identity)
            return {'answer': 'Must not publish', 'model': 'mock', 'status': 'ok', 'validation': {'passed': True}}
        result = append_turn(self.user, conversation.pk, 'Career?', request_id=identity, expected_revision=0, generator=cancel)
        self.assertEqual(result.http_status, 409)
        self.assertFalse(Message.objects.filter(role=Message.ASSISTANT).exists())
        self.assertEqual(CreditAccount.objects.get().reserved, 0)

    def test_memory_delete_releases_and_preserves_financial_row(self):
        conversation = self.conversation()
        row = self.reserve(conversation)
        self.assertTrue(change_memory(self.user, conversation.pk, 'delete', expected_revision=0))
        row.refresh_from_db()
        self.assertIsNone(row.conversation_id)
        self.assertEqual(row.status, 'cancelled')
        self.assertEqual(CreditAccount.objects.get().reserved, 0)

    def test_p7_11_finance_dashboard_denies_users_and_staff_and_has_no_chart_text(self):
        self.reserve()
        for user in (self.user, self.other):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('contribution_dashboard')).status_code, 403)
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('contribution_dashboard')).status_code, 403)
        self.user.is_superuser = True
        self.user.save(update_fields=['is_superuser'])
        response = self.client.get(reverse('contribution_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.chart.name)
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        self.assertIsNone(contribution_report()['plans']['free']['contribution_margin_estimate'])

    def test_margin_uses_allocations_and_actual_cost_when_available(self):
        row = self.reserve()
        UsageRequest.objects.filter(pk=row.pk).update(revenue_usd=1, payment_fee_usd='.1', infrastructure_usd='.2', actual_cost='.3')
        self.assertEqual(contribution_report()['plans']['free']['contribution_margin_estimate'], Decimal('.4'))

    def test_cross_user_reservation_fails_and_changed_request_key_conflicts(self):
        conversation = self.conversation()
        row = self.reserve(conversation)
        with self.assertRaises(BudgetExceeded): reserve(self.other, self.chart, conversation, uuid4(), 'x')
        with self.assertRaises(BudgetExceeded): self.reserve(conversation, row.request_id, 'Changed body')

    @override_settings(ASTROGPT_DAILY_PROVIDER_CAP_USD='0.000001')
    def test_daily_provider_cap_blocks_across_requests(self):
        row = self.reserve()
        with request_budget(row), self.assertRaises(BudgetExceeded):
            responses_create(self.provider, model='gpt-4o-mini', input='x')
        self.provider.responses.create.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.stop_reason, 'daily_cost_limit')

    def test_started_attempt_liability_survives_worker_abandonment(self):
        row = self.reserve()
        budget = Budget(row.policy, row.pk)
        budget.before({'model': 'gpt-4o-mini', 'input': 'x'})
        row.refresh_from_db()
        self.assertGreater(row.estimated_cost, 0)
        UsageRequest.objects.filter(pk=row.pk).update(created_at=timezone.now() - timedelta(hours=1))
        call_command('reconcile_usage', stdout=io.StringIO())
        row.refresh_from_db()
        self.assertEqual(row.status, 'running')
        call_command('reconcile_usage', apply=True, stdout=io.StringIO())
        row.refresh_from_db()
        self.assertEqual(row.status, 'abandoned_unknown')
        self.assertEqual(CreditAccount.objects.get().reserved, 0)
        self.assertEqual(row.provider_calls.get().status, 'started')
        self.assertGreater(row.estimated_cost, 0)

    def test_expired_deterministic_cache_recomputes(self):
        args = {'chart_id': self.chart.pk, 'charts': ['d1']}
        first = invoke_tool(self.user, 'get_chart_facts', args)
        cache.clear()
        second = invoke_tool(self.user, 'get_chart_facts', args)
        self.assertEqual(first, second)

    def test_observed_zero_searches_do_not_claim_reserved_search_as_actual(self):
        row = self.reserve()
        response = reply()
        response.output = []
        self.provider.responses.create.return_value = response
        with request_budget(row):
            responses_create(self.provider, model='gpt-4o-mini', input='x', tools=[{'type': 'file_search'}])
        call = row.provider_calls.get()
        self.assertEqual((call.file_searches, call.reported_file_searches), (1, 0))
        self.assertLess(call.rated_cost, call.reserved_cost)

    def test_existing_answers_bootstrap_allowance_only_once(self):
        conversation = self.conversation()
        Message.objects.create(conversation=conversation, role=Message.ASSISTANT, content='Historical reading')
        row = self.reserve(conversation)
        self.assertEqual(CreditAccount.objects.get().consumed, 1)
        settle(row.pk, delivered=True)
        self.assertEqual(question_credit_status(self.user)['remaining'], 0)
        with self.assertRaises(BudgetExceeded): self.reserve()

    def test_partial_or_invalid_reading_does_not_consume_customer_credit(self):
        for status, checked in [('partial', True), ('ok', False)]:
            with self.subTest(status=status):
                conversation = self.conversation()
                outcome = append_turn(self.user, conversation.pk, 'Career?', request_id=uuid4(), expected_revision=0,
                    generator=lambda *args, **kwargs: {'status': status, 'answer': 'Synthetic', 'model': 'mock', 'validation': {'passed': checked}})
                self.assertEqual(CreditAccount.objects.get().consumed, 0)
                self.assertEqual(CreditAccount.objects.get().reserved, 0)

    @override_settings(ENFORCE_QUESTION_LIMITS=False)
    def test_disabled_customer_limits_do_not_disable_concurrency_or_provider_limits(self):
        self.reserve()
        self.reserve()
        with self.assertRaises(BudgetExceeded): self.reserve()

    def test_unknown_and_malformed_tariffs_are_not_guessed(self):
        with override_settings(ASTROGPT_API_TARIFFS={}):
            with self.assertRaises(BudgetExceeded): tariff_for('gpt-4o-mini')

    def test_actual_usage_overrun_blocks_publication_and_more_calls(self):
        row = self.reserve()
        self.provider.responses.create.return_value = reply(9999999, 20)
        with request_budget(row):
            with self.assertRaises(BudgetExceeded): responses_create(self.provider, model='gpt-4o-mini', input='x')
            before = self.provider.responses.create.call_count
            with self.assertRaises(BudgetExceeded): responses_create(self.provider, model='gpt-4o-mini', input='x')
            self.assertEqual(self.provider.responses.create.call_count, before)
        self.assertEqual(row.provider_calls.get().status, 'overrun')

    @override_settings(ASTROGPT_AGENT_ENABLED=True)
    def test_factual_agent_request_is_ledgered_without_provider_spend(self):
        from chat.agent_service import generate_question_answer
        with patch('openai.OpenAI', side_effect=AssertionError('Factual lookup must not call LLM')):
            result = append_turn(self.user, self.conversation().pk, 'Who rules my 10th house?',
                request_id=uuid4(), expected_revision=0, generator=generate_question_answer)
        self.assertEqual(result.state, 'complete')
        row = UsageRequest.objects.get()
        self.assertEqual(row.actual_cost, 0)
        self.assertEqual(row.estimated_cost, 0)
        self.assertFalse(row.provider_calls.exists())

    def test_agent_cost_limit_returns_explicit_partial_without_charging(self):
        from astrology.agent.orchestrator import run_consultation
        from astrology.test_agent import ScriptedProvider
        metered_client = self.provider
        class MeteredProvider(ScriptedProvider):
            def complete(self, payload, **kwargs):
                responses_create(metered_client, model='gpt-4o-mini', input='synthetic')
                return super().complete(payload, **kwargs)
        def generate(user, chart, question, depth, **kwargs):
            return run_consultation(user, chart.pk, question, today=date(2026, 11, 7), provider=MeteredProvider())
        policy = {**policy_for('free'), 'cost': '0.000001'}
        with override_settings(ASTROGPT_USAGE_POLICIES={'free': policy}):
            result = append_turn(self.user, self.conversation().pk, 'Is my career generally promising?',
                request_id=uuid4(), expected_revision=0, generator=generate)
        self.assertEqual(result.result['stop_reason'], 'spending_limit')
        self.assertEqual(UsageRequest.objects.get().credits_consumed, 0)
        self.provider.responses.create.assert_not_called()


@override_settings(ENFORCE_QUESTION_LIMITS=True, FREE_QUESTION_CREDITS=1)
class ConcurrentCreditTests(TransactionTestCase):
    def test_p7_05_two_real_connections_cannot_reserve_last_credit_twice(self):
        user = get_user_model().objects.create_user(username='parallel-owner')
        chart = owned_chart(user)
        UserProfile.objects.create(user=user)
        CreditAccount.objects.create(user=user)
        conversations = [Conversation.objects.create(user=user, chart=chart) for _ in range(2)]
        barrier = Barrier(2)
        def worker(pk):
            close_old_connections()
            try:
                local_user = get_user_model().objects.get(pk=user.pk)
                local_chart = SavedChart.objects.get(pk=chart.pk)
                conversation = Conversation.objects.get(pk=pk)
                barrier.wait(timeout=10)
                try:
                    row, created = reserve(local_user, local_chart, conversation, uuid4(), 'Career?')
                    return 'reserved' if created else 'duplicate'
                except BudgetExceeded: return 'no_credit'
                except OperationalError as exc:
                    if 'locked' not in str(exc).lower(): raise
                    return 'busy'
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(worker, [c.pk for c in conversations]))
        self.assertLessEqual(outcomes.count('reserved'), 1)
        self.assertLessEqual(UsageRequest.objects.count(), 1)
        account = CreditAccount.objects.get(user=user)
        self.assertLessEqual(account.reserved + account.consumed, 1)
        self.assertEqual(account.reserved, UsageRequest.objects.count())
        if not outcomes.count('reserved'):
            # SQLite may reject both racing read-to-write upgrades; a fresh retry must make progress.
            reserve(user, chart, conversations[0], uuid4(), 'Career?')
        self.assertEqual(CreditAccount.objects.get(user=user).reserved, 1)
