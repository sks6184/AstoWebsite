from datetime import date, datetime, time

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase

from astrology.calculations.annual_yogini import build_annual_yogini_periods
from astrology.calculations.dasha_facts import _current_period as current_dasha_period
from astrology.calculations.dasha_facts import build_dasha_facts
from astrology.calculations.jaimini import (
    build_ak_dasha_caution,
    build_amatyakaraka_factors,
    build_childhood_factors,
    build_karaka_condition_facts,
    build_karakas,
    build_navamsha_jaimini_yogas,
    build_rajayoga_factors,
    build_relationship_factors,
    build_sagittarius_dasha_caution,
    jaimini_aspected_signs,
)
from astrology.calculations.varga import SUPPORTED_VARGAS, build_chart_facts
from astrology.rag.query_builder import build_rag_query
from astrology.rules.engine import run_rule_engine
from astrology.rules.loader import load_rules
from astrology.rules.scoring import aggregate_scores
from astrology.services.prediction_service import build_prediction_evidence
from astrology.synthesis.answer_schema import REQUIRED_SECTIONS
from astrology.synthesis.prompt_builder import build_prompt_messages
from astrology.validation.answer_validator import validate_astrology_answer
from astrology.validation.validator import validate_answer
from chat.llm_engine import _apply_deterministic_remedy, build_prompt_payload as build_live_prompt_payload
from charts.astro_engine import JAIMINI_KARAKAS, _assign_jaimini_karakas, build_vedic_chart
from charts.divisional_confirmation import evaluate_divisional_confirmation
from charts.models import SavedChart
from charts.jaimini import _period_calculation, _subperiods, build_chara_dasha
from charts.planetary_dasha_principles import evaluate_planetary_dasha_pair
from charts.yogini_alignment import build_yogini_alignment
from charts.yogini_baselines import YOGINI_PAIR_BASELINES, evaluate_yogini_baseline
from charts.yogini_event_confirmation import build_event_confirmation
from charts.yogini_derived_meanings import get_experimental_yogini_themes
from charts.yogini_principles import evaluate_yogini_lord
from charts.yogini_reference_frames import build_reference_frames
from charts.yogini_transit_convergence import evaluate_transit_convergence


def sample_chart_data():
    return build_vedic_chart(
        "Sample",
        date(1990, 5, 17),
        time(10, 30),
        "Delhi, India",
        28.6139,
        77.2090,
        "Asia/Kolkata",
    )


class AstrologyEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chart_data = sample_chart_data()

    def test_chart_engine_calculates_supported_vargas(self):
        for chart_key in SUPPORTED_VARGAS:
            self.assertIn(chart_key, self.chart_data)
            self.assertIn("planets", self.chart_data[chart_key])
        self.assertEqual(self.chart_data["dashas"]["yogini"]["calculation_status"], "active")
        self.assertGreater(len(self.chart_data["dashas"]["yogini"]["periods"]), 8)

    def test_jaimini_seven_karakas_exclude_nodes_and_follow_degree_order(self):
        planets = [
            {"code": code, "longitude": longitude}
            for code, longitude in [
                ("Su", 28.0),
                ("Mo", 24.0),
                ("Ma", 20.0),
                ("Me", 16.0),
                ("Ju", 12.0),
                ("Ve", 8.0),
                ("Sa", 4.0),
                ("Ra", 29.0),
                ("Ke", 29.0),
            ]
        ]

        assigned = _assign_jaimini_karakas(planets)

        self.assertEqual(
            [planet["jaimini_karaka"] for planet in assigned[:7]],
            JAIMINI_KARAKAS,
        )
        self.assertEqual(assigned[7]["jaimini_karaka"], "")
        self.assertEqual(assigned[8]["jaimini_karaka"], "")

    def test_jaimini_chara_dasha_repeats_second_cycle_and_exposes_math(self):
        chara = self.chart_data["jaimini"]["chara_dasha"]

        self.assertEqual(chara["cycles_generated"], 2)
        self.assertEqual(len(chara["periods"]), 24)
        self.assertEqual(chara["periods"][0]["sign_number"], chara["periods"][12]["sign_number"])
        self.assertEqual(chara["periods"][0]["duration_years"], chara["periods"][12]["duration_years"])
        self.assertEqual(chara["periods"][0]["cycle"], 1)
        self.assertEqual(chara["periods"][12]["cycle"], 2)
        self.assertIn("count_direction", chara["periods"][0]["calculation"])

    def test_jaimini_chara_dasha_major_and_subperiod_orders(self):
        planets = self.chart_data["d1"]["planets"]
        direct = build_chara_dasha(date(1990, 1, 1), {"sign_number": 1}, planets, cycles=1)
        indirect = build_chara_dasha(date(1990, 1, 1), {"sign_number": 2}, planets, cycles=1)
        subperiods = _subperiods(1, datetime(1990, 1, 1), datetime(1991, 1, 1), 1)

        self.assertEqual([period["sign_number"] for period in direct["periods"][:3]], [1, 2, 3])
        self.assertEqual([period["sign_number"] for period in indirect["periods"][:3]], [2, 1, 12])
        self.assertEqual(subperiods[0]["sign_number"], 2)
        self.assertEqual(subperiods[-1]["sign_number"], 1)

    def test_jaimini_dual_lord_edge_cases_follow_chapter_six(self):
        both_own = [
            {"code": "Ma", "sign_number": 8, "longitude": 217.0},
            {"code": "Ke", "sign_number": 8, "longitude": 219.0},
        ]
        one_own = [
            {"code": "Ma", "sign_number": 8, "longitude": 217.0},
            {"code": "Ke", "sign_number": 6, "longitude": 169.0},
        ]
        associated_lower_degree = [
            {"code": "Ma", "sign_number": 6, "longitude": 151.0},
            {"code": "Ke", "sign_number": 7, "longitude": 194.0},
            {"code": "Ju", "sign_number": 6, "longitude": 155.0},
        ]
        aquarius_one_own = [
            {"code": "Sa", "sign_number": 11, "longitude": 312.0},
            {"code": "Ra", "sign_number": 3, "longitude": 79.0},
        ]

        self.assertEqual(_period_calculation(8, both_own)["duration_years"], 12)
        self.assertEqual(_period_calculation(8, both_own)["lord_selection_rule"], "both_dual_lords_in_own_sign")
        self.assertEqual(_period_calculation(8, one_own)["selected_lord"], "Ke")
        self.assertEqual(_period_calculation(8, one_own)["lord_selection_rule"], "ignore_dual_lord_in_own_sign")
        self.assertEqual(_period_calculation(8, associated_lower_degree)["selected_lord"], "Ma")
        self.assertEqual(
            _period_calculation(8, associated_lower_degree)["lord_selection_rule"],
            "stronger_dual_lord_by_more_associations",
        )
        self.assertEqual(_period_calculation(11, aquarius_one_own)["selected_lord"], "Ra")
        self.assertEqual(_period_calculation(11, aquarius_one_own)["count_direction"], "indirect")

    def test_jaimini_current_period_is_empty_outside_generated_range(self):
        periods = self.chart_data["jaimini"]["chara_dasha"]["periods"]

        self.assertEqual(current_dasha_period(periods, date(1900, 1, 1)), {})

    def test_jaimini_rashi_aspects_follow_sign_modalities(self):
        self.assertEqual(jaimini_aspected_signs(1), [5, 8, 11])
        self.assertEqual(jaimini_aspected_signs(2), [4, 7, 10])
        self.assertEqual(jaimini_aspected_signs(3), [6, 9, 12])

    def test_jaimini_sthira_karakas_are_exposed_as_unscored_reference(self):
        karakas = build_karakas(self.chart_data)

        self.assertEqual(karakas["sthira_karakas"]["1"]["planet"], "Su")
        self.assertEqual(karakas["sthira_karakas"]["10"]["planet"], "Me")
        self.assertEqual(karakas["sthira_karakas_scoring_status"], "unscored_reference_only")

    def test_chart_facts_expose_varga_lookup(self):
        facts = build_chart_facts(self.chart_data, "career")
        d10 = facts["varga"]["charts"]["d10"]
        self.assertIn("planet_lookup", d10)
        self.assertIn("Su", d10["planet_lookup"])
        self.assertIn("10_lord", d10["all_lord_placements"])

    def test_yogini_is_active(self):
        dasha_facts = build_dasha_facts(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))
        yogini = dasha_facts["yogini"]
        self.assertEqual(yogini["calculation_status"], "active")
        self.assertIn("current_yogini_dasha", yogini)
        self.assertIn("current_yogini_subperiod", yogini)
        self.assertIn("pair_assessment", yogini)
        self.assertIn("divisional_confirmation", yogini)
        self.assertIn("classical_baseline", yogini)
        self.assertIn("snapshot_checklist", yogini)
        self.assertGreater(len(yogini["periods"]), 8)

    def test_yogini_lord_quality_is_contextual_not_fixed_by_yogini_name(self):
        supportive_chart = {
            "ascendant": {"sign_number": 1},
            "d1": {"planets": [{"code": "Sa", "house": 7, "sign_number": 7}]},
            "d9": {"planets": [{"code": "Sa", "house": 7, "sign_number": 7}]},
        }
        pressured_chart = {
            "ascendant": {"sign_number": 1},
            "d1": {"planets": [{"code": "Sa", "house": 1, "sign_number": 1}]},
            "d9": {"planets": [{"code": "Sa", "house": 1, "sign_number": 1}]},
        }

        supportive = evaluate_yogini_lord(supportive_chart, "Sa", "general", [])
        pressured = evaluate_yogini_lord(pressured_chart, "Sa", "general", [])

        self.assertEqual(supportive["quality"], "supportive")
        self.assertEqual(pressured["quality"], "pressured")
        self.assertGreater(supportive["score"], pressured["score"])

    def test_yogini_alignment_exposes_chapter_three_lord_assessments(self):
        alignment = build_yogini_alignment(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))

        self.assertEqual(alignment["calculation_status"], "active")
        self.assertNotIn("major_nature", alignment)
        self.assertIn("major_lord_quality", alignment)
        self.assertIn("major_lord_assessment", alignment)
        self.assertEqual(alignment["source_reference"]["chapter"], "Chapter 3: The Basic Principles")

    def test_yogini_lord_assessment_uses_dispositor_for_rahu(self):
        chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ra", "house": 5, "sign_number": 1},
                    {"code": "Ma", "house": 10, "sign_number": 10},
                ]
            },
            "d10": {"planets": [{"code": "Ra", "house": 5, "sign_number": 1}]},
            "d9": {"planets": [{"code": "Ra", "house": 5, "sign_number": 1}]},
        }

        assessment = evaluate_yogini_lord(chart, "Ra", "business", [2, 7, 10, 11])
        factor_codes = {factor["code"] for factor in assessment["factors"]}

        self.assertEqual(assessment["dispositor"]["code"], "Ma")
        self.assertIn("strong_dispositor", factor_codes)
        self.assertIn("category_relevant_dispositor", factor_codes)

    def test_yogini_lord_assessment_surfaces_raja_yoga_activation(self):
        chart = {
            "ascendant": {"sign_number": 2},
            "d1": {"planets": [{"code": "Sa", "house": 10, "sign_number": 11}]},
            "d10": {"planets": [{"code": "Sa", "house": 10, "sign_number": 11}]},
            "d9": {"planets": [{"code": "Sa", "house": 10, "sign_number": 11}]},
        }

        assessment = evaluate_yogini_lord(chart, "Sa", "career", [2, 6, 10, 11])
        factor_codes = {factor["code"] for factor in assessment["factors"]}

        self.assertIn("active_lord_raja_yoga", factor_codes)
        self.assertTrue(any(ref["chapter"].startswith("Chapter 4") for ref in assessment["source_references"]))

    def test_chapter_five_divisional_confirmation_checks_active_lord_in_d10(self):
        chart = {
            "d10": {
                "planets": [
                    {"code": "Asc", "house": 1, "sign_number": 1},
                    {"code": "Ma", "house": 10, "sign_number": 10},
                    {"code": "Su", "house": 5, "sign_number": 5},
                ],
                "houses": [
                    {"number": house, "sign_number": house}
                    for house in range(1, 13)
                ],
            }
        }

        confirmation = evaluate_divisional_confirmation(chart, "career", [10], ["Ma"])
        factor_codes = {factor["code"] for factor in confirmation["factors"]}

        self.assertEqual(confirmation["primary_varga"], "d10")
        self.assertIn("active_lord_in_varga_topic_house", factor_codes)
        self.assertEqual(confirmation["source_reference"]["chapter"], "Chapter 5: Interpretation of Divisional Charts")

    def test_chapter_six_dasha_pair_support_and_pressure(self):
        supportive_chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ma", "house": 1, "sign_number": 1},
                    {"code": "Sa", "house": 10, "sign_number": 10},
                ]
            },
        }
        pressured_chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ma", "house": 1, "sign_number": 1},
                    {"code": "Sa", "house": 8, "sign_number": 8},
                ]
            },
        }

        supportive = evaluate_planetary_dasha_pair(supportive_chart, "Ma", "Sa", [10])
        pressured = evaluate_planetary_dasha_pair(pressured_chart, "Ma", "Sa", [10])

        self.assertTrue(supportive["is_kendra_or_trikona"])
        self.assertEqual(supportive["status"], "supports")
        self.assertTrue(pressured["is_six_eight"])
        self.assertEqual(pressured["status"], "pressured")

    def test_vimshottari_facts_expose_pair_and_divisional_confirmation(self):
        dasha_facts = build_dasha_facts(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))
        vimshottari = dasha_facts["parashari_vimshottari"]

        self.assertIn("pair_assessment", vimshottari)
        self.assertIn("divisional_confirmation", vimshottari)
        self.assertEqual(vimshottari["divisional_confirmation"]["primary_varga"], "d10")

    def test_chapter_seven_yogini_pair_matrix_is_complete_and_low_weight(self):
        baseline = evaluate_yogini_baseline("Sankata", "Siddha")

        self.assertEqual(len(YOGINI_PAIR_BASELINES), 64)
        self.assertEqual(baseline["pair_baseline"]["tone"], "supportive")
        self.assertLessEqual(abs(baseline["score"]), 4)
        self.assertTrue(baseline["is_low_weight_modifier"])

    def test_chapter_eight_snapshot_checklist_is_explanatory_only(self):
        alignment = build_yogini_alignment(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))
        checklist = alignment["snapshot_checklist"]

        self.assertTrue(checklist["aspects_checked"])
        self.assertTrue(checklist["conjunctions_checked"])
        self.assertTrue(checklist["is_snapshot_only"])
        self.assertIn("Do not bypass", checklist["instruction"])
        self.assertTrue(any(ref["chapter"].startswith("Chapter 8") for ref in alignment["source_references"]))

    def test_chapter_nine_event_confirmation_ranks_three_system_intersection_first(self):
        confirmation = build_event_confirmation(
            {"status": "supports", "score": 80},
            {"status": "mixed", "score": 45},
            {"status": "supports", "score": 70},
            {"primary_varga": "d10", "status": "supports", "score": 12},
        )

        self.assertEqual(confirmation["confirmation_count"], 3)
        self.assertEqual(confirmation["intersection_tier"], "intersection_of_three")
        self.assertEqual(confirmation["divisional_confirmation"]["primary_varga"], "d10")

    def test_chapter_ten_reference_frames_include_moon_karaka_and_d10_lagna(self):
        frames = build_reference_frames(self.chart_data, "career", [2, 6, 10, 11])
        labels = {frame["label"] for frame in frames["frames"]}

        self.assertIn("D1 Lagna", labels)
        self.assertIn("Moon as Lagna", labels)
        self.assertIn("Sun as karaka Lagna", labels)
        self.assertIn("D10 Lagna", labels)
        self.assertEqual(frames["primary_varga"], "d10")

    def test_chapter_eleven_transit_convergence_is_confirmation_only(self):
        convergence = evaluate_transit_convergence(self.chart_data, [2, 6, 10, 11], date(2026, 5, 15))

        self.assertLessEqual(convergence["score"], 15)
        self.assertIn("not as the sole prediction basis", convergence["instruction"])
        self.assertIn("moon_lagna_vedha_ranking", convergence["deferred_unscored_rules"])
        self.assertTrue(all("transit_house_from_moon" in trigger for trigger in convergence["triggers"]))

    def test_dasha_facts_expose_chapter_nine_and_ten_evidence(self):
        dasha_facts = build_dasha_facts(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))

        self.assertIn("event_confirmation", dasha_facts)
        self.assertIn("reference_frames", dasha_facts)
        self.assertIn(dasha_facts["event_confirmation"]["confirmation_count"], {0, 1, 2, 3})

    def test_chapter_twelve_annual_yogini_matches_pingala_example(self):
        annual = build_annual_yogini_periods(
            birth_nakshatra_number=13,
            completed_years=26,
            moon_remaining_fraction=0.8,
            annual_chart_start=date(1994, 1, 26),
        )

        self.assertEqual(annual["formula_remainder"], 2)
        self.assertEqual(annual["first_yogini"], "Pingala")
        self.assertEqual(annual["first_balance_days"], 16)
        self.assertEqual(annual["periods"][0]["yogini"], "Pingala")
        self.assertEqual(annual["periods"][-1]["yogini"], "Pingala")
        self.assertEqual(annual["annual_chart_end"], "1995-01-21")
        self.assertEqual(
            annual["scoring_status"],
            "isolated_until_varshaphala_chart_is_calculated",
        )
        self.assertEqual(len(annual["periods"][0]["subperiods"]), 8)

    def test_chapter_thirteen_themes_are_experimental_and_unscored(self):
        themes = get_experimental_yogini_themes("Sankata")

        self.assertTrue(themes["experimental"])
        self.assertFalse(themes["scored"])
        self.assertIn("technical themes", themes["themes"])
        self.assertIn("Do not treat any Yogini as automatically positive or negative", themes["instruction"])

    def test_vimshottari_dasha_lord_facts_include_dignity(self):
        dasha_facts = build_dasha_facts(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))
        first_lord = dasha_facts["parashari_vimshottari"]["dasha_lord_facts"][0]
        self.assertIn("dignity", first_lord["d1"])

    def test_prediction_evidence_includes_parashari_ledger_and_contradictions(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        self.assertEqual(evidence["parashari"]["calculation_status"], "active")
        self.assertIn("rajayoga_factors", evidence["parashari"])
        self.assertIn("evidence_ledger", evidence)
        self.assertTrue(any(item["system"] == "Jaimini" for item in evidence["evidence_ledger"]))
        self.assertTrue(any(item["system"] == "Yogini" for item in evidence["evidence_ledger"]))
        self.assertIn("contradictions", evidence)

    def test_enhanced_jaimini_fields_exist(self):
        dasha_facts = build_dasha_facts(self.chart_data, "career", [2, 6, 10, 11], date(2026, 5, 15))
        jaimini = dasha_facts["jaimini"]
        self.assertIn("karakamsha", jaimini)
        self.assertIn("padas", jaimini)
        self.assertIn("arudha_factors", jaimini)
        self.assertIn("atmakaraka_dasha_caution", jaimini)
        self.assertIn("ak_amk_relation", jaimini)
        self.assertIn("sagittarius_dasha_caution", jaimini)
        self.assertIn("dasha_sign_as_lagna", jaimini)
        self.assertIn("predictive_checklist", jaimini)
        self.assertIn("relationship_factors", jaimini)
        self.assertIn("childhood_factors", jaimini)
        self.assertIn("amatyakaraka_factors", jaimini)
        self.assertIn("rajayoga_factors", jaimini)
        self.assertIn("karaka_condition_facts", jaimini)
        self.assertIn("navamsha_fifth_lord_references", jaimini)
        self.assertIn("tenth_from_karakamsha", jaimini["karakamsha"])
        self.assertIn("eleventh_from_arudha", jaimini["arudha_factors"])
        self.assertEqual(len(jaimini["padas"]["all_padas"]), 12)
        self.assertFalse(jaimini["padas"]["exceptions_applied"])
        self.assertEqual(jaimini["padas"]["planetary_padas"]["calculation_status"], "deferred")
        self.assertEqual(
            len(jaimini["dasha_sign_as_lagna"]["mahadasha"]["houses_from_dasha_sign"]),
            12,
        )
        self.assertEqual(
            jaimini["karaka_condition_facts"]["scoring_status"],
            "unscored_reference_only",
        )
        self.assertIn("darakaraka", jaimini["karaka_method"]["karakas"])
        self.assertIn("putrakaraka", jaimini["karaka_method"]["karakas"])

    def test_chapter_eight_navamsha_confirmation_includes_full_pair_list(self):
        chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ju", "jaimini_karaka": "Atmakaraka"},
                    {"code": "Ve", "jaimini_karaka": "Amatyakaraka"},
                    {"code": "Mo", "jaimini_karaka": "Putrakaraka"},
                    {"code": "Ma", "jaimini_karaka": "Darakaraka"},
                ]
            },
            "d9": {
                "planets": [
                    {"code": "Asc", "sign_number": 1},
                    {"code": "Ju", "sign_number": 3},
                    {"code": "Ve", "sign_number": 3},
                    {"code": "Mo", "sign_number": 3},
                    {"code": "Ma", "sign_number": 3},
                    {"code": "Su", "sign_number": 3},
                ]
            },
        }

        names = {yoga["name"] for yoga in build_navamsha_jaimini_yogas(chart)}

        self.assertIn("D9 Putrakaraka-fifth lord", names)
        self.assertIn("D9 fifth lord-Darakaraka", names)
        self.assertIn("D9 Moon-Venus Jaimini Rajayoga", names)

    def test_upapada_availability_rules_are_unscored(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}

        self.assertEqual(rules["JAIMINI_UPAPADA_FAMILY_RELATION_001"]["weight"], 0)
        self.assertEqual(rules["JAIMINI_UPAPADA_FAMILY_RELATION_001"]["outcomes"], {})
        self.assertEqual(rules["JAIMINI_UPAPADA_MARRIAGE_AVAILABLE_001"]["weight"], 0)
        self.assertEqual(rules["JAIMINI_UPAPADA_MARRIAGE_AVAILABLE_001"]["outcomes"], {})

    def test_chapters_eleven_twelve_relationship_factors_use_reference_axes(self):
        chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ve", "sign_number": 7, "house": 7, "jaimini_karaka": "Darakaraka"},
                    {"code": "Ju", "sign_number": 5, "house": 5, "jaimini_karaka": "Putrakaraka"},
                    {"code": "Ra", "sign_number": 3, "house": 3},
                    {"code": "Ke", "sign_number": 9, "house": 9},
                ]
            },
            "d9": {
                "planets": [
                    {"code": "Asc", "sign_number": 2, "house": 1},
                    {"code": "Ve", "sign_number": 8, "house": 7},
                ]
            },
        }
        padas = {
            "all_padas": {"7": {"pada_sign_number": 4, "pada_sign": "Cancer"}},
            "upapada_lagna": {"pada_sign_number": 11, "pada_sign": "Aquarius"},
        }

        factors = build_relationship_factors(
            chart,
            padas,
            build_karaka_condition_facts(chart),
            {"sign_number": 7},
            {"sign_number": 1},
        )

        self.assertEqual(factors["references"]["d1_lagna"]["seventh_sign_number"], 7)
        self.assertEqual(factors["references"]["darapada"]["sign_number"], 4)
        self.assertEqual(factors["references"]["darakaraka_navamsha"]["sign_number"], 8)
        self.assertGreaterEqual(factors["timing"]["support_count"], 2)
        self.assertTrue(factors["timing"]["antardasha"]["putrakaraka_in_fifth_from_period"])
        self.assertIn("rahu_aspected_signs", factors["rahu_ketu_axis"])
        self.assertIn("pressure_count", factors["pressure"])
        self.assertIn("must not be converted", factors["scoring_note"])

    def test_chapters_eleven_twelve_rules_use_precise_timing_and_caution(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}

        self.assertNotIn("JAIMINI_DARAKARAKA_RELATIONSHIP_001", rules)
        self.assertEqual(
            rules["JAIMINI_RELATIONSHIP_TIMING_STRONG_001"]["condition"]["path"],
            "jaimini.relationship_factors.timing.support_count",
        )
        self.assertEqual(rules["JAIMINI_RELATIONSHIP_PRESSURE_001"]["polarity"], "mixed")
        self.assertNotIn("divorce", rules["JAIMINI_RELATIONSHIP_PRESSURE_001"]["outcomes"])

    def test_chapters_eleven_twelve_relationship_rules_trigger_from_normalized_facts(self):
        result = run_rule_engine(
            {
                "jaimini": {
                    "relationship_factors": {
                        "timing": {"support_count": 2},
                        "pressure": {"pressure_count": 1},
                    }
                }
            },
            "marriage",
        )
        rule_ids = {rule["rule_id"] for rule in result["triggered_rules"]}

        self.assertIn("JAIMINI_RELATIONSHIP_TIMING_STRONG_001", rule_ids)
        self.assertIn("JAIMINI_RELATIONSHIP_PRESSURE_001", rule_ids)
        self.assertNotIn("JAIMINI_RELATIONSHIP_TIMING_SINGLE_001", rule_ids)

    def test_chapter_thirteen_amatyakaraka_facts_expose_placement_influences_and_timing(self):
        chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ju", "sign_number": 10, "house": 10, "jaimini_karaka": "Amatyakaraka"},
                    {"code": "Me", "sign_number": 10, "house": 10},
                    {"code": "Sa", "sign_number": 2, "house": 2},
                    {"code": "Ma", "sign_number": 4, "house": 4},
                ]
            },
        }

        factors = build_amatyakaraka_factors(
            chart,
            {"sign_number": 1},
            {"sign_number": 12},
        )

        self.assertTrue(factors["placement_from_d1_lagna"]["supportive_for_smoother_career"])
        self.assertEqual(factors["timing"]["mahadasha"]["relation"], "amatyakaraka_in_tenth_from_period")
        self.assertEqual(factors["timing"]["antardasha"]["relation"], "amatyakaraka_in_eleventh_from_period")
        self.assertEqual(factors["timing"]["support_count"], 2)
        self.assertTrue(factors["sixth_lord_connection"]["connected"])
        self.assertFalse(factors["eighth_lord_connection"]["connected"])
        self.assertTrue(factors["struggle_capacity_pattern"]["active"])
        self.assertTrue(factors["caution"]["active"])
        self.assertIn("Sa", {planet["code"] for planet in factors["malefic_influences"]})
        self.assertEqual(factors["important_person_scope"]["scoring_status"], "context_only")

    def test_chapter_thirteen_rules_use_normalized_amatyakaraka_facts(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}
        result = run_rule_engine(
            {
                "jaimini": {
                    "amatyakaraka_factors": {
                        "placement_from_d1_lagna": {"supportive_for_smoother_career": True},
                        "timing": {"support_count": 1},
                        "caution": {"active": True},
                        "important_person_scope": {"available": True},
                    }
                }
            },
            "career",
        )
        rule_ids = {rule["rule_id"] for rule in result["triggered_rules"]}

        self.assertEqual(
            rules["JAIMINI_AMK_KEY_PERSONS_001"]["weight"],
            0,
        )
        self.assertEqual(
            rules["JAIMINI_AMK_KEY_PERSONS_001"]["category"],
            ["career", "job", "business"],
        )
        self.assertIn("JAIMINI_CAREER_002", rule_ids)
        self.assertIn("JAIMINI_AMK_CHARA_TIMING_CAREER_001", rule_ids)
        self.assertIn("JAIMINI_AMK_PRESSURE_CAREER_001", rule_ids)

    def test_chapter_fourteen_rajayoga_factors_filter_through_navamsha_and_time_tenth_focus(self):
        chart = {
            "d1": {
                "planets": [
                    {"code": "Ju", "jaimini_karaka": "Atmakaraka"},
                    {"code": "Ve", "jaimini_karaka": "Amatyakaraka"},
                ]
            },
            "d9": {
                "planets": [
                    {"code": "Ju", "sign_number": 2},
                    {"code": "Ve", "sign_number": 5},
                ]
            },
        }
        d1_yogas = [
            {
                "name": "Atmakaraka-Amatyakaraka",
                "planets": [{"code": "Ju", "sign_number": 2}, {"code": "Ve", "sign_number": 5}],
            },
            {
                "name": "Atmakaraka-Putrakaraka",
                "planets": [{"code": "Ju", "sign_number": 2}, {"code": "Mo", "sign_number": 8}],
            },
        ]
        d9_yogas = [
            {
                "name": "D9 Atmakaraka-Amatyakaraka",
                "planets": [{"code": "Ju", "sign_number": 2}, {"code": "Ve", "sign_number": 5}],
            }
        ]

        factors = build_rajayoga_factors(
            chart,
            d1_yogas,
            d9_yogas,
            {"sign_number": 5},
            {"sign_number": 1},
        )

        self.assertEqual(factors["d1_pair_count"], 2)
        self.assertEqual(factors["surviving_pair_count"], 1)
        self.assertEqual(factors["filtered_out_pair_names"], ["Atmakaraka-Putrakaraka"])
        self.assertEqual(factors["navamsha_filtration_status"], "partial_survival")
        self.assertTrue(factors["ak_amk_navamsha_relation"]["supportive"])
        self.assertTrue(factors["timing"]["mahadasha"]["active"])
        self.assertTrue(factors["timing"]["active"])

    def test_chapter_fourteen_rules_score_filtered_survival_and_timing_once(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}
        result = run_rule_engine(
            {
                "jaimini": {
                    "rajayoga_factors": {
                        "d1_pair_count": 2,
                        "surviving_pair_count": 1,
                        "timing": {"active": True},
                    }
                }
            },
            "career",
        )
        rule_ids = {rule["rule_id"] for rule in result["triggered_rules"]}

        self.assertEqual(rules["JAIMINI_RAJA_YOGA_001"]["weight"], 0)
        self.assertEqual(rules["JAIMINI_FULL_RAJA_YOGA_PAIR_001"]["weight"], 0)
        self.assertEqual(rules["JAIMINI_NAVAMSHA_FULL_RAJA_YOGA_001"]["weight"], 0)
        self.assertIn("JAIMINI_NAVAMSHA_RAJA_YOGA_001", rule_ids)
        self.assertIn("JAIMINI_RAJA_YOGA_CHARA_TENTH_FOCUS_001", rule_ids)

    def test_chapters_fifteen_sixteen_expose_guarded_atmakaraka_and_period_cautions(self):
        chart = {
            "ascendant": {"sign_number": 1},
            "d1": {
                "planets": [
                    {"code": "Ju", "sign_number": 5, "house": 5, "jaimini_karaka": "Atmakaraka"},
                ]
            },
            "d9": {
                "planets": [
                    {"code": "Ju", "sign_number": 9, "house": 1},
                ]
            },
        }

        ak_caution = build_ak_dasha_caution(
            chart,
            {"sign_number": 10},
            {"sign_number": 8},
            {"sign_number": 9},
        )
        sixth_eighth_caution = build_sagittarius_dasha_caution(
            chart,
            {"sign_number": 8},
            {"sign_number": 1},
            ak_caution,
        )
        children_caution = build_sagittarius_dasha_caution(
            chart,
            {"sign_number": 6},
            {"sign_number": 9},
            ak_caution,
        )

        self.assertTrue(ak_caution["major_period"]["aspected_by_atmakaraka"])
        self.assertTrue(ak_caution["major_period"]["atmakaraka_in_eighth_from_period"])
        self.assertTrue(ak_caution["subperiod"]["atmakaraka_in_tenth_from_period"])
        self.assertTrue(ak_caution["karakamsha_in_sagittarius"])
        self.assertEqual(ak_caution["d9_dignity"], "own_sign")
        self.assertTrue(sixth_eighth_caution["sixth_or_eighth_subperiod_from_major"]["active"])
        self.assertTrue(sixth_eighth_caution["sixth_or_eighth_subperiod_from_major"]["aspected_by_atmakaraka"])
        self.assertTrue(children_caution["subperiod_active"])
        self.assertTrue(children_caution["children_sixth_house_period"]["active"])
        self.assertIn("Do not convert", sixth_eighth_caution["scoring_note"])

    def test_chapters_fifteen_sixteen_rules_keep_context_unscored_and_cautions_scoped(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}
        result = run_rule_engine(
            {
                "jaimini": {
                    "atmakaraka_dasha_caution": {
                        "active": True,
                        "tenth_house_context_active": True,
                        "sagittarius_reference_active": True,
                        "eighth_house_caution_active": True,
                    },
                    "sagittarius_dasha_caution": {
                        "active": True,
                        "sixth_or_eighth_subperiod_from_major": {
                            "active": True,
                            "aspected_by_atmakaraka": True,
                        },
                        "children_sixth_house_period": {"active": True},
                    },
                }
            },
            "children",
        )
        rule_ids = {rule["rule_id"] for rule in result["triggered_rules"]}

        self.assertEqual(rules["JAIMINI_AK_TENTH_FROM_CHARA_CONTEXT_001"]["weight"], 0)
        self.assertEqual(rules["JAIMINI_AK_SAGITTARIUS_REFERENCE_001"]["weight"], 0)
        self.assertIn("JAIMINI_AK_EIGHTH_FROM_CHARA_CAUTION_001", rule_ids)
        self.assertIn("JAIMINI_CHARA_SUBPERIOD_SIXTH_EIGHTH_CAUTION_001", rule_ids)
        self.assertIn("JAIMINI_CHARA_SUBPERIOD_SIXTH_EIGHTH_AK_ASPECT_CAUTION_001", rule_ids)
        self.assertIn("JAIMINI_CHILDREN_SIXTH_HOUSE_DASHA_CAUTION_001", rule_ids)

    def test_chapter_ten_childhood_factors_use_gnatikaraka_only_as_child_caution(self):
        chart = {
            "d1": {
                "planets": [
                    {"code": "Ve", "sign_number": 9, "house": 9, "jaimini_karaka": "Gnatikaraka"},
                    {"code": "Mo", "sign_number": 9, "house": 9, "jaimini_karaka": "Putrakaraka"},
                    {"code": "Ma", "sign_number": 9, "house": 9},
                    {"code": "Ra", "sign_number": 9, "house": 9},
                ]
            },
        }

        factors = build_childhood_factors(
            chart,
            build_karaka_condition_facts(chart),
            {"sign_number": 10},
            {"sign_number": 9},
        )

        self.assertEqual(factors["gnatikaraka_malefic_influence_count"], 2)
        self.assertTrue(factors["timing"]["antardasha"]["contains_gnatikaraka"])
        self.assertTrue(factors["putrakaraka_gnatikaraka_same_sign"])
        self.assertTrue(factors["putrakaraka_gnatikaraka_active_period"])
        self.assertTrue(factors["sagittarius_gnatikaraka_subperiod_caution"])
        self.assertTrue(factors["caution"]["active"])
        self.assertIn("child-related questions", factors["scoring_note"])

    def test_chapter_ten_rules_trigger_only_for_children_and_score_pressure_once(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}
        evidence = {
            "jaimini": {
                "childhood_factors": {
                    "caution": {"active": True},
                    "putrakaraka_gnatikaraka_active_period": True,
                    "sagittarius_gnatikaraka_subperiod_caution": True,
                }
            }
        }

        children_ids = {
            rule["rule_id"]
            for rule in run_rule_engine(evidence, "children")["triggered_rules"]
        }
        career_ids = {
            rule["rule_id"]
            for rule in run_rule_engine(evidence, "career")["triggered_rules"]
        }

        self.assertEqual(rules["JAIMINI_CHILDHOOD_PK_GK_LINK_CONTEXT_001"]["weight"], 0)
        self.assertEqual(rules["JAIMINI_CHILDHOOD_SAGITTARIUS_GK_CONTEXT_001"]["weight"], 0)
        self.assertIn("JAIMINI_CHILDHOOD_GNATIKARAKA_PRESSURE_001", children_ids)
        self.assertIn("JAIMINI_CHILDHOOD_PK_GK_LINK_CONTEXT_001", children_ids)
        self.assertIn("JAIMINI_CHILDHOOD_SAGITTARIUS_GK_CONTEXT_001", children_ids)
        self.assertNotIn("JAIMINI_CHILDHOOD_GNATIKARAKA_PRESSURE_001", career_ids)

    def test_rules_load_without_errors(self):
        result = load_rules()
        self.assertGreater(result.rules, [])
        self.assertEqual(result.errors, [])

    def test_jaimini_rules_have_sources_and_consistent_scoring_metadata(self):
        jaimini_rules = [
            rule
            for rule in load_rules().rules
            if rule.get("system") == "Jaimini"
        ]

        self.assertEqual(len({rule["rule_id"] for rule in jaimini_rules}), len(jaimini_rules))
        for rule in jaimini_rules:
            self.assertTrue(rule.get("source_book"), rule["rule_id"])
            self.assertTrue(rule.get("source_chapter"), rule["rule_id"])
            self.assertTrue(rule.get("source_page"), rule["rule_id"])
            if rule.get("weight", 0) == 0:
                self.assertEqual(rule.get("outcomes"), {}, rule["rule_id"])
            else:
                self.assertTrue(rule.get("outcomes"), rule["rule_id"])

    def test_zero_weight_rules_never_change_summary_scores(self):
        scores = aggregate_scores(
            [
                {
                    "rule_id": "TRACE_ONLY",
                    "weight": 0,
                    "outcomes": {"risk_score": 99, "promotion_score": 99},
                },
            ],
            "career",
        )

        self.assertEqual(scores["risk_score"], 0)
        self.assertEqual(scores["promotion_score"], 0)

    def test_broad_jaimini_reference_rules_remain_unscored(self):
        rules = {rule["rule_id"]: rule for rule in load_rules().rules}
        context_rule_ids = {
            "JAIMINI_CAREER_001",
            "JAIMINI_MIXED_001",
            "JAIMINI_CAREER_AK_001",
            "JAIMINI_ARUDHA_CAREER_001",
            "JAIMINI_KARAKAMSHA_AVAILABLE_001",
            "JAIMINI_DASHA_SIGN_AS_LAGNA_RELEVANT_001",
            "JAIMINI_DASHA_SIGN_TENTH_OCCUPIED_001",
            "JAIMINI_PUTRAKARAKA_CHILDREN_001",
            "JAIMINI_CHARA_DASHA_CATEGORY_TIMING_001",
        }

        for rule_id in context_rule_ids:
            self.assertEqual(rules[rule_id]["weight"], 0, rule_id)
            self.assertEqual(rules[rule_id]["outcomes"], {}, rule_id)

    def test_prediction_evidence_triggers_rules_scores_and_rag_query(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        self.assertGreater(evidence["rule_engine"]["rule_count"], 0)
        self.assertGreater(evidence["rule_engine"]["triggered_count"], 0)
        self.assertGreater(len(evidence["triggered_rules"]), 0)
        self.assertTrue(any(value > 0 for value in evidence["summary_scores"].values()))
        self.assertEqual(evidence["rag"]["status"], "query_built")
        self.assertIn("D10", evidence["rag"]["query"])
        self.assertIn("future_timing", evidence["transits"])
        self.assertGreaterEqual(evidence["transits"]["future_timing"]["scan_months"], 36)
        self.assertIn("Sarvashtakavarga", evidence["rag"]["query"])

    def test_rag_query_uses_triggered_rules_not_raw_question_only(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        query = build_rag_query(evidence)
        self.assertIn(evidence["triggered_rules"][0]["rule_id"], query)
        self.assertIn("career", query)

    def test_prompt_builder_requires_strict_sections(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        messages = build_prompt_messages(evidence)
        self.assertIn("must not invent chart facts", messages["system"].lower())
        self.assertIn("exact muhurta facts are missing", messages["system"].lower())
        self.assertIn("d10", messages["system"].lower())
        self.assertIn("rahu", messages["system"].lower())
        self.assertIn("mercury", messages["system"].lower())
        for section in REQUIRED_SECTIONS:
            self.assertIn(section, messages["user"])
        self.assertEqual(evidence["synthesis"]["status"], "prompt_built")

    def test_live_chat_payload_uses_hybrid_evidence_systems(self):
        payload = build_live_prompt_payload(
            "Will I get promoted or switch job?",
            self.chart_data,
            depth_level=2,
        )
        evidence = payload["evidence_payload"]
        self.assertNotIn("computed_context", payload)
        self.assertEqual(evidence["parashari"]["calculation_status"], "active")
        self.assertEqual(evidence["jaimini"]["calculation_status"], "active")
        self.assertEqual(evidence["yogini"]["calculation_status"], "active")
        self.assertIn(evidence["varga"]["status"], {"supports", "mixed", "weak", "active"})
        self.assertIn("parashari_vimshottari", evidence)
        self.assertIn("Sarvashtakavarga", evidence["rag_context_request"]["query"])
        self.assertGreaterEqual(evidence["transits"]["future_timing"]["scan_months"], 36)
        self.assertGreater(len(evidence["remedy_context"]["remedies"]), 0)
        self.assertTrue(any(item["system"] == "Jaimini" for item in evidence["evidence_ledger"]))
        self.assertTrue(any(item["system"] == "Yogini" for item in evidence["evidence_ledger"]))
        self.assertTrue(any(item["system"] == "Divisional" for item in evidence["evidence_ledger"]))

    def test_validator_rejects_generic_answer(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        answer = "Stay positive and work hard. Good things will happen soon."
        result = validate_answer(answer, evidence)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["issues"]), 0)
        self.assertIn("Regenerate", result["repair_instruction"])

    def test_validator_accepts_evidence_based_answer(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        # Derive active lord names from evidence so the answer stays in sync with the chart
        from charts.vedic_utils import PLANET_NAMES
        vimshottari = evidence.get("parashari_vimshottari", {})
        md_code = (vimshottari.get("current_mahadasha") or {}).get("lord", "Ju")
        ad_code = (vimshottari.get("current_antardasha") or {}).get("lord", "Mo")
        md_name = PLANET_NAMES.get(md_code, md_code)
        ad_name = PLANET_NAMES.get(ad_code, ad_code)
        md_start = (vimshottari.get("current_mahadasha") or {}).get("start", "")
        md_end = (vimshottari.get("current_mahadasha") or {}).get("end", "")
        yogini = evidence.get("yogini", {})
        yogini_name = yogini.get("current_yogini_dasha", {}).get("yogini", "Pingala")
        sub_yogini = yogini.get("current_yogini_subperiod", {}).get("yogini", "Dhanya")
        jaimini = evidence.get("jaimini", {})
        karakas = (jaimini.get("karaka_method") or {}).get("karakas", {})
        ak_code = (karakas.get("atmakaraka") or {}).get("planet", "Ma")
        amk_code = (karakas.get("amatyakaraka") or {}).get("planet", "Mo")
        ak_name = PLANET_NAMES.get(ak_code, ak_code)
        amk_name = PLANET_NAMES.get(amk_code, amk_code)
        answer = "\n".join(
            [
                "### Jyotish Analysis",
                f"Career improvement is possible. "
                f"The chart shows mixed support — some career activation is indicated, but delay and risk are present. "
                f"The workable timing should be watched around **May 2026 to June 2026**, not treated as a guarantee. "
                f"D10 (Dashamsha) is central for this career question.",
                "### Why We Advise That",
                f"Parashari/Vimshottari: The active dasha is {md_name} Mahadasha / {ad_name} Antardasha "
                f"({md_start} to {md_end}). Transit timing and Sarvashtakavarga points support this window. "
                f"Jaimini/Chara: {ak_name} as Atmakaraka and {amk_name} as Amatyakaraka are assessed through "
                f"Chara Dasha and Arudha factors. "
                f"Yogini: The active {yogini_name} Yogini major period with {sub_yogini} sub-period is considered. "
                f"D10 placements and Sarvashtakavarga support the career assessment.",
                "### Remedy",
                "- Beej Mantra guidance is included from deterministic remedy context.",
                "### Practical Guidance",
                "The practical prediction is cautious about timing and avoids irreversible advice.",
            ]
        )
        result = validate_answer(answer, evidence)
        self.assertTrue(result["passed"], result["issues"])

    def test_deterministic_remedy_replaces_missing_mantra_text(self):
        payload = build_live_prompt_payload(
            "When should I start my astrology website business?",
            self.chart_data,
            depth_level=2,
        )
        answer = "\n".join(
            [
                "### Jyotish Analysis",
                "The reading is preliminary.",
                "### Remedy",
                "No deterministic remedy was calculated.",
                "### Practical Guidance",
                "Prepare quietly.",
            ]
        )
        repaired = _apply_deterministic_remedy(answer, payload)
        self.assertIn("Beej Mantra", repaired)
        self.assertNotIn("No deterministic remedy was calculated", repaired)

    def test_deterministic_remedy_replaces_llm_remedy_with_actual_beej_mantra(self):
        payload = build_live_prompt_payload(
            "When should I start my astrology website business?",
            self.chart_data,
            depth_level=2,
        )
        answer = "\n".join(
            [
                "### Jyotish Analysis",
                "The reading is preliminary.",
                "### Remedy",
                "- Pray with discipline during this period.",
                "### Practical Guidance",
                "Prepare quietly.",
            ]
        )
        repaired = _apply_deterministic_remedy(answer, payload)
        self.assertIn("Beej Mantra", repaired)
        self.assertIn("Deity Mantra", repaired)
        self.assertNotIn("Pray with discipline during this period", repaired)

    def test_midday_transit_sampling_handles_sun_taurus_ingress(self):
        sunny_chart = build_vedic_chart(
            "Sunny",
            date(1983, 6, 6),
            time(11, 47),
            "Dehri On Son, Bihar",
            24.905,
            84.182,
            "Asia/Kolkata",
        )
        evidence = build_prediction_evidence(
            "I am starting a business of astrology website. It will be part-time. When should I start?",
            sunny_chart,
            date(2026, 5, 15),
        )
        sun_event = next(event for event in evidence["transits"]["relevant_transits"] if event["planet"] == "Su")
        self.assertEqual(sun_event["transit_sign"], "Taurus")
        self.assertEqual(sun_event["transit_house"], 10)
        self.assertEqual(sun_event["sarvashtakavarga_points"], 31)
        self.assertEqual(sun_event["tone"], "supportive")

    def test_weak_business_timing_answer_fails_quality_validator(self):
        evidence = build_prediction_evidence(
            "I am starting a business of astrology website. It will be part-time. When should I start? What is the best time for it?",
            self.chart_data,
            date(2026, 5, 15),
        )
        weak_answer = (
            "The timing for starting your part-time astrology website reveals significant caution primarily around May 15, 2026. "
            "The analysis indicates that this period has very challenging transit configurations, notably with the Sun, Mercury, Venus, and Mars in difficult positions, all of which provide low Sarvashtakavarga support. "
            "This suggests delays and potential pressures that may hinder your business's initial success during this timeframe.\n\n"
            "The current frameworks from the Parashari system, in conjunction with Jaimini observations, do not present strong affirmative signals for a favorable business launch. "
            "The indicated influence from the 7th, 10th, and 11th houses lacks supportive conditions that would indicate strong market viability or positive visibility. "
            "Overall, the evidence reflects weak auspiciousness in the current planetary alignments regarding business, emphasizing a prudent approach.\n\n"
            "It may be beneficial to postpone the launch of your website until after May 2026 due to prevailing challenges. "
            "Use this time for thorough preparation, refining your strategy and content. Keep an eye on future planetary movements that might create more advantageous conditions for your business aspirations."
        )
        result = validate_astrology_answer(weak_answer, evidence)
        self.assertFalse(result["passed"])
        self.assertLess(result["score"], 75)
        combined = " ".join(result["issues"] + result["missing_evidence"] + result["unsupported_claims"])
        self.assertIn("better alternative date/window", combined)
        self.assertIn("D10", combined)
        self.assertIn("dasha", combined.lower())
        self.assertIn("Yogini", combined)
        self.assertIn("Jaimini", combined)
        self.assertIn("Parashari", combined)
        self.assertIn("Sarvashtakavarga", combined)
        self.assertIn("confidence", combined.lower())

    def test_stronger_business_timing_answer_passes_quality_validator(self):
        evidence = build_prediction_evidence(
            "I am starting a business of astrology website. It will be part-time. When should I start? What is the best time for it?",
            self.chart_data,
            date(2026, 5, 15),
        )
        strong_answer = "\n".join(
            [
                "## Jyotish Analysis",
                "Do not use 15 May 2026 for a full paid public launch; use it only for private testing, with moderate confidence. A better preliminary window is **July 2026 to September 2026**, subject to exact muhurta confirmation. Use soft launch and private beta first, then payment launch after testing, and public marketing only after the better window is confirmed. D1 Rashi business judgment checks the 2nd house for income, 7th house for public dealings, 10th house for work, and 11th house for gains, with Mercury for website communication, Jupiter for astrology advisory wisdom, Saturn for execution pressure, and Rahu for online scaling. Parashari dasha timing uses the current Vimshottari Mahadasha and Antardasha from the calculated payload, along with Yogini dasha lord support. D9 Navamsha confirms planet strength and D10/Dashamsha checks professional execution and visibility. Jaimini is judged through Amatyakaraka, Arudha Lagna, and Chara Dasha relevance. Exact muhurta selection requires tithi, nakshatra, yoga, karana, weekday, lagna, Moon strength, and planetary hour calculation. Based on current available evidence, this is only a preliminary timing recommendation. Classical support is used only to explain deterministic evidence, and the signal is mixed because execution pressure and timing caution coexist with some business-house activation.",
                "## Remedy",
                "- Use deterministic Beej Mantra guidance for the active Mahadasha and Antardasha lords.",
                "## Practical Guidance",
                "Prepare content, backend, analytics, and payment flow before public marketing.",
            ]
        )
        result = validate_astrology_answer(strong_answer, evidence)
        self.assertTrue(result["passed"], result)

    def test_validator_rejects_contradictory_timing_without_clarification(self):
        evidence = build_prediction_evidence(
            "When should I start my astrology website business?",
            self.chart_data,
            date(2026, 5, 15),
        )
        answer = "\n".join(
            [
                "## Jyotish Analysis",
                "The recommended date is 15 May 2026 and you should start on this date. However, the same date is unfavorable, not auspicious, high risk, and not recommended. D1 Rashi checks the 2nd house, 7th house, 10th house, and 11th house with Mercury, Jupiter, Saturn, and Rahu. Parashari dasha timing includes Mahadasha and Antardasha, Yogini dasha is included, D9 Navamsha and D10 Dashamsha are checked, and Jaimini uses Amatyakaraka and Arudha. Exact muhurta selection requires tithi, nakshatra, yoga, karana, weekday, lagna, Moon strength, and planetary hour calculation. The confidence is medium.",
                "## Remedy",
                "- Beej Mantra guidance is included.",
                "## Practical Guidance",
                "Prepare carefully.",
            ]
        )
        result = validate_astrology_answer(answer, evidence)
        self.assertFalse(result["passed"])
        self.assertTrue(any("positive timing recommendation" in issue for issue in result["issues"]))

    def test_validator_rejects_vimshottari_as_system_language(self):
        evidence = build_prediction_evidence("Will my career improve?", self.chart_data, date(2026, 5, 15))
        answer = "\n".join(
            [
                "## Jyotish Analysis",
                "The Vimshottari system and Chara system both show mixed results, with confidence moderate. D10 house evidence and Sarvashtakavarga points are included.",
                "## Remedy",
                "- Beej Mantra guidance is included.",
                "## Practical Guidance",
                "Proceed carefully.",
            ]
        )
        result = validate_answer(answer, evidence)
        self.assertFalse(result["passed"])
        self.assertTrue(any("Vimshottari" in issue and "dasha" in issue for issue in result["issues"]))

    def test_validator_allows_contradictory_timing_with_soft_launch_clarification(self):
        evidence = build_prediction_evidence(
            "When should I start my astrology website business?",
            self.chart_data,
            date(2026, 5, 15),
        )
        answer = "\n".join(
            [
                "## Jyotish Analysis",
                "Best Available Option in Checked Window: **15 May 2026**. Overall Recommendation: postpone public launch beyond May 2026 because this date is not auspicious and carries high risk. Suggested Use: soft launch / testing only, not public launch. D1 Rashi checks the 2nd house, 7th house, 10th house, and 11th house with Mercury, Jupiter, Saturn, and Rahu. Parashari dasha timing includes Mahadasha and Antardasha, Yogini dasha is included, D9 Navamsha and D10 Dashamsha are checked, and Jaimini uses Amatyakaraka and Arudha. Exact muhurta selection requires tithi, nakshatra, yoga, karana, weekday, lagna, Moon strength, and planetary hour calculation. The confidence is medium.",
                "## Remedy",
                "- Beej Mantra guidance is included.",
                "## Practical Guidance",
                "Prepare carefully.",
            ]
        )
        result = validate_astrology_answer(answer, evidence)
        self.assertTrue(
            not any("positive timing recommendation" in issue for issue in result["issues"]),
            result,
        )


class RefreshChartDataCommandTests(TestCase):
    def test_refresh_chart_data_dry_run(self):
        User = get_user_model()
        user = User.objects.create_user(username="sample@example.com", email="sample@example.com", password="test")
        SavedChart.objects.create(
            user=user,
            name="Sample",
            birth_date=date(1990, 5, 17),
            birth_time=time(10, 30),
            birth_place="Delhi, India",
            latitude=28.6139,
            longitude=77.2090,
            timezone="Asia/Kolkata",
            chart_data={},
        )
        call_command("refresh_chart_data", "--dry-run")
