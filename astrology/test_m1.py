"""M1 tests: calculation integrity, dasha boundaries, method profile, security.

Two kinds of numerical evidence appear here and are kept separate:

* ``IndependentFormulaReferenceTests`` recompute quantities from published
  formulas written independently in this file (Meeus; Astronomical Almanac
  low-precision series; first-principles dasha arithmetic; classical varga
  definitions). They are lower precision than professional software.
* ``JagannathaHoraReferenceTests`` compare against owner-prepared Jagannatha
  Hora values in ``m1_reference_charts_v1.json``. Until those values exist,
  the test is skipped with an explicit PENDING message. The calculations are
  then UNVERIFIED against JH. A skip is never a pass.

All charts are synthetic. No provider or network call is made.
"""
import json
import math
import os
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import swisseph as swe
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from astrology.calculations.method_profile import METHOD_PROFILE_ID, ephemeris_from_flags
from astrology.calculations.periods import select_period, timing_fields, resolve_timezone
from charts.astro_engine import CHART_TEMPLATE, build_vedic_chart

BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURE = BASE_DIR / "astrology" / "evaluation" / "fixtures" / "m1_reference_charts_v1.json"
UTC = dt_timezone.utc
LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "m1-tests"}}


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def build_fixture_chart(spec):
    return build_vedic_chart(spec["id"], date.fromisoformat(spec["birth_date"]), time.fromisoformat(spec["birth_time"]),
                             spec["place_label"], spec["latitude"], spec["longitude"], spec["timezone"])


_CHARTS = {}


def fixture_charts():
    if not _CHARTS:
        for spec in load_fixture()["charts"]:
            _CHARTS[spec["id"]] = (spec, build_fixture_chart(spec))
    return _CHARTS


def planet(chart, code, key="d1"):
    return next(p for p in chart[key]["planets"] if p["code"] == code)


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def angle_diff(a, b):
    return abs((a - b + 180) % 360 - 180)


# ── Independent low-precision formulas (written for this test, not app code) ──

def _sin(deg):
    return math.sin(math.radians(deg))


def _cos(deg):
    return math.cos(math.radians(deg))


def centuries(jd):
    return (jd - 2451545.0) / 36525.0


def nutation(jd):
    """Meeus ch. 22 low-precision nutation, degrees (dpsi, deps)."""
    t = centuries(jd)
    omega = 125.04452 - 1934.136261 * t
    l_sun = 280.4665 + 36000.7698 * t
    l_moon = 218.3165 + 481267.8813 * t
    dpsi = (-17.20 * _sin(omega) - 1.32 * _sin(2 * l_sun) - 0.23 * _sin(2 * l_moon) + 0.21 * _sin(2 * omega)) / 3600
    deps = (9.20 * _cos(omega) + 0.57 * _cos(2 * l_sun) + 0.10 * _cos(2 * l_moon) - 0.09 * _cos(2 * omega)) / 3600
    return dpsi, deps


def meeus_sun_apparent(jd):
    """Meeus ch. 25 low-precision apparent solar longitude (about 0.01 degree)."""
    t = centuries(jd)
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t * t
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * _sin(m)
         + (0.019993 - 0.000101 * t) * _sin(2 * m) + 0.000289 * _sin(3 * m))
    omega = 125.04 - 1934.136 * t
    return (l0 + c - 0.00569 - 0.00478 * _sin(omega)) % 360


def almanac_moon(jd):
    """Astronomical Almanac low-precision lunar longitude (about 0.3 degree)."""
    t = centuries(jd)
    return (218.32 + 481267.881 * t + 6.29 * _sin(135.0 + 477198.87 * t) - 1.27 * _sin(259.3 - 413335.36 * t)
            + 0.66 * _sin(235.7 + 890534.22 * t) + 0.21 * _sin(269.9 + 954397.74 * t)
            - 0.19 * _sin(357.5 + 35999.05 * t) - 0.11 * _sin(186.5 + 966404.03 * t)) % 360


def meeus_ascendant(jd_ut, latitude, east_longitude):
    """Tropical ascendant of date from Meeus GMST (ch. 12) and the horizon-ecliptic intersection."""
    t = centuries(jd_ut)
    gmst = 280.46061837 + 360.98564736629 * (jd_ut - 2451545.0) + 0.000387933 * t * t - t ** 3 / 38710000
    dpsi, deps = nutation(jd_ut)
    eps = 23.439291 - 0.0130042 * t + deps
    ramc = (gmst + dpsi * _cos(eps) + east_longitude) % 360
    asc = math.degrees(math.atan2(_cos(ramc), -(_sin(ramc) * _cos(eps) + math.tan(math.radians(latitude)) * _sin(eps))))
    return asc % 360


