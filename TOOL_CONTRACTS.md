# P2 deterministic local tool contracts

Schema version: **1.0**. Implementation: [astrology/tools](astrology/tools/__init__.py). This is a local Python interface, not an HTTP endpoint, agent, or model tool loop. The legacy site does not import this registry. Existing calculations, saved data, endpoints and one-shot answer generation are unchanged.

## Invocation and trust boundary

```python
from astrology.tools import describe_tools, invoke_tool

# request.user is supplied by trusted authenticated server code, never by a model.
result = invoke_tool(request.user, "get_chart_facts", {
    "chart_id": authorized_chart_id,
    "charts": ["d1", "d9", "d10"],
})
schemas = describe_tools()  # six names and their input/output JSON schemas
```

The only dispatch entry point is `invoke_tool(user, name, arguments)`. Arguments must be a plain JSON object; unknown fields are rejected. `user`, `user_id`, raw chart data, caller-supplied evidence, Python names, module names, filenames and instructions are not accepted arguments. The server principal must be authenticated, active and have a persisted integer ID. There is no staff/superuser ownership bypass.

`SavedChart.objects.filter(pk=chart_id, user_id=user.pk).first()` runs **before fingerprinting, calculations and cache access on every request**. Foreign and missing IDs have the same `chart_not_found` error and no chart provenance/data. Do not accept the principal from a future LLM argument dictionary or raw client user ID.

The immutable allowlist contains only the six functions below. There is no arbitrary dispatch, command execution, caller-directed filesystem access, model write, payment, LLM or retrieval API. Fixed repository source/rule files are read internally for calculation and provenance. Internal caching is permitted; chart/user/conversation records are never changed by these tools.

Sources: [registry.py](astrology/tools/registry.py), `TOOL_REGISTRY`, `invoke_tool`; [contracts.py](astrology/tools/contracts.py), request dataclasses and `parse_request`.

## Envelope and validation

