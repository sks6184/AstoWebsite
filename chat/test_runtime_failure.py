"""Post-P8 runtime regressions. Synthetic charts; provider and network are offline."""
from decimal import Decimal
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse

from accounts.models import UsageRequest
from accounts.provider_meter import Budget, responses_create
from accounts.token_budget import input_token_bound
from accounts.usage_policy import BudgetExceeded
from accounts.test_usage import owned_chart
from chat.agent_service import generate_question_answer
from chat.consultation_service import append_turn
from chat.llm_engine import build_prompt_payload, _system_instructions, _compact_live_evidence
from chat.models import Conversation, Message


class RuntimeTokenTests(SimpleTestCase):
    def test_large_json_is_counted_in_tokens_without_raising_spending_ceiling(self):
        kwargs = {'model': 'gpt-4o-mini', 'input': 'deterministic evidence ' * 16000,
                  'tools': [{'type': 'file_search'}]}
        self.assertGreater(len(json.dumps(kwargs).encode()), 128000)
        self.assertLess(input_token_bound(kwargs, 'gpt-4o-mini'), 128000)
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(usage=None, output=[])
        with patch('socket.socket.connect', side_effect=AssertionError('No network')):
            responses_create(client, **kwargs)
        client.responses.create.assert_called_once()
        reservation = Budget().before(dict(kwargs))
        self.assertEqual(reservation[2], 128000)  # Hosted retrieval still reserves full context.
        self.assertLessEqual(reservation[5], Decimal('0.05'))

    def test_true_token_overflow_is_blocked_before_provider(self):
        client = Mock()
        with self.assertRaisesRegex(BudgetExceeded, 'input_limit'):
            responses_create(client, model='gpt-4o-mini', input='different evidence ' * 100000)
        client.responses.create.assert_not_called()

    def test_context_reserves_output_headroom(self):
        with patch('accounts.provider_meter.input_token_bound', return_value=127000):
            with self.assertRaisesRegex(BudgetExceeded, 'input_limit'):
                Budget().before({'model': 'gpt-4o-mini'})

    def test_missing_tokenizer_fails_closed_without_private_error(self):
        with patch('tiktoken.encoding_for_model', side_effect=OSError('private network detail')):
            with self.assertRaisesRegex(BudgetExceeded, '^tokenizer_unavailable$'):
                input_token_bound({'input': 'private synthetic input'}, 'gpt-4o-mini')

    def test_special_tokens_in_untrusted_input_are_text(self):
        self.assertGreater(input_token_bound({'input': '<|endoftext|> ॐ'}, 'gpt-4o-mini'), 4096)

    def test_yogini_transport_retains_all_overlapping_periods_without_mutating_calculations(self):
        evidence = {'question': {'time_scope': {'start': '2027-01-01', 'end': '2027-12-31'}},
            'yogini': {'periods': [
                {'start': '1990-01-01', 'end': '1998-01-01', 'subperiods': []},
                {'start': '2026-01-01', 'end': '2027-05-01', 'subperiods': [
                    {'start': '2026-01-01', 'end': '2026-12-31'},
                    {'start': '2027-01-01', 'end': '2027-05-01'}]},
                {'start': '2027-05-01', 'end': '2035-01-01', 'subperiods': [
                    {'start': '2027-05-01', 'end': '2028-01-01'}]},
                {'start': '2035-01-01', 'end': '2040-01-01', 'subperiods': []}]}}
        original = deepcopy(evidence)
        selected = _compact_live_evidence(evidence)['yogini']
        self.assertEqual(evidence, original)
        self.assertEqual(len(selected['periods']), 2)
        self.assertEqual(selected['periods'][0]['subperiods'], original['yogini']['periods'][1]['subperiods'][1:])
        self.assertEqual(selected['periods'][1], original['yogini']['periods'][2])