def true_lahiri(jd_ut):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa_ut(jd_ut) + nutation(jd_ut)[0]


VIM_LORDS = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
VIM_YEARS = {"Ke": 7, "Ve": 20, "Su": 6, "Mo": 10, "Ma": 7, "Ra": 18, "Ju": 16, "Sa": 19, "Me": 17}
YOGINIS = [("Mangala", 1), ("Pingala", 2), ("Dhanya", 3), ("Bhramari", 4),
           ("Bhadrika", 5), ("Ulka", 6), ("Siddha", 7), ("Sankata", 8)]
NAK = 360 / 27
YEAR_DAYS = 365.2425


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)  # Windows rejects negative timestamps; use arithmetic.


def _jd(moment):
    return 2440587.5 + (moment - EPOCH).total_seconds() / 86400


def independent_sidereal_sun(jd):
    # Aberration and nutation are nearly constant over a few days and cancel
    # in the year-to-year differences that the dasha clock uses.
    return (meeus_sun_apparent(jd) - true_lahiri(jd)) % 360


def independent_solar_year_instant(birth, years):
    """Instant when the sidereal Sun has advanced 360*years degrees from birth (Meeus Sun)."""
    jd0 = _jd(birth)
    target = independent_sidereal_sun(jd0) + 360 * years
    jd = jd0 + years * 365.256363
    for _ in range(30):
        jd += ((target - independent_sidereal_sun(jd) + 180) % 360 - 180) / 0.9856
    return EPOCH + timedelta(days=jd - 2440587.5)


# Meeus low-precision Sun: 0.01 degree is about 15 minutes of solar motion.
SOLAR_CLOCK_TOLERANCE_S = 3600


