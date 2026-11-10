# Phase 02 Test Report

Date: 7 November 2026 (Asia/Bangkok).  
**Phase gate recommendation: PASS for the P2 local-tool interface scope.**  
P3 has not started. Await explicit user approval before any agent integration.

## Branch / commit and scope delivered

- Branch: `feature/deterministic-tools-p2`.
- Base/current HEAD: `2312a4274ceb566ddc0d9f011516d60b459233c0`.
- Implementation is uncommitted. Existing working-tree edits from earlier work were preserved; this phase did not stage or commit them.
- Delivered an additive local registry with six typed, schema-validated tool wrappers, strict argument validation, owner-scoped read-only chart access, explicit method/precision/coverage metadata, input/output/work limits and provenance-based caching.
- Delivered [TOOL_CONTRACTS.md](../../TOOL_CONTRACTS.md) and [PHASE_02_PLAN.md](PHASE_02_PLAN.md).
- No existing calculation, view, model, migration, configuration, dependency or template file was changed. The legacy question route does not invoke these tools. No LLM tool loop, conversation memory, HTTP API or P3 orchestrator was added.

The user explicitly requested P2 assuming P1 approval. P1's observed baseline was 70 passing tests. The broader independent-reference fixture work described in the Phase 1 plan remains unverified; this report does not claim it was completed or certify the astrology mathematics.

## Changed files

All nine phase files are additions:

| File | Purpose |
|---|---|
| `astrology/tools/__init__.py` | Exports local `invoke_tool` and schema discovery. |
| `astrology/tools/contracts.py` | Frozen request/result dataclasses, JSON validation, limits and machine-readable failures. |
| `astrology/tools/registry.py` | Six-tool immutable allowlist, trusted principal/ownership boundary, dispatch, validated cache responses and JSON schemas. |
| `astrology/tools/fingerprints.py` | Fixed-source/rule, chart/input, settings/dependency and request digests. |
| `astrology/tools/adapters.py` | Calls existing fact/schedule/transit/Ashtakavarga/rule/timing implementations without modifying them. |
| `astrology/test_tools.py` | Thirty offline P2 test methods with per-tool/subcase coverage. |
| `TOOL_CONTRACTS.md` | Invocation, schemas, supported methods, limits, error/coverage semantics and caveats. |
| `docs/agent_migration/PHASE_02_PLAN.md` | Pre-implementation scope, file map, risk and rollback plan. |
| `docs/agent_migration/PHASE_02_TEST_REPORT.md` | This report. |

Content-hash comparison checked **166 existing source/document/configuration files**, including legacy calculation and test files: **zero changes**. New Python additions were exactly the five package files and the P2 test file. Root/docs additions are listed separately above. `manage.py check` reported no issues. Applied application-database migration state and external deployments were not inspected or altered.

## Test commands actually run

```powershell
# Focused suite, run repeatedly while implementing P2:
.\.venv\Scripts\python.exe manage.py test astrology.test_tools --verbosity 1 --noinput

# Focused cache failure investigation:
.\.venv\Scripts\python.exe manage.py test astrology.test_tools.DeterministicToolTests.test_p2_09_cache_hit_and_chart_changes_invalidate_without_updated_at_change --verbosity 1 --noinput

# Final complete discovery, including every current P2 and legacy test:
.\.venv\Scripts\python.exe manage.py test --verbosity 1 --noinput

.\.venv\Scripts\python.exe manage.py check
git diff --check
```

New Python files were also parsed with Python's AST parser. No dependencies were installed. No `migrate` command was run against the application database; the Django test runner created/applied migrations to/destroyed its isolated in-memory SQLite test database.

### Final results

| Check | Actual result |
|---|---|
| Final full suite | **100 passed; 0 failures; 0 errors; 0 skips** |
| Final full-suite runtime | **39.604 seconds** reported by Django |
| Existing tests within final suite | All **70** passed |
| P2 tests within final suite | All **30** passed |
| Last intermediate focused P2 run before the final three added cases | 27 passed in 12.344 seconds; the final three were subsequently exercised by the final 100-test run |
| Django checks | No issues, 0 silenced |
| Existing-file content comparison | 166 checked, zero changed |
| AST parse / whitespace diff check | Passed; Git emitted line-ending warnings for pre-existing files, not whitespace errors |

