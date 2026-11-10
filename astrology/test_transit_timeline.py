from datetime import date, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase

from astrology.calculations.dasha_transit_timeline import (
    build_dasha_transit_timeline, segments_in_range, summarize_segments,
)
from astrology.calculations.transit_facts import _compact_future_window
from astrology.validation.evidence_checker import _transit_period_issues, _transit_coverage_issues
from chat.prediction_context import detect_question_scope


def boundary_chart():
    return {
        "ascendant": {"sign_number": 1},
        "ashtakavarga": {"rows": [{"house": h, "sarva": 20 + h} for h in range(1, 13)]},
        "dashas": {"vimshottari": {"periods": [
            {"lord": "Ke", "start": "2027-01-01", "end": "2027-01-05", "antardashas": [
                {"lord": "Ve", "start": "2027-01-01", "end": "2027-01-05"}]},
            {"lord": "Ve", "start": "2027-01-05", "end": "2027-02-01", "antardashas": [
                {"lord": "Ve", "start": "2027-01-05", "end": "2027-01-08"},
                {"lord": "Su", "start": "2027-01-08", "end": "2027-02-01"}]},
        ]}},
    }


class DashaTransitTimelineTests(SimpleTestCase):
    def test_md_ad_boundaries_and_unique_same_lord_transit(self):
        with patch("astrology.calculations.dasha_transit_timeline.transit_longitude", return_value=45) as positions:
            timeline = build_dasha_transit_timeline(boundary_chart(), date(2027, 1, 2), date(2027, 1, 9), [2, 10])
        rows = timeline["intervals"]
        self.assertEqual([(r["start"], r["end"], r["mahadasha_lord"], r["antardasha_lord"]) for r in rows], [
            ("2027-01-02", "2027-01-04", "Ke", "Ve"),
            ("2027-01-05", "2027-01-07", "Ve", "Ve"),
            ("2027-01-08", "2027-01-09", "Ve", "Su"),
        ])
        self.assertEqual(len(rows[1]["transit_segments"]), 1)
        self.assertEqual(rows[1]["transit_segments"][0]["role"], "Mahadasha and Antardasha lord")
        self.assertEqual(positions.call_count, 3 * 2 + 3 + 2 * 2)
        self.assertEqual(timeline["status"], "complete")

    def test_transit_reentry_and_sav_attached_after_positions(self):
        calls = []

        class TrackedChart(dict):
            def get(self, key, default=None):
                if key == "ashtakavarga":
                    calls.append(("SAV", None))
                return super().get(key, default)

        chart = TrackedChart(boundary_chart())

        def longitude(lord, instant):
            calls.append((lord, instant.date()))
            # Includes retrograde re-entry into the original sign.
            return {2: 45, 3: 75, 4: 45}[instant.day]

        with patch("astrology.calculations.dasha_transit_timeline.transit_longitude", side_effect=longitude):
            t = build_dasha_transit_timeline(chart, date(2027, 1, 2), date(2027, 1, 4), [2])
        segments = t["intervals"][0]["transit_segments"]
        for lord in ("Ke", "Ve"):
            rows = [s for s in segments if s["lord"] == lord]
            self.assertEqual([s["transit_sign_number"] for s in rows], [2, 3, 2])
            self.assertEqual([s["transit_house_from_lagna"] for s in rows], [2, 3, 2])
            self.assertEqual([s["sarvashtakavarga_points"] for s in rows], [22, 23, 22])
        self.assertEqual(len(calls), 7)
        self.assertEqual(calls[-1], ("SAV", None))

    def test_single_day_inclusive_end_and_clipping(self):
        with patch("astrology.calculations.dasha_transit_timeline.transit_longitude", return_value=45):
            t = build_dasha_transit_timeline(boundary_chart(), date(2027, 1, 5), date(2027, 1, 9), [2])
        segments = segments_in_range(t, date(2027, 1, 9), date(2027, 1, 9))
        self.assertEqual({s["lord"] for s in segments}, {"Ve", "Su"})
        self.assertTrue(all(s["start"] == s["end"] == "2027-01-09" for s in segments))

    def test_missing_sav_is_preliminary_not_zero(self):
        chart = boundary_chart()
        chart.pop("ashtakavarga")
        with patch("astrology.calculations.dasha_transit_timeline.transit_longitude", return_value=45):
            t = build_dasha_transit_timeline(chart, date(2027, 1, 5), date(2027, 1, 5), [2])
        self.assertEqual(t["status"], "preliminary")
        s = t["intervals"][0]["transit_segments"][0]
        self.assertIsNone(s["sarvashtakavarga_points"])
        self.assertIsNone(s["can_deliver_owned_or_placed_house_results"])

    def test_missing_dasha_coverage_is_explicit(self):
        t = build_dasha_transit_timeline({}, date(2027, 1, 1), date(2027, 1, 2), [])
        self.assertEqual(t["status"], "preliminary")
        self.assertTrue(t["issues"])
        self.assertEqual(t["intervals"][0]["transit_segments"], [])
        evidence = {"transits": {"future_timing": {"dasha_transit_timeline": t}}}
        self.assertTrue(_transit_coverage_issues("Strong support.", evidence))
        self.assertFalse(_transit_coverage_issues("This timing is preliminary.", evidence))

    def test_duration_weighted_scores_use_full_period(self):
        rows = [
            {"lord": "Ve", "lord_name": "Venus", "role": "Antardasha lord", "start": "2027-01-01", "end": "2027-01-09", "transit_score": 0},
            {"lord": "Ve", "lord_name": "Venus", "role": "Antardasha lord", "start": "2027-01-10", "end": "2027-01-10", "transit_score": 20},
        ]
        for s in rows:
            s.update(transit_sign="Aries", transit_house_from_lagna=1, sarvashtakavarga_points=20)
        self.assertEqual(summarize_segments(rows)[0]["transit_score"], 2)

    def test_default_three_years_and_explicit_month(self):
        today = date(2026, 11, 7)
        for question in ("When will I change jobs?", "Job change opportunities?"):
            scope = detect_question_scope(question, today)
            self.assertEqual(scope["months"], 36)
            self.assertEqual(scope["end"], date(2029, 11, 7))
        scope = detect_question_scope("Will I change jobs next year?", today)
        self.assertEqual((scope["start"], scope["end"]), (date(2027, 1, 1), date(2027, 12, 31)))
        scope = detect_question_scope("Will I change jobs in May 2028?", today)
        self.assertEqual((scope["start"], scope["end"]), (date(2028, 5, 1), date(2028, 5, 31)))

    def test_compaction_keeps_both_lords_and_every_segment(self):
        segments = [{"lord": "Su", "lord_name": "Sun"}] * 11 + [{"lord": "Ju", "lord_name": "Jupiter"}] * 3
        compact = _compact_future_window({"transit_segments": segments, "dasha_lord_transit_checks": [{"lord": "Ju"}]})
        self.assertEqual(len(compact["transit_segments"]), 14)
        self.assertEqual(compact["dasha_lord_transit_checks"], [{"lord": "Ju"}])

    def test_validator_rejects_wrong_window_lords(self):
        evidence = {"timing_selection": {"best_window": {
            "start": "2027-01-03", "end": "2027-10-21", "transit_segments": [{"lord": "Ju"}],
            "vimshottari": {"mahadasha_lord_name": "Sun", "antardasha_lord_name": "Jupiter"},
        }}}
        self.assertTrue(_transit_period_issues("**Transits & Ashtakavarga:** Sun and Rahu support this period.", evidence))
        self.assertFalse(_transit_period_issues("**Transits & Ashtakavarga:** Sun and Jupiter support this period.", evidence))


