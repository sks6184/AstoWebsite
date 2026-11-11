"""P8 bounded offline pilot: synthetic births, no live provider/payment/email traffic."""
from datetime import date, timedelta
from io import StringIO
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from astrology.agent.orchestrator import run_consultation
from astrology.test_agent import ScriptedProvider
from astrology.tests import sample_chart_data
from charts.forms import SavedChartForm
from charts.models import SavedChart
from chat.consultation_service import append_turn
from chat.models import Conversation, Message
from payments.models import PaymentEvent
from .models import UsageRequest, CreditAccount, AnswerFeedback, PilotMetric, PilotRateBucket
from .pilot_ops import allow_rate, metric
from astro_site.pilot_middleware import SafeJsonFormatter

OFFLINE_RESULTS = {}


@override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_P3_COMPAT=True, FREE_QUESTION_CREDITS=20,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'p8-tests'}})
class PilotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='pilot-owner', password='P8-test-password!987')
        cls.other = get_user_model().objects.create_user(username='pilot-other')
        cls.data = sample_chart_data()
        cls.chart = SavedChart.objects.create(user=cls.user, name='Synthetic private chart', birth_date=date(1990, 5, 17),
            birth_time='10:30', birth_place='Synthetic private place', latitude='28.6139', longitude='77.2090',
            timezone='Asia/Kolkata', chart_data=cls.data)

    def setUp(self):
        self.client.force_login(self.user)
        for target in ('socket.socket.connect', 'openai.OpenAI'):
            block = patch(target, side_effect=AssertionError('Live traffic forbidden in P8 tests'))
            block.start()
            self.addCleanup(block.stop)

    def generate(self, user, chart, question, depth, **kwargs):
        return run_consultation(user, chart.pk, question, today=date(2026, 11, 8),
            provider=ScriptedProvider(), consultation_context=kwargs.get('consultation_context'))

    def consultation(self):
        conversation = Conversation.objects.create(user=self.user, chart=self.chart, memory_enabled=True, memory_consent_at=timezone.now())
        result = append_turn(self.user, conversation.pk, 'Is my career generally promising?',
            request_id=uuid4(), expected_revision=0, generator=self.generate)
        self.assertEqual(result.state, 'complete')
        return conversation

    def chart_payload(self):
        return {'name': 'Pilot synthetic', 'birth_date': '17-May-1990', 'birth_time': '10:30',
            'birth_place': 'Synthetic place', 'latitude': '28.6139', 'longitude': '77.2090', 'timezone': 'Asia/Kolkata'}

    def test_p8_01_signup_chart_question_followup(self):
        client = Client()
        signup = client.post(reverse('account_signup'), {'username': 'new-pilot', 'email': 'pilot@example.test',
            'password1': 'Independent-pilot!739', 'password2': 'Independent-pilot!739'})
        self.assertEqual(signup.status_code, 302)
        user = get_user_model().objects.get(username='new-pilot')
        self.assertIn('_auth_user_id', client.session)
        created = client.post(reverse('chart_create'), self.chart_payload())
        self.assertEqual(created.status_code, 302)
        chart = SavedChart.objects.get(user=user)
        identity = uuid4()
        with patch('chat.views.generate_question_answer', side_effect=self.generate):
            asked = client.post(reverse('ask_question'), {'request_id': identity, 'chart_id': chart.pk,
                'answer_language': 'English', 'question': 'When might I get promoted in May 2027?', 'memory_enabled': 'on'})
            self.assertEqual(asked.status_code, 302)
            conversation = Conversation.objects.get(user=user)
            followed = client.post(reverse('conversation_followup', args=[conversation.pk]), {
                'request_id': uuid4(), 'expected_revision': conversation.revision, 'question': 'What about D10?', 'kind': 'question'})
        self.assertEqual(followed.status_code, 302)
        self.assertEqual(conversation.messages.count(), 4)
        self.assertEqual(UsageRequest.objects.filter(user=user).count(), 2)
        self.assertTrue(PilotMetric.objects.filter(event='signup').exists())
        self.assertTrue(PilotMetric.objects.filter(event='followup').exists())

    def test_p8_02_invalid_inputs_and_calculation_failure_save_nothing(self):
        payload = self.chart_payload()
        for changes in ({'birth_date': '31-Feb-2026'}, {'birth_time': '25:99'}, {'timezone': 'Fake/Zone'},
                        {'latitude': '91'}, {'longitude': '-181'}, {'latitude': ''}, {'birth_date': '01-Jan-2200'}):
            with self.subTest(changes=changes):
                form = SavedChartForm({**payload, **changes})
                self.assertFalse(form.is_valid())
        before = SavedChart.objects.count()
        with patch('charts.views.build_vedic_chart', side_effect=ValueError('private birth data')):
            response = self.client.post(reverse('chart_create'), payload)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'no chart was saved', status_code=400)
        self.assertNotContains(response, 'private birth data', status_code=400)
        self.assertEqual(SavedChart.objects.count(), before)

    def test_p8_03_other_user_cannot_read_chart_chat_summary_progress_or_manifest(self):
        conversation = self.consultation()
        message = conversation.messages.get(role=Message.ASSISTANT)
        row = UsageRequest.objects.get(conversation=conversation)
        self.client.force_login(self.other)
        for route, value in [('conversation_detail', conversation.pk), ('conversation_memory', conversation.pk),
                             ('answer_provenance', message.pk), ('request_status', row.request_id)]:
            self.assertEqual(self.client.get(reverse(route, args=[value])).status_code, 404)
        self.assertEqual(self.client.post(reverse('answer_feedback', args=[message.pk]), {'vote': 'helpful'}).status_code, 404)
        self.client.post(reverse('chart_delete', args=[self.chart.pk]))
        self.assertTrue(SavedChart.objects.filter(pk=self.chart.pk).exists())

    def test_p8_04_csrf_host_private_cache_and_admin_boundaries(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post(reverse('account_delete'), {'confirmation': 'DELETE'}).status_code, 403)
        self.assertEqual(csrf.post(reverse('ask_question'), {}).status_code, 403)
        csrf.get(reverse('ask_question'))
        token = csrf.cookies['csrftoken'].value
        with patch('chat.views.generate_question_answer', side_effect=self.generate):
            accepted = csrf.post(reverse('ask_question'), {'csrfmiddlewaretoken': token, 'request_id': uuid4(),
                'chart_id': self.chart.pk, 'answer_language': 'English', 'question': 'Who rules my 10th house?'})
        self.assertEqual(accepted.status_code, 302)
        response = self.client.get(reverse('ask_question'))
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        with override_settings(ALLOWED_HOSTS=['testserver']):
            self.assertEqual(self.client.get('/', HTTP_HOST='evil.invalid').status_code, 400)
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.user.user_permissions.add(*Permission.objects.all())
        for path in ('/admin/chat/message/', '/admin/charts/savedchart/', '/admin/auth/user/'):
            self.assertNotEqual(self.client.get(path).status_code, 200)
        administrator = Client()
        administrator.post('/admin/login/', {'username': self.user.username, 'password': 'P8-test-password!987', 'next': '/admin/'})
        self.assertNotIn('_auth_user_id', administrator.session)

    def test_p8_05_outage_partial_visible_and_no_credit_consumed(self):
        def outage(user, chart, question, depth, **kwargs):
            return run_consultation(user, chart.pk, question, today=date(2026, 11, 8), provider=ScriptedProvider([TimeoutError()]))
        with patch('chat.views.generate_question_answer', side_effect=outage):
            response = self.client.post(reverse('ask_question'), {'request_id': uuid4(), 'chart_id': self.chart.pk,
                'answer_language': 'English', 'question': 'Is my career generally promising?'})
        page = self.client.get(response.url)
        self.assertContains(page, 'preliminary')
        self.assertEqual(CreditAccount.objects.get(user=self.user).consumed, 0)
        row = UsageRequest.objects.get()
        state = self.client.get(reverse('request_status', args=[row.request_id])).json()
        self.assertFalse(state['active'])
        self.assertEqual(state['credits_consumed'], 0)
        self.assertContains(page, 'no question credit consumed')

    def test_p8_06_account_delete_requires_confirmation_and_cascades_private_data(self):
        conversation = self.consultation()
        message = conversation.messages.get(role=Message.ASSISTANT)
        AnswerFeedback.objects.create(message=message, vote='helpful')
        PaymentEvent.objects.create(user=self.user, gateway='stripe', payload={'private': 'must disappear'})
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        LogEntry.objects.create(user=self.other, content_type=ContentType.objects.get_for_model(SavedChart),
            object_id=str(self.chart.pk), object_repr='Historical private birth record', action_flag=2)
        bad = self.client.post(reverse('account_delete'), {'confirmation': 'DELETE', 'password': 'wrong'})
        self.assertEqual(bad.status_code, 400)
        response = self.client.post(reverse('account_delete'), {'confirmation': 'DELETE', 'password': 'P8-test-password!987'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(UsageRequest.objects.filter(user_id=self.user.pk).exists())
        self.assertFalse(AnswerFeedback.objects.exists())
        self.assertFalse(PaymentEvent.objects.exists())
        self.assertFalse(LogEntry.objects.filter(object_repr='Historical private birth record').exists())
        self.assertTrue(PilotMetric.objects.filter(event='account_deleted').exists())

    def test_p8_07_bounded_offline_burst_limits_and_records_latency(self):
        times, statuses = [], []
        with patch('chat.views.generate_question_answer', side_effect=self.generate):
            for _ in range(12):
                started = time.perf_counter()
                response = self.client.post(reverse('ask_question'), {'request_id': uuid4(), 'chart_id': self.chart.pk,
                    'answer_language': 'English', 'question': 'Who rules my 10th house?'})
                statuses.append(response.status_code)
                times.append((time.perf_counter() - started) * 1000)
        self.assertEqual(statuses.count(302), 10)
        self.assertEqual(statuses.count(429), 2)
        self.assertEqual(UsageRequest.objects.count(), 10)
        self.assertEqual(CreditAccount.objects.get(user=self.user).consumed, 10)
        self.assertFalse(any(row.provider_calls.exists() for row in UsageRequest.objects.all()))
        self.assertTrue(PilotMetric.objects.filter(event='rate_limited').exists())
        # No invented production threshold: this local sample only records a positive elapsed bound.
        self.assertGreater(max(times), 0)
        OFFLINE_RESULTS.update(requests=12, delivered=statuses.count(302), rate_limited=statuses.count(429),
            mean_ms=sum(times) / len(times), p95_ms=sorted(times)[11],
            provider_calls=0, measurement='offline_synthetic_http_client', threshold_agreed=False)

    def test_p8_08_legacy_flag_rollback_keeps_history_and_credits(self):
        conversation = self.consultation()
        count = conversation.messages.count()
        from chat.agent_service import generate_question_answer
        with override_settings(ASTROGPT_AGENT_ENABLED=False), patch('chat.agent_service.generate_placeholder_answer',
            return_value={'status': 'ok', 'answer': 'Verified legacy fixture', 'model': 'mock', 'validation_result': {'passed': True}}) as legacy:
            conversation.refresh_from_db()
            result = append_turn(self.user, conversation.pk, 'Follow-up career question', request_id=uuid4(),
                expected_revision=conversation.revision, generator=generate_question_answer)
        self.assertEqual(result.state, 'complete')
        legacy.assert_called_once()
        self.assertEqual(conversation.messages.count(), count + 2)
        self.assertEqual(UsageRequest.objects.filter(conversation=conversation).count(), 2)

    def test_p8_09_retained_provenance_has_real_fingerprints_and_no_reasoning(self):
        conversation = self.consultation()
        message = conversation.messages.get(role=Message.ASSISTANT)
        metadata = self.client.get(reverse('answer_provenance', args=[message.pk])).json()
        self.assertEqual(metadata['pipeline'], 'agent')
        self.assertTrue(metadata['tools'][0]['fingerprints']['engine_fingerprint'])
        self.assertFalse(metadata['exact_replay_available'])
        self.assertNotIn('reason', json.dumps(metadata))
        self.assertNotIn(self.chart.birth_place, json.dumps(metadata))
        self.assertLess(len(json.dumps(metadata).encode()), 16384)

    def test_historical_answer_has_explicit_unretained_provenance(self):
        conversation = Conversation.objects.create(user=self.user, chart=self.chart)
        message = Message.objects.create(conversation=conversation, role=Message.ASSISTANT, content='Historical answer')
        payload = self.client.get(reverse('answer_provenance', args=[message.pk])).json()
        self.assertEqual(payload['pipeline'], 'historical')
        self.assertIsNone(payload['validated'])

    def test_p8_10_feedback_once_and_metrics_have_no_identity_or_text(self):
        conversation = self.consultation()
        message = conversation.messages.get(role=Message.ASSISTANT)
        for _ in range(2): self.client.post(reverse('answer_feedback', args=[message.pk]), {'vote': 'helpful'})
        self.assertEqual(AnswerFeedback.objects.count(), 1)
        self.assertEqual(PilotMetric.objects.get(event='feedback').count, 1)
        self.assertNotIn('user', {f.name for f in PilotMetric._meta.fields})
        self.assertNotIn('content', {f.name for f in PilotMetric._meta.fields})
        self.assertEqual(self.client.get(reverse('pilot_analytics')).status_code, 403)

    def test_retention_is_dry_run_then_cascades_content_preserving_financial_metadata(self):
        conversation = self.consultation()
        Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now() - timedelta(days=40))
        call_command('purge_pilot_data', stdout=StringIO())
        self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
        call_command('purge_pilot_data', apply=True, stdout=StringIO())
        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertIsNone(UsageRequest.objects.get().conversation_id)

    def test_readiness_detects_wallet_inconsistency_without_dumping_private_data(self):
        self.consultation()
        output = StringIO()
        call_command('pilot_readiness', development=True, stdout=output)
        self.assertTrue(json.loads(output.getvalue())['passed'])
        CreditAccount.objects.filter(user=self.user).update(reserved=99)
        with self.assertRaises(CommandError): call_command('pilot_readiness', development=True, stdout=StringIO())

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
    def test_unverified_session_cannot_bypass_pilot_verification(self):
        from allauth.account.models import EmailAddress
        response = self.client.get(reverse('ask_question'))
        self.assertRedirects(response, reverse('account_email_verification_sent'), fetch_redirect_response=False)
        self.assertFalse(UsageRequest.objects.exists())
        EmailAddress.objects.create(user=self.user, email='verified@example.test', verified=True, primary=True)
        self.assertEqual(self.client.get(reverse('ask_question')).status_code, 200)

    def test_social_deletion_requires_recent_login(self):
        self.client.force_login(self.other)
        session = self.client.session
        session['privacy_authenticated_at'] = 0
        session.save()
        self.assertEqual(self.client.post(reverse('account_delete'), {'confirmation': 'DELETE'}).status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())

    @override_settings(ACCOUNT_ADAPTER='accounts.pilot_adapter.PilotAccountAdapter',
        ASTROGPT_PILOT_SIGNUPS_RESTRICTED=True, ASTROGPT_PILOT_EMAILS=('invited@example.test',))
    def test_non_invited_signup_creates_no_account(self):
        client = Client()
        client.post(reverse('account_signup'), {'username': 'not-invited', 'email': 'outsider@example.test',
            'password1': 'Independent-pilot!739', 'password2': 'Independent-pilot!739'})
        self.assertFalse(get_user_model().objects.filter(username='not-invited').exists())


class ConfigurationTests(SimpleTestCase):
    def test_safe_logging_drops_body_url_and_exception_text(self):
        record = logging.LogRecord('django.request', logging.ERROR, 'private/path', 1,
            'Birth 1990 private question?token=secret', (), None)
        record.request = 'private request body'
        text = SafeJsonFormatter().format(record)
        self.assertNotIn('1990', text)
        self.assertNotIn('secret', text)
        self.assertNotIn('private', text)

    def production_environment(self):
        env = os.environ.copy()
        env.update(DJANGO_SETTINGS_MODULE='astro_site.production', DJANGO_DEBUG='false',
            DJANGO_SECRET_KEY='synthetic-configuration-only-1234567890-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            DJANGO_ALLOWED_HOSTS='pilot.example.test', DATABASE_URL='postgresql://pilot:synthetic@127.0.0.1/pilot',
            EMAIL_HOST='smtp.example.test', DEFAULT_FROM_EMAIL='pilot@example.test', ASTROGPT_PILOT_EMAILS='invited@example.test',
            OPENAI_API_KEY='', OPENAI_VECTOR_STORE_ID='')
        return env

    def test_production_deploy_checks_without_database_or_provider_calls(self):
        process = subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'ERROR'],
            cwd=settings.BASE_DIR, env=self.production_environment(), capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        # Pilot does not assert control of every subdomain or opt into browser preload prematurely.
        self.assertIn('security.W005', process.stderr)
        self.assertIn('security.W021', process.stderr)

    def test_production_rejects_debug_tunnel_and_development_secret(self):
        for changes in ({'DJANGO_DEBUG': 'true'}, {'DJANGO_ALLOWED_HOSTS': 'demo.ngrok-free.app'}, {'DJANGO_SECRET_KEY': 'dev-only-change-me'}):
            env = {**self.production_environment(), **changes}
            process = subprocess.run([sys.executable, '-c', 'import astro_site.production'], cwd=settings.BASE_DIR,
                env=env, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(process.returncode, 0)


class PilotMigrationTests(TransactionTestCase):
    def test_migrate_existing_reading_without_fabricating_provenance(self):
        executor = MigrationExecutor(connection)
        old = [('accounts', '0005_reported_search_usage')]
        try:
            executor.migrate(old)
            apps = executor.loader.project_state(old).apps
            user = apps.get_model('auth', 'User').objects.create(username='pre-p8-user')
            chart = apps.get_model('charts', 'SavedChart').objects.create(user_id=user.pk, name='Old chart',
                birth_date=date(1990, 5, 17), birth_time='10:30', birth_place='Synthetic', chart_data={})
            conversation = apps.get_model('chat', 'Conversation').objects.create(user_id=user.pk, chart_id=chart.pk)
            message = apps.get_model('chat', 'Message').objects.create(conversation_id=conversation.pk, role='assistant', content='Old result', provenance={})
            old_usage = apps.get_model('accounts', 'UsageRequest').objects.create(user_id=user.pk, chart_id=chart.pk,
                conversation_id=conversation.pk, request_id=uuid4(), plan='free', fingerprint='historical',
                status='succeeded', credits_reserved=0, credits_consumed=1)
            apps.get_model('accounts', 'CreditAccount').objects.create(user_id=user.pk, consumed=1, reserved=0)
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            self.assertEqual(Message.objects.get(pk=message.pk).content, 'Old result')
            self.assertEqual(Message.objects.get(pk=message.pk).provenance, {})
            self.assertEqual(PilotMetric.objects.count(), 0)
            self.assertEqual(UsageRequest.objects.get(pk=old_usage.pk).progress, 'queued')
            self.assertEqual(CreditAccount.objects.get(user_id=user.pk).consumed, 1)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
