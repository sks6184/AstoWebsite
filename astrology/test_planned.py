"""Planned consultation: offline tests (synthetic chart, synthetic passages, scripted model; no network).

These show the pipeline's behaviour stage by stage: intent, calculation plan, engine calls, retrieval from
the results, the brief, the fact check and targeted repair. They do not show astrological correctness or
what a live model writes.
"""
from copy import deepcopy
import json
import os
from pathlib import Path

from django.test import override_settings
from django.urls import reverse
from unittest.mock import patch

from accounts.models import UsageRequest
from astrology.agent.general import AgentLimits
from astrology.planned.brief import ordinal
from astrology.planned.checker import SentenceCheck, check_answer, clean_text, prune
from astrology.planned.consultation import PlannedConsultation, run_planned_consultation
from astrology.planned.plan import build_plan, clamp_window, stated_window
from astrology.planned.provider import PlannedProvider, answer_schema, intent_schema
from astrology.planned.retrieval import build_queries, display_title, guided_books, rerank
from astrology.planned.tables import Tables, planet_name as P, sign_name as S
from astrology.test_m3 import M3Base, TODAY, FakeLibrary
from chat.models import Message

TRACE_DIR = Path(__file__).resolve().parent.parent / 'docs' / 'claude_migration' / 'm3_traces'
WINDOW = {'start': '2027-01-01', 'end': '2027-12-31', 'stated': True}
CAREER = {'question_type': 'predictive_timing', 'domains': ['career'],
          'events': ['career:voluntary_employer_change', 'career:promotion'], 'window': WINDOW}
QUESTION = 'Can I get a good job next year?'
# True divisional and Jaimini statements for the synthetic chart, for tests that write their own reading.
BASIS = ' In D10 the 10th lord Jupiter sits in the 6th house in Scorpio. Your Amatyakaraka Moon is placed in the 7th house.'


class Scripted:
    """Scripted model: one reply (or a function of the payload) per stage, in order."""
    name = 'scripted-offline'

    def __init__(self, intent, *answers):
        self.steps = {'intent': [intent], 'answers': list(answers)}
        self.calls = []

    def count_tokens(self, stage, payload):
        return PlannedProvider().count_tokens(stage, payload)      # the real tiktoken count

    def complete(self, stage, payload, *, max_output_tokens, timeout):
        self.calls.append((stage, deepcopy(payload)))
        queue = self.steps['intent'] if stage == 'intent' else self.steps['answers']
        if not queue:
            raise AssertionError(f'scripted model has no reply for stage {stage}')
        step = queue.pop(0)
        if isinstance(step, Exception):
            raise step
        return {'reply': step(payload) if callable(step) else step, 'input_tokens': 2000, 'output_tokens': 500, 'model': 'scripted'}


def astrologer(consultation, **override):
    """A truthful stand-in for the writer: sentences assembled from the engine's tables (never from a model)."""
    t, plan = consultation.tables, consultation.plan
    h = plan.houses['primary'][0]
    lord = t.lords['d1'][h]
    code = lord['lord']
    ruled = ' and '.join(ordinal(x) for x in t.ruled(code))
    natal = (f"Your {ordinal(h)} lord {P(code)} sits in the {ordinal(lord['placed_house'])} house in {S(lord['placed_sign'])}. "
             f"{P(code)} rules the {ruled}. ")
    occupants = t.occupants(h)
    if occupants:
        natal += f"The {ordinal(h)} house is occupied by {' and '.join(P(c) for c in occupants)}. "
    aspecting = t.aspecting(h)
    if aspecting:
        natal += f"The {ordinal(h)} house is aspected by {P(aspecting[0])}. "
    d10 = t.lords.get('d10', {}).get(h)
    divisional = f"In D10 the {ordinal(h)} lord {P(d10['lord'])} sits in the {ordinal(d10['placed_house'])} house in {S(d10['placed_sign'])}." if d10 else ''
    amk = t.karakas.get('Amatyakaraka')
    jaimini = f"Your Amatyakaraka {P(amk['code'])} is placed in the {ordinal(amk['house'])} house." if amk else ''
    periods = ''
    rows = t.dashas.get('vimshottari') or []
    if rows:
        first = rows[0]
        periods = (f"The {P(first['major'])} Mahadasha runs through the window. The {P(first['major'])}/{P(first['sub'])} period runs "
                   f"from {first['start']} to {first['end']}.")
    saturn = next((x for x in t.transits if x['planet'] == 'Sa'), None)
    transits = f"Saturn transits {S(saturn['sign'])}, the {ordinal(saturn['house'])} house from the Lagna, until {saturn['end']}." if saturn else ''
    cite = f"A retrieved source discusses how the relevant houses and their lords are weighed together ({consultation.kept[0]['marker']})." if consultation.kept else ''
    answer = {'direct_answer': f"The indications for the period from {plan.window['start']} to {plan.window['end']} are mixed but workable. "
                               f"Your {ordinal(h)} lord {P(code)} is the main factor.",
              'natal_promise': natal.strip(), 'divisional_confirmation': divisional, 'jaimini_view': jaimini, 'periods': periods, 'transits': transits,
              'event_assessment': ('Promotion is supported by the status factors of the birth chart. A change of employer has fewer direct supports '
                                   'in this window, so the evidence leans to promotion.') if len(plan.events) > 1 else '',
              'conflicts': 'The supportive period rules are qualified by cautionary rules, so the reading stays measured.' if t.conflicts else '',
              'classical_support': cite, 'guidance': 'Prepare steadily and use the better supported stretch of the window.',
              'evidence_strength': {'label': 'moderate', 'reason': 'Several independent calculated factors were compared for this question.'}}
    answer.update(override)
    return answer


@override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('m3-pilot',))
class PlannedBase(M3Base):
    def consult(self, provider, question=QUESTION, **kwargs):
        kwargs.setdefault('knowledge_adapter', self.library)
        self.consultation = PlannedConsultation(self.owner, self.chart.pk, question, today=TODAY, provider=provider, **kwargs)
        return self.consultation.run()

    def truthful(self, **override):
        return lambda payload: astrologer(self.consultation, **override)