class RealChartTransitPipelineTests(SimpleTestCase):
    def test_real_chart_timeline_reaches_prompt_and_evidence_card(self):
        from astrology.tests import sample_chart_data
        from chat.llm_engine import build_prompt_payload

        p = build_prompt_payload("Will I change jobs in 2027?", sample_chart_data(), 3)["evidence_payload"]
        future = p["transits"]["future_timing"]
        rows = future["dasha_transit_timeline"]["intervals"]
        self.assertEqual(rows[0]["start"], "2027-01-01")
        self.assertEqual(rows[-1]["end"], "2027-12-31")
        self.assertNotIn("dasha_lord_transits", p["transits"])
        for previous, current in zip(rows, rows[1:]):
            self.assertEqual(date.fromisoformat(previous["end"]) + timedelta(days=1), date.fromisoformat(current["start"]))
        for row in rows:
            expected = {row["mahadasha_lord"], row["antardasha_lord"]}
            self.assertEqual({s["lord"] for s in row["transit_segments"]}, expected)
            for lord in expected:
                segments = [s for s in row["transit_segments"] if s["lord"] == lord]
                self.assertEqual(segments[0]["start"], row["start"])
                self.assertEqual(segments[-1]["end"], row["end"])
        best = p["timing_selection"]["best_window"]
        self.assertEqual(p["evidence_card"]["transit_ashtakavarga_basis"][0]["start"], best["transit_segments"][0]["start"])
        expected = {best["vimshottari"]["mahadasha_lord"], best["vimshottari"]["antardasha_lord"]}
        self.assertEqual({s["lord"] for s in best["transit_segments"]}, expected)
        for window in future["windows"]:
            self.assertTrue(all(window["start"] <= s["start"] <= s["end"] <= window["end"] for s in window["transit_segments"]))
