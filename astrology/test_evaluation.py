"""Harness tests use invented response/score fixtures, never actual human evaluation results."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase

from astrology.evaluation import harness


def records():
    return [{'case_id': c['id'], 'system': system, 'answer': 'Synthetic unit-test answer ' + system,
        'metrics': {'latency_ms': 20, 'input_tokens': 100, 'output_tokens': 30,
                    'cost_amount': None, 'currency': None, 'measurement': 'mock_offline'},
        'objective': {'critical_calculation_errors': 0, 'privacy_errors': 0, 'validation_passed': True}}
        for c in harness.load_cases() for system in ('legacy', 'agent')]


class EvaluationTests(SimpleTestCase):
    def test_locked_set_has_36_questions_and_12_followups(self):
        cases = harness.load_cases()
        self.assertEqual(sum(c['parent_id'] is None for c in cases), 36)
        self.assertEqual(sum(c['parent_id'] is not None for c in cases), 12)
        self.assertEqual(hashlib.sha256(harness.FIXTURE.read_bytes()).hexdigest(), harness.LOCK_SHA256)

    def test_lock_rejects_silent_changes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cases.json'
            path.write_bytes(harness.FIXTURE.read_bytes() + b' ')
            path.with_suffix('.sha256').write_text(harness.LOCK_SHA256)
            with patch.object(harness, 'FIXTURE', path), self.assertRaises(ValueError):
                harness.load_cases()

    def test_blinding_hides_system_metrics_and_keeps_followup_context(self):
        supplied = records()
        # Actual prose can reveal writing style, but metadata must not unblind graders.
        for record in supplied: record['answer'] = 'Anonymous supplied answer.'
        packet, key = harness.blinded_packet(supplied, seed='private-unit-test-seed')
        self.assertEqual(len(packet), 48)
        self.assertEqual(len(key), 48)
        self.assertNotIn('legacy', json.dumps(packet))
        self.assertNotIn('agent', json.dumps(packet))
        followup = next(p for p in packet if p['parent_question'])
        self.assertEqual(followup['parent_A'], 'Anonymous supplied answer.')
        self.assertEqual(followup['parent_B'], 'Anonymous supplied answer.')
        self.assertEqual(harness.blinded_packet(supplied, seed='private-unit-test-seed'), (packet, key))

    def test_missing_human_and_performance_data_are_pending_not_wins_or_zero_cost(self):
        supplied = records()
        _, key = harness.blinded_packet(supplied, seed='test')
        report = harness.summarize(supplied, key)
        self.assertEqual(report['gate'], 'BLOCKED')
        self.assertIsNone(report['human']['agent_preference_non_tied'])
        self.assertEqual(report['human']['scored_case_count'], 0)
        self.assertIsNone(report['performance']['agent']['cost_amount']['total'])
        self.assertIn('human_evaluation_incomplete', report['reasons'])
        self.assertIn('live_performance_unverified', report['reasons'])

    def score(self, pair_id):
        return {'pair_id': pair_id, 'assessor': 'unit-test-fixture-not-a-real-vote', 'source': 'human',
            'preference': 'tie', 'quality': {s: {k: 3 for k in
                ('accuracy', 'grounding', 'responsiveness', 'clarity', 'concision')} for s in ('A', 'B')},
            'errors': {'A': 0, 'B': 0}}

    def test_ai_scores_duplicates_and_malformed_scores_are_rejected(self):
        supplied = records()
        _, key = harness.blinded_packet(supplied, seed='test')
        score = self.score(next(iter(key)))
        with self.assertRaises(ValueError): harness.summarize(supplied, key, [score, score])
        score['source'] = 'llm_judge'
        with self.assertRaises(ValueError): harness.summarize(supplied, key, [score])
        score['source'], score['quality'] = 'human', []
        with self.assertRaises(ValueError): harness.summarize(supplied, key, [score])

    def test_preference_errors_quality_and_performance_stay_separate(self):
        supplied = records()
        _, key = harness.blinded_packet(supplied, seed='test')
        pid = next(iter(key))
        score = self.score(pid)
        side = next(s for s in ('A', 'B') if key[pid][s] == 'agent')
        score['preference'] = side
        score['errors'][side] = 1
        report = harness.summarize(supplied, key, [score])
        self.assertEqual(report['human']['agent_preference_non_tied'], 1)
        self.assertEqual(report['human']['observed_errors']['agent'], 1)
        self.assertEqual(report['objective']['agent']['critical_errors'], 0)
        self.assertEqual(len(report['human']['quality_ratings']['agent']), 1)
        self.assertEqual(report['gate'], 'BLOCKED')

    def test_critical_errors_fail_even_if_human_evaluation_is_missing(self):
        supplied = records()
        next(r for r in supplied if r['system'] == 'agent')['objective']['critical_calculation_errors'] = 1
        _, key = harness.blinded_packet(supplied, seed='test')
        self.assertEqual(harness.summarize(supplied, key)['gate'], 'FAIL')

    def test_unknown_objective_counts_are_not_success(self):
        supplied = records()
        for row in supplied: row['objective']['privacy_errors'] = None
        _, key = harness.blinded_packet(supplied, seed='test')
        report = harness.summarize(supplied, key)
        self.assertEqual(report['objective']['agent']['unknown_privacy_cases'], 48)
        self.assertIn('automatic_safety_unknown', report['reasons'])

    def test_size_extra_private_fields_bad_metrics_and_duplicate_records_rejected(self):
        for mutation in (lambda x: x.update(prompt='private'), lambda x: x.update(case_id=[]),
                         lambda x: x.update(answer='x' * 32769),
                         lambda x: x['metrics'].update(latency_ms=float('nan'))):
            supplied = records()
            mutation(supplied[0])
            with self.assertRaises(ValueError): harness.validate_records(supplied)
        supplied = records()
        supplied[1] = deepcopy(supplied[0])
        with self.assertRaises(ValueError): harness.validate_records(supplied)

    def test_cross_currency_totals_and_unknown_metrics_are_not_compared(self):
        supplied = records()
        for index, row in enumerate(supplied):
            row['metrics'].update(cost_amount=1, currency='USD' if index < 2 else 'EUR')
        _, key = harness.blinded_packet(supplied, seed='test')
        report = harness.summarize(supplied, key, latency_ratio_limit=2, cost_ratio_limit=2)
        self.assertIsNone(report['performance']['agent']['cost_amount']['total'])
        self.assertIn('cost_currency_comparison_unverified', report['reasons'])
        with self.assertRaises(ValueError): harness.summarize(supplied, key, cost_ratio_limit=-1)

    def test_injected_collectors_do_not_default_to_paid_provider(self):
        with patch('openai.OpenAI', side_effect=AssertionError('No provider allowed')):
            output = harness.collect_responses({s: lambda case: {'answer': case['question']} for s in ('agent', 'legacy')})
        self.assertEqual(len(output), 96)
        self.assertIsNone(output[0]['metrics']['cost_amount'])
        with self.assertRaises(ValueError): harness.collect_responses({})

    def test_command_creates_private_key_without_calls_and_preserves_existing_artifacts(self):
        with TemporaryDirectory() as tmp, patch('openai.OpenAI', side_effect=AssertionError('No provider')):
            source = Path(tmp) / 'responses.json'
            source.write_text(json.dumps(records()), encoding='utf-8')
            target = Path(tmp) / 'out'
            call_command('p6_evaluate', responses=str(source), output_dir=str(target), seed='test', stdout=io.StringIO())
            report = json.loads((target / 'evaluation_report.json').read_text())
            self.assertEqual(report['gate'], 'BLOCKED')
            self.assertTrue((target / 'PRIVATE_unblinding_key.json').exists())
            with self.assertRaises(CommandError):
                call_command('p6_evaluate', responses=str(source), output_dir=str(target), seed='test', stdout=io.StringIO())