@override_settings(ASTROGPT_AGENT_ENABLED=False, OPENAI_API_KEY='offline-test-key',
    OPENAI_VECTOR_STORE_ID='offline-test-store', OPENAI_MODEL='gpt-4o-mini',
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'runtime-tests'}})
class RuntimeRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='runtime-synthetic')
        cls.chart = owned_chart(cls.owner)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        block = patch('socket.socket.connect', side_effect=AssertionError('No paid/live network'))
        block.start()
        self.addCleanup(block.stop)

    def test_exact_question_real_payload_reaches_provider_and_invalid_draft_stays_unpublished(self):
        question = 'Can I get new job next year ?'
        # Real calculations and real request builder; never load a customer's chart into a test.
        payload = build_prompt_payload(question, self.chart.chart_data, Conversation.FULL)
        kwargs = dict(model='gpt-4o-mini', instructions=_system_instructions(Conversation.FULL),
            input=[{'role': 'user', 'content': [{'type': 'input_text',
                'text': json.dumps(payload, ensure_ascii=False, default=str)}]}],
            tools=[{'type': 'file_search', 'vector_store_ids': ['offline-test-store'], 'max_num_results': 8}])
        self.assertGreater(len(json.dumps(kwargs, ensure_ascii=False).encode()) + 4096, 128000)
        Budget().before(kwargs)  # This precise guard used to raise input_limit.
        conversation = Conversation.objects.create(user=self.owner, chart=self.chart)
        response = SimpleNamespace(output_text='Unverified draft.', output=[], usage=SimpleNamespace(input_tokens=100, output_tokens=20))
        with patch('chat.llm_engine.build_prompt_payload', return_value=payload), patch('chat.llm_engine.OpenAI') as provider:
            provider.return_value.responses.create.return_value = response
            result = append_turn(self.owner, conversation.pk, question, request_id=uuid4(),
                                 expected_revision=0, generator=generate_question_answer)
        # Validation remains real; the deliberately invalid answer cannot be published.
        provider.return_value.responses.create.assert_called_once()
        self.assertEqual(result.state, 'failed')
        row = UsageRequest.objects.get()
        self.assertEqual(row.provider_calls.count(), 1)
        self.assertNotEqual(row.stop_reason, 'input_limit')
        self.assertEqual((row.credits_consumed, row.credits_released), (0, 1))
        self.assertFalse(Message.objects.filter(conversation=conversation, role=Message.ASSISTANT).exists())

    def test_memory_consent_does_not_claim_context_is_active_when_flag_off(self):
        from django.utils import timezone
        conversation = Conversation.objects.create(user=self.owner, chart=self.chart,
            memory_enabled=True, memory_consent_at=timezone.now())
        self.client.force_login(self.owner)
        response = self.client.get(reverse('conversation_detail', args=[conversation.pk]))
        self.assertContains(response, 'Memory consent is on; contextual processing is inactive.')
        self.assertNotContains(response, 'Memory is on.')

    @override_settings(ASTROGPT_AGENT_ENABLED=True)
    def test_memory_flag_on_displays_active_context(self):
        from django.utils import timezone
        conversation = Conversation.objects.create(user=self.owner, chart=self.chart,
            memory_enabled=True, memory_consent_at=timezone.now())
        self.client.force_login(self.owner)
        response = self.client.get(reverse('conversation_detail', args=[conversation.pk]))
        self.assertContains(response, 'Memory is on.')
        self.assertNotContains(response, 'Contextual answers are currently unavailable')

    def test_real_sdk_read_timeout_in_legacy_path_never_charges_completed_reading(self):
        import httpx
        self._assert_sdk_timeout_not_charged(httpx.ReadTimeout)

    def test_real_sdk_connect_timeout_in_legacy_path_never_charges_completed_reading(self):
        import httpx
        self._assert_sdk_timeout_not_charged(httpx.ConnectTimeout)

    def _assert_sdk_timeout_not_charged(self, timeout_type):
        import httpx
        from openai import OpenAI
        from accounts.models import CreditAccount
        from chat import llm_engine

        attempts = []

        def read_timeout(request):
            attempts.append(1)
            raise timeout_type('Synthetic private transport diagnostic', request=request)

        transport = httpx.Client(transport=httpx.MockTransport(read_timeout))
        provider = OpenAI(api_key='offline-test-key', timeout=20, max_retries=0, http_client=transport)
        self.addCleanup(provider.close)
        conversation = Conversation.objects.create(user=self.owner, chart=self.chart)
        # Payload size is covered by the separate real-calculation regression;
        # this test isolates the actual SDK -> meter -> legacy fallback -> settlement path.
        payload = {'evidence_payload': {'question': {'text': 'Can I get new job next year ?'}}}
        with patch.object(llm_engine, 'OpenAI', return_value=provider), \
             patch.object(llm_engine, 'build_prompt_payload', return_value=payload), \
             patch.object(llm_engine, 'validate_answer', wraps=llm_engine.validate_answer) as validation, \
             patch.object(llm_engine, '_repair_answer', wraps=llm_engine._repair_answer) as repair:
            outcome = append_turn(self.owner, conversation.pk, 'Can I get new job next year ?',
                request_id=uuid4(), expected_revision=0, generator=generate_question_answer)
        self.assertEqual(attempts, [1])  # max_retries=0 must be honored by the real SDK.
        validation.assert_not_called()
        repair.assert_not_called()
        # M1 S-2: the user sees an error code, never the provider's exception text.
        self.assertIn('APITimeoutError', outcome.result['answer'])
        self.assertNotIn('Request timed out', outcome.result['answer'])
        self.assertNotIn('Synthetic private transport diagnostic', outcome.result['answer'])
        self.assertNotEqual(outcome.result.get('status'), 'ok')
        row = UsageRequest.objects.get()
        self.assertEqual(row.status, 'partial_free')
        self.assertEqual((row.credits_consumed, row.credits_released), (0, 1))
        call = row.provider_calls.get()
        self.assertEqual((call.status, call.error_code), ('error', 'provider_failure'))
        self.assertIsNone(call.input_tokens)
        self.assertIsNone(call.output_tokens)
        wallet = CreditAccount.objects.get(user=self.owner)
        self.assertEqual((wallet.reserved, wallet.consumed), (0, 0))
        assistant = Message.objects.get(conversation=conversation, role=Message.ASSISTANT)
        self.assertNotEqual(assistant.provenance['status'], 'ok')
