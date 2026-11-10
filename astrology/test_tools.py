"""Offline P2 contracts and legacy parity, not independent astronomy goldens."""
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from astrology.tests import sample_chart_data
from astrology.tools import describe_tools, invoke_tool
from astrology.tools.contracts import MAX_RESPONSE_BYTES, json_bytes, validate_payload
from astrology.tools.fingerprints import engine_fingerprint
from astrology.tools.registry import TOOL_REGISTRY
from charts.models import SavedChart


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "p2-tests"}})
class DeterministicToolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="tool-owner")
        cls.other = get_user_model().objects.create_user(username="tool-other")
        cls.calculated = sample_chart_data()
        cls.chart = SavedChart.objects.create(
            user=cls.owner, name="Synthetic P2 fixture", birth_date=date(1990, 5, 17),
            birth_time="10:30:00", birth_place="Synthetic fixture", latitude="28.613900", longitude="77.209000",
            timezone="Asia/Kolkata", chart_data=cls.calculated,
        )

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.net = patch("socket.socket.connect", side_effect=AssertionError("Network forbidden in P2 tests"))
        self.net.start()
        self.addCleanup(self.net.stop)
        self.api = patch("openai.OpenAI", side_effect=AssertionError("LLM forbidden in P2 tests"))
        self.api.start()
        self.addCleanup(self.api.stop)

    def arguments(self):
        chart = self.chart.pk
        return {
            "get_chart_facts": {"chart_id": chart, "charts": ["D1", "D9", "D10"]},
            "get_dasha_periods": {"chart_id": chart, "system": "vimshottari", "start_date": "2027-05-01", "end_date": "2027-05-31"},
            "get_transits": {"chart_id": chart, "planets": ["Su", "Ju"], "start_date": "2027-05-01", "end_date": "2027-05-31"},
            "get_ashtakavarga": {"chart_id": chart},
            "evaluate_astrology_rules": {"chart_id": chart, "category": "job", "as_of": "2027-05-01"},
            "get_timing_candidates": {"chart_id": chart, "topic": "job", "start_date": "2027-05-01", "end_date": "2027-05-31"},
        }

    def invoke(self, tool, **changes):
        return invoke_tool(self.owner, tool, {**self.arguments()[tool], **changes})

    def test_p2_01_all_six_tools_have_valid_json_and_no_model_writes(self):
        before = deepcopy(self.chart.chart_data)
        with CaptureQueriesContext(connection) as queries:
            for tool in self.arguments():
                with self.subTest(tool=tool):
                    result = self.invoke(tool)
                    self.assertIn(result["status"], ("ok", "partial"), result.get("error"))
                    self.assertEqual(json.loads(json_bytes(result)), result)
                    self.assertLessEqual(len(json_bytes(result)), MAX_RESPONSE_BYTES)
                    self.assertEqual(result["schema_version"], "1.0")
                    self.assertIsNone(result["error"])
                    validate_payload(tool, result)
        self.assertTrue(all(q["sql"].lstrip().upper().startswith("SELECT") for q in queries.captured_queries))
        self.chart.refresh_from_db()
        self.assertEqual(self.chart.chart_data, before)

    def test_p2_01_discovery_is_fixed_read_only_and_typed(self):
        specs = describe_tools()
        self.assertEqual({s["name"] for s in specs}, set(self.arguments()))
        self.assertEqual(len(specs), 6)
        self.assertTrue(all(not s["input_schema"]["additionalProperties"] for s in specs))
        self.assertTrue(all("chart_id" in s["input_schema"]["required"] for s in specs))
        json_bytes(specs)
        with self.assertRaises(TypeError):
            TOOL_REGISTRY["save_chart"] = None

    def test_p2_02_strict_argument_validation_for_every_tool(self):
        for tool, arguments in self.arguments().items():
            for bad in ({**arguments, "user_id": self.other.pk}, {**arguments, "chart_id": True},
                        {**arguments, "chart_id": "1"}, {**arguments, "chart_id": -1}, {}):
                with self.subTest(tool=tool, bad_fields=sorted(bad)):
                    result = invoke_tool(self.owner, tool, bad)
                    self.assertEqual(result["status"], "error")
                    self.assertEqual(result["error"]["code"], "invalid_arguments")
                    self.assertIsNone(result["data"])
        for bad in ([], None, {"chart_id": self.chart.pk, "charts": []}, {"chart_id": self.chart.pk, "charts": [1]}):
            self.assertEqual(invoke_tool(self.owner, "get_chart_facts", bad)["error"]["code"], "invalid_arguments")

    def test_p2_02_dates_filters_caps_and_nonfinite_json(self):
        cases = [
            ("get_dasha_periods", {"start_date": "20270501"}, "invalid_date"),
            ("get_transits", {"start_date": "2027-02-30"}, "invalid_date"),
            ("get_transits", {"start_date": "2027-06-01"}, "invalid_range"),
            ("evaluate_astrology_rules", {"as_of": "9999-01-01"}, "date_limit"),
            ("get_ashtakavarga", {"sign": True}, "invalid_arguments"),
            ("get_ashtakavarga", {"house": 13}, "invalid_arguments"),
            ("evaluate_astrology_rules", {"max_rules": 0}, "invalid_arguments"),
            ("get_timing_candidates", {"max_candidates": 6}, "invalid_arguments"),
        ]
        for tool, changes, code in cases:
            with self.subTest(tool=tool, code=code):
                self.assertEqual(self.invoke(tool, **changes)["error"]["code"], code)
        self.assertEqual(self.invoke("get_chart_facts", charts=[float("nan")])["error"]["code"], "invalid_arguments")
        self.assertEqual(self.invoke("get_chart_facts", charts=["x" * 9000])["error"]["code"], "request_limit")

    def test_p2_03_every_tool_denies_foreign_and_missing_ids_before_computation(self):
        for tool, arguments in self.arguments().items():
            with self.subTest(tool=tool):
                # Warm the owner's cache to prove a cached response cannot bypass ownership.
                self.invoke(tool)
                with patch("astrology.tools.registry.engine_fingerprint", side_effect=AssertionError("Must not compute denied request")):
                    foreign = invoke_tool(self.other, tool, arguments)
                    absent = invoke_tool(self.other, tool, {**arguments, "chart_id": self.chart.pk + 10000})
                self.assertEqual(foreign, absent)
                self.assertEqual(foreign["error"]["code"], "chart_not_found")
                self.assertEqual(foreign["provenance"], {})
                self.assertIsNone(foreign["data"])

    def test_p2_03_anonymous_inactive_and_transferred_ownership(self):
        for user in (None, AnonymousUser()):
            self.assertEqual(invoke_tool(user, "get_chart_facts", {"chart_id": self.chart.pk})["error"]["code"], "authentication_required")
        self.owner.is_active = False
        self.assertEqual(self.invoke("get_chart_facts")["error"]["code"], "authentication_required")
        self.owner.is_active = True
        self.invoke("get_chart_facts")
        SavedChart.objects.filter(pk=self.chart.pk).update(user=self.other)
        self.assertEqual(self.invoke("get_chart_facts")["error"]["code"], "chart_not_found")

    def test_p2_04_unsupported_methods_are_explicit(self):
        cases = [
            ("get_chart_facts", {"charts": ["d99"]}),
            ("get_dasha_periods", {"granularity": "pratyantardasha"}),
            ("get_dasha_periods", {"system": "annual_yogini"}),
            ("get_transits", {"resolution": "hourly"}),
            ("get_transits", {"planets": ["Uranus"]}),
            ("get_ashtakavarga", {"planet": "Ra", "kind": "bav"}),
            ("evaluate_astrology_rules", {"category": "unknown"}),
            ("get_timing_candidates", {"evidence_policy": "agent_decides"}),
        ]
        for tool, changes in cases:
            with self.subTest(tool=tool):
                result = self.invoke(tool, **changes)
                self.assertEqual(result["status"], "unsupported", result.get("error"))
                self.assertIsNone(result["data"])
        for name in ("__import__", "save_chart", "../../.env", "execute_python"):
            self.assertEqual(invoke_tool(self.owner, name, {})["status"], "unsupported")

    def test_p2_05_all_dasha_systems_preserve_native_periods(self):
        for system in ("vimshottari", "yogini", "chara"):
            for level in ("mahadasha", "antardasha"):
                with self.subTest(system=system, level=level):
                    result = self.invoke("get_dasha_periods", system=system, granularity=level)
                    self.assertTrue(result["data"]["periods"])
                    self.assertIn("[start,end)", result["method"]["interval_convention"])
                    self.assertTrue(result["data"]["coverage"]["complete"])
                    source = (self.calculated["jaimini"]["chara_dasha"] if system == "chara" else self.calculated["dashas"][system])
                    native = [p for md in source["periods"] for p in ([md] if level == "mahadasha" else md.get("antardashas" if system == "vimshottari" else "subperiods", []))]
                    for row in result["data"]["periods"]:
                        self.assertTrue(any(all(row[k] == p[k] for k in p if k not in ("antardashas", "subperiods")) for p in native))

    def test_p2_05_boundary_selects_new_period_and_reports_gaps(self):
        data = deepcopy(self.calculated)
        data["dashas"]["vimshottari"]["periods"] = [{"lord": "Ke", "start": "2027-01-01", "end": "2027-01-05"}, {"lord": "Ve", "start": "2027-01-05", "end": "2027-02-01"}]
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        result = self.invoke("get_dasha_periods", granularity="mahadasha", start_date="2027-01-05", end_date="2027-01-05")
        self.assertEqual([r["lord"] for r in result["data"]["periods"]], ["Ve"])
        result = self.invoke("get_dasha_periods", granularity="mahadasha", start_date="2026-12-31", end_date="2027-01-05")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["data"]["coverage"]["gaps"], [{"start": "2026-12-31", "end": "2026-12-31"}])

    def test_p2_05_transits_match_noon_and_segments_do_not_claim_exact_ingress(self):
        from charts.vedic_utils import transit_context_for_lord
        result = self.invoke("get_transits", planets=["Su"], start_date="2027-05-01", end_date="2027-05-01", output="positions")
        expected = transit_context_for_lord(self.calculated, "Su", datetime(2027, 5, 1, 12, tzinfo=timezone.utc))
        row = result["data"]["samples"][0]
        self.assertEqual({k: row[k] for k in expected}, expected)
        self.assertIn("12:00 UTC", result["method"]["precision"])
        result = self.invoke("get_transits", planets=["Su", "Su"])
        self.assertEqual(result["data"]["planets"], ["Su"])
        self.assertEqual(result["data"]["samples"][0]["start"], "2027-05-01")
        self.assertEqual(result["data"]["samples"][-1]["end"], "2027-05-31")

    def test_p2_06_range_sample_request_and_output_limits(self):
        for tool in ("get_dasha_periods", "get_transits", "get_timing_candidates"):
            self.assertEqual(self.invoke(tool, start_date="2027-01-01", end_date="2031-01-01")["error"]["code"], "range_limit")
        result = self.invoke("get_transits", planets=["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"], start_date="2027-01-01", end_date="2029-01-01")
        self.assertEqual(result["error"]["code"], "sample_limit")
        with patch("astrology.tools.contracts.MAX_RESPONSE_BYTES", 1800):
            self.assertEqual(self.invoke("get_chart_facts")["error"]["code"], "output_limit")

    def test_p2_07_chart_and_ashtakavarga_match_stored_legacy_values(self):
        from astrology.calculations.varga import build_varga_facts
        result = self.invoke("get_chart_facts")
        self.assertEqual(result["data"]["charts"], build_varga_facts(self.calculated, chart_keys=["d1", "d9", "d10"])["charts"])
        self.assertNotIn("birth_data", result["data"])
        self.assertEqual(result["data"]["longitudes"]["d1"]["Su"], next(p["longitude"] for p in self.calculated["d1"]["planets"] if p["code"] == "Su"))
        result = self.invoke("get_ashtakavarga")
        for row, native in zip(result["data"]["rows"], self.calculated["ashtakavarga"]["rows"]):
            self.assertEqual(row["sav"], native["sarva"])
            self.assertEqual(row["bav"], native["scores"])
            self.assertEqual(row["house"], native["house"])
        row = result["data"]["rows"][0]
        selected = self.invoke("get_ashtakavarga", sign=row["sign_number"], house=row["house"], planet="Su")
        self.assertEqual(len(selected["data"]["rows"]), 1)
        bad = self.invoke("get_ashtakavarga", sign=1, house=row["house"] % 12 + 1)
        self.assertEqual(bad["error"]["code"], "invalid_arguments")

    def test_p2_07_rules_match_legacy_single_date_composition(self):
        from astrology.services.prediction_service import build_prediction_evidence
        day = date(2027, 5, 1)
        with patch("astrology.services.prediction_service.detect_question_scope", return_value={"start": day, "end": day, "months": 1, "is_fixed": True}):
            legacy = build_prediction_evidence("job", self.calculated, day)
        result = self.invoke("evaluate_astrology_rules", max_rules=100)
        self.assertIn(result["status"], ("ok", "partial"), result.get("error"))
        self.assertEqual(result["data"]["summary_scores"], legacy["summary_scores"])
        self.assertEqual(result["data"]["total_triggered"], len(legacy["triggered_rules"]))
        self.assertEqual(result["data"]["triggered_rules"], legacy["triggered_rules"][:100])
        self.assertIn("not probabilities", result["data"]["score_kind"])

    def test_p2_07_timing_matches_legacy_selection_without_recalculation_changes(self):
        from astrology.services.timing_window_service import build_timing_window_selection
        legacy = build_timing_window_selection(self.calculated, "", "job", date(2027, 5, 1), months=1, end_date=date(2027, 5, 31))
        result = self.invoke("get_timing_candidates")
        self.assertEqual(result["data"]["candidates"], [legacy["best_window"], *legacy["secondary_windows"]])

    def test_p2_08_empty_chart_is_explicit_and_never_regenerated(self):
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data={}, latitude=None, longitude=None)
        with patch("charts.astro_engine.build_vedic_chart", side_effect=AssertionError("Must not regenerate")):
            facts = self.invoke("get_chart_facts")
            self.assertEqual(facts["status"], "partial")
            self.assertEqual(facts["data"]["missing_charts"], ["d1", "d9", "d10"])
            periods = self.invoke("get_dasha_periods")
            self.assertEqual(periods["status"], "partial")
            for tool in ("get_transits", "get_ashtakavarga", "evaluate_astrology_rules", "get_timing_candidates"):
                self.assertEqual(self.invoke(tool)["error"]["code"], "incomplete_chart")

    def test_p2_08_missing_sav_is_none_but_real_zero_is_preserved(self):
        data = deepcopy(self.calculated)
        data["ashtakavarga"]["rows"] = []
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        result = self.invoke("get_ashtakavarga")
        self.assertEqual(result["status"], "partial")
        self.assertTrue(all(r["sav"] is None for r in result["data"]["rows"]))
        result = self.invoke("get_transits", planets=["Su"], start_date="2027-05-01", end_date="2027-05-01")
        self.assertIsNone(result["data"]["samples"][0]["sarvashtakavarga_points"])
        data = deepcopy(self.calculated)
        data["ashtakavarga"]["rows"][0]["sarva"] = 0
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        self.assertEqual(self.invoke("get_ashtakavarga", sign=1, kind="sav")["data"]["rows"][0]["sav"], 0)
        self.assertEqual(self.invoke("get_ashtakavarga", planet="Ra", kind="sav")["status"], "ok")

    def test_p2_08_missing_category_chart_marks_rule_and_timing_results_partial(self):
        data = deepcopy(self.calculated)
        data.pop("d10")
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        for tool in ("evaluate_astrology_rules", "get_timing_candidates"):
            result = self.invoke(tool)
            self.assertEqual(result["status"], "partial", result.get("error"))
            self.assertTrue(any("d10" in w for w in result["warnings"]))

    def test_p2_09_cache_hit_and_chart_changes_invalidate_without_updated_at_change(self):
        from astrology.calculations.varga import build_varga_facts
        with patch("astrology.tools.adapters.build_varga_facts", wraps=build_varga_facts) as calculations:
            with patch("astrology.tools.registry.cache.set", wraps=cache.set) as writes:
                first = self.invoke("get_chart_facts")
                self.assertEqual(writes.call_count, 1)
                self.assertTrue(writes.call_args.args[0].startswith("astro-tools-v1:"))
                stored = cache.get(writes.call_args.args[0])
                self.assertIsNotNone(stored, "Successful result must be stored in the cache")
                validate_payload("get_chart_facts", stored)
                self.assertEqual(stored["provenance"], first["provenance"])
            again = self.invoke("get_chart_facts")
            self.assertEqual(first, again)
            self.assertEqual(calculations.call_count, 1, "An identical authorized request must reuse its cached data")
        with patch("astrology.tools.adapters.build_varga_facts", side_effect=AssertionError("Cache hit must skip adapter")):
            cached = self.invoke("get_chart_facts")
            self.assertEqual(cached["status"], first["status"], "A cache hit must skip calculation")
        data = deepcopy(self.calculated)
        data["d1"]["planets"][1]["longitude"] += 0.01
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        changed = self.invoke("get_chart_facts")
        self.assertNotEqual(first["provenance"]["chart_fingerprint"], changed["provenance"]["chart_fingerprint"])
        self.assertNotEqual(first["data"]["longitudes"]["d1"]["Su"], changed["data"]["longitudes"]["d1"]["Su"])

    def test_p2_09_settings_code_rules_and_request_change_fingerprints(self):
        first = self.invoke("get_chart_facts")
        with override_settings(TIME_ZONE="Asia/Bangkok"):
            changed = self.invoke("get_chart_facts")
        self.assertNotEqual(first["provenance"]["engine_fingerprint"], changed["provenance"]["engine_fingerprint"])
        changed = self.invoke("get_chart_facts", charts=["d1"])
        self.assertNotEqual(first["provenance"]["request_fingerprint"], changed["provenance"]["request_fingerprint"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rules = root / "astrology" / "rules"
            rules.mkdir(parents=True)
            source = root / "charts"
            source.mkdir()
            code = source / "engine.py"
            code.write_text("version=1", encoding="utf-8")
            rule = rules / "rules.yaml"
            rule.write_text("rules: []", encoding="utf-8")
            with patch("astrology.tools.fingerprints.ROOT", root):
                original = engine_fingerprint()
                rule.write_text("rules: [changed]", encoding="utf-8")
                changed_rule = engine_fingerprint()
                code.write_text("version=2", encoding="utf-8")
                changed_code = engine_fingerprint()
            self.assertNotEqual(original, changed_rule)
            self.assertNotEqual(changed_rule, changed_code)

    def test_response_schema_rejects_corruption_and_hides_internal_errors(self):
        result = self.invoke("get_chart_facts")
        broken = deepcopy(result)
        broken["data"]["charts"] = []
        with self.assertRaises(ValueError):
            validate_payload("get_chart_facts", broken)
        cache.clear()
        with patch("astrology.tools.adapters.build_varga_facts", side_effect=ValueError("private-birth-data-and-secret-path")):
            failed = self.invoke("get_chart_facts")
        self.assertEqual(failed["error"]["code"], "computation_error")
        self.assertNotIn("private-birth", json.dumps(failed))

    def test_p2_09_corrupt_cache_is_recomputed_and_results_are_defensive_copies(self):
        good = self.invoke("get_chart_facts")
        broken = deepcopy(good)
        broken["data"]["charts"] = []
        with patch("astrology.tools.registry.cache.get", return_value=broken):
            recovered = self.invoke("get_chart_facts")
        self.assertEqual(recovered, good)
        broken = deepcopy(good)
        broken["provenance"]["chart_id"] = self.chart.pk + 1
        with patch("astrology.tools.registry.cache.get", return_value=broken):
            recovered = self.invoke("get_chart_facts")
        self.assertEqual(recovered["provenance"], good["provenance"])
        recovered["data"]["charts"].clear()
        self.assertTrue(self.invoke("get_chart_facts")["data"]["charts"])

    def test_p2_09_birth_metadata_change_invalidates_and_is_not_recalculated(self):
        first = self.invoke("get_chart_facts")
        SavedChart.objects.filter(pk=self.chart.pk).update(timezone="UTC")
        result = self.invoke("get_chart_facts")
        self.assertNotEqual(first["provenance"]["chart_fingerprint"], result["provenance"]["chart_fingerprint"])
        self.assertEqual(result["status"], "partial")
        self.assertTrue(any("inputs differ" in w for w in result["warnings"]))
        self.assertEqual(result["data"], first["data"])

    def test_p2_08_timing_and_rules_disclose_incomplete_sav(self):
        data = deepcopy(self.calculated)
        data["ashtakavarga"]["rows"] = []
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        for tool in ("get_timing_candidates", "evaluate_astrology_rules"):
            result = self.invoke(tool)
            self.assertEqual(result["status"], "partial", result.get("error"))
        for window in self.invoke("get_timing_candidates")["data"]["candidates"]:
            self.assertTrue(all(s["sarvashtakavarga_points"] is None for s in window["transit_segments"]))

    def test_p2_07_selected_planets_delegate_existing_segment_helper(self):
        from chat.timing_windows import _transit_segments_for_lord
        planets = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
        result = self.invoke("get_transits", planets=planets, start_date="2027-05-01", end_date="2027-05-07")
        self.assertEqual(result["status"], "ok")
        expected = [segment for planet in planets for segment in _transit_segments_for_lord(self.calculated, planet, date(2027, 5, 1), date(2027, 5, 7), [])]
        self.assertTrue(result["data"]["samples"] == expected, "Selected-planet segments changed from legacy helper")

    def test_p2_01_schema_contains_output_and_rejects_invalid_integer_scores(self):
        self.assertTrue(all("output_schema" in item for item in describe_tools()))
        result = self.invoke("get_ashtakavarga")
        result["data"]["rows"][0]["sav"] = "0"
        with self.assertRaises(ValueError):
            validate_payload("get_ashtakavarga", result)

    def test_p2_03_staff_cannot_bypass_chart_ownership(self):
        self.other.is_staff = True
        self.other.is_superuser = True
        self.assertEqual(invoke_tool(self.other, "get_chart_facts", {"chart_id": self.chart.pk})["error"]["code"], "chart_not_found")

    def test_p2_06_candidate_and_rule_caps_are_explicit(self):
        rules = self.invoke("evaluate_astrology_rules", max_rules=1)
        self.assertEqual(len(rules["data"]["triggered_rules"]), 1)
        self.assertEqual(rules["data"]["omitted_rules"], rules["data"]["total_triggered"] - 1)
        timing = self.invoke("get_timing_candidates", start_date="2027-01-01", end_date="2027-12-31", max_candidates=1)
        self.assertEqual(len(timing["data"]["candidates"]), 1)
        self.assertEqual(timing["data"]["omitted_candidates"], timing["data"]["coverage"]["candidate_count"] - 1)

    def test_p2_08_partial_natal_coverage_and_unknown_frame_are_not_full_confirmation(self):
        data = deepcopy(self.calculated)
        data["d1"]["planets"] = data["d1"]["planets"][:3]
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        for tool in ("get_chart_facts", "get_transits", "get_dasha_periods", "get_ashtakavarga"):
            self.assertEqual(self.invoke(tool)["status"], "partial")
        data = deepcopy(self.calculated)
        data["system"] = "other_frame"
        SavedChart.objects.filter(pk=self.chart.pk).update(chart_data=data)
        self.assertEqual(self.invoke("get_transits")["status"], "unsupported")

    def test_p2_09_optional_cache_failure_does_not_expose_errors_or_write_models(self):
        with patch("astrology.tools.registry.cache.get", side_effect=RuntimeError("private-cache-error")), patch("astrology.tools.registry.cache.set", side_effect=RuntimeError("private-cache-error")):
            result = self.invoke("get_chart_facts")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("private-cache", json.dumps(result))

    def test_p2_06_oversized_transit_does_not_start_position_calculation(self):
        with patch("astrology.tools.adapters._transit_segments_for_lord", side_effect=AssertionError("Must enforce limits first")):
            result = self.invoke("get_transits", planets=list(self.calculated["ashtakavarga"]["planet_codes"]), start_date="2027-01-01", end_date="2029-01-01")
        self.assertEqual(result["error"]["code"], "sample_limit")