Every result is strict JSON and has exactly these top-level keys:

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "data": {},
  "warnings": [],
  "method": {
    "tool": "get_chart_facts",
    "version": "1.0",
    "engine": "existing AstroGPT deterministic helpers",
    "precision": "tool-specific supported precision",
    "interval_convention": "tool-specific date convention",
    "reference_frame": "Lahiri sidereal; natal whole-sign Lagna houses"
  },
  "provenance": {
    "chart_id": 1,
    "chart_fingerprint": "SHA-256 digest",
    "engine_fingerprint": "SHA-256 digest",
    "request_fingerprint": "SHA-256 digest",
    "source": "authorized stored chart plus existing local helpers; no independent numerical certification"
  },
  "error": null
}
```

This example illustrates shape only; it is not a real chart or a literal successful response. `data` is the required tool-specific object defined below. Error responses use `data: null` and `error: {"code": "...", "message": "..."}`. On denial/validation errors, provenance is empty and method contains only non-sensitive tool/version/engine metadata. Once an owned chart is authorized, supported adapter errors may include that chart's fingerprint metadata. Unexpected exceptions return a generic `computation_error` with no private exception text or provenance.

| Status | Meaning |
|---|---|
| `ok` | The requested supported operation completed with available required evidence. Informational method warnings may still be present. |
| `partial` | Missing/limited evidence, capped selected results, absent coordinates or differing stored-versus-model input metadata. A partial result must not be treated as full prediction confirmation. |
| `unsupported` | Tool/method/system/chart/precision/policy is outside the implemented allowlist. No guessed result. |
| `error` | Authentication, authorization, request/range/size validation, unusable chart or sanitized computation failure. |

Frozen request/result dataclasses define types. Runtime validators reject extra request fields, primitive coercion (including bool-as-int), invalid dates, non-finite numbers, non-JSON values and over-deep trees. Output validation enforces the exact envelope and exact top-level per-tool data fields/types. Legacy nested fact/rule objects are open JSON objects to preserve their existing trace metadata, not a newly redesigned domain schema. Numeric longitude and BAV/SAV/summary-score checks additionally reject invalid output values. These are structural/domain-range checks, not independent astronomical verification or validation of every narrative claim in legacy rule text.

`describe_tools()` exports input and output JSON schemas. Cross-field date/range/filter/resource checks are enforced in Python; schemas alone are not sufficient to dispatch safely. Successful cached results must match the current provenance/tool and pass the output validator again before return. Returned objects are copied so callers cannot mutate cached values.

## Shared limits and errors

| Limit | Value / behavior |
|---|---|
| Request | 8192 UTF-8 JSON bytes; unknown arguments rejected |
| Response | 262144 UTF-8 JSON bytes; `output_limit` rather than silent truncation |
| Stored chart input | 2 MiB serialized chart JSON; `chart_limit` |
| Dates | Explicit ISO `YYYY-MM-DD`, years 1800–2200; no implicit today/date parsing |
| Range | At most 1097 inclusive calendar days; end must be on/after start |
| Transit computation | At most 4096 distinct-planet/day samples; duplicates are calculated once |
| List arguments | Nonempty, at most sixteen items; actual supported chart/planet set also checked |
| Rule output cap | `max_rules` 1–100; default 40; total/omitted counts returned; all rules still contribute to summary/conflicts |
| Timing output cap | `max_candidates` 1–5; default 5; omissions explicit; legacy preselection cap remains eight |

Machine-readable codes include `authentication_required`, `chart_not_found`, `invalid_arguments`, `invalid_date`, `invalid_range`, `date_limit`, `range_limit`, `sample_limit`, `request_limit`, `output_limit`, `chart_limit`, `incomplete_chart`, `unsupported`, `unsupported_tool`, and `computation_error`. Do not interpret message text as a stable machine enum. No partial evidence is silently dropped to fit the byte limit; narrow a rejected request.

## 1. get_chart_facts

**Input**

```json
{"chart_id": 1, "charts": ["d1", "d9", "d10"]}
```

`charts` defaults to `["d1"]`; case is normalized by the adapter. Supported: D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60. An unknown division is `unsupported`, not an inferred harmonic chart.

**Data fields:** `system: string|null`, `ayanamsa: string|null`, `charts: object`, `longitudes: object`, `missing_charts: string[]`, `units: object`.

`charts` contains the existing `build_varga_facts` normalized Lagna/planet/lord-placement objects for requested charts. `longitudes[chart][planet_code]` supplies original stored numeric longitudes (including Asc where present); no recomputation is performed. Units distinguish numeric longitude degrees from legacy `DD-MM-SS` degree strings. Raw birth-name/place/date metadata is not returned. Missing/incomplete charts or absent stored longitudes are flagged; an empty saved chart can return partial facts rather than fake placements.

Underlying source: [varga.py](astrology/calculations/varga.py), `build_varga_facts`. This wrapper does not change the fact normalizer or any varga transform.

## 2. get_dasha_periods

**Input**

```json
{
  "chart_id": 1,
  "system": "vimshottari",
  "start_date": "2027-01-01",
  "end_date": "2027-12-31",
  "granularity": "antardasha"
}
```

Supported `system`: `vimshottari`, `yogini`, `chara`. Supported `granularity`: `mahadasha`, `antardasha` (default). Pratyantardasha and annual-Yogini integration are `unsupported`.

**Data fields:** `system: string`, `granularity: string`, `periods: object[]`, `coverage: object`, `source_method: object`.

The tool reads stored schedules: `dashas.vimshottari`, `dashas.yogini`, or `jaimini.chara_dasha`. It returns **whole intersecting source periods**, including their original dates, durations, lord/sign metadata, and parent `mahadasha` metadata. It does not recalculate a schedule, clip durations, extend missing cycles, or invent subperiods.

Requested dates are inclusive; source schedules are selected as `[start,end)`. A period that ends on the requested start date is not selected; the new period beginning that day is selected. Precision is calendar dates, not exact transition instants. `coverage` has inclusive `start`, `end`, `complete`, and inclusive `gaps`. Source periods may extend beyond the requested dates because they are retained whole; requested coverage is separately bounded.

Legacy selectors disagree on inclusivity; this choice is explicit adapter selection metadata, not a modification to their algorithms. Missing schedules/coverage produce `partial`. Source calculations remain [Vimshottari](astrology/calculations/vimshottari.py), [Yogini](astrology/calculations/yogini.py), [Chara](charts/jaimini.py), with original method metadata returned.

## 3. get_transits

**Input**

```json
{
  "chart_id": 1,
  "planets": ["Su", "Ju"],
  "start_date": "2027-05-01",
  "end_date": "2027-05-31",
  "resolution": "daily",
  "output": "segments"
}
```

Planet codes: Su/Mo/Ma/Me/Ju/Ve/Sa/Ra/Ke. `resolution` supports only `daily`; `output` is `segments` (default) or `positions`. Exact/hourly ingress times, muhurta and other resolutions are `unsupported`.

**Data fields:** `planets: string[]`, `output: string`, `samples: object[]`, `coverage: object`, `units: object`.

Positions call existing `transit_context_for_lord` for each selected planet/day at **12:00 UTC**. Segments call existing `_transit_segments_for_lord` over the same inclusive date range. Their start/end are dates describing daily samples, not exact entry/exit timestamps. Natal house frame is whole-sign Lagna. This selected-planet tool does not imply that every requested planet is an active dasha lord; dasha periods are retrieved separately. Planet output order follows the distinct requested order.

Stored D1 planets and a valid Lagna are required. Birth coordinates missing from model metadata generate a warning/partial status; stored natal facts are never regenerated. Missing SAV is converted to unavailable (`null`, delivery flag null) in the wrapper's returned evidence rather than exposing the helper's legacy zero fallback. A measured zero remains zero. Coordinate calculations and actual transit longitude/rashi computations are untouched.

Underlying sources: [vedic_utils.py](charts/vedic_utils.py), `transit_context_for_lord`, `transit_longitude`; [timing_windows.py](chat/timing_windows.py), `_transit_segments_for_lord`.

## 4. get_ashtakavarga

**Input**

```json
{"chart_id": 1, "planet": "Su", "kind": "both", "sign": 2}
```

`planet`: one classical code or `all` (default). `kind`: `sav`, `bav`, or `both` (default). Optional `sign` and `house` are integers 1–12; if both are supplied they must identify the same natal rashi/house. No filter means all twelve rashis. Rahu/Ketu are accepted only with `kind: "sav"`; a request for their planet-specific BAV returns `unsupported`.

**Data fields:** `kind: string`, `planet: string`, `rows: object[]`, `units: string`.

Each row has exactly `sign_number`, `sign`, `house`, `sav`, `bav`. `sav` is integer bindu or null (also null when not requested); `bav` maps requested classical planet codes to stored integer bindu or null. It is empty when `kind=sav`. The tool uses stored per-rashi scores and existing `house_from_sign` mapping. Missing cells yield partial status; null is never replaced with zero. BAV/SAV are not recalculated from incomplete inputs.

Underlying sources: [ashtakavarga.py](charts/ashtakavarga.py), original stored `rows`; [vedic_utils.py](charts/vedic_utils.py), `house_from_sign`.

## 5. evaluate_astrology_rules

**Input**

```json
{"chart_id": 1, "category": "job", "as_of": "2027-05-01", "max_rules": 40}
```

Supported categories are the existing `CATEGORY_RULES` keys plus `business` and `general`. The category is explicit; no LLM classifies it. No caller-supplied evidence object or free-text question may override chart facts or expand the one-day scope.

**Data fields:** `category: string`, `as_of: string`, `triggered_rules: object[]`, `total_triggered: integer`, `omitted_rules: integer`, `summary_scores: object`, `conflicts: object`, `score_kind: string`.

The adapter constructs single-date facts using the existing chart/dasha/Parashari/varga/transit helpers, runs the existing YAML engine, then invokes the same generic/D1/D2/D3/D4/D7/D9/D10/D12/D16 Python evaluator set used by the legacy prediction service. It uses the existing score aggregator, ledger and contradiction resolver. It does not call the full prediction service's free-text time-scope parser, RAG, prompt generation, or an LLM.

Results preserve legacy rule order/composition, including potential overlapping rules and inclusive base-dasha selectors. The cap selects the first N emitted rules; all emitted rules still contribute to scores/conflicts and omitted count is explicit. Missing category charts, load errors and incomplete dasha/transit/SAV evidence produce warnings/partial results. Scores are labeled **heuristic outcome scores, not probabilities**. Source references/match reasons remain within rule objects; file/rule source fingerprints are in provenance.

Underlying source/call set: [prediction_service.py](astrology/services/prediction_service.py), imported evaluator functions; [rules/engine.py](astrology/rules/engine.py), `run_rule_engine`; [rules/scoring.py](astrology/rules/scoring.py), `aggregate_scores`; [ledger.py](astrology/evidence/ledger.py); [contradiction resolver](astrology/evidence/contradiction_resolver.py). The wrapper composition is regression-tested against the legacy service forced to the same explicit day.

## 6. get_timing_candidates

**Input**

```json
{
  "chart_id": 1,
  "topic": "job",
  "start_date": "2027-01-01",
  "end_date": "2027-12-31",
  "evidence_policy": "legacy_intersections",
  "max_candidates": 5
}
```

Supported topics follow the existing categories except `general`, which has no classified timing. Only `legacy_intersections` is implemented. The policy is explicit; no adaptive agent policy or alternative ranking algorithm is introduced.

**Data fields:** `topic: string`, `candidates: object[]`, `coverage: object`, `selection_rule: string`, `omitted_candidates: integer`, `score_kind: string`.

The existing `build_timing_window_selection` supplies its best window followed by its selected secondary windows. Original dates, scores, rule explanations, dasha labels and scoped transit evidence are preserved; lower max-candidate caps are disclosed. The legacy engine first preselects at most eight windows, and the selector returns best plus at most four secondary windows. `omitted_candidates` counts omissions from that selected set, not every possible period in the input schedule. Scores and legacy confidence labels are **heuristics, not probabilities or guarantees**.

`coverage.complete` describes availability of required stored dasha ranges, category charts and SAV, not uniform support or forecast accuracy. Missing schedules/charts/SAV and an empty selected set return partial. Returned missing-SAV transit evidence is null; ranking scores retain legacy behavior and a warning explains missing-score fallbacks. Daily-noon precision and source-date conventions are explicit in method metadata. No exact event/muhurta instant is inferred.

Underlying source: [timing_window_service.py](astrology/services/timing_window_service.py), `build_timing_window_selection`; [timing_windows.py](chat/timing_windows.py), legacy candidate computation/ranking.

## Caching, reproducibility and remaining limits

Successful/partial results use a 300-second Django cache. The cache is optional; cache failures do not turn computation into a database write. Keys include owner ID, tool, chart ID, request fingerprint, stored chart/birth inputs, schema version, hashes of fixed calculation/tool/rule source files, relevant deterministic Django settings and installed Django/pyswisseph/PyYAML versions. Provenance returns digests, never configuration secrets. `.env` and arbitrary caller paths are not read for fingerprints.

Every request reauthorizes the owner first, then rebuilds fingerprints even if a result is cached. Changes to chart JSON do not rely on `updated_at`; chart metadata, rules/source, settings and request changes create different keys. Ownership transfer cannot reuse a former owner's cached result. Source edits still require normal Python process reload to execute newly edited code; a fingerprint is not a hot-reload mechanism. External ephemeris-file and timezone-database contents are not independently hashed/certified by this phase.

These tests establish local contracts and compatibility, not independent astronomical correctness. P1's outstanding oracle requirements and existing boundary/ranking/fallback/credit issues remain. The old Ask handler's invalid-chart path is not fixed here; the new local dispatch independently rejects it. No model, migration, dependency or HTTP integration change was made. Rollback is removal of P2's new files; the legacy path remains available unchanged.

Plan: [PHASE_02_PLAN.md](docs/agent_migration/PHASE_02_PLAN.md). Evidence/report: [PHASE_02_TEST_REPORT.md](docs/agent_migration/PHASE_02_TEST_REPORT.md).
