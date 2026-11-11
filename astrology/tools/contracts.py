"""Versioned local-tool contracts. No coercion or extra argument acceptance."""
from dataclasses import asdict, dataclass, fields
from datetime import date
import json
import math
import re
from types import UnionType
from typing import Literal, TypeAlias, get_args, get_origin, get_type_hints

JSONValue: TypeAlias = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
SCHEMA_VERSION = "1.0"
MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 262144
MAX_DAYS = 1097
MAX_SAMPLES = 4096


class ToolFailure(Exception):
    def __init__(self, code: str, message: str, status: str = "error"):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass(frozen=True)
class ChartFactsRequest:
    chart_id: int
    charts: tuple[str, ...] = ("d1",)
    include_yogas: bool = False  # M3: expose the stored chart_data['yogas'] (charts/yogas.py)


@dataclass(frozen=True)
class JaiminiRequest:
    """M3 read-only wrapper over astrology/calculations/jaimini.py (7 karakas, house padas)."""
    chart_id: int
    include: tuple[str, ...] = ("karakas", "karakamsha", "padas", "jaimini_yogas", "ak_amk")


@dataclass(frozen=True)
class CountedSignRequest:
    """M3 OD-31: n-th sign (1-12, inclusive) from AL, UL or Karakamsha."""
    chart_id: int
    reference: str
    count: int


@dataclass(frozen=True)
class AspectsRequest:
    """M3 OD-32: Parashari natal aspects (charts/vedic_utils.py); not Jaimini rasi drishti."""
    chart_id: int
    house: int | None = None
    planet: str | None = None


@dataclass(frozen=True)
class DashaRequest:
    chart_id: int
    system: str
    start_date: str
    end_date: str
    granularity: str = "antardasha"


@dataclass(frozen=True)
class TransitRequest:
    chart_id: int
    planets: tuple[str, ...]
    start_date: str
    end_date: str
    resolution: str = "daily"
    output: str = "segments"


@dataclass(frozen=True)
class AshtakavargaRequest:
    chart_id: int
    planet: str = "all"
    kind: str = "both"
    sign: int | None = None
    house: int | None = None


@dataclass(frozen=True)
class RuleRequest:
    chart_id: int
    category: str
    as_of: str
    max_rules: int = 40


@dataclass(frozen=True)
class TimingRequest:
    chart_id: int
    topic: str
    start_date: str
    end_date: str
    evidence_policy: str = "legacy_intersections"
    max_candidates: int = 5


@dataclass(frozen=True)
class ChartFactsData:
    system: str | None
    ayanamsa: str | None
    charts: dict[str, JSONValue]
    longitudes: dict[str, JSONValue]
    missing_charts: list[str]
    units: dict[str, JSONValue]
    yogas: list[dict[str, JSONValue]] | None = None


@dataclass(frozen=True)
class DashaData:
    system: str
    granularity: str
    periods: list[dict[str, JSONValue]]
    coverage: dict[str, JSONValue]
    source_method: dict[str, JSONValue]


@dataclass(frozen=True)
class TransitData:
    planets: list[str]
    output: str
    samples: list[dict[str, JSONValue]]
    coverage: dict[str, JSONValue]
    units: dict[str, JSONValue]


@dataclass(frozen=True)
class AshtakavargaData:
    kind: str
    planet: str
    rows: list[dict[str, JSONValue]]
    units: str


@dataclass(frozen=True)
class RuleData:
    category: str
    as_of: str
    triggered_rules: list[dict[str, JSONValue]]
    total_triggered: int
    omitted_rules: int
    summary_scores: dict[str, JSONValue]
    conflicts: dict[str, JSONValue]
    score_kind: str


@dataclass(frozen=True)
class TimingData:
    topic: str
    candidates: list[dict[str, JSONValue]]
    coverage: dict[str, JSONValue]
    selection_rule: str
    omitted_candidates: int
    score_kind: str


@dataclass(frozen=True)
class JaiminiData:
    karakas: dict[str, JSONValue] | None
    karakamsha: dict[str, JSONValue] | None
    padas: dict[str, JSONValue] | None
    jaimini_yogas: list[dict[str, JSONValue]] | None
    ak_amk: dict[str, JSONValue] | None
    conventions: dict[str, JSONValue]
    unavailable: list[str]


@dataclass(frozen=True)
class CountedSignData:
    result: dict[str, JSONValue]
    conventions: dict[str, JSONValue]


@dataclass(frozen=True)
class AspectsData:
    system: str
    planets: list[dict[str, JSONValue]]
    houses: dict[str, JSONValue]
    mutual_aspects: list[dict[str, JSONValue]]
    convention: dict[str, JSONValue]


@dataclass(frozen=True)
class ToolError:
    code: str
    message: str


@dataclass(frozen=True)
class ToolResponse:
    schema_version: str
    status: Literal["ok", "partial", "unsupported", "error"]
    data: ChartFactsData | DashaData | TransitData | AshtakavargaData | RuleData | TimingData | JaiminiData | CountedSignData | AspectsData | None
    warnings: list[str]
    method: dict[str, JSONValue]
    provenance: dict[str, JSONValue]
    error: ToolError | None


DATA_TYPES = {
    "get_chart_facts": ChartFactsData,
    "get_dasha_periods": DashaData,
    "get_transits": TransitData,
    "get_ashtakavarga": AshtakavargaData,
    "evaluate_astrology_rules": RuleData,
    "get_timing_candidates": TimingData,
    "get_jaimini_facts": JaiminiData,
    "get_counted_sign": CountedSignData,
    "get_natal_aspects": AspectsData,
}


