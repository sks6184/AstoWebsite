# P6 implementation and test report

**Automated implementation checks: PASS, all 240 tests. Full P6 rollout gate: BLOCKED pending actual blinded human evaluation, agreed quality/performance thresholds and verified live cost/latency. P7 has not started.**

## Scope and preservation

- Branch `feature/evidence-quality-p6`; base/current HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. Changes remain uncommitted alongside earlier work.
- P6 adds source-bound factual claims, controlled conversational composition, final publication checks, legacy failed-cache protection and a locked offline evaluation harness. No calculation rewrite, schema change, dependency change or live paid call.
- A pre-P6 hash inventory covered 201 existing source/document/template files: **196 unchanged; five intentionally changed**: `astrology/agent/orchestrator.py`, `astrology/agent/policy.py`, `astrology/agent/provider.py`, `chat/consultation_service.py`, `chat/llm_engine.py`.
- Existing natal/varga/Dasha/transit/BAV/SAV calculations, rule YAML/evaluators, P2 wrappers, retrieval implementation, settings, earlier migrations and existing test files remain unchanged from the pre-P6 workspace. Prior uncommitted changes were preserved.
- No application-database migration was executed. Earlier P5 migration files still require the deployment procedure documented in P5; this phase adds none. Tests use Django's isolated test database.

## Implementation map

| Source | Responsibility |
|---|---|
| `astrology/synthesis/fact_catalog.py:build_catalog`, `verify_atom` | Bounded fact slots, exact source bindings, scopes, precision and real provenance |
| `astrology/validation/claim_validator.py:validate_draft`, `validate_final`, `final_schema` | Closed draft schema, numerical/date claim agreement, final-text and source revalidation |
| `astrology/synthesis/verified_answer.py:publish_answer`, `select_facts`, `narratives` | Concise paragraphs, focused factual/follow-up answers, conflict/overlap/uncertainty disclosure, safe fallback |
| `astrology/agent/orchestrator.py:Consultation` | Catalog exposure, bounded draft acceptance, validation trace and fallback status |
| `astrology/agent/policy.py:make_plan` | Narrow position/BAV/SAV/named-period Dasha lookups and professional-growth career routing |
| `astrology/agent/provider.py:OpenAIProvider` | Structured final composition with existing budgets and tool allowlist |
| `chat/publication.py` | Legacy final structural validation, cache markers/revalidation, failed-cache exclusion |
| `chat/llm_engine.py:generate_answer`, `_generate_rashifal_answer` | Final checks after deterministic remedy replacement in both paths |
| `chat/consultation_service.py:_append_turn` | Reject supplied failed/malformed final validation before assistant publication |
| `astrology/evaluation/fixtures/p6_cases_v1.json` and `.sha256` | Locked 36 primary questions plus 12 follow-ups |
| `astrology/evaluation/harness.py` | Paired records, unknown-safe metrics, blind packet/key, attested human scores and explicit gate reasons |
| `charts/management/commands/p6_evaluate.py` | Artifact-only evaluation CLI; no API calls/database writes |
| `astrology/test_quality.py`, `astrology/test_evaluation.py` | 29 new offline tests, including the 48-case loop |
| `PHASE_06_PLAN.md`, `PHASE_06_CONTRACTS.md`, `PHASE_06_EVALUATION.md` in this directory | Pre-implementation plan, contracts/limitations and human evaluation protocol |

## Executed checks

```powershell
# Before P6 production changes:
.\.venv\Scripts\python.exe manage.py test --verbosity 0 --noinput

# Existing agent/retrieval/memory regressions:
.\.venv\Scripts\python.exe manage.py test astrology.test_agent astrology.test_knowledge chat.test_memory --noinput --verbosity 0

# New checks (also included in full discovery):
.\.venv\Scripts\python.exe manage.py test astrology.test_quality --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py test astrology.test_evaluation --noinput --verbosity 0

# Final regression and framework/schema checks:
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --noinput
```

