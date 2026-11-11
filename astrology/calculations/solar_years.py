"""True sidereal solar years for Vimshottari dasha (owner decision M1b).

A dasha year is measured by the Sun, not by a fixed number of days. Elapsed
dasha year ``Y`` (which may be negative, before birth) is the instant when
the Sun's sidereal longitude has advanced ``360 * Y`` degrees from its
position at birth. This is the convention Jagannatha Hora labels "true
sidereal solar years".
"""

from datetime import datetime, timedelta, timezone as dt_timezone

import swisseph as swe

from .method_profile import POSITION_FLAGS, SIDEREAL_MODE

UTC = dt_timezone.utc
_J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)
_J2000_JD = 2451545.0
MEAN_SIDEREAL_YEAR_DAYS = 365.256363
_TOLERANCE_DAYS = 1e-7  # about 0.01 second
_MAX_ITERATIONS = 20


def _julian_day(instant: datetime) -> float:
    return _J2000_JD + (instant - _J2000).total_seconds() / 86400


def _instant(jd_ut: float) -> datetime:
    return _J2000 + timedelta(days=jd_ut - _J2000_JD)


def _sun(jd_ut: float) -> tuple[float, float]:
    swe.set_sid_mode(SIDEREAL_MODE)
    values, _ = swe.calc_ut(jd_ut, swe.SUN, POSITION_FLAGS)
    return values[0] % 360, values[3]


class SiderealSolarYearClock:
    """Map elapsed dasha years, counted from birth, to exact UTC instants."""

    def __init__(self, birth: datetime):
        if birth.tzinfo is None:
            raise ValueError("birth must be an aware datetime")
        self.birth = birth.astimezone(UTC)
        self.birth_jd = _julian_day(self.birth)
        self.birth_sun, _ = _sun(self.birth_jd)
        self._cache: dict[float, datetime] = {}

    def instant(self, years: float) -> datetime:
        if years in self._cache:
            return self._cache[years]
        target = self.birth_sun + 360.0 * years
        jd = self.birth_jd + years * MEAN_SIDEREAL_YEAR_DAYS
        for _ in range(_MAX_ITERATIONS):
            longitude, speed = _sun(jd)
            # The mean-year starting guess is within days of the answer, so the
            # wrapped difference is the true remaining arc.
            step = (((target - longitude) + 180.0) % 360.0 - 180.0) / speed
            jd += step
            if abs(step) < _TOLERANCE_DAYS:
                break
        else:  # pragma: no cover - the Sun's motion is smooth; never observed
            raise ArithmeticError("sidereal solar year did not converge")
        result = _instant(jd)
        self._cache[years] = result
        return result
