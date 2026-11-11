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

    def test_replay_of_live_failure_recovers_with_an_imperfect_model(self):
        """Live run of 2026-11-11 (message 462): wrong argument values, a judgement before any search,
        untagged prose and no coverage. The same kinds of slips must now recover to a valid answer."""
        import re
        lab = label('predictive_timing', 'career', events=['career:voluntary_employer_change'])
        window = {'start_date': '2026-11-07', 'end_date': '2027-11-07'}
        sloppy = [req('get_dasha_periods', system='Vimshottari Dasha', granularity='Antardasha', **window),
                  req('get_transits', planets=['Jupiter', 'Saturn'], output='summary', resolution='daily', **window)]

        def answer(p):
            venus = next(t for t in p['facts'].values() if t.startswith('In D1, Venus is in'))
            sign, house = re.match(r'In D1, Venus is in (\w+), house (\d+)', venus).groups()
            dasha = next(t for t in p['facts'].values() if t.startswith('Vimshottari:'))
            md = re.match(r'Vimshottari: (\w+) Mahadasha', dasha).group(1)
            ordinal = {'1': '1st', '2': '2nd', '3': '3rd'}.get(house, house + 'th')
            body = f'Venus sits in {sign} in your {ordinal} house. The {md} Mahadasha is running across the window.'
            cover = [{**c, 'evidence_ids': ['E1']} for c in p['coverage_template']]
            return reply(final=final(p, body=body, cover=cover))   # default final() states the rule conflicts

        provider = Script(reply(lab, sloppy, judgements=[{'evidence_id': 'E9', 'judgement': 'relevant', 'passage_ids': [], 'note': ''}]),
                          reply(requests=[req('get_chart_facts', charts=['D1', 'D10']),
                                          req('evaluate_astrology_rules', category='Career', as_of='2026-11-07')]),
                          answer)
        response = self.post(provider, 'can I get a new job next year ?')
        self.assertContains(response, 'Evidence strength')
        saved = Message.objects.filter(role=Message.ASSISTANT, conversation__user=self.owner).latest('pk').provenance['evidence']
        events = [e['event'] for e in saved['agent_events']]
        self.assertEqual(saved['stop_reason'], 'complete', saved)
        self.assertIn('arguments_normalized', events)
        self.assertIn('auto_grounded', events)
        self.assertIn('search_judgement_ignored', events)
        self.assertTrue(all(t['status'] in ('ok', 'partial') for t in saved['tools']), saved['tools'])

    def test_draft_sent_with_requests_is_set_aside_and_requests_run(self):
        """Live run of 2026-11-11 (message 464): the model sent requests AND a draft final in the same
        round, twice. The requests must run and the drafts must not consume the repair."""
        lab = label('predictive_timing', 'career', events=['career:voluntary_employer_change'])
        junk = {'direct_answer': 'You will likely get a new job next year.', 'body': 'Jupiter favours it.', 'conflicts': [],
                'evidence_strength': {'label': 'strong', 'reason': 'x'}, 'coverage': [], 'unavailable_calculations': [],
                'no_source_support': True}
        reqs = domain_requests(self.profile, ['career'])
        provider = Script(reply(lab, reqs[:2], final=junk), reply(requests=reqs[2:], final=junk), lambda p: reply(final=final(p)))
        response = self.post(provider, 'can I get a new job next year ?')
        self.assertContains(response, 'Evidence strength')
        saved = Message.objects.filter(role=Message.ASSISTANT, conversation__user=self.owner).latest('pk').provenance['evidence']
        events = [e['event'] for e in saved['agent_events']]
        self.assertEqual(saved['stop_reason'], 'complete', saved)
        self.assertEqual(events.count('premature_final_set_aside'), 2)
        self.assertNotIn('repair_requested', events)
        self.assertTrue(saved['tools'])

    def test_false_untagged_sentence_is_never_auto_grounded(self):
        from astrology.validation.prose_validator import ground
        from astrology.synthesis.fact_catalog import build_catalog
        from astrology.tools import invoke_tool
        facts = invoke_tool(self.owner, 'get_chart_facts', {'chart_id': self.chart.pk, 'charts': ['d1']})
        evidence = {'E1': {'tool': 'get_chart_facts', 'arguments': {}, 'reason': 'x', 'result': facts}}
        catalog = build_catalog(evidence, full=True)
        tenth = facts['data']['charts']['d1']['all_lord_placements']['10_lord']
        name = {'Su': 'Sun', 'Mo': 'Moon', 'Ma': 'Mars', 'Me': 'Mercury', 'Ju': 'Jupiter', 'Ve': 'Venus', 'Sa': 'Saturn'}[tenth['lord']]
        wrong = 10 if tenth['placed_house'] != 10 else 11
        text, count = ground(f'{name} is in your {wrong}th house.', catalog, evidence)
        self.assertEqual(count, 0, text)                       # the lord atom (house 10 + placed house) is not used
        text, count = ground(f"{name} is in {tenth['placed_sign']} in your {tenth['placed_house']}th house.", catalog, evidence)
        self.assertEqual(count, 1)

    def test_repair_round_may_fetch_missing_evidence(self):
        lab = label('natal_assessment', 'marriage', events=['marriage:nature_of_spouse'])
        provider = Script(reply(lab, [req('get_chart_facts', charts=['d1'])]),
                          lambda p: reply(final=final(p, cover=[])),
                          lambda p: reply(requests=[req('get_jaimini_facts'), req('get_chart_facts', charts=['d9'])]),
                          lambda p: reply(final=final(p)))
        response = self.post(provider, 'What kind of spouse does my chart indicate?')
        saved = Message.objects.filter(role=Message.ASSISTANT, conversation__user=self.owner).latest('pk').provenance['evidence']
        self.assertEqual(saved['stop_reason'], 'complete', saved)
        self.assertIn('core_factors_to_fix', provider.payloads[2]['repair'])

    def test_locked_database_during_followup_save_leaves_nothing_stuck(self):
        from uuid import uuid4
        from django.db import OperationalError
        from chat.consultation_service import append_turn
        from chat.models import Conversation, ConsultationTurn
        conversation = Conversation.objects.create(user=self.owner, chart=self.chart)
        result = {'status': 'ok', 'answer': 'text', 'model': 'deterministic', 'validation': {'passed': True}}
        real_create = Message.objects.create

        def create(**kwargs):
            if kwargs.get('role') == Message.ASSISTANT:
                raise OperationalError('database is locked')
            return real_create(**kwargs)

        with patch.object(Message.objects, 'create', side_effect=create):
            outcome = append_turn(self.owner, conversation.pk, 'question', request_id=uuid4(), expected_revision=0,
                                  generator=lambda *a, **k: result)
        self.assertEqual(outcome.http_status, 409)
        conversation.refresh_from_db()
        self.assertIsNone(conversation.active_request)
        self.assertFalse(UsageRequest.objects.filter(user=self.owner, status__in=['reserved', 'running']).exists())
        self.assertFalse(ConsultationTurn.objects.filter(conversation=conversation, state='pending').exists())

    def test_fallback_after_provider_failure_is_saved_and_settled(self):
        lab = label('predictive_timing', 'career', events=['career:promotion'])
        provider = Script(reply(lab, domain_requests(self.profile, ['career'])), TimeoutError('slow'))
        response = self.post(provider)
        self.assertEqual(response.status_code, 200)
        row = UsageRequest.objects.get(user=self.owner)
        self.assertNotIn(row.status, ('reserved', 'running'))
        self.assertContains(response, 'could not complete a verified written interpretation')