class FactCheckTests(PlannedBase):
    """Synthetic chart: Cancer Lagna; Mars (10th lord) in Aquarius, house 8; Mercury in Aries, house 10;
    Venus exalted in Pisces, house 9; Saturn retrograde in Capricorn, house 7; Jupiter Mahadasha with the
    Moon sub-period to 2027-03-14 and then Mars."""

    def setUp(self):
        super().setUp()
        self.consult(Scripted(CAREER, self.truthful()))
        self.c = self.consultation

    def codes(self, sentence, field=None):
        passages = {p['marker']: p for p in self.c.kept}
        check = SentenceCheck(sentence, self.c.tables, self.c.plan, passages, TODAY, field).run()
        return [f['code'] for f in check.findings], check

    TRUE = [
        'Your 10th lord Mars sits in the 8th house in Aquarius.',
        'Mars, the lord of the 10th house, is placed in Aquarius.',
        'Mercury occupies your 10th house in Aries.',
        'Your 10th house, Aries, is occupied by Mercury.',
        'Jupiter aspects the 6th and 8th houses from the 12th.',
        'The 8th house is aspected by Jupiter.',
        'Venus is exalted in Pisces in your 9th house.',
        'Saturn is retrograde in Capricorn, its own sign, in the 7th house.',
        'You are running the Jupiter Mahadasha, with the Moon sub-period until 14 March 2027.',
        'The Jupiter/Mars period begins on 2027-03-14.',
        'Saturn transits Aries, your 10th house, from 3 June 2027 to 19 October 2027.',
        'In D10 the 10th lord Jupiter sits in the 6th house in Scorpio.',
        'Your Amatyakaraka, the Moon, sits in the 7th house.',
        'Your Lagna is Cancer and the Lagna lord Moon is in the 7th house.',
        'Mars rules the 5th and 10th houses.',
        "Jupiter's transit through Cancer, the 1st house from the Lagna and the 7th from the Moon, runs from 25 January 2027 to 25 June 2027.",
        'The Arudha Lagna falls in Aries.',
        'Mars, your 10th lord, also rules the 5th and sits in the 8th house, while Mercury occupies the 10th itself.',
        'With Venus, the 11th lord, exalted in the 9th house, gains are supported.',
        'The Moon and Mars sub-periods cover the window.',
        'The app does not calculate combustion, so that cannot be assessed here.',
        'Sasa Yoga is detected in your chart.',
        'Mars sits in Aquarius in your 8th house and is not exalted there.',
        'The 10th from your Arudha Lagna is in Capricorn (house 7).',
        'In D10, Jupiter as the 10th lord sits in the 6th house.',
        'Mars as the 10th lord in the 8th house of D1 shows pressure.',
        'Jupiter transits Cancer, the 7th sign counted from the Moon, in early 2027.',
        'Saturn in transit through Pisces aspects your 11th house.',
        'Jupiter, transiting your 1st house, aspects the 5th, 7th and 9th houses.',
        'Jupiter transits through Cancer, where it supports houses 1 (self) and 5 (intelligence) during 2027.',   # occupies 1, aspects 5
        'Mars supports your 10th house as its lord.',
        'Saturn strengthens your 9th house by its aspect.',
        'Jupiter in the 12th house aspects the 8th, where exalted Venus is not involved.',
    ]
    FALSE = [
        ('Your 10th lord Venus sits in the 12th house.', 'wrong_house_lord'),
        ('Mars sits in the 10th house.', 'wrong_placement'),
        ('Mars is placed in Leo.', 'wrong_placement'),
        ('Saturn aspects your 10th house.', 'wrong_aspect'),
        ('The 10th house is aspected by Saturn.', 'wrong_aspect'),
        ('Venus is debilitated in your chart.', 'wrong_dignity'),
        ('Jupiter is retrograde in your chart.', 'wrong_retrograde'),
        ('You are running the Saturn Mahadasha now.', 'wrong_period'),
        ('The Jupiter/Saturn period runs through your window.', 'wrong_period'),
        ('The Mars sub-period begins in August 2027.', 'unsupported_date'),
        ('Your Jupiter Mahadasha changes on 5 May 2027.', 'unsupported_date'),
        ('Mercury is combust in your chart.', 'uncalculated_factor'),
        ('Gajakesari Yoga in your chart supports this.', 'yoga_not_detected'),
        ('There is a 70% chance of a new job.', 'event_probability'),
        ('You will definitely get the job.', 'certainty_claim'),
        ('Brihat Parashara Hora Shastra says this placement gives rise.', 'uncited_source'),
        ('Saturn transits your 12th house during 2027.', 'wrong_placement'),
        ('Your 10th house is Leo.', 'wrong_house_sign'),
        ('The SAV of Aries is 45 bindus.', 'wrong_ashtakavarga_value'),
        ('Your Amatyakaraka Venus is strong.', 'wrong_karaka'),
        ('The 10th house is occupied by Saturn.', 'wrong_placement'),
        ('Your Lagna is Leo.', 'wrong_pada_or_karakamsha'),
        ('This is confirmed by the passage (P9).', 'unknown_source_marker'),
        ('The cosmic energies favour you.', 'generic_phrase'),
        ('Strong planetary influences favour employment in your chart.', 'generic_phrase'),
        ('Venus sits in Pisces in your 9th house but is not exalted.', 'wrong_dignity'),
        ('Saturn in Capricorn is not retrograde in your chart.', 'wrong_retrograde'),
        ('Saturn transits Capricorn during 2027.', 'wrong_placement'),          # its natal sign is not its transit sign
        ('The 10th from your Arudha Lagna is in Scorpio.', 'wrong_pada_or_karakamsha'),
        ('The Arudha Lagna falls in Cancer.', 'wrong_pada_or_karakamsha'),           # the uncorrected direct count
        ('Jupiter transits Cancer, your 7th house, in early 2027.', 'wrong_placement'),   # 7th is its count from the Moon
        ('Saturn in transit through Pisces aspects your 10th house.', 'wrong_aspect'),
        # The sentence form of the live error of 2026-11-13: a planet said to "support" a house it neither occupies,
        # rules nor aspects (in the synthetic chart Jupiter in Cancer occupies 1 and aspects 5, 7 and 9, not 3).
        ('Jupiter transits through Cancer, where it indicates gains as it supports houses 1 (identity) and 3 (effort) during 2027.', 'unsupported_relation'),
        ('Jupiter transits Leo, your 8th house, late in 2027.', 'wrong_placement'),          # 8th is its count from the Moon; from the Lagna it is the 2nd
        ('Saturn strengthens the connection with your 11th house.', 'unsupported_relation'),      # no occupation, lordship or aspect
        ('Venus activates your 10th house during this period.', 'unsupported_relation'),
    ]

    def test_true_statements_are_accepted(self):
        for sentence in self.TRUE:
            with self.subTest(sentence=sentence):
                found, check = self.codes(sentence)
                self.assertEqual(found, [], check.findings)

    def test_true_statements_are_verified_with_provenance(self):
        _, check = self.codes('Your 10th lord Mars sits in the 8th house in Aquarius.')
        self.assertGreaterEqual(check.verified, 3)
        self.assertTrue(all(r['evidence_id'] in self.c.evidence for r in check.refs))

    def test_false_statements_are_caught_with_the_calculated_value(self):
        for sentence, code in self.FALSE:
            with self.subTest(sentence=sentence):
                found, check = self.codes(sentence)
                self.assertIn(code, found, check.findings or check.soft)

    def test_a_sentence_in_the_transits_part_is_read_as_a_transit(self):
        sentence = 'Saturn is in Aries (10th house) from 3 June 2027 to 19 October 2027.'
        self.assertIn('wrong_placement', self.codes(sentence)[0])               # as a birth-chart statement it is false
        self.assertEqual(self.codes(sentence, 'transits')[0], [])               # as a transit it is what the engine calculated

    def test_correction_states_the_calculated_value(self):
        _, check = self.codes('Your 10th lord Venus sits in the 12th house.')
        text = ' '.join(f['correction'] for f in check.findings)
        self.assertIn('The lord of house 10 is Mars', text)
        self.assertIn('Venus is in Pisces, house 9', text)

    def test_general_principles_and_source_viewpoints_are_not_judged_as_chart_facts(self):
        marker = self.c.kept[0]['marker']
        for sentence in (f'When the 10th lord is in the 6th house, service is emphasised ({marker}).',
                         'Generally, Saturn in the 10th house gives a slow rise.'):
            with self.subTest(sentence=sentence):
                self.assertEqual(self.codes(sentence)[0], [])

    def test_prune_removes_only_the_wrong_sentence_and_a_sentence_leaning_on_it(self):
        answer = astrologer(self.c, natal_promise='Your 10th lord Mars sits in the 8th house. Saturn aspects your 10th house. '
                                            'This gives heavy pressure at work. Mercury occupies your 10th house.' + BASIS)
        report = check_answer(answer, self.c.tables, self.c.plan, self.c.kept, today=TODAY, conflicts_present=True)
        self.assertEqual([f['code'] for f in report['findings']], ['wrong_aspect'])
        cleaned, removed = prune(answer, report['findings'])
        self.assertEqual(cleaned['natal_promise'], 'Your 10th lord Mars sits in the 8th house. Mercury occupies your 10th house.' + BASIS)
        self.assertEqual(len(removed), 2)
        self.assertTrue(check_answer(cleaned, self.c.tables, self.c.plan, self.c.kept, today=TODAY, conflicts_present=True)['passed'])

    def test_reader_text_has_source_names_and_no_internal_ids(self):
        marker = self.c.kept[0]['marker']
        text = clean_text(f'A source agrees ({marker}). See F0123456789abcdef and [E3].', self.c.kept)
        self.assertIn('(Synthetic Parashari Notes', text)
        self.assertNotRegex(text, r'F0123456789abcdef|E3|\(P\d\)')
        several = clean_text(f'Two sources agree ({marker}, P9 and {marker}).', self.c.kept)      # a list of markers in one bracket
        self.assertEqual(several.count('Synthetic Parashari Notes'), 1)
        self.assertNotIn('P9', several)


