"""Fixed local dispatcher; principal comes from trusted server code, not JSON."""
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, MISSING
from decimal import Decimal
from types import MappingProxyType, UnionType
from typing import Callable, get_args, get_origin, get_type_hints

from django.core.cache import cache

from charts.models import SavedChart
from . import adapters
from .contracts import (
    AshtakavargaRequest, ChartFactsRequest, DashaRequest, RuleRequest, TimingRequest,
    AspectsRequest, CountedSignRequest, JaiminiRequest,
    DATA_TYPES, SCHEMA_VERSION, ToolError, ToolFailure, TransitRequest, json_bytes, parse_request, response, validate_payload,
)
from .fingerprints import chart_fingerprint, digest, engine_fingerprint


@dataclass(frozen=True)
class ToolSpec:
    request_type: type
    adapter: Callable
    requires_natal: bool = False


TOOL_REGISTRY = MappingProxyType({
    "get_chart_facts": ToolSpec(ChartFactsRequest, adapters.get_chart_facts),
    "get_dasha_periods": ToolSpec(DashaRequest, adapters.get_dasha_periods),
    "get_transits": ToolSpec(TransitRequest, adapters.get_transits, True),
    "get_ashtakavarga": ToolSpec(AshtakavargaRequest, adapters.get_ashtakavarga, True),
    "evaluate_astrology_rules": ToolSpec(RuleRequest, adapters.evaluate_astrology_rules, True),
    "get_timing_candidates": ToolSpec(TimingRequest, adapters.get_timing_candidates, True),
    # M3 read-only wrappers over existing calculations (OD-25, OD-31, OD-32).
    "get_jaimini_facts": ToolSpec(JaiminiRequest, adapters.get_jaimini_facts, True),
    "get_counted_sign": ToolSpec(CountedSignRequest, adapters.get_counted_sign, True),
    "get_natal_aspects": ToolSpec(AspectsRequest, adapters.get_natal_aspects, True),
})
CACHE_TTL = 300


def _is_partial(data, warnings):
    if isinstance(data, adapters.ChartFactsData):
        return bool(data.missing_charts)
    if isinstance(data, adapters.DashaData):
        return not data.coverage["complete"]
    if isinstance(data, adapters.TimingData):
        return not data.coverage["complete"] or bool(data.omitted_candidates) or not data.candidates
    return bool(warnings)