def _matches(value, annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is UnionType:
        return any(_matches(value, item) for item in args)
    if origin is Literal:
        return value in args
    if annotation is type(None):
        return value is None
    if origin in (list, tuple):
        return type(value) is origin and all(_matches(item, args[0]) for item in value)
    if origin is dict:
        return type(value) is dict and all(type(key) is str for key in value)
    if annotation in (str, int, bool, float, dict, list):
        return type(value) is annotation
    return isinstance(value, annotation)


def json_bytes(value) -> bytes:
    """Reject non-JSON values, NaN, integer dictionary keys and over-deep trees."""
    def check(item, depth=0):
        if depth > 32:
            raise ValueError("JSON nesting limit exceeded")
        if type(item) in (str, int, bool, type(None)):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) in (list, tuple):
            for child in item:
                check(child, depth + 1)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child, depth + 1)
            return
        raise ValueError("Value is not strict JSON")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def parse_request(request_type, arguments):
    try:
        if type(arguments) is not dict:
            raise ValueError("Arguments must be an object")
        if len(json_bytes(arguments)) > MAX_REQUEST_BYTES:
            raise ToolFailure("request_limit", "Request exceeds 8192 UTF-8 bytes.")
        allowed = {f.name for f in fields(request_type)}
        if set(arguments) - allowed:
            raise ValueError("Unknown argument")
        hints = get_type_hints(request_type)
        values = dict(arguments)
        for name, value in values.items():
            if get_origin(hints[name]) is tuple:
                if type(value) not in (list, tuple) or not value or len(value) > 16:
                    raise ValueError("Expected a nonempty bounded list")
                value = values[name] = tuple(value)
            if not _matches(value, hints[name]):
                raise ValueError("Argument type mismatch")
        result = request_type(**values)
        if not 0 < result.chart_id <= 9223372036854775807:
            raise ValueError("Chart ID must be positive")
        return result
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ToolFailure("invalid_arguments", "Arguments do not match the tool schema.") from None


def parse_date(value: str) -> date:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ToolFailure("invalid_date", "Dates must be valid YYYY-MM-DD strings.") from None


def date_range(start: str, end: str):
    left, right = parse_date(start), parse_date(end)
    days = (right - left).days + 1
    if days <= 0:
        raise ToolFailure("invalid_range", "End must be on or after start.")
    if days > MAX_DAYS:
        raise ToolFailure("range_limit", f"Range exceeds {MAX_DAYS} inclusive days.")
    # Legacy helpers add one day and may scan a dasha/year beyond the request.
    if not 1800 <= left.year <= right.year <= 2200:
        raise ToolFailure("date_limit", "Supported tool dates are 1800 through 2200.")
    return left, right


def supported(condition, message):
    if not condition:
        raise ToolFailure("unsupported", message, "unsupported")


def validate_payload(tool: str, payload: dict):
    """Validate both live and cached results; legacy nested objects remain JSON."""
    if type(payload) is not dict or set(payload) != {f.name for f in fields(ToolResponse)}:
        raise ValueError("Invalid envelope")
    hints = get_type_hints(ToolResponse)
    for key in ("schema_version", "status", "warnings", "method", "provenance"):
        if not _matches(payload[key], hints[key]):
            raise ValueError("Invalid envelope field")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Invalid version")
    success = payload["status"] in ("ok", "partial")
    if success:
        cls = DATA_TYPES[tool]
        data = payload["data"]
        if type(data) is not dict or set(data) != {f.name for f in fields(cls)}:
            raise ValueError("Invalid data object")
        for key, annotation in get_type_hints(cls).items():
            if not _matches(data[key], annotation):
                raise ValueError("Invalid data field")
        if cls is ChartFactsData:
            for chart in data["longitudes"].values():
                if type(chart) is not dict or any(value is not None and (type(value) not in (int, float) or not 0 <= value < 360) for value in chart.values()):
                    raise ValueError("Invalid stored longitude")
        if cls is AshtakavargaData:
            for row in data["rows"]:
                if set(row) != {"sign_number", "sign", "house", "sav", "bav"}:
                    raise ValueError("Invalid Ashtakavarga row")
                if any(type(row[key]) is not int or not 1 <= row[key] <= 12 for key in ("sign_number", "house")):
                    raise ValueError("Invalid sign/house mapping")
                if type(row["bav"]) is not dict or type(row["sign"]) is not str:
                    raise ValueError("Invalid score mapping")
                if row["sav"] is not None and (type(row["sav"]) is not int or not 0 <= row["sav"] <= 56):
                    raise ValueError("Invalid SAV")
                if any(v is not None and (type(v) is not int or not 0 <= v <= 8) for v in row["bav"].values()):
                    raise ValueError("Invalid BAV")
        if cls is RuleData and any(type(v) is not int or not 0 <= v <= 100 for v in data["summary_scores"].values()):
            raise ValueError("Invalid rule summary scores")
        if payload["error"] is not None:
            raise ValueError("Unexpected error")
    else:
        error = payload["error"]
        if payload["data"] is not None or type(error) is not dict or set(error) != {"code", "message"}:
            raise ValueError("Invalid error")
        if not all(type(v) is str for v in error.values()):
            raise ValueError("Invalid error fields")
    if len(json_bytes(payload)) > MAX_RESPONSE_BYTES:
        raise ToolFailure("output_limit", "Result exceeds 262144 UTF-8 bytes; narrow the request.")
    return payload


def response(tool, status, data=None, warnings=(), method=None, provenance=None, error=None):
    value = asdict(ToolResponse(SCHEMA_VERSION, status, data, list(warnings), method or {}, provenance or {}, error))
    return validate_payload(tool, value)