def save_trace(name, result, provider):
    """Complete evidence-to-answer trace for a synthetic run (written only when ASTROGPT_WRITE_M3_TRACES=1)."""
    if os.environ.get('ASTROGPT_WRITE_M3_TRACES') != '1':
        return
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    value = {'name': name, 'synthetic': True, 'model': 'scripted offline stand-in (no model call)',
             '1_intent': result['intent'], '2_plan': result['plan'],
             '3_tool_outputs': {e: {'tool': v['tool'], 'arguments': {k: a for k, a in v['arguments'].items() if k != 'chart_id'},
                                    'status': v['result']['status']} for e, v in result['evidence'].items()},
             '4_retrieval': {'searches': next((t['queries'] for t in result['trace'] if t['event'] == 'rerank'), []),
                             'ranking': result['retrieval'], 'passages_given_to_writer': result['passages']},
             '5_brief': result['brief'].split('\n'), '6_answer': result['answer'].split('\n\n'),
             '7_validation': result['validation'], '8_provenance': result['provenance'], 'removed_statements': result['removed_statements'],
             'unsupported': result['unsupported'], 'usage': result['usage'], 'status': result['status'], 'stop_reason': result['stop_reason'],
             'model_calls': [stage for stage, _ in provider.calls],
             'trace': [{k: v for k, v in t.items() if k != 'profile_fingerprint'} for t in result['trace']]}
    (TRACE_DIR / f'planned_{name}.json').write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')


