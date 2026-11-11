"""M3 end-to-end through the real /chat/ view for an allow-listed account (offline, scripted model)."""
import json
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from accounts.models import UsageRequest
from chat.models import Message
from astrology.test_m3 import M3Base, Script, final, label, reply, req, domain_requests


@override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('m3-pilot',))
class M3InterpretiveUiTests(M3Base):
    def post(self, provider, question='In next year can I get a career rise by promotion or job change?'):
        self.client.force_login(self.owner)
        with patch('astrology.agent.general_provider.GeneralProvider', return_value=provider), \
             patch('astrology.agent.general.KnowledgeSession.__init__', autospec=True,
                   side_effect=lambda s, u, c, a=None: setattr(s, 'user', u) or setattr(s, 'chart_id', c) or
                   setattr(s, 'adapter', self.library) or setattr(s, 'cache', {}) or
                   setattr(s, 'last_usage', {'input_tokens': 0, 'output_tokens': 0, 'provider_rounds': 0})):
            return self.client.post(reverse('ask_question'), {'chart_id': self.chart.pk, 'question': question,
                                                              'answer_language': 'English'}, follow=True)

    def test_published_interpretive_answer_is_saved_and_settled(self):
        lab = label('predictive_timing', 'career', events=['career:promotion'])
        provider = Script(reply(lab, domain_requests(self.profile, ['career'])), lambda p: reply(final=final(p)))
        response = self.post(provider)
        self.assertEqual(response.status_code, 200)
        row = UsageRequest.objects.get(user=self.owner)
        self.assertNotIn(row.status, ('reserved', 'running'))
        self.assertTrue(Message.objects.filter(role=Message.ASSISTANT, conversation__user=self.owner).exists())
        self.assertContains(response, 'Evidence strength')

    def test_label_only_first_round_continues_and_diagnostics_are_saved(self):
        lab = label('predictive_timing', 'career', events=['career:promotion', 'career:voluntary_employer_change'])
        provider = Script(reply(lab), reply(requests=domain_requests(self.profile, ['career'])), lambda p: reply(final=final(p)))
        response = self.post(provider, 'can i get new job or get promotion next year .. can you provide timings ?')
        self.assertContains(response, 'Evidence strength')
        self.assertIn('guidance', provider.payloads[1])            # guidance arrives after the label-only round
        saved = Message.objects.filter(role=Message.ASSISTANT, conversation__user=self.owner).latest('pk').provenance['evidence']
        self.assertEqual(saved['stop_reason'], 'complete')
        self.assertEqual(saved['label']['domains'], ['career'])
        self.assertIn('label_only_round', [e['event'] for e in saved['agent_events']])
        self.assertNotIn('can i get new job', json.dumps(saved))   # no question text in diagnostics

    def test_schema_enumerates_event_ids(self):
        from astrology.agent.general_provider import reply_schema
        events = reply_schema()['schema']['properties']['label']['anyOf'][0]['properties']['events']['items']['enum']
        self.assertIn('career:voluntary_employer_change', events)
        self.assertNotIn('career:job_change', events)

    def test_fallback_after_provider_failure_is_saved_and_settled(self):
        lab = label('predictive_timing', 'career', events=['career:promotion'])
        provider = Script(reply(lab, domain_requests(self.profile, ['career'])), TimeoutError('slow'))
        response = self.post(provider)
        self.assertEqual(response.status_code, 200)
        row = UsageRequest.objects.get(user=self.owner)
        self.assertNotIn(row.status, ('reserved', 'running'))
        self.assertContains(response, 'could not complete a verified written interpretation')
