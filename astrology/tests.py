from datetime import date, time

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase

from astrology.calculations.dasha_facts import build_dasha_facts
from astrology.calculations.varga import SUPPORTED_VARGAS, build_chart_facts
from astrology.rag.query_builder import build_rag_query
from astrology.rules.loader import load_rules
from astrology.services.prediction_service import build_prediction_evidence
from astrology.synthesis.answer_schema import REQUIRED_SECTIONS
from astrology.synthesis.prompt_builder import build_prompt_messages
from astrology.validation.answer_validator import validate_astrology_answer
from astrology.validation.validator import validate_answer
from chat.llm_engine import _apply_deterministic_remedy, build_prompt_payload as build_live_prompt_payload
from charts.astro_engine import build_vedic_chart
from charts.models import SavedChart


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
        self.assertGreater(len(yogini["periods"]), 8)

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
        self.assertIn("tenth_from_karakamsha", jaimini["karakamsha"])
        self.assertIn("eleventh_from_arudha", jaimini["arudha_factors"])
        self.assertIn("darakaraka", jaimini["karaka_method"]["karakas"])
        self.assertIn("putrakaraka", jaimini["karaka_method"]["karakas"])

    def test_rules_load_without_errors(self):
        result = load_rules()
        self.assertGreater(result.rules, [])
        self.assertEqual(result.errors, [])

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