class PipelineTests(PlannedBase):
    def test_normal_path_is_one_intent_call_and_one_writer_call(self):
        provider = Scripted(CAREER, self.truthful())
        result = self.consult(provider)
        save_trace('career_two_events', result, provider)
        self.assertEqual((result['status'], result['stop_reason'], result['published_by']), ('ok', 'complete', 'model'))
        self.assertEqual([stage for stage, _ in provider.calls], ['intent', 'writer'])
        self.assertEqual(result['usage']['rounds'], 2)
        self.assertTrue(result['validation']['passed'])
        self.assertEqual(result['validation']['stage'], 'fact_check')
        self.assertLess(max(result['usage']['round_input_tokens']), AgentLimits().round_input_tokens)

    def test_plan_merges_every_labelled_event_and_domain(self):
        intent = {**CAREER, 'domains': ['career', 'business'],
                  'events': ['career:voluntary_employer_change', 'career:promotion', 'business:starting_a_business']}
        result = self.consult(Scripted(intent, self.truthful()))
        plan = result['plan']
        self.assertEqual(plan['houses']['primary'], [10, 7])
        self.assertTrue({6, 12, 11, 3} <= set(plan['houses']['event']), plan['houses'])      # 6/12 move, 11 promotion, 3 self-effort
        self.assertEqual(plan['events'], intent['events'])
        self.assertEqual(plan['rule_categories'], ['career', 'job'])
        self.assertEqual(plan['vargas'], ['d1', 'd9', 'd10'])
        self.assertIn('Ju', plan['planets'])                                                 # business karaka merged with career's
        self.assertIn('muhurta', plan['unsupported'])                                        # named by the start-a-business guide
        self.assertIn('muhurta and panchanga', result['answer'])                             # and disclosed to the reader

    def test_the_model_chooses_no_tool_and_no_call_is_repeated(self):
        provider = Scripted(CAREER, self.truthful())
        result = self.consult(provider)
        intent_payload = provider.calls[0][1]
        self.assertNotIn('tools', intent_payload)
        calls = [json.dumps([v['tool'], v['arguments']], sort_keys=True) for v in result['evidence'].values()]
        self.assertEqual(len(calls), len(set(calls)))
        tools = [v['tool'] for v in result['evidence'].values()]
        for expected in ('get_chart_facts', 'get_natal_aspects', 'get_ashtakavarga', 'get_jaimini_facts', 'get_counted_sign',
                         'get_dasha_periods', 'get_transits', 'evaluate_astrology_rules', 'get_timing_candidates'):
            self.assertIn(expected, tools)
        self.assertEqual(sorted(v['arguments']['system'] for v in result['evidence'].values() if v['tool'] == 'get_dasha_periods'),
                         ['chara', 'vimshottari', 'yogini'])
        transit = next(v for v in result['evidence'].values() if v['tool'] == 'get_transits')
        self.assertEqual((transit['arguments']['start_date'], transit['arguments']['end_date']), ('2027-01-01', '2027-12-31'))

    def test_a_repeated_planned_call_is_served_once(self):
        self.consult(Scripted(CAREER, self.truthful()))
        c = self.consultation
        before = len(c.evidence)
        first = c.plan.calls[0]
        self.assertEqual(c.calculate(first), c.seen[json.dumps([first['tool'], first['args']], sort_keys=True)])
        self.assertEqual(len(c.evidence), before)
        self.assertEqual(c.trace[-1]['event'], 'deduplicated')

    def test_one_bounded_supplementary_investigation_when_the_window_spans_sub_periods(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        events = [t for t in result['trace'] if t['event'] == 'supplementary']
        self.assertEqual(len(events), 1)
        self.assertIn('more than one Vimshottari sub-period', events[0]['reason'])
        extra = [t for t in result['trace'] if t['event'] == 'tool_result' and t['supplementary']]
        self.assertTrue(1 <= len(extra) <= 2)
        self.assertEqual({t['tool'] for t in extra}, {'evaluate_astrology_rules'})
        self.assertIn('Rules for career as of 2027-03-14', result['brief'])

    def test_retrieval_runs_after_calculation_and_searches_the_actual_results(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        order = [t['event'] for t in result['trace']]
        self.assertGreater(order.index('search'), max(i for i, e in enumerate(order) if e == 'tool_result'))
        queries = self.library.queries
        self.assertTrue(2 <= len(queries) <= AgentLimits().searches)
        # One principle per search, each made applicable by a calculated result (synthetic chart: the 10th lord is
        # in the 8th; Jupiter/Mars covers most of 2027; Saturn's longest stay is in Pisces, the 3rd from the Moon).
        self.assertEqual(queries[0], 'Results of the lord of the 10th house placed in the 8th house; effect on profession')
        self.assertIn('Effects of the sub-period (antardasha) of Mars in the Mahadasha of Jupiter', queries)
        self.assertIn('Results of the transit of Saturn through the 3rd house from the natal Moon (gochara)', queries)
        self.assertTrue(all(q.count(';') <= 1 for q in queries))                           # no string of chart factors
        rerank_event = next(t for t in result['trace'] if t['event'] == 'rerank')
        self.assertIn('contrary', [q['stance'] for q in rerank_event['queries']])          # contrary principles are searched too
        self.assertTrue(all(len(q['query'].encode()) <= 200 for q in rerank_event['queries']))
        self.assertLessEqual(len(result['passages']), 6)
        self.assertIn('BPHS', rerank_event['guided_books'])

    def test_rerank_keeps_semantic_order_and_boosts_overlap_and_guided_books(self):
        def passage(i, score, text, filename):
            citation = {'file_id': f'f{i}', 'filename': filename, 'document': None, 'book': None, 'chapter': None, 'page': None, 'tradition': None}
            return {'evidence_id': f'K{i:020d}', 'snippet': text, 'citation': citation, 'score': score}
        query = {'purpose': 'the natal promise', 'stance': 'supporting', 'query': 'q', 'keys': {'planets': ['Ma'], 'houses': [10, 8]}}
        contrary = {'purpose': 'contrary or cautionary indications', 'stance': 'contrary', 'query': 'c', 'keys': {'planets': [], 'houses': [10]}}
        label = {'question_type': 'predictive_timing', 'domains': ['career'], 'events': ['career:promotion']}
        kept, report = rerank([(query, [passage(1, 0.60, 'Synthetic text on trade.', 'Other_Notes.pdf'),
                                        passage(2, 0.58, 'Synthetic: Mars as tenth lord in the eighth house.', 'Phaladeepika_Synthetic.pdf'),
                                        passage(3, 0.10, 'Synthetic unrelated text.', 'Other_Notes.pdf')]),
                               (contrary, [passage(4, 0.40, 'Synthetic caution about the Xth house.', 'Other_Notes.pdf')])], label)
        by_id = {r['id'][-1]: r for r in report}
        self.assertGreater(by_id['2']['score'], by_id['1']['score'])       # same meaning range, more of the chart's factors, guided book
        self.assertEqual(by_id['2']['guided_book'], 'PD')
        self.assertFalse(by_id['3']['kept'])                               # weak and unrelated
        self.assertTrue(by_id['1']['kept'])                                # kept on its semantic score alone: no keyword needed
        self.assertTrue(by_id['4']['kept'])                                # a contrary passage is always carried when one qualifies
        self.assertEqual(by_id['4']['overlap'], 1.0)                       # "Xth" matches house 10
        self.assertEqual([p['marker'] for p in kept], ['P1', 'P2', 'P3'])

    def test_worked_examples_of_other_charts_are_held_back_from_the_writer(self):
        from astrology.planned.retrieval import worked_example

        def passage(i, score, text):
            citation = {'file_id': f'f{i}', 'filename': 'Synthetic_Notes.pdf', 'document': None, 'book': None, 'chapter': None, 'page': None, 'tradition': None}
            return {'evidence_id': f'K{i:020d}', 'snippet': text, 'citation': citation, 'score': score}
        example = ('Synthetic Chart 12. Analysis of the chart: the native has the tenth lord Mars in the eighth house. In 1994 he changed '
                   'his work, and his position improved.')
        principle = 'Synthetic principle: when the lord of the tenth house is placed in the eighth house, the work meets interruptions.'
        self.assertTrue(worked_example(example))
        self.assertFalse(worked_example(principle))
        natal = {'purpose': 'the 10th lord in the 8th house', 'stance': 'supporting', 'query': 'q', 'keys': {'planets': [], 'houses': [10, 8]}}
        other = {'purpose': "Saturn's transit", 'stance': 'supporting', 'query': 't', 'keys': {'planets': ['Sa'], 'houses': [3]}}
        label = {'question_type': 'predictive_timing', 'domains': ['career'], 'events': []}
        kept, report = rerank([(natal, [passage(1, 0.85, example), passage(2, 0.70, principle)]),
                               (other, [passage(3, 0.80, example.replace('Chart 12', 'Chart 13'))])], label)
        by_id = {r['id'][-1]: r for r in report}
        self.assertTrue(by_id['1']['worked_example'] and not by_id['1']['kept'])     # a higher score does not save a case study
        self.assertTrue(by_id['2']['kept'] and not by_id['2']['worked_example'])
        # When a search finds nothing but a worked example, it is passed on, labelled as one.
        self.assertTrue(by_id['3']['kept'] and by_id['3']['worked_example'])
        self.assertLess(by_id['1']['score'], by_id['2']['score'])

    def test_brief_labels_a_worked_example_and_carries_transit_ashtakavarga(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        self.assertNotIn('a worked example from another person', result['brief'])    # the synthetic passages state principles
        self.assertRegex(result['brief'], r"SAV of Aries: 30\. Saturn's own BAV in Aries: \d of 8\.")
        self.assertRegex(result['brief'], r"SAV of Cancer: 23\. Jupiter's own BAV in Cancer: \d of 8\.")

    def test_a_citation_must_be_about_what_the_sentence_says(self):
        self.consult(Scripted(CAREER, self.truthful()))
        c = self.consultation
        marker = c.kept[0]['marker']
        passages = {p['marker']: p for p in c.kept}
        on_topic = SentenceCheck(f'A source explains how the houses and their lords are weighed together ({marker}).', c.tables, c.plan, passages, TODAY).run()
        self.assertEqual(on_topic.findings, [])
        off_topic = SentenceCheck(f'Marriage after thirty brings lasting happiness ({marker}).', c.tables, c.plan, passages, TODAY).run()
        self.assertEqual([f['code'] for f in off_topic.findings], ['citation_not_supported'])

    def test_saved_record_keeps_the_retained_passages_with_their_sources(self):
        from chat.evidence_manifest import manifest
        result = self.consult(Scripted(CAREER, self.truthful()))
        saved = manifest(result)
        self.assertEqual([s['evidence_id'] for s in saved['sources']], [p['id'] for p in result['passages']])
        first = saved['sources'][0]
        self.assertEqual(first['citation']['filename'], 'Synthetic_Parashari_Notes.pdf')
        self.assertTrue(first['excerpt'].startswith('Synthetic test passage'))
        self.assertTrue(first['retrieved_for'] and first['marker'] == 'P1')
        self.assertFalse(saved.get('truncated'))

    def test_answer_has_no_internal_tags_and_provenance_is_kept_internally(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        self.assertNotRegex(result['answer'], r'\[[FKE][0-9a-f]+\]|\bE\d+\b|\(P\d+|Calculated facts referenced')
        self.assertIn('(Synthetic Parashari Notes', result['answer'])
        self.assertTrue(result['provenance'])
        for row in result['provenance']:
            for ref in row['refs']:
                if 'evidence_id' in ref:
                    self.assertIn(ref['evidence_id'], result['evidence'])
        self.assertTrue(result['claims'])                                  # fact atoms behind the verified statements
        self.assertTrue(all(c['id'].startswith('F') for c in result['claims']))

    def test_an_incorrect_claim_gets_one_targeted_repair(self):
        wrong = self.truthful(natal_promise='Your 10th lord Venus sits in the 12th house. Mercury occupies your 10th house in Aries.')
        provider = Scripted(CAREER, wrong, self.truthful())
        result = self.consult(provider)
        save_trace('career_targeted_repair', result, provider)
        self.assertEqual([stage for stage, _ in provider.calls], ['intent', 'writer', 'repair'])
        repair = provider.calls[2][1]
        self.assertIn('The lord of house 10 is Mars', repair['corrections'])
        self.assertIn('Venus is in Pisces, house 9', repair['corrections'])
        self.assertIn('Correct only the statements listed', repair['corrections'])
        self.assertEqual(repair['previous_answer']['guidance'], 'Prepare steadily and use the better supported stretch of the window.')
        self.assertEqual((result['status'], result['stop_reason']), ('ok', 'complete'))
        self.assertIn('10th lord Mars', result['answer'])
        self.assertNotIn('10th lord Venus', result['answer'])

    def test_a_claim_still_wrong_after_repair_is_removed_not_the_whole_answer(self):
        wrong = self.truthful(natal_promise='Your 10th lord Mars sits in the 8th house in Aquarius. Saturn aspects your 10th house. '
                                      'This brings heavy pressure. Mercury occupies your 10th house in Aries.' + BASIS)
        provider = Scripted(CAREER, wrong, wrong)
        result = self.consult(provider)
        self.assertEqual((result['status'], result['stop_reason'], result['published_by']), ('ok', 'complete', 'model'))
        self.assertNotIn('Saturn aspects', result['answer'])
        self.assertNotIn('heavy pressure', result['answer'])               # the sentence that leaned on it goes too
        self.assertIn('Mercury occupies your 10th house', result['answer'])
        self.assertEqual(len(result['removed_statements']), 2)
        self.assertIn('could not be verified against the calculations were removed', result['answer'])
        self.assertTrue(result['validation']['passed'])
        self.assertEqual(result['validation']['removed_statements'], 2)

    def test_formatting_alone_never_rejects_an_answer(self):
        styled = self.truthful(guidance='## Guidance\n- Prepare steadily.\n- Use the better supported stretch of the window.')
        provider = Scripted(CAREER, styled)
        result = self.consult(provider)
        self.assertEqual([stage for stage, _ in provider.calls], ['intent', 'writer'])
        self.assertEqual(result['stop_reason'], 'complete')

    def test_an_answer_without_calculated_basis_is_repaired_then_falls_back_to_the_evidence_report(self):
        empty = {'direct_answer': 'Things look promising.', 'natal_promise': 'Stay positive.', 'divisional_confirmation': '', 'jaimini_view': '',
                 'periods': 'Soon.', 'transits': '', 'event_assessment': '', 'conflicts': 'None.',
                 'classical_support': '', 'guidance': 'Work hard.', 'evidence_strength': {'label': 'strong', 'reason': 'It simply feels right to say so.'}}
        provider = Scripted(CAREER, empty, empty)
        result = self.consult(provider)
        self.assertEqual((result['status'], result['stop_reason'], result['published_by']), ('partial', 'validation_failed', 'server'))
        self.assertIn('Ground the reading in the calculated placements', provider.calls[2][1]['corrections'])
        self.assertIn('10th house (primary): sign Aries. Its lord Mars is placed in Aquarius, house 8', result['answer'])
        self.assertNotIn('Things look promising', result['answer'])

    def test_writer_failure_gives_the_deterministic_evidence_report(self):
        result = self.consult(Scripted(CAREER, TimeoutError('slow')))
        self.assertEqual((result['status'], result['stop_reason']), ('partial', 'provider_timeout'))
        self.assertIn('could not complete a verified written interpretation', result['answer'])
        self.assertIn('Vimshottari Mahadasha: Jupiter', result['answer'])
        self.assertIn('Saturn transits Aries', result['answer'])

    def test_out_of_scope_runs_no_tool_and_no_search(self):
        provider = Scripted({'question_type': 'out_of_scope', 'domains': [], 'events': [], 'window': WINDOW})
        result = self.consult(provider, 'What will the weather be tomorrow?')
        self.assertEqual((result['stop_reason'], result['evidence'], self.library.queries), ('out_of_scope', {}, []))

    def test_an_event_of_an_unlabelled_domain_is_dropped_not_guessed(self):
        intent = {**CAREER, 'events': ['career:promotion', 'marriage:timing_of_marriage']}
        result = self.consult(Scripted(intent, self.truthful()))
        self.assertEqual(result['label']['events'], ['career:promotion'])
        self.assertIn('events_dropped', [t['event'] for t in result['trace']])

    def test_natal_question_uses_the_running_period_and_no_transits(self):
        intent = {'question_type': 'natal_assessment', 'domains': ['career'], 'events': [], 'window': WINDOW}
        result = self.consult(Scripted(intent, self.truthful(transits='')), 'What does my chart say about my career?')
        tools = [v['tool'] for v in result['evidence'].values()]
        self.assertNotIn('get_transits', tools)
        self.assertNotIn('get_timing_candidates', tools)
        dasha = [v for v in result['evidence'].values() if v['tool'] == 'get_dasha_periods']
        self.assertEqual([(d['arguments']['system'], d['arguments']['start_date'], d['arguments']['end_date']) for d in dasha],
                         [('vimshottari', TODAY.isoformat(), TODAY.isoformat())])
        self.assertEqual(result['stop_reason'], 'complete', result['draft_validation'])
        self.assertNotIn('muhurta', result['answer'])

    def test_concept_question_is_retrieval_and_explanation_only(self):
        intent = {'question_type': 'concept_explanation', 'domains': ['general'], 'events': [], 'window': WINDOW}
        explain = lambda p: {'direct_answer': 'Upapada is the pada of the twelfth house, read for marriage matters.',
                             'natal_promise': f"A retrieved source describes how it is weighed ({self.consultation.kept[0]['marker']}).",
                             'divisional_confirmation': '', 'jaimini_view': '', 'periods': '', 'transits': '', 'event_assessment': '',
                             'conflicts': '', 'classical_support': '', 'guidance': '',
                             'evidence_strength': {'label': 'limited', 'reason': 'This explanation rests on one retrieved passage only.'}}
        result = self.consult(Scripted(intent, explain), 'What is Upapada?')
        self.assertEqual(result['stop_reason'], 'complete', result['draft_validation'])
        self.assertEqual([v['tool'] for v in result['evidence'].values()], ['search_astrology_knowledge'])
        self.assertEqual(self.library.queries, ['What is Upapada?'])

    def test_a_default_window_is_stated_to_the_writer(self):
        intent = {**CAREER, 'window': {'start': 'soon', 'end': '', 'stated': False}}
        result = self.consult(Scripted(intent, self.truthful()), 'Can I get a good job?')
        self.assertEqual(result['plan']['window'], {'start': '2026-11-07', 'end': '2027-11-07', 'stated': False})
        self.assertIn('default: the user gave none', result['brief'])
        self.assertEqual(clamp_window({'start': '2027-01-01', 'end': '2040-01-01', 'stated': True}, TODAY)['end'], '2030-01-01')

    def test_a_period_stated_in_plain_words_is_read_by_the_server(self):
        for question, expected in (('Can I get a good job next year?', ('2027-01-01', '2027-12-31')),
                                   ('Will I change jobs this year?', ('2026-11-07', '2026-12-31')),
                                   ('Any promotion in 2028?', ('2028-01-01', '2028-12-31')),
                                   ('Will I marry in the next six months?', ('2026-11-07', '2027-05-06'))):
            window = stated_window(question, TODAY)
            self.assertEqual((window['start'], window['end'], window['stated']), (*expected, True), question)
        self.assertIsNone(stated_window('What does my chart say about my career?', TODAY))
        # The model's own window is ignored when the question states one.
        intent = {**CAREER, 'window': {'start': '2026-11-07', 'end': '2027-11-07', 'stated': True}}
        result = self.consult(Scripted(intent, self.truthful()))
        self.assertEqual(result['plan']['window'], WINDOW)
        self.assertIn('window_from_question', [t['event'] for t in result['trace']])

    def test_talk_of_jaimini_or_divisional_charts_without_the_actual_factors_is_sent_back(self):
        vague = self.truthful(divisional_confirmation='The divisional charts confirm this.', jaimini_view='The Jaimini indicators agree.')
        provider = Scripted(CAREER, vague, self.truthful())
        result = self.consult(provider)
        first = result['attempts'][0]
        self.assertEqual(first['missing'], ['divisional_basis', 'jaimini_basis'])
        corrections = provider.calls[2][1]['corrections']
        self.assertIn('Add the divisional confirmation with actual placements', corrections)
        self.assertIn('Add the Jaimini view with actual factors', corrections)
        self.assertEqual((result['status'], result['stop_reason']), ('ok', 'complete'))
        self.assertEqual(result['validation']['coverage']['evidence_used'], ['divisional', 'jaimini', 'natal', 'period', 'transit'])

    def test_a_reading_still_missing_a_body_of_evidence_after_repair_is_published_as_partial(self):
        vague = self.truthful(divisional_confirmation='The divisional charts confirm this.', jaimini_view='The Jaimini indicators agree.')
        result = self.consult(Scripted(CAREER, vague, vague))
        self.assertEqual((result['status'], result['stop_reason'], result['published_by']), ('partial', 'complete', 'model'))
        self.assertEqual(result['validation']['missing_sections'], ['divisional_basis', 'jaimini_basis'])
        self.assertIn('10th lord Mars sits in the 8th house', result['answer'])

    def test_passages_given_but_not_cited_are_asked_for_and_then_disclosed_accurately(self):
        silent = self.truthful(classical_support='')
        provider = Scripted(CAREER, silent, silent)
        result = self.consult(provider)
        self.assertEqual(result['attempts'][0]['missing'], ['classical_support'])
        self.assertIn('cite each one you use as (P1)', provider.calls[2][1]['corrections'])
        self.assertIn('Classical passages were retrieved for these factors, but this reading does not cite them.', result['answer'])
        self.assertNotIn('No classical support was retrieved', result['answer'])

    def test_brief_ends_with_the_coverage_checklist(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        checklist = result['brief'].split('WHAT THE READING MUST COVER')[1]
        for needle in ('Natal promise: the 10th, 6th, 12th, 5th, 9th, 11th houses', 'Each event separately (EVENT EVIDENCE)', 'Divisional confirmation: the actual placements in D9, D10',
                       'Jaimini view', 'every Vimshottari sub-period', 'where Saturn and Jupiter transit', 'Both sides'):
            self.assertIn(needle, checklist)

    def test_source_names_are_made_readable_without_adding_anything(self):
        base = {'file_id': None, 'document': None, 'book': None, 'chapter': None, 'page': None, 'tradition': None}
        self.assertEqual(display_title({**base, 'filename': '250256424-Synthetic-Notes-on-Houses-pdf'}), 'Synthetic Notes on Houses')
        self.assertEqual(display_title({**base, 'filename': 'synthetic-varga-notes.pdf'}), 'Synthetic Varga Notes')

    def test_search_failure_is_disclosed_and_the_reading_is_still_written(self):
        self.library = FakeLibrary(fail=TimeoutError('search down'))
        result = self.consult(Scripted(CAREER, self.truthful(classical_support='')))
        self.assertEqual(result['stop_reason'], 'complete', result['draft_validation'])
        self.assertEqual(result['status'], 'partial')
        self.assertIn('retrieval_failed', result['non_answer_states'])
        self.assertIn('could not be searched', result['answer'])
        self.assertIn('None retrieved. Do not name or cite any book', result['brief'])

    def test_brief_carries_the_calculations_and_withholds_policy_sensitive_rule_text(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        brief = result['brief']
        for needle in ('Lagna (Ascendant): Cancer', '10th house (primary): sign Aries. Its lord Mars is placed in Aquarius, house 8',
                       'D10: Lagna Gemini. Its 10th lord Jupiter is in Scorpio, D10 house 6', 'Amatyakaraka: Moon',
                       '10th from the Arudha Lagna: Capricorn',
                       'A count from the Moon is where the planet stands relative to the Moon; it is not an aspect',
                       'Jupiter transits Cancer, 2027-01-25 to 2027-06-25: it occupies house 1 from the Lagna (counted from the Moon it is the 7th sign from the Moon). '
                       'From there it aspects houses 5, 7, 9 from the Lagna (Parashari aspect). SAV of Cancer: 23. Jupiter\'s own BAV in Cancer:', 'Vimshottari sub-period Jupiter / Mars: 2027-03-14 to 2028-02-18',
                       'Yogini Mahadasha: Pingala (Sun)', 'Chara Mahadasha: Pisces',
                       'Sub-period lord: Mars rules houses 5, 10 (the primary house for this question); sits in house 8', 'Saturn transits Aries, 2027-06-03 to 2027-10-19: it occupies house 10 from the Lagna',
                       'Cautionary or mixed', 'Supportive', 'TIMING CANDIDATES', 'NOT CALCULATED BY THIS APP', 'KP cusps'):
            self.assertIn(needle, brief)
        rules = brief.split('TRIGGERED RULES')[1].split('TIMING CANDIDATES')[0]
        self.assertNotRegex(rules, r'death|�')

    def test_schemas_are_strict_and_closed(self):
        intent = intent_schema(self.profile)['schema']
        self.assertIn('career:voluntary_employer_change', intent['properties']['events']['items']['enum'])
        self.assertEqual(set(intent['required']), {'question_type', 'domains', 'events', 'window'})
        answer = answer_schema()['schema']
        self.assertEqual(set(answer['required']), set(answer['properties']))
        self.assertFalse(answer['additionalProperties'])


@override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('m3-pilot',))
class EventEvaluationTests(PlannedBase):
    """Promotion and a change of employer are distinct events: each has its own houses, derived relationships,
    opposing factors and rule count, and the reading must weigh them separately."""

    def test_profile_revision_4_keeps_the_three_career_events_distinct(self):
        from astrology.methodology.profile import ProfileError, validate_profile
        import yaml
        guides = self.profile.entry('career')['event_guides']
        self.assertEqual(self.profile.data['revision'], 4)
        self.assertEqual(guides['voluntary_employer_change']['derived_houses'],
                         {5: 'the 12th from the 6th: separation from the present service', 9: 'the 12th from the 10th: a change of professional position'})
        self.assertNotIn('derived_houses', guides['promotion'])
        self.assertEqual((guides['promotion']['rule_outcomes'], guides['voluntary_employer_change']['rule_outcomes'],
                          guides['involuntary_disruptive_change']['rule_outcomes']), (['promotion_score', 'authority_score'], ['job_change_score'], ['risk_score']))
        for name in ('promotion', 'voluntary_employer_change', 'involuntary_disruptive_change'):
            self.assertTrue(guides[name]['opposing'])
        # Nothing here states an outcome: a derived house is described, never judged.
        self.assertNotRegex(' '.join(guides['voluntary_employer_change']['derived_houses'].values()), r'(?i)job loss|will|must')
        data = yaml.safe_load(open(self.profile_path(), encoding='utf-8'))
        data['domains']['career']['event_guides']['promotion']['rule_outcomes'] = ['luck_score']
        with self.assertRaises(ProfileError):
            validate_profile(data)

    @staticmethod
    def profile_path():
        from astrology.methodology.profile import PROFILE_PATH
        return PROFILE_PATH

    def test_each_event_keeps_its_own_houses_in_the_plan(self):
        self.consult(Scripted(CAREER, self.truthful()))
        events = {e['id']: e for e in self.consultation.plan.events}
        self.assertEqual(events['career:promotion']['houses'], [10, 11])
        self.assertEqual(events['career:promotion']['derived'], {})
        self.assertEqual(events['career:voluntary_employer_change']['houses'], [10, 6, 12])
        self.assertEqual(sorted(events['career:voluntary_employer_change']['derived']), [5, 9])
        self.assertTrue({5, 9} <= set(self.consultation.plan.houses['event']))      # the derived houses are calculated and shown too

    def test_brief_gives_each_event_its_own_evidence(self):
        result = self.consult(Scripted(CAREER, self.truthful()))
        section = result['brief'].split('EVENT EVIDENCE')[1].split('NOT CALCULATED')[0]
        change, promotion = section.split('Event: promotion.')
        self.assertIn('Event: voluntary employer change. Houses read for it: 10, 6, 12.', change)
        self.assertIn('never a rule on their own): the 5th is the 12th from the 6th: separation from the present service; '
                      'the 9th is the 12th from the 10th: a change of professional position.', change)
        # Synthetic chart: Mars rules 5 and 10 and sits in 8; Jupiter rules 6 and 9 and sits in 12.
        self.assertIn('Period Jupiter / Mars (2027-03-14 to 2028-02-18): Jupiter rules 6, 9 (derived: the 12th from the 10th: a change of professional position); '
                      'sits in 12; aspects 6. Mars rules 5 (derived: the 12th from the 6th: separation from the present service), 10.', change)
        self.assertIn('Houses read for it: 10, 11.', promotion)
        self.assertIn('Period Jupiter / Mars (2027-03-14 to 2028-02-18): Mars rules 10; aspects 11.', promotion)
        self.assertNotIn('derived', promotion)
        self.assertIn('Transit Saturn in Aries (2027-06-03 to 2027-10-19): occupies 10', promotion)
        for part in (change, promotion):
            self.assertRegex(part, r'Triggered rules that speak to this event \(a count of rules, not a probability\): \d+ for, \d+ against\.')
            self.assertIn('Would argue against it, if found in the chart above:', part)
        self.assertNotRegex(section, r'(?i)probability of|\d+\s?%|score')

    def test_a_reading_that_merges_the_two_events_is_sent_back(self):
        merged = self.truthful(event_assessment='')
        provider = Scripted(CAREER, merged, self.truthful())
        result = self.consult(provider)
        self.assertEqual(result['attempts'][0]['missing'], ['event_comparison'])
        self.assertIn('take each event in EVENT EVIDENCE in turn', provider.calls[2][1]['corrections'])
        self.assertEqual((result['status'], result['stop_reason']), ('ok', 'complete'))
        self.assertIn('the evidence leans to promotion', result['answer'])

    def test_one_event_needs_no_comparison(self):
        intent = {**CAREER, 'events': ['career:promotion']}
        result = self.consult(Scripted(intent, self.truthful()))
        self.assertEqual(result['stop_reason'], 'complete')
        self.assertTrue(result['validation']['passed'], result['validation'])

    def test_rule_engine_scores_are_never_given_to_the_writer(self):
        # The legacy summary scores add weight x outcome over every triggered rule and clamp at 100, so they
        # saturate and cannot separate two events; the brief carries rule texts and counts instead.
        result = self.consult(Scripted(CAREER, self.truthful()))
        rules = next(v for v in result['evidence'].values() if v['tool'] == 'evaluate_astrology_rules')['result']['data']
        self.assertEqual(rules['score_kind'], 'heuristic outcome scores, not probabilities')
        self.assertNotRegex(result['brief'], r'promotion_score|job_change_score|summary_scores')


class ChartFreshnessTests(PlannedBase):
    """A chart stored under an earlier calculation method is never read silently."""

    def stale(self, **changes):
        from charts.models import SavedChart
        chart = SavedChart.objects.get(pk=self.chart.pk)
        data = deepcopy(chart.chart_data)
        data['calculation_method'] = {'profile': 'lahiri.apparent.earlier.v1'}
        data['chart_template'] = 'earlier_template'
        periods = data['dashas']['vimshottari']['periods']
        periods[0]['start'] = '1900-01-01'                                 # a marker that only a recalculation removes
        SavedChart.objects.filter(pk=chart.pk).update(chart_data=data, **changes)
        return chart

    def test_stale_chart_is_recalculated_before_the_reading_and_the_method_is_traced(self):
        from charts.models import SavedChart
        self.stale()
        provider = Scripted(CAREER, self.truthful())
        result = self.consult(provider)
        self.assertEqual(result['stop_reason'], 'complete', result['trace'][-3:])
        method = result['chart_method']
        self.assertEqual((method['recorded_profile'], method['stale'], method['refreshed']), ('lahiri.apparent.earlier.v1', True, True))
        self.assertEqual(method['profile_after'], method['current_profile'])
        self.assertNotEqual(method['fingerprint_before'], method['chart_fingerprint'])
        stored = SavedChart.objects.get(pk=self.chart.pk).chart_data
        self.assertNotEqual(stored['dashas']['vimshottari']['periods'][0]['start'], '1900-01-01')
        self.assertIn('recalculated with the current calculation method', result['answer'])
        self.assertEqual(result['trace'][0]['event'], 'chart_method')         # before any model call or tool

    def test_stale_chart_that_cannot_be_recalculated_stops_a_timing_question_before_any_paid_call(self):
        self.stale(latitude=None, longitude=None)                          # no coordinates: the app cannot recalculate it
        provider = Scripted(CAREER, self.truthful())
        result = self.consult(provider)
        self.assertEqual((result['status'], result['stop_reason']), ('partial', 'chart_recalculation_required'))
        self.assertEqual(provider.calls, [])                               # "next year" is a dated question: no model call
        self.assertEqual(result['evidence'], {})
        self.assertIn('calculated with an earlier version of the calculation method', result['answer'])
        self.assertIn('this timing question was not answered', result['answer'])

    def test_stale_chart_without_a_stated_period_stops_after_the_label_shows_a_timing_question(self):
        self.stale(latitude=None, longitude=None)
        provider = Scripted(CAREER, self.truthful())
        result = self.consult(provider, 'Will I get a promotion?')
        self.assertEqual(result['stop_reason'], 'chart_recalculation_required')
        self.assertEqual([stage for stage, _ in provider.calls], ['intent'])
        self.assertEqual(result['evidence'], {})


@override_settings(ASTROGPT_AGENT_ENABLED=True, ASTROGPT_AGENT_USERS=('m3-pilot',))
class PlannedUiTests(M3Base):
    def post(self, question=QUESTION, answers=None):
        self.client.force_login(self.owner)
        made = []

        def provider(consultation):
            made.append(consultation)
            return Scripted(CAREER, *(answers or [lambda p: astrologer(consultation)]))
        with patch.object(PlannedConsultation, 'default_provider', provider), \
             patch('astrology.agent.general.KnowledgeSession.__init__', autospec=True,
                   side_effect=lambda s, u, c, a=None: setattr(s, 'user', u) or setattr(s, 'chart_id', c) or
                   setattr(s, 'adapter', self.library) or setattr(s, 'cache', {}) or
                   setattr(s, 'last_usage', {'input_tokens': 0, 'output_tokens': 0, 'provider_rounds': 0})):
            response = self.client.post(reverse('ask_question'), {'chart_id': self.chart.pk, 'question': question,
                                                                  'answer_language': 'English'}, follow=True)
        return response, made

    def test_allow_listed_account_gets_the_planned_consultation_through_the_real_view(self):
        response, made = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(made), 1)
        self.assertContains(response, 'Your 10th lord Mars sits in the 8th house in Aquarius')
        self.assertContains(response, 'Evidence strength: moderate')
        row = UsageRequest.objects.get(user=self.owner)
        self.assertNotIn(row.status, ('reserved', 'running'))
        saved = Message.objects.filter(role=Message.ASSISTANT, conversation__user=self.owner).latest('pk').provenance['evidence']
        self.assertEqual((saved['pipeline'], saved['stop_reason'], saved['published_by']), ('planned_consultation', 'complete', 'model'))
        events = {e['event']: e for e in saved['agent_events']}
        self.assertEqual([e['stage'] for e in saved['agent_events'] if e['event'] == 'round'], ['intent', 'writer'])
        self.assertEqual(events['plan']['houses']['primary'], [10])
        self.assertIn('get_transits', events['plan']['calls'])
        self.assertEqual(events['rerank']['kept'], 4)
        self.assertFalse(saved.get('truncated'))
        self.assertEqual(len(saved['sources']), 4)                           # exactly the passages given to the writer
        self.assertTrue(all(s['excerpt'] and s['retrieved_for'] and s['citation']['filename'] for s in saved['sources']))
        self.assertEqual(saved['chart_method']['recorded_profile'], saved['chart_method']['current_profile'])
        self.assertFalse(saved['chart_method']['stale'])
        self.assertTrue(all(t['method'].get('method_profile') for t in saved['tools'] if t['tool'] != 'search_astrology_knowledge'))
        self.assertTrue(saved['tools'])
        self.assertNotIn('good job next year', json.dumps(saved))          # no question text in the saved diagnostics
        self.assertNotIn('10th lord Mars in the 8th house', json.dumps(saved['agent_events']))   # nor the search text built from the chart

    @override_settings(ASTROGPT_AGENT_PIPELINE='loop')
    def test_the_earlier_agent_loop_stays_selectable(self):
        from chat import agent_service
        with patch.object(agent_service, 'run_general_consultation', return_value={'status': 'ok', 'answer': 'loop'}) as loop:
            agent_service.generate_question_answer(self.owner, self.chart, QUESTION, 'standard')
        self.assertTrue(loop.called)