class IndependentFormulaReferenceTests(SimpleTestCase):
    """Formula-level independent checks (lower precision than JH; labelled as such in M1_REPORT)."""

    def test_lahiri_definition_value(self):
        # Lahiri (Indian Astronomical Ephemeris) definition: 23 deg 15' 00.658" on 1956-03-21 0h.
        # The value is recalled from the published definition; the owner should confirm it against print.
        definition = 23 + 15 / 60 + 0.658 / 3600
        jd = swe.julday(1956, 3, 21, 0.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        calculated = swe.get_ayanamsa_ut(jd) + swe.calc_ut(jd, swe.ECL_NUT, swe.FLG_MOSEPH)[0][2]
        self.assertLess(abs(calculated - definition) * 3600, 1.0)

    def test_sun_moon_and_ascendant_against_independent_formulas(self):
        for cid, (spec, chart) in fixture_charts().items():
            with self.subTest(chart=cid):
                jd = chart["julian_day_ut"]
                aya = true_lahiri(jd)
                sun = (meeus_sun_apparent(jd) - aya) % 360
                moon = (almanac_moon(jd) - aya) % 360
                asc = (meeus_ascendant(jd, spec["latitude"], spec["longitude"]) - aya) % 360
                self.assertLess(angle_diff(sun, planet(chart, "Su")["longitude"]), 0.02)
                # 0.5 deg is about one hour of lunar motion: catches timezone/DST mistakes.
                self.assertLess(angle_diff(moon, planet(chart, "Mo")["longitude"]), 0.5)
                self.assertLess(angle_diff(asc, chart["ascendant"]["longitude"]) * 60, 1.0)

    def test_birth_instant_uses_local_zone_including_dst(self):
        expected = {"R1": "1985-07-14T01:00:00Z", "R2": "1992-11-04T04:45:00Z", "R3": "1978-03-25T23:20:00Z",
                    "R4": "2001-01-20T03:10:00Z", "R5": "1969-09-02T06:30:00Z"}
        for cid, (_, chart) in fixture_charts().items():
            self.assertEqual(chart["birth_instant_utc"], expected[cid], cid)

    def test_vimshottari_from_first_principles(self):
        # M1b: the birth Mahadasha is a full period that began before birth, and
        # dasha years are true sidereal solar years, recomputed here from the
        # independent Meeus solar longitude.
        for cid, (_, chart) in fixture_charts().items():
            with self.subTest(chart=cid):
                moon = planet(chart, "Mo")["longitude"]
                index = int(moon // NAK)
                lord = VIM_LORDS[index % 9]
                cursor = -VIM_YEARS[lord] * (moon - index * NAK) / NAK
                birth = instant(chart["birth_instant_utc"])
                periods = chart["dashas"]["vimshottari"]["periods"]
                sequence = VIM_LORDS[VIM_LORDS.index(lord):] + VIM_LORDS[:VIM_LORDS.index(lord)]
                self.assertLess(instant(periods[0]["start_utc"]), birth)
                self.assertLessEqual(birth, instant(periods[0]["end_utc"]))
                for number, period in enumerate(periods[:9]):
                    self.assertEqual(period["lord"], sequence[number])
                    expected = independent_solar_year_instant(birth, cursor)
                    self.assertLess(abs((instant(period["start_utc"]) - expected).total_seconds()), SOLAR_CLOCK_TOLERANCE_S)
                    cursor += VIM_YEARS[sequence[number]]

    def test_antardashas_divide_full_mahadashas_from_first_principles(self):
        # Checks the birth Mahadasha (M1-F1) and the one after it.
        for cid, (_, chart) in fixture_charts().items():
            moon = planet(chart, "Mo")["longitude"]
            index = int(moon // NAK)
            birth = instant(chart["birth_instant_utc"])
            md_start = -VIM_YEARS[VIM_LORDS[index % 9]] * (moon - index * NAK) / NAK
            for md in chart["dashas"]["vimshottari"]["periods"][:2]:
                order = VIM_LORDS[VIM_LORDS.index(md["lord"]):] + VIM_LORDS[:VIM_LORDS.index(md["lord"])]
                cursor = md_start
                self.assertEqual(len(md["antardashas"]), 9)
                for ad, lord in zip(md["antardashas"], order):
                    self.assertEqual(ad["lord"], lord)
                    expected = independent_solar_year_instant(birth, cursor)
                    self.assertLess(abs((instant(ad["start_utc"]) - expected).total_seconds()), SOLAR_CLOCK_TOLERANCE_S, (cid, md["lord"], lord))
                    cursor += VIM_YEARS[md["lord"]] * VIM_YEARS[lord] / 120
                self.assertEqual(md["antardashas"][-1]["end_utc"], md["end_utc"])
                md_start += VIM_YEARS[md["lord"]]

    def test_birth_falls_in_the_antardasha_given_by_the_full_period_method(self):
        # M1-F1: the antardasha running at birth is found by dividing the full
        # birth Mahadasha, not by restarting with the Mahadasha lord at birth.
        for cid, (_, chart) in fixture_charts().items():
            moon = planet(chart, "Mo")["longitude"]
            index = int(moon // NAK)
            lord = VIM_LORDS[index % 9]
            elapsed = VIM_YEARS[lord] * (moon - index * NAK) / NAK
            order = VIM_LORDS[VIM_LORDS.index(lord):] + VIM_LORDS[:VIM_LORDS.index(lord)]
            cursor, expected = 0.0, None
            for sub in order:
                cursor += VIM_YEARS[lord] * VIM_YEARS[sub] / 120
                if elapsed < cursor:
                    expected = sub
                    break
            birth_md = chart["dashas"]["vimshottari"]["periods"][0]
            self.assertTrue(birth_md["starts_before_birth"], cid)
            found = select_period(birth_md["antardashas"], instant(chart["birth_instant_utc"]))
            self.assertEqual(found["lord"], expected, cid)

    def test_yogini_from_first_principles(self):
        names = [name for name, _ in YOGINIS]
        years = dict(YOGINIS)
        for cid, (_, chart) in fixture_charts().items():
            with self.subTest(chart=cid):
                moon = planet(chart, "Mo")["longitude"]
                number = int(moon // NAK) + 1
                remainder = (number + 3) % 8  # Classical rule: (nakshatra + 3) / 8, remainder 0 = Sankata.
                first = names[7 if remainder == 0 else remainder - 1]
                remaining = years[first] * (1 - (moon - (number - 1) * NAK) / NAK)
                periods = chart["dashas"]["yogini"]["periods"]
                start = instant(chart["birth_instant_utc"])
                order = names[names.index(first):] + names[:names.index(first)]
                for index, period in enumerate(periods[:8]):
                    self.assertEqual(period["yogini"], order[index])
                    self.assertLess(abs((instant(period["start_utc"]) - start).total_seconds()), 120)
                    start += timedelta(days=(remaining if index == 0 else years[order[index]]) * YEAR_DAYS)

    def test_d9_and_d10_signs_from_classical_definitions_with_boundary_guard(self):
        guard = 1 / 60
        flagged = []
        for cid, (_, chart) in fixture_charts().items():
            rows = [chart["ascendant"]] + [p for p in chart["d1"]["planets"] if p["code"] != "Asc"]
            for row in rows:
                lon = row["longitude"] % 360
                code = row["code"]
                part9 = lon % (30 / 9)
                if min(part9, 30 / 9 - part9) < guard:
                    flagged.append((cid, code, "D9"))
                else:
                    self.assertEqual(planet(chart, code, "d9")["sign_number"], int(lon // (30 / 9)) % 12 + 1, (cid, code))
                sign = int(lon // 30) + 1
                part10 = (lon % 30) % 3
                if min(part10, 3 - part10) < guard:
                    flagged.append((cid, code, "D10"))
                else:
                    first = sign if sign % 2 == 1 else (sign + 8 - 1) % 12 + 1
                    expected = (first - 1 + int((lon % 30) // 3)) % 12 + 1
                    self.assertEqual(planet(chart, code, "d10")["sign_number"], expected, (cid, code))
        self.assertLess(len(flagged), 5, f"Boundary-flagged (not silently passed): {flagged}")


class JagannathaHoraReferenceTests(SimpleTestCase):
    """Owner-prepared JH values. Skipped as PENDING until supplied; never treated as a pass."""

    @staticmethod
    def dms(value):
        d, m, s = (float(x) for x in value.split(":"))
        return d + m / 60 + s / 3600

    def test_against_jagannatha_hora(self):
        fixture = load_fixture()
        provided = [c for c in fixture["charts"] if c["jagannatha_hora"]["status"] == "provided"]
        if not provided:
            self.skipTest("PENDING: owner has not yet supplied Jagannatha Hora values; calculations are UNVERIFIED against JH.")
        tol = fixture["tolerances"]
        charts = fixture_charts()
        for spec in provided:
            chart = charts[spec["id"]][1]
            expected = spec["jagannatha_hora"]["expected"]
            for code, value in expected.get("d1_longitudes_dms", {}).items():
                ours = chart["ascendant"]["longitude"] if code == "Asc" else planet(chart, code)["longitude"]
                limit = tol["ascendant_longitude_arcmin" if code == "Asc" else "planet_longitude_arcmin"]
                self.assertLessEqual(angle_diff(ours, self.dms(value)) * 60, limit, (spec["id"], code))
            for key in ("d9_signs", "d10_signs"):
                for code, sign in expected.get(key, {}).items():
                    self.assertEqual(planet(chart, code, key[:3] if key.startswith("d10") else "d9")["sign_number"], sign, (spec["id"], key, code))
            ours = chart["dashas"]["vimshottari"]["periods"]
            for row in expected.get("vimshottari_md_starts", []):
                match = next(p for p in ours if p["lord"] == row["lord"])
                self.assertLessEqual(abs((date.fromisoformat(match["start"]) - date.fromisoformat(row["start"])).days),
                                     tol["dasha_start_days"], (spec["id"], row))


class PeriodSelectorTests(SimpleTestCase):
    """OD-8: one [start, end) selector; exact instants; timezone/date-change cases."""

    def periods(self, zone="Asia/Kolkata"):
        tz = resolve_timezone(zone)
        a = datetime(2029, 1, 1, 5, 0, tzinfo=UTC)
        b = datetime(2030, 5, 1, 20, 0, tzinfo=UTC)  # 01:30 on 2 May in Kolkata
        c = datetime(2031, 1, 1, 0, 0, tzinfo=UTC)
        return [{"lord": "Ju", **timing_fields(a, b, tz)}, {"lord": "Sa", **timing_fields(b, c, tz)}]

    def test_display_date_is_in_chart_timezone(self):
        first, second = self.periods()
        self.assertEqual(first["end_utc"], "2030-05-01T20:00:00Z")
        self.assertEqual(first["end"], "2030-05-02")  # local Kolkata date of the transition
        self.assertEqual(second["start"], "2030-05-02")
        new_york = self.periods("America/New_York")
        self.assertEqual(new_york[1]["start"], "2030-05-01")  # 16:00 local, same UTC instant

    def test_date_queries_are_half_open(self):
        periods = self.periods()
        self.assertEqual(select_period(periods, date(2030, 5, 1))["lord"], "Ju")
        self.assertEqual(select_period(periods, date(2030, 5, 2))["lord"], "Sa")  # new period from its start date
        self.assertEqual(select_period(periods, date(2030, 5, 3))["lord"], "Sa")

    def test_instant_queries_use_exact_boundary(self):
        periods = self.periods()
        boundary = datetime(2030, 5, 1, 20, 0, tzinfo=UTC)
        self.assertEqual(select_period(periods, boundary - timedelta(seconds=1))["lord"], "Ju")
        self.assertEqual(select_period(periods, boundary)["lord"], "Sa")

    def test_out_of_range_fallbacks_preserved_and_never_affect_boundaries(self):
        periods = self.periods()
        before = date(2000, 1, 1)
        self.assertEqual(select_period(periods, before), {})
        self.assertEqual(select_period(periods, before, fallback="first")["lord"], "Ju")
        self.assertEqual(select_period(periods, before, fallback="last")["lord"], "Sa")
        self.assertEqual(select_period(periods, date(2031, 1, 1)), {})  # end is exclusive
        with self.assertRaises(ValueError):
            select_period(periods, before, fallback="nearest")

    def test_pre_m1_stored_periods_still_select_by_date(self):
        legacy = [{"lord": "Ju", "start": "2020-01-01", "end": "2025-06-01"},
                  {"lord": "Sa", "start": "2025-06-01", "end": "2044-06-01"}]
        self.assertEqual(select_period(legacy, date(2025, 6, 1))["lord"], "Sa")
        self.assertEqual(select_period(legacy, datetime(2025, 5, 31, 23, tzinfo=UTC))["lord"], "Ju")

    def test_no_inclusive_period_selection_remains(self):
        pattern = re.compile(r"\bstart\w*\s*<=\s*[\w.]+\s*<=\s*\w*end\w*")
        offenders = []
        for folder in ("accounts", "astrology", "charts", "chat", "payments", "astro_site"):
            for path in (BASE_DIR / folder).rglob("*.py"):
                if path.name.startswith("test") or "migrations" in path.parts:
                    continue
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if pattern.search(line):
                        offenders.append(f"{path.relative_to(BASE_DIR)}:{number}")
        self.assertEqual(offenders, [])


class ChartDashaBoundaryTests(SimpleTestCase):
    """Every surface reports the same period on the day before, of and after a transition."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.charts = fixture_charts()

    def test_consecutive_periods_share_exact_instants(self):
        for cid, (_, chart) in self.charts.items():
            groups = [chart["dashas"]["vimshottari"]["periods"], chart["dashas"]["yogini"]["periods"],
                      chart["jaimini"]["chara_dasha"]["periods"]]
            groups += [md["antardashas"] for md in chart["dashas"]["vimshottari"]["periods"]]
            groups += [md["subperiods"] for md in chart["dashas"]["yogini"]["periods"][:3]]
            groups += [md["subperiods"] for md in chart["jaimini"]["chara_dasha"]["periods"][:3]]
            for periods in groups:
                for left, right in zip(periods, periods[1:]):
                    self.assertEqual(left["end_utc"], right["start_utc"], cid)
                    self.assertEqual(left["end"], right["start"], cid)

    def test_first_period_starts_at_birth_instant_and_local_birth_date(self):
        _, chart = self.charts["R2"]  # 23:45 local on 3 Nov; 04:45 UTC on 4 Nov
        # Yogini and Chara are unchanged by M1b: they start at the birth instant.
        for periods in (chart["dashas"]["yogini"]["periods"], chart["jaimini"]["chara_dasha"]["periods"]):
            self.assertEqual(periods[0]["start_utc"], "1992-11-04T04:45:00Z")
            self.assertEqual(periods[0]["start"], "1992-11-03")
        # Vimshottari (M1b): the birth Mahadasha began before birth and is the
        # period selected at the birth instant and on the local birth date.
        vimshottari = chart["dashas"]["vimshottari"]["periods"]
        birth = datetime(1992, 11, 4, 4, 45, tzinfo=UTC)
        self.assertLess(instant(vimshottari[0]["start_utc"]), birth)
        self.assertEqual(select_period(vimshottari, birth)["lord"], vimshottari[0]["lord"])
        self.assertEqual(select_period(vimshottari, date(1992, 11, 3))["lord"], vimshottari[0]["lord"])

    def test_all_vimshottari_surfaces_agree_around_an_antardasha_transition(self):
        from astrology.calculations.dasha_facts import _current_period as facts_select
        from astrology.calculations.dasha_transit_timeline import _active_pair
        from chat.prediction_context import _current_period as prediction_select
        from chat.rashifal_context import _current_period as rashifal_select
        from chat.timing_windows import _current_period_at, _vimshottari_at

        for cid, (_, chart) in self.charts.items():
            periods = chart["dashas"]["vimshottari"]["periods"]
            md = periods[2]
            previous_ad, new_ad = md["antardashas"][3], md["antardashas"][4]
            day = date.fromisoformat(new_ad["start"])
            for target, expected in ((day - timedelta(days=1), previous_ad), (day, new_ad), (day + timedelta(days=1), new_ad)):
                with self.subTest(chart=cid, target=target):
                    results = {
                        "dasha_facts": facts_select(facts_select(periods, target)["antardashas"], target),
                        "prediction_context": prediction_select(prediction_select(periods, target)["antardashas"], target),
                        "rashifal_context": rashifal_select(rashifal_select(periods, target)["antardashas"], target),
                        "timing_windows": _current_period_at(_current_period_at(periods, target)["antardashas"], target),
                        "timing_windows_pair": _vimshottari_at(chart, target)[1],
                    }
                    for surface, found in results.items():
                        self.assertEqual(found["start_utc"], expected["start_utc"], surface)
                    self.assertEqual(_active_pair(periods, target)[1], expected["lord"])

    def test_yogini_and_chara_surfaces_agree_at_transition(self):
        from astrology.calculations.yogini import _current_period as yogini_select
        from charts.jaimini_confirmation import _current_period as jaimini_select
        from charts.yogini_alignment import _current_period as alignment_select
        from chat.prediction_context import _current_period as prediction_select
        from chat.timing_windows import _current_period_at

        for cid, (_, chart) in self.charts.items():
            yogini, chara = chart["dashas"]["yogini"]["periods"], chart["jaimini"]["chara_dasha"]["periods"]
            for periods, selectors in ((yogini, (yogini_select, alignment_select, _current_period_at)),
                                       (chara, (jaimini_select, prediction_select, _current_period_at))):
                day = date.fromisoformat(periods[3]["start"])
                for target, expected in ((day - timedelta(days=1), periods[2]), (day, periods[3])):
                    for selector in selectors:
                        self.assertEqual(selector(periods, target)["start_utc"], expected["start_utc"], (cid, selector.__module__))


class MethodProfileTests(TestCase):
    def test_actual_ephemeris_is_recorded_not_assumed(self):
        _, chart = fixture_charts()["R1"]
        _, flag = swe.calc_ut(chart["julian_day_ut"], swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)
        method = chart["calculation_method"]
        self.assertEqual(method["profile"], METHOD_PROFILE_ID)
        self.assertEqual(method["ephemeris_used"], ephemeris_from_flags([flag]))
        if flag & swe.FLG_MOSEPH:
            self.assertEqual(method["ephemeris_used"], "moshier")
            self.assertIn("data files not found", method["ephemeris_used_label"])
        self.assertEqual(chart["chart_template"], CHART_TEMPLATE)

    def test_flag_classification(self):
        self.assertEqual(ephemeris_from_flags([swe.FLG_SWIEPH, swe.FLG_SWIEPH]), "swiss_ephemeris_files")
        self.assertEqual(ephemeris_from_flags([swe.FLG_MOSEPH]), "moshier")
        self.assertEqual(ephemeris_from_flags([swe.FLG_MOSEPH, swe.FLG_SWIEPH]), "mixed")
        self.assertEqual(ephemeris_from_flags([]), "unknown")

    def test_tool_metadata_exposes_method_profile_and_instants(self):
        from astrology.tools import invoke_tool
        from charts.models import SavedChart
        spec, chart_data = fixture_charts()["R1"]
        user = get_user_model().objects.create_user(username="m1-method")
        chart = SavedChart.objects.create(user=user, name="Synthetic", birth_date=date.fromisoformat(spec["birth_date"]),
            birth_time=spec["birth_time"], birth_place="Synthetic", latitude=str(spec["latitude"]),
            longitude=str(spec["longitude"]), timezone=spec["timezone"], chart_data=chart_data)
        with override_settings(CACHES=LOCMEM):
            result = invoke_tool(user, "get_dasha_periods", {"chart_id": chart.pk, "system": "vimshottari",
                "granularity": "antardasha", "start_date": "2028-01-01", "end_date": "2030-12-31"})
        self.assertIn(result["status"], ("ok", "partial"))
        self.assertEqual(result["method"]["method_profile"]["profile"], METHOD_PROFILE_ID)
        self.assertIn("exact transition instants", result["method"]["precision"])
        self.assertTrue(all(row.get("start_utc") for row in result["data"]["periods"]))


@override_settings(CACHES=LOCMEM)
class ChartRefreshTests(TestCase):
    """OD-20 / P-3: visiting the chart list does not recalculate or rewrite current charts."""

    def setUp(self):
        from charts.models import SavedChart
        spec, chart_data = fixture_charts()["R1"]
        self.user = get_user_model().objects.create_user(username="m1-refresh")
        self.chart = SavedChart.objects.create(user=self.user, name="Synthetic", birth_date=date.fromisoformat(spec["birth_date"]),
            birth_time=spec["birth_time"], birth_place="Synthetic", latitude=str(spec["latitude"]),
            longitude=str(spec["longitude"]), timezone=spec["timezone"], chart_data=json.loads(json.dumps(chart_data)))
        self.client.force_login(self.user)

    def visit(self):
        from charts.models import SavedChart
        with patch("charts.views.build_vedic_chart", wraps=build_vedic_chart) as calculate, \
                patch.object(SavedChart, "save", autospec=True, side_effect=SavedChart.save) as save:
            self.assertEqual(self.client.get(reverse("chart_list")).status_code, 200)
        return calculate.call_count, save.call_count

    def test_current_chart_is_not_recalculated_or_saved(self):
        self.assertEqual(self.visit(), (0, 0))
        self.assertEqual(self.visit(), (0, 0))

    def test_outdated_chart_is_recalculated_exactly_once(self):
        stale = dict(self.chart.chart_data, chart_template="north_indian_clear_sign_positions_v10_shodashvarga")
        type(self.chart).objects.filter(pk=self.chart.pk).update(chart_data=stale)
        self.assertEqual(self.visit(), (1, 1))
        self.assertEqual(self.visit(), (0, 0))


@override_settings(CACHES=LOCMEM, OPENAI_API_KEY="offline-test-key", OPENAI_VECTOR_STORE_ID="offline-store")
class ProviderSecurityTests(TestCase):
    """S-2, S-3, S-4. The OpenAI client and sockets are blocked or mocked."""

    def setUp(self):
        cache.clear()
        block = patch("socket.socket.connect", side_effect=AssertionError("No live network in M1 tests"))
        block.start()
        self.addCleanup(block.stop)

    def reserved_row(self):
        from accounts.test_usage import owned_chart
        from accounts.usage import reserve
        from chat.models import Conversation
        user = get_user_model().objects.create_user(username=f"m1-{uuid4().hex[:8]}")
        chart = owned_chart(user)
        conversation = Conversation.objects.create(user=user, chart=chart)
        return reserve(user, chart, conversation, uuid4(), "Synthetic question")[0]

    @staticmethod
    def reply(text):
        return SimpleNamespace(output_text=text, output=[], usage=SimpleNamespace(
            input_tokens=50, output_tokens=8, input_tokens_details=SimpleNamespace(cached_tokens=0)))

    def test_s2_provider_error_text_is_not_stored_in_answer(self):
        import httpx
        from openai import APIConnectionError
        from astrology.tests import sample_chart_data
        from chat.llm_engine import generate_answer
        error = APIConnectionError(message="private-provider-detail org-synthetic req_abc123",
                                   request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        with patch("chat.intent_engine.classify_intent", return_value={"intent": "specific", "horizon": None}), \
                patch("chat.llm_engine.OpenAI"), patch("chat.llm_engine.responses_create", side_effect=error), \
                self.assertLogs("chat.llm_engine", "WARNING") as logs:
            result = generate_answer("When will my career improve?", sample_chart_data(), "full")
        self.assertNotIn("private-provider-detail", result["answer"])
        self.assertNotIn("req_abc123", result["answer"])
        self.assertIn("APIConnectionError", result["answer"])
        self.assertNotIn("private-provider-detail", "\n".join(logs.output))

    def test_s3_s4_classifier_is_metered_bounded_and_logs_no_question_text(self):
        from accounts.models import ProviderUsage
        from accounts.provider_meter import request_budget
        from chat.intent_engine import _llm_classify
        row = self.reserved_row()
        client = Mock()
        client.responses.create.return_value = self.reply('{"intent": "periodic", "horizon": "monthly"}')
        question = "synthetic-private-question about my manager"
        with patch("openai.OpenAI", return_value=client) as factory, request_budget(row), \
                self.assertLogs("chat.intent_engine", "INFO") as logs:
            result = _llm_classify(question)
        self.assertEqual(result["intent"], "periodic")
        self.assertEqual(factory.call_args.kwargs["timeout"], 10)
        self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
        self.assertNotIn("synthetic-private-question", "\n".join(logs.output))
        usage = ProviderUsage.objects.get(request=row)
        self.assertEqual((usage.input_tokens, usage.output_tokens), (50, 8))

    def test_s3_classifier_failure_logs_only_error_class(self):
        from accounts.provider_meter import request_budget
        from chat.intent_engine import _llm_classify
        client = Mock()
        client.responses.create.side_effect = ValueError("private response body text")
        with patch("openai.OpenAI", return_value=client), request_budget(self.reserved_row()), \
                self.assertLogs("chat.intent_engine", "WARNING") as logs:
            result = _llm_classify("another synthetic question")
        self.assertEqual(result["method"], "llm-failed")
        output = "\n".join(logs.output)
        self.assertIn("ValueError", output)
        self.assertNotIn("private response body text", output)

    def test_s4_classifier_without_accounted_budget_makes_no_call(self):
        from chat.intent_engine import _llm_classify
        with patch("openai.OpenAI", side_effect=AssertionError("unaccounted call")) as factory:
            result = _llm_classify("synthetic question outside a request")
        factory.assert_not_called()
        self.assertEqual(result["method"], "llm-skipped-unmetered")

    def test_s4_classifier_over_budget_fails_closed_before_network(self):
        from accounts.provider_meter import request_budget
        from chat.intent_engine import _llm_classify
        client = Mock()
        with patch("openai.OpenAI", return_value=client), request_budget(self.reserved_row()) as budget:
            budget.rounds = budget.policy["rounds"]
            result = _llm_classify("synthetic over-budget question")
        client.responses.create.assert_not_called()
        self.assertEqual(result["method"], "llm-failed")

    def test_s4_yearly_predictions_never_call_without_accounted_budget(self):
        from charts.yearly_predictions import _llm_month_predictions
        with patch("charts.yearly_predictions.OpenAI", side_effect=AssertionError("unaccounted call")) as factory:
            self.assertEqual(_llm_month_predictions(date(2027, 1, 1), []), {})
        factory.assert_not_called()

    def test_s4_yearly_predictions_metered_inside_request(self):
        from accounts.models import ProviderUsage
        from accounts.provider_meter import request_budget
        from charts.yearly_predictions import _llm_month_predictions
        row = self.reserved_row()
        client = Mock()
        client.responses.create.return_value = self.reply("{}")
        with patch("charts.yearly_predictions.OpenAI", return_value=client) as factory, \
                patch("charts.yearly_predictions._deterministic_prediction_payload", return_value={}), request_budget(row):
            _llm_month_predictions(date(2027, 1, 1), [])
        self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
        self.assertEqual(ProviderUsage.objects.filter(request=row).count(), 1)


class ConfigurationAndEndpointSecurityTests(TestCase):
    def run_settings(self, **env):
        environment = {k: v for k, v in os.environ.items() if k not in ("DJANGO_SECRET_KEY", "DJANGO_DEBUG")}
        environment.update(DJANGO_SETTINGS_MODULE="astro_site.settings", **env)
        return subprocess.run([sys.executable, "-c", "import astro_site.settings"], cwd=BASE_DIR, env=environment,
                              capture_output=True, text=True, timeout=120)

    def test_s5_debug_off_requires_strong_secret(self):
        weak = self.run_settings(DJANGO_DEBUG="false")
        self.assertNotEqual(weak.returncode, 0)
        self.assertIn("ImproperlyConfigured", weak.stderr)
        dev = self.run_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY="dev-only-change-me")
        self.assertNotEqual(dev.returncode, 0)
        strong = self.run_settings(DJANGO_DEBUG="false", DJANGO_SECRET_KEY="synthetic-strong-test-key-" + "Ab3Xy9Qz" * 5)
        self.assertEqual(strong.returncode, 0, strong.stderr[-500:])

    def test_s8_webhook_placeholder_fails_closed(self):
        self.assertEqual(self.client.get(reverse("payment_webhook")).status_code, 405)
        self.assertEqual(self.client.post(reverse("payment_webhook"), {"event": "paid"}).status_code, 501)

    def test_s9_rejected_first_turn_leaves_no_empty_conversation(self):
        from accounts.test_usage import owned_chart
        from chat.consultation_service import TurnOutcome
        from chat.models import Conversation
        user = get_user_model().objects.create_user(username="m1-s9")
        chart = owned_chart(user)
        self.client.force_login(user)
        with override_settings(CACHES=LOCMEM, FREE_QUESTION_CREDITS=2), \
                patch("chat.views.append_turn", return_value=TurnOutcome(403, "insufficient_credits", None)):
            response = self.client.post(reverse("ask_question"), {"request_id": uuid4(), "chart_id": chart.pk,
                "answer_language": "English", "question": "Synthetic question"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Conversation.objects.filter(user=user).exists())

    def test_geocoding_error_hides_exception_detail(self):
        from urllib.error import URLError
        from charts.geocoding import search_places
        with override_settings(GEONAMES_USERNAME="synthetic"), \
                patch("charts.geocoding.urlopen", side_effect=URLError("private-host-detail")):
            result = search_places("Delhi")
        self.assertNotIn("private-host-detail", result["error"])
        self.assertIn("URLError", result["error"])