Runtime environment used the existing virtual environment: Python 3.11.9, Django 5.2.13, pyswisseph 2.10.3.2, PyYAML 6.0.3, OpenAI SDK 1.109.1. These are locally observed versions, not a new lockfile or deployment guarantee.

## P2 acceptance matrix

| ID | Expected | Actual evidence | Result |
|---|---|---|---|
| **P2-01** | Six callable local tools, typed/stable JSON result schema. | `test_p2_01_all_six_tools_have_valid_json_and_no_model_writes` invokes all six; validates JSON, envelopes, limits and SELECT-only ORM activity; discovery exposes exact input/output schemas. Schema tests reject malformed nested score types and invalid shapes. | **PASS** |
| **P2-02** | Invalid arguments yield machine-readable errors. | Every tool rejects unknown fields, forged user fields, bool/string/negative chart IDs and missing required fields. Tests cover invalid date formats, impossible dates, bad ranges/filters/caps, NaN and oversize request data. | **PASS** |
| **P2-03** | Ownership checked, no foreign-chart leakage. | Every tool warmed as owner then denied as another user with identical foreign/missing-ID response; provenance/calculation blocked on denial. Anonymous/inactive principals denied. Staff/superuser cannot bypass; ownership transfer invalidates former-owner access even with warm cache. | **PASS** |
| **P2-04** | Unsupported methods/levels return `unsupported`. | Unknown tools, arbitrary names/paths, D99, Pratyantardasha, annual-Yogini integration, hourly sampling, unknown planets/categories/policies, node BAV and unsupported chart systems are explicitly rejected. | **PASS** |
| **P2-05** | Date/precision conventions explicit. | All three stored dasha systems and both supported granularities preserve native period data. Synthetic handover selects the new half-open period; gaps explicit. Actual transit samples match existing noon-UTC helper and segment boundaries retain requested dates. | **PASS** |
| **P2-06** | Work/output bounded or clear rejection. | Tests enforce date/range/planet-day/request/response limits, check excess transit work is rejected before sampling, and verify disclosed rule/candidate caps. No silent evidence truncation to fit bytes. | **PASS** |
| **P2-07** | No unintended numerical/calculation changes. | Chart facts, numeric stored longitudes, BAV/SAV rows and all-nine-planet segments compared to legacy data/helpers. Rule composition/scores compared with legacy evidence constrained to the same day. Timing candidates compared with existing selector. Existing 70 tests remain green and existing source hashes unchanged. | **PASS for compatibility**, not independent numerical certification |
| **P2-08** | Incomplete chart/coverage explicitly flagged. | Empty chart returns partial stored facts/schedules or an explicit incomplete-chart error. Missing category charts, natal planets, SAV and birth metadata are exposed; no regeneration invoked. Real zero SAV remains zero; absent values become null. Unsupported frame cannot be silently mixed into calculations. | **PASS** |
| **P2-09** | Fingerprinted cache cannot reuse stale/unauthorized data. | Actual repeat request skips fact calculation; content updates invalidate without relying on `updated_at`; metadata/request/settings changes alter digests; temp fixed-source/rule changes alter engine digest. Corrupt/mismatched cache entries recompute, returned data is copied, ownership is rechecked, cache outages remain safe. | **PASS** |

Full test definitions: [astrology/test_tools.py](../../astrology/test_tools.py). The named scenarios include parameterized subcases within the 30 unittest methods; the acceptance IDs are not a claim of only nine assertions.

## Prior failures versus newly introduced failures

### Existing baseline failures

**None observed.** The Phase 1 baseline had 70 passing tests, and all 70 passed in the final P2 suite. No legacy test expectation was changed.

### P2 development failures, corrected before final run