| Check | Observed result |
|---|---|
| Pre-P6 baseline | 211 passed, 88.970 s; no existing test failures |
| Existing P3/P4/P5 focused regression | 111 passed, 47.731 s |
| New quality/publication checks | 17 passed, 35.268 s |
| New evaluation harness checks | 12 passed, 0.378 s |
| Full discovery after P6 | 240 passed, 130.430 s |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Fixture checksum | Matches locked code constant and sidecar |
| Pre-P6 file preservation | 196/201 unchanged; five changes listed above |

All new tests prohibit live provider/network use or operate only on explicitly supplied synthetic artifacts. Durations above are test-run durations, **not live response latency comparisons**. Harness tests contain synthetic ratings solely to verify scoring behavior; they are not human votes or evidence of agent preference.

## Acceptance coverage

| ID | Evidence and outcome |
|---|---|
| P6-01 | Wrong canonical Dasha date rejected; server fallback preserves original tool dates; rejection retained in draft validation |
| P6-02 | Wrong position, SAV and transit values rejected; transit text states daily sample precision; missing SAV stays unavailable |
| P6-03 | Synthetic D1/D10 conflict remains visible even when a valid draft selects another fact; overlapping rule/score inputs explicitly disclosed |
| P6-04 | Promotion versus online-business questions produce different responsive guidance/evidence, including business Mercury/Rahu and muhurta limitation |
| P6-05 | No retrieved support produces no invented K-ID/book/page; unsupported remedy is explicitly withheld |
| P6-06 | Focused D10 follow-up uses one chart tool and short context-specific response; inherited dates/corrections covered by locked and P5 cases |
| P6-07 | Tenth-lord factual answer uses one D1 tool, no provider and short output; position/BAV/SAV/Dasha lookups similarly deterministic |
| P6-08 | Historical May 2020 tools retain that scope; forecasts remain conditional, with scores distinguished from probabilities |
| P6-09 | Postprocessing additions of numbers, remedies or citations fail final validation; changed source bindings fail; regular and periodic legacy checks run after remedy replacement; failed results never enter the validated cache |
| P6-10 | Paired blinding and separate preference/quality/error/latency/token/cost records tested; actual human scoring **not performed** |
| Locked sample | All 48 scenarios run offline, every emitted calculation atom source-verified; no critical invented-calculation or chart-disclosure failure observed in this synthetic sample |
| Existing safety | Existing authorization, injection, budgets, memory consent, deletion and concurrency tests pass in full discovery |

## Failures and issues, separated

**Pre-existing test failures:** none in the 211-test baseline.

**Existing behavior gap newly exposed by locked evaluation:** “professional growth” was classified as an unsupported general topic. `make_plan` now routes it to career without changing calculations. Original baseline tests did not cover that phrase.

**New regressions during development:** two existing assertions initially failed because concise rendering omitted the classical-support label and the explicit October–December meaning of “late year.” Both were restored; the 111-test regression then passed. New test scaffolding also needed dictionary catalog access and JSON-list memory windows corrected; those were fixture issues rather than application failures. All focused P6 tests now pass.

**Remaining evaluation limitations:** no independent new ephemeris oracle, real model completion, paid run, blinded human panel, custom-GPT benchmark or verified live performance comparison was performed. Source agreement does not prove astronomical correctness. The locked run uses one synthetic natal chart with scenario variants and is not a population-wide quality study. Controlled composition improves enforceability but limits arbitrary prose and multilingual flexibility; no measured human preference improvement is claimed. Legacy free prose has final structural checks, not closed-slot mathematical certification. Previously unchecked legacy periodic readings may now be blocked for insufficient evidence. These limits are documented, not silently treated as passes.

## Gate disposition

The automated P6 implementation and harness are reviewable offline. The proposed >=60% preference is only an unapproved pilot target; there are zero actual human votes. Actual paired responses/human ratings and previously agreed performance limits must be supplied before the full gate can pass. Missing costs remain null and mock measurements cannot satisfy live comparison requirements. The full phase gate remains **BLOCKED**, with no P7 implementation or activation.