def invoke_tool(user, name: str, arguments: dict) -> dict:
    """The only dispatch boundary. No provider, model write or dynamic import API."""
    safe_name = name if type(name) is str and name in TOOL_REGISTRY else "unknown"
    method = {"tool": safe_name, "version": "1.0", "engine": "existing AstroGPT deterministic helpers"}
    provenance = {}
    try:
        if not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False) or type(getattr(user, "pk", None)) is not int:
            raise ToolFailure("authentication_required", "An authenticated active principal is required.")
        if safe_name == "unknown":
            raise ToolFailure("unsupported_tool", "Tool is not in the deterministic allowlist.", "unsupported")
        spec = TOOL_REGISTRY[name]
        request = parse_request(spec.request_type, arguments)
        # Always query the owner even when a cached result is available. No staff bypass.
        chart = SavedChart.objects.filter(pk=request.chart_id, user_id=user.pk).first()
        if chart is None:
            raise ToolFailure("chart_not_found", "Chart is unavailable.")
        if type(chart.chart_data) is not dict:
            raise ToolFailure("incomplete_chart", "Stored chart data is not a valid object.")
        if len(json_bytes(chart.chart_data)) > 2 * 1024 * 1024:
            raise ToolFailure("chart_limit", "Stored chart exceeds the tool input limit.")
        if spec.requires_natal and (not chart.chart_data.get("d1", {}).get("planets") or
                                    type(chart.chart_data.get("ascendant", {}).get("sign_number")) is not int or
                                    chart.chart_data.get("ascendant", {}).get("sign_number") not in range(1, 13)):
            raise ToolFailure("incomplete_chart", "Stored D1 planets and a valid natal Lagna are required; no chart is regenerated.")
        if spec.requires_natal and chart.chart_data.get("system") != "vedic_lahiri":
            raise ToolFailure("unsupported", "Calculating tools require the implemented vedic_lahiri chart system.", "unsupported")
        provenance = {"chart_id": chart.pk, "chart_fingerprint": chart_fingerprint(chart),
                      "engine_fingerprint": engine_fingerprint(), "request_fingerprint": digest(asdict(request)),
                      "source": "authorized stored chart plus existing local helpers; no independent numerical certification"}
        cache_key = "astro-tools-v1:" + digest({"owner": user.pk, "tool": name, **provenance})
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached is not None:
            try:
                if cached.get("provenance") == provenance and cached.get("method", {}).get("tool") == name:
                    return deepcopy(validate_payload(name, cached))
            except (ValueError, TypeError, KeyError, ToolFailure):
                pass  # Invalid cache entries never bypass the output schema.
        data, warnings, precision, interval = spec.adapter(request, chart)
        warnings = list(warnings)
        natal_incomplete = {p.get("code") for p in chart.chart_data.get("d1", {}).get("planets", []) if p.get("code") != "Asc"} != set(adapters.PLANET_NAMES)
        if natal_incomplete:
            warnings.append("Stored natal planet coverage is incomplete; no missing planets were calculated or inferred.")
        if chart.latitude is None or chart.longitude is None:
            warnings.append("Birth coordinates are missing; using stored facts only, without regeneration.")
        metadata = {"birth_date": chart.birth_date.isoformat(), "birth_time": chart.birth_time.isoformat(), "timezone": chart.timezone}
        input_mismatch = any(chart.chart_data.get(key) is not None and chart.chart_data[key] != value for key, value in metadata.items())
        for key in ("latitude", "longitude"):
            if chart.chart_data.get(key) is not None and getattr(chart, key) is not None:
                input_mismatch = input_mismatch or Decimal(str(chart.chart_data[key])) != getattr(chart, key)
        if input_mismatch:
            warnings.append("Stored calculation inputs differ from chart metadata; results describe stored facts, without recalculation.")
        method.update({"precision": precision, "interval_convention": interval,
                       "method_profile": chart.chart_data.get("calculation_method") or
                       {"profile": "unrecorded", "note": "Chart was calculated before M1; ephemeris method was not recorded."},
                       "reference_frame": "Lahiri sidereal; natal whole-sign Lagna houses" if chart.chart_data.get("system") == "vedic_lahiri" else "Unspecified stored chart frame; no frame inferred"})
        partial = _is_partial(data, warnings) or chart.latitude is None or chart.longitude is None or input_mismatch or natal_incomplete
        payload = response(name, "partial" if partial else "ok", data, warnings, method, provenance)
        try:
            cache.set(cache_key, payload, CACHE_TTL)
        except Exception:
            pass  # The cache is optional; deterministic computation remains available.
        return deepcopy(payload)
    except ToolFailure as exc:
        return response(safe_name, exc.status, method=method, provenance=provenance,
                        error=ToolError(exc.code, exc.message))
    except Exception:
        # Never leak exception details, filesystem paths, chart data or credentials.
        return response(safe_name, "error", method=method, error=ToolError(
            "computation_error", "Stored evidence could not be processed safely; no result was inferred."
        ))


def _schema(annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is UnionType:
        return {"anyOf": [_schema(item) for item in args]}
    if origin in (tuple, list):
        result = {"type": "array", "items": _schema(args[0])}
        if origin is tuple:
            result.update(minItems=1, maxItems=16)
        return result
    if origin is dict:
        return {"type": "object"}
    return {"type": {str: "string", int: "integer", bool: "boolean", dict: "object", type(None): "null"}[annotation]}


def _object_schema(cls):
    return {"type": "object", "additionalProperties": False,
            "properties": {key: _schema(annotation) for key, annotation in get_type_hints(cls).items()},
            "required": [f.name for f in fields(cls)]}


def output_schema(tool):
    data_schema = _object_schema(DATA_TYPES[tool])
    properties = {
        "schema_version": {"const": SCHEMA_VERSION},
        "status": {"enum": ["ok", "partial", "unsupported", "error"]},
        "data": {"anyOf": [data_schema, {"type": "null"}]},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "method": {"type": "object"}, "provenance": {"type": "object"},
        "error": {"anyOf": [_object_schema(ToolError), {"type": "null"}]},
    }
    return {"type": "object", "additionalProperties": False, "properties": properties,
            "required": list(properties), "allOf": [{
                "if": {"properties": {"status": {"enum": ["ok", "partial"]}}},
                "then": {"properties": {"data": data_schema, "error": {"type": "null"}}},
                "else": {"properties": {"data": {"type": "null"}, "error": _object_schema(ToolError)}},
            }]}


def describe_tools():
    """JSON schemas for discovery only; does not provide a model or agent loop."""
    result = []
    for name, spec in TOOL_REGISTRY.items():
        props = {key: _schema(annotation) for key, annotation in get_type_hints(spec.request_type).items()}
        props["chart_id"]["minimum"] = 1
        for key in ("start_date", "end_date", "as_of"):
            if key in props:
                props[key]["format"] = "date"
        result.append({"name": name, "schema_version": "1.0", "input_schema": {
            "type": "object", "additionalProperties": False, "properties": props,
            "required": [f.name for f in fields(spec.request_type) if f.default is MISSING and f.default_factory is MISSING],
        }, "output_schema": output_schema(name)})
    return result