1. The first 20-test P2 run had one failure: cache invalidation changed the fingerprint but the legacy compact fact object omitted numeric longitude. The new wrapper was extended with an explicit stored-longitude mapping; no calculation/legacy normalizer was changed. A subsequent 20-test run passed.
2. Later focused/full runs exposed a new cache-write bug: a loop variable shadowed the hashed cache key. A 97-test intermediate full run had one new P2 failure; legacy tests passed. The wrapper now uses a dedicated `cache_key`, and the test asserts the stored key prefix, schema-valid stored data and an actual skipped calculation on cache hit. Subsequent 27-test focused and final 100-test complete runs passed.

**New unresolved test failures: none.** Existing risks below are not newly introduced failures and are not silently treated as corrected.

## Mocked versus live-verified behavior

- All new tests use synthetic test-database users/charts and existing deterministic numerical helpers. No live user's birth records, private prompts, chat transcripts or secrets are included in this report.
- P2 test setup blocks socket connections and replaces `openai.OpenAI` with a failure if invoked. Provider/model execution is not part of a local deterministic-tool test.
- Swiss Ephemeris and stored-score/normalization logic execute locally in parity cases; these are **legacy comparisons**, not independent astronomy references.
- Source/rule invalidation tests modify temporary fixture directories only, not production source or books. Metadata/ownership changes in tests affect isolated test rows only.
- Read-only dispatch is checked using captured SQL: tool invocation issued SELECT queries only. Chart data remains unchanged after all-six-tool invocation. Internal cache writes are distinct from application model mutations.
- Existing 70 tests use their original local deterministic/assertion paths. This report does not claim a hosted corpus, Google OAuth flow, deployed server, payments, PDF delivery or model-generated prediction was live-tested.

**External API calls / cost:** no OpenAI, GeoNames or payment API calls; automated-test provider cost **$0**. No live paid smoke test was run.

## Coverage limitations and unresolved pre-existing risks

1. Independent natal/varga/dasha/transit/BAV/SAV oracle certification remains pending from Phase 1. Passing P2 establishes interface safety and compatibility, not predictive validity or complete doctrinal correctness.
2. Legacy dasha selectors have different end-date semantics. The tool explicitly selects stored periods half-open, while rule-evaluation base helpers retain their existing inclusivity. Native stored dates and durations are not rewritten.
3. Legacy rule overlap, ranking stages, representative micro-period metadata and confidence heuristics are retained. Scores are labeled heuristics, not probabilities. Incomplete timing evidence is partial; legacy scores may still include missing-score fallbacks, which are disclosed rather than recalculated.
4. The old HTTP Ask route's invalid-chart path and fail-open answer validation remain pre-existing risks. The new local boundary independently rejects foreign/missing charts. It is not wired into the legacy route and does not claim to fix that route.
5. Output schemas precisely validate envelopes/tool-level fields and selected numeric domains; deep legacy fact/rule metadata remains extensible strict JSON. They do not prove every interpretation or every nested numerical relation.
6. Source/rule hashes, dependency versions and relevant settings are fingerprinted; external ephemeris-file/timezone-database contents are not independently hashed. Normal process reload is still necessary to execute edited Python code.
7. Only local invocation and in-memory SQLite test execution are covered. Production cache failures, shared workers, database engines and deployment authorization integration need their own later-stage verification.
8. The tools are bounded local operations, not a complete agent-ready deployment. No public route, LLM registry, new feature toggle or adaptive evidence-policy implementation has been introduced in P2.

## Rollback

Remove/revert only the nine added files listed above. The existing website, legacy generation path and calculation files remain available without any database/configuration rollback. Preserve all pre-existing working-tree edits. The feature branch records isolation; no production rollout or schema migration occurred.

## Gate and approval

**PASS — P2 local deterministic contracts/wrappers satisfy P2-01 through P2-09 within the documented limitations.** Final automated evidence is 100 passing tests with no skips. Numerical oracle certification and production integration are not implied.

**Approval requested:** review and accept P2 before authorizing another phase. **Do not execute P3 without a new explicit instruction.**
