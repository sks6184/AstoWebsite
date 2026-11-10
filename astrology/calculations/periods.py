"""Shared dasha period timing: exact instants, display dates and one selector.

Convention (owner decision OD-8): every period is half-open, ``[start, end)``.

* Internally, a period's boundaries are exact instants, ``start_utc`` and
  ``end_utc`` (ISO-8601, UTC). One period's ``end_utc`` equals the next
  period's ``start_utc``.
* ``start`` and ``end`` are calendar dates in the period's display timezone
  (the chart's timezone; there is no per-user timezone yet). A new period is
  in effect from its start date, and the previous period ends the day before.
* A date query selects by calendar date: ``start <= day < end``.
* An aware-datetime query selects by instant: ``start_utc <= t < end_utc``.
  Periods stored before M1 carry no instants; they fall back to calendar
  dates.
"""

from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = dt_timezone.utc
FALLBACKS = ("none", "first", "last")


def resolve_timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def birth_instant(birth: date | datetime, timezone_name: str | None = None,
                  birth_time: time | None = None) -> datetime:
    """Return the birth moment as an aware UTC datetime.

    An aware datetime is used as given. A naive datetime, or a date plus an
    optional time, is interpreted in ``timezone_name``. A bare date with no
    time means local midnight, the pre-M1 behaviour.
    """
    if isinstance(birth, datetime):
        local = birth
    else:
        local = datetime.combine(birth, birth_time or time(0, 0))
    if local.tzinfo is None:
        local = local.replace(tzinfo=resolve_timezone(timezone_name))
    return local.astimezone(UTC)


def chart_birth_instant(chart_data: dict[str, Any]) -> datetime | None:
    """Birth instant from the inputs recorded in stored chart data."""
    raw_date = chart_data.get("birth_date")
    if not raw_date:
        return None
    birth_date = raw_date if isinstance(raw_date, date) else datetime.fromisoformat(str(raw_date)).date()
    raw_time = chart_data.get("birth_time")
    birth_time = None
    if raw_time:
        birth_time = raw_time if isinstance(raw_time, time) else time.fromisoformat(str(raw_time))
    return birth_instant(birth_date, chart_data.get("timezone"), birth_time)


def iso_utc(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


def local_date(instant: datetime, display_zone: ZoneInfo) -> date:
    return instant.astimezone(display_zone).date()


def format_display_date(value: date) -> str:
    return value.strftime("%d-%b-%Y")


def timing_fields(start: datetime, end: datetime, display_zone: ZoneInfo) -> dict[str, str]:
    """Stored period boundary fields for one period (instants plus display dates)."""
    start_day, end_day = local_date(start, display_zone), local_date(end, display_zone)
    return {
        "start": start_day.isoformat(),
        "end": end_day.isoformat(),
        "start_display": format_display_date(start_day),
        "end_display": format_display_date(end_day),
        "start_utc": iso_utc(start),
        "end_utc": iso_utc(end),
    }


def interval_metadata(display_zone: ZoneInfo) -> dict[str, str]:
    return {
        "interval_convention": "[start, end)",
        "boundary_precision": "exact instants in start_utc/end_utc; start/end are calendar dates in display_timezone",
        "display_timezone": display_zone.key,
    }


def _parse_day(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_instant(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def period_contains(period: dict[str, Any], target: date | datetime) -> bool:
    """True when ``target`` lies in the half-open period ``[start, end)``."""
    if isinstance(target, datetime) and target.tzinfo is not None:
        start, end = _parse_instant(period.get("start_utc")), _parse_instant(period.get("end_utc"))
        if start is not None and end is not None:
            return start <= target < end
        target = target.date()  # Pre-M1 stored period: calendar dates only.
    elif isinstance(target, datetime):
        target = target.date()
    start, end = _parse_day(period.get("start")), _parse_day(period.get("end"))
    return start is not None and end is not None and start <= target < end


def select_period(periods: Iterable[dict[str, Any]] | None, target: date | datetime,
                  fallback: str = "none") -> dict[str, Any]:
    """Return the period in effect at ``target``, using the ``[start, end)`` convention.

    ``fallback`` keeps each legacy caller's existing out-of-range behaviour:
    ``"none"`` returns ``{}``, ``"first"`` or ``"last"`` return that period.
    The fallback applies only when no period contains the target (for example
    a date before birth). It never changes a boundary decision.
    """
    if fallback not in FALLBACKS:
        raise ValueError(f"fallback must be one of {FALLBACKS}")
    items = [period for period in (periods or []) if isinstance(period, dict)]
    for period in items:
        if period_contains(period, target):
            return period
    if not items or fallback == "none":
        return {}
    return items[0] if fallback == "first" else items[-1]


def split_interval(start: datetime, end: datetime, weights: list[float]) -> list[tuple[datetime, datetime]]:
    """Split ``[start, end)`` exactly in proportion to ``weights``.

    The last part ends exactly at ``end``, so consecutive parts share their
    boundary instants without rounding gaps.
    """
    total_weight = sum(weights)
    span = end - start
    parts = []
    elapsed = 0.0
    current = start
    for index, weight in enumerate(weights):
        elapsed += weight
        part_end = end if index == len(weights) - 1 else start + span * (elapsed / total_weight)
        parts.append((current, part_end))
        current = part_end
    return parts


def add_years(instant: datetime, years: float, year_days: float) -> datetime:
    return instant + timedelta(days=years * year_days)
