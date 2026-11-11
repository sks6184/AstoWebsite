"""M1b tests: calculation settings that match the owner's Jagannatha Hora.

Owner decisions: geometric planet positions with Lahiri, true sidereal solar
years for Vimshottari, and a full-period birth Mahadasha (finding M1-F1).

``OwnerPrivateJagannathaHoraTests`` reads the owner's own chart and JH values
from a git-ignored file. When the file is absent (for example on another
machine), the test is skipped: a skip is never a pass. All other tests use
synthetic charts. No provider or network call is made.
"""
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe
from django.test import SimpleTestCase

from astrology.calculations.method_profile import POSITION_FLAGS, SIDEREAL_MODE, build_method_profile
from astrology.calculations.periods import select_period
from astrology.calculations.solar_years import SiderealSolarYearClock
from astrology.calculations.vimshottari import build_vimshottari_dasha
from astrology.test_m1 import UTC, fixture_charts, instant, planet
from charts.astro_engine import build_vedic_chart
from charts.vedic_utils import transit_longitude

PRIVATE_REFERENCE = Path(__file__).resolve().parent / "evaluation" / "private" / "owner_jh_reference.json"


def dms(value):
    d, m, s = (float(x) for x in value.split(":"))
    return d + m / 60 + s / 3600


def arcsec(a, b):
    return abs((a - b + 180) % 360 - 180) * 3600


class GeometricPositionTests(SimpleTestCase):
    def test_natal_planets_use_geometric_positions(self):
        _, chart = fixture_charts()["R1"]
        swe.set_sid_mode(SIDEREAL_MODE)
        for code, body in (("Su", swe.SUN), ("Mo", swe.MOON), ("Ma", swe.MARS)):
            geometric = swe.calc_ut(chart["julian_day_ut"], body, POSITION_FLAGS)[0][0]
            self.assertLess(arcsec(planet(chart, code)["longitude"], geometric), 0.01, code)  # stored to 6 decimals
        self.assertTrue(POSITION_FLAGS & swe.FLG_TRUEPOS)

    def test_transits_use_the_same_convention_as_natal_positions(self):
        _, chart = fixture_charts()["R1"]
        birth = instant(chart["birth_instant_utc"])
        for code in ("Su", "Mo", "Sa", "Ra"):
            self.assertLess(arcsec(transit_longitude(code, birth), planet(chart, code)["longitude"]), 0.01, code)

    def test_method_profile_records_the_owner_conventions(self):
        profile = build_method_profile("moshier")
        self.assertIn("geometric", profile["planet_positions"])
        self.assertIn("true sidereal solar year", profile["vimshottari_year"])
        self.assertIn("before birth", profile["vimshottari_birth_mahadasha"])
        self.assertEqual(profile["yogini_chara_year_days"], 365.2425)
        self.assertIn("true node", profile["lunar_node"])


class SiderealSolarYearClockTests(SimpleTestCase):
    def setUp(self):
        self.birth = datetime(1992, 11, 4, 4, 45, tzinfo=UTC)
        self.clock = SiderealSolarYearClock(self.birth)

    def sun(self, moment):
        jd = swe.julday(moment.year, moment.month, moment.day,
                        moment.hour + moment.minute / 60 + (moment.second + moment.microsecond / 1e6) / 3600)
        swe.set_sid_mode(SIDEREAL_MODE)
        return swe.calc_ut(jd, swe.SUN, POSITION_FLAGS)[0][0]

    def test_zero_years_is_the_birth_instant(self):
        self.assertLess(abs((self.clock.instant(0.0) - self.birth).total_seconds()), 0.01)

    def test_fractional_and_negative_years_land_on_the_solar_longitude(self):
        start = self.sun(self.birth)
        for years in (-2.4937, -0.25, 0.3, 1.0, 6.0, 17.75, 120.0):
            moment = self.clock.instant(years)
            self.assertLess(arcsec(self.sun(moment), start + 360 * years), 0.05, years)

    def test_year_length_varies_only_slightly_around_the_sidereal_year(self):
        one = (self.clock.instant(1.0) - self.birth).total_seconds() / 86400
        self.assertAlmostEqual(one, 365.2564, delta=0.05)

    def test_rejects_naive_birth(self):
        with self.assertRaises(ValueError):
            SiderealSolarYearClock(datetime(1992, 11, 4, 4, 45))


