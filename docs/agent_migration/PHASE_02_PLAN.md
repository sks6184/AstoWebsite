# P2 implementation plan — local deterministic tools

Branch: `feature/deterministic-tools-p2`; base HEAD: `2312a4274ceb566ddc0d9f011516d60b459233c0` with pre-existing uncommitted work preserved.

The user explicitly requested P2, assuming P1 approval. P1's observed baseline was 70 passing tests; independent numerical references remain unverified. P2 must preserve those limitations rather than claim new astronomical correctness.

## Scope and file map

- Add `astrology/tools/`: typed request/result dataclasses, strict JSON-boundary validation, immutable six-tool allowlist, owner-scoped read-only dispatch, source/chart/settings fingerprints and adapters to existing calculations.
- Add `astrology/test_tools.py`: offline test-DB authorization, schemas, boundary metadata, limits, legacy comparisons, incomplete facts and cache invalidation.
- Add `TOOL_CONTRACTS.md` and `docs/agent_migration/PHASE_02_TEST_REPORT.md`.
- No edits to existing calculations, HTTP handlers, models, migrations, settings, dependencies or legacy answer routing. No LLM, agent loop, new HTTP endpoint or P3.

## Contracts and reversible implementation choices

Each request contains a chart ID; the authenticated principal is supplied by trusted server code, never the argument payload. Reauthorize before every cache lookup. Unknown tool names/arguments and wrong primitive types fail explicitly. The response has a schema version plus status/data/warnings/method/provenance/error; structured tool-specific data is validated before return/cache.

Six tools: chart facts; stored Vimshottari/Yogini/Chara MD/AD periods; selected-planet daily transit positions/segments; stored BAV/SAV; legacy YAML/Python rule evaluation at an explicit date; legacy timing candidates over explicit dates. No arbitrary caller-provided chart facts, evidence overrides, module paths or function names. Rules read only server-owned rule files.

Limits: 8 KiB request, 256 KiB response, 1097 inclusive days per request, 4096 planet-day samples, explicit chart/planet lists and bounded rule/candidate counts. Reject excess rather than silently truncate evidence. Candidate/rule selection caps disclose omitted counts. Non-daily transit resolution, unsupported charts/dasha levels and undefined policies return `unsupported`.

Stored period boundaries are preserved verbatim, with overlap selection described as half-open source periods and inclusive requested windows. Return intersecting whole periods rather than rewriting their source dates; disclose missing coverage. Daily transits use existing noon-UTC helpers. Do not invent precision or node BAV; distinguish missing SAV from zero in wrapper output.

Cache keys include owner/chart ID, normalized request, stored chart and birth-input hashes, source/rule hashes, relevant deterministic settings, dependency versions and schema version. Reauthorize even on hits; never persist tool results in application models. Cache success/partial results only and validate cached envelopes. Cache backends are internal infrastructure, not tools exposed to the caller.

## Risks and verification

Preserve known legacy date/ranking/rule duplication behavior; label scores as heuristics. Incomplete stored charts cannot trigger regeneration or writes. Coordinate/model mismatch is a warning, not permission to rebuild a chart. Full rules use the existing evaluators on locally constructed authorized facts, not the question parser's implicit date range. Existing full evidence orchestration is not called to let free text expand the requested horizon.

Run P2-01 through P2-09 offline, block external APIs, assert zero writes and generic foreign/missing-chart denial, compare wrappers against legacy helpers, and run all existing tests. No independent numerical-reference certification is implied.

## Rollback

The legacy app never imports the new tool registry. Rollback consists of removing the new package/test/docs files from this phase only; do not discard pre-existing working-tree edits. No database rollback or feature toggle is needed because the wrappers are additive and are not wired into user traffic.

Stop after the P2 test report and await approval. P3 is not authorized.