class FullPeriodBirthMahadashaTests(SimpleTestCase):
    def test_moon_at_nakshatra_start_gives_a_birth_mahadasha_starting_at_birth(self):
        birth = datetime(2000, 1, 1, 12, tzinfo=UTC)
        dasha = build_vimshottari_dasha(birth, 0.0, timezone_name="UTC")
        first = dasha["periods"][0]
        self.assertEqual(first["lord"], "Ke")
        self.assertFalse(first["starts_before_birth"])
        self.assertLess(abs((instant(first["start_utc"]) - birth).total_seconds()), 0.01)
        self.assertEqual(first["antardashas"][0]["lord"], "Ke")

    def test_birth_mahadasha_keeps_its_full_antardasha_sequence(self):
        birth = datetime(2000, 1, 1, 12, tzinfo=UTC)
        # Moon halfway through Ashwini: 3.5 of Ketu's 7 years have elapsed.
        dasha = build_vimshottari_dasha(birth, 360 / 54, timezone_name="UTC")
        first = dasha["periods"][0]
        self.assertTrue(first["starts_before_birth"])
        self.assertAlmostEqual(first["balance_years_at_birth"], 3.5, places=6)
        self.assertEqual([ad["lord"] for ad in first["antardashas"]], ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"])
        # Cumulative Ketu antardashas: Ke 0.408, Ve 1.575, Su 1.925, Mo 2.508, Ma 2.917, Ra 3.967 years.
        # Elapsed 3.5 years therefore falls in Ketu-Rahu, not Ketu-Ketu.
        self.assertEqual(select_period(first["antardashas"], birth)["lord"], "Ra")
        self.assertEqual(first["antardashas"][-1]["end_utc"], first["end_utc"])
        self.assertEqual(first["end_utc"], dasha["periods"][1]["start_utc"])


class OwnerPrivateJagannathaHoraTests(SimpleTestCase):
    """The owner's own chart against their JH values (git-ignored data; skipped when absent)."""

    def test_against_owner_jagannatha_hora(self):
        if not PRIVATE_REFERENCE.exists():
            self.skipTest("PENDING: private owner JH reference file is not present on this machine.")
        reference = json.loads(PRIVATE_REFERENCE.read_text(encoding="utf-8"))
        tolerance = reference["tolerances"]
        zone = ZoneInfo("Asia/Kolkata")
        for spec in reference["charts"]:
            chart = build_vedic_chart("private", date.fromisoformat(spec["birth_date"]), time.fromisoformat(spec["birth_time"]),
                                      "private", spec["latitude"], spec["longitude"], spec["timezone"])
            for code, value in spec["d1_longitudes_dms"].items():
                self.assertLessEqual(arcsec(planet(chart, code)["longitude"], dms(value)), tolerance["planet_arcsec"], code)
            periods = chart["dashas"]["vimshottari"]["periods"]
            limit = timedelta(hours=tolerance["dasha_start_hours"])

            def local(value):
                return datetime.fromisoformat(value).replace(tzinfo=zone)

            for lord, value in spec["vimshottari_md_starts_local"].items():
                found = next(p for p in periods if p["lord"] == lord)
                self.assertLessEqual(abs(instant(found["start_utc"]) - local(value)), limit, ("MD", lord))
            birth_md = periods[0]
            for lord, value in spec["birth_md_antardasha_starts_local"].items():
                found = next(p for p in birth_md["antardashas"] if p["lord"] == lord)
                self.assertLessEqual(abs(instant(found["start_utc"]) - local(value)), limit, ("AD", lord))
            at_birth = select_period(birth_md["antardashas"], instant(chart["birth_instant_utc"]))
            self.assertEqual(at_birth["lord"], spec["antardasha_at_birth"])
