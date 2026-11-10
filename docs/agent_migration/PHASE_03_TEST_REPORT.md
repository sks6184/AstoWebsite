# P3 test report

**Gate recommendation: PASS for the offline P3 orchestration gate, within the limitations below. Stop for approval; P4 has not started.**

## Branch and scope

- Branch: `feature/bounded-agent-p3`.
- Base/current HEAD: `2312a4274ceb566ddc0d9f011516d60b459233c0`.
- P3 changes remain uncommitted; the working tree already contained substantial prior work. Existing changes were preserved, not reset, stashed or indiscriminately committed.
- User authorized P3 assuming P2 approval. No additional phase or live paid smoke test was performed.

Delivered a deterministic minimum-evidence planner, bounded optional tool investigation, fixed authorized P2 dispatch, evidence-only rendering and disabled-by-default legacy routing. Future MD/AD transit requests use each requested period's lords and boundaries; comparisons evaluate both windows. No underlying calculation, rule YAML, schema, dependency or legacy LLM-generation implementation was changed by P3.

## P3 files

| File | Responsibility |
|---|---|
| `astrology/agent/__init__.py` | New package |
| `astrology/agent/policy.py` | Typed plan, question/topic selection and calendar scopes |
| `astrology/agent/orchestrator.py` | `Limits`, `Consultation`, `run_consultation`; minimum evidence, reasoned optional calls, authorization, dedup, budgets and trace |
| `astrology/agent/provider.py` | Injectable provider protocol and Responses adapter; fixed function schemas, no retries, no storage |
| `astrology/agent/rendering.py` | Deterministic preliminary evidence report; no publishable model-calculated facts |
| `chat/agent_service.py` | Feature-flag router, explicit English-only limitation |
| `chat/views.py` | Route generation, reject unavailable charts before conversation creation, no assistant message on total failure |
| `astro_site/settings.py` | `ASTROGPT_AGENT_ENABLED`, default false |
| `astrology/test_agent.py` | 38 offline P3 test methods |
| `docs/agent_migration/PHASE_03_PLAN.md` | Plan written before implementation |
| `docs/agent_migration/PHASE_03_ORCHESTRATION.md` | Invocation, result/provider contracts, methodology, limits, activation and limitations |
| `docs/agent_migration/PHASE_03_TEST_REPORT.md` | This report |

A content-hash comparison against the saved 166-file existing-source/document/configuration baseline found changes only in `astro_site/settings.py` and `chat/views.py`, the two intended existing-file integration points. The other 164 referenced files, including legacy calculation sources and tests, remained unchanged. Additions from P2 and P3 are outside that original baseline; their presence is not claimed as an original-baseline match.

## Commands actually run

```powershell
# Baseline before P3 production implementation:
.\.venv\Scripts\python.exe manage.py test --verbosity 0 --noinput

# Focused P3 runs while implementing:
.\.venv\Scripts\python.exe manage.py test astrology.test_agent --verbosity 1 --noinput

# Final full discovery:
.\.venv\Scripts\python.exe manage.py test --verbosity 1 --noinput

.\.venv\Scripts\python.exe manage.py check
```

| Execution | Result |
|---|---|
| Pre-P3 baseline | **100 passed**, 39.754 seconds |
| First P3 focused run | 30 tests; **one new failure**, ambiguous relative scope; fixed below |
| Next focused run | **31 passed**, 14.703 seconds |
| Intermediate full suite | **131 passed**, 58.722 seconds |
| Expanded focused P3 run | **38 passed**, 18.792 seconds |
| Final full suite | **138 passed**, 62.362 seconds; **zero skips** |
| Existing tests within final suite | **All 100 passed** (70 pre-P2 plus 30 P2) |
| New P3 tests within final suite | **All 38 passed** |
| Django system check | **No issues**, zero silenced |

Django created and destroyed an isolated test database. No migration was applied to the application database. Existing chart-refresh coverage ran in its original dry-run test mode. Tests were not bypassed or marked expected-failure.

## Acceptance matrix

All test names below are in `astrology/test_agent.py::AgentTests`; helper computations use real existing P2 wrappers unless explicitly mocked.

| ID | Expected | Actual evidence | Result |
|---|---|---|---|
| P3-01 | Tenth lord uses D1 only, no RAG | `test_p3_01_tenth_lord_is_d1_only_without_provider`: one facts request, D1 only, actual stored ruler appears; zero provider requests | PASS |
| P3-02 | Career assessment has D1/D10/Dasha and methodology | `test_p3_02_career_minimum_and_method_explanation`: exact minimum sequence, scope and rationales; deterministic topic rules; preliminary qualification | PASS |
| P3-03 | Scoped timing periods/transits, candidates beyond a single default | `test_p3_03_timing_uses_each_scoped_md_ad_before_transits_and_sav`: intersected MD/AD pair and date containment; SAV request follows scoped transits; legacy candidates retained. Separate synthetic Ketu–Venus → Venus–Venus test asserts exact planet/date requests | PASS |
| P3-04 | Investigate conflicts with justified extra evidence | `test_p3_04_multistep_conflict_investigation_records_reason`: scripted provider requests D9 then Yogini, finishes on third round; requests/evidence/reasons traced. Additional test requests implemented D2 and Chara successfully | PASS, mocked provider reasoning |
| P3-05 | Jupiter in Leo is a focused transit request | `test_p3_05_jupiter_leo_is_focused_transit`: Jupiter alone, no broad forecast/provider; Leo segments highlighted within explicit 2027 scope | PASS |
| P3-06 | Current Dasha is direct deterministic query | `test_p3_06_current_dasha_is_direct_one_day_query`: one Vimshottari query on explicit frozen date, no provider | PASS |
| P3-07 | Compare both Jan and July 2027 | `test_p3_07_both_requested_months_are_evaluated`: independently scoped candidate requests for Jan 1–31 and July 1–31, both retained | PASS |
| P3-08 | Unsupported calculation is explicit | `test_p3_08_unsupported_level_is_not_invented`: P2 returns `unsupported` for Pratyantardasha; no invented schedule; limitation rendered | PASS |
| P3-09 | Deduplication and hard count/size/calendar/token bounds | Dedicated tests assert duplicate-only stop, round/call/output-byte limits, pre-dispatch token stop, cumulative token reservation, malformed/oversized provider replies and output-token usage checks; horizon/ambiguous dates stop before tools | PASS |
| P3-10 | Failure/timeout/empty evidence yields useful qualified result | Provider failure/timeout tests assert one attempt and useful partial evidence without exception leakage; local tool exception and elapsed deadlines stop; empty schedule is explicitly incomplete | PASS, cooperative local timing |
| P3-11 | Injection cannot cause unauthorized actions | Tests reject `execute_python`, foreign chart IDs, absent reasons and dates outside scope. Injected tool warning is passed as untrusted data; attempted forbidden call is rejected and markup escaped. Anonymous/cross-user requests return no evidence. Ownership change during a request clears previously collected evidence and stops before provider dispatch | PASS |
| Integration | Legacy route survives; enabled route actually renders | Flag-off test asserts original function signature/exactly one call; flag-on test excludes legacy retry. Actual enabled factual POST renders the ruler through existing template formatting. Foreign chart POST creates no conversation; failed run creates no assistant credit-count message; unsupported language is explicit | PASS |

P3-09 also checks immutable budget validation and explicit default/range boundaries. Provider adapter tests mock the SDK itself and verify six function-only tools, rationale extraction, `store=False`, timeout, client close and `max_retries=0`.

## Prior failures versus new issues

**Prior test failures: none observed.** All 100 baseline tests passed before implementation and in final discovery. Existing architecture limitations below are not mislabeled as new test failures.

**New P3 issue discovered and fixed:** the first focused run treated `Career next month` as a date-free assessment and bypassed date clarification. Classification now recognizes that relative-time intent; unsupported relative scopes require explicit dates. The strengthened tests also verify exact MD/AD switches, real page-format compatibility, cumulative budgets and ownership revocation. Final unresolved test failures: **none**.

An intermediate patch application was rejected before changing its target file; the renderer replacement was then applied successfully and tested. No production failure or code rollback resulted.

## Mocked versus verified

- All provider decisions and SDK responses are mocked. Multi-step tool selection is demonstrated offline, not a claim of live model quality or model availability.
- Tests block socket connections and the default OpenAI client constructor. The adapter-specific test substitutes a fake client inside that block. No OpenAI, GeoNames or payment API call was made.
- P2 tools execute existing deterministic helpers against a synthetic chart in Django's test database. Exact Ketu/Venus boundary data is an intentionally synthetic orchestration fixture, not an independently calculated birth-chart oracle.
- Tests establish behavioral compatibility, dispatch/authorization safety and budget behavior. They do not independently certify ephemeris values, Dasha conventions, astrological predictions or source-book correctness.
- No secrets, real-user birth records, full private prompts or transcripts were logged or placed in this report.

**External API calls/cost: 0 paid calls, $0.** No live smoke test was requested or performed. Official documentation was read for the provider interface; this is not a live API smoke test.

## Limitations and remaining risks

1. **Cooperative local deadlines:** a synchronous read-only helper cannot be forcibly preempted. Elapsed-time checks discard late results and stop further work, but cannot guarantee hard wall-clock termination. Provider SDK timeouts also do not create process isolation. This is explicitly documented and tested, not claimed as a hard cancellation SLA.
2. Scope parsing is intentionally bounded English. Unsupported/ambiguous requests ask for clarification; earlier conversation dates are not remembered (P5). Enabled reports are currently English only.
3. P3 publishes a preliminary deterministic evidence report rather than unvalidated model prose. This prevents fabricated calculations, but does not provide the full fluent serious-prediction format. Comprehensive synthesis/claim validation remains P6. The legacy path remains available while later phases are reviewed.
4. P2's native boundary conventions, noon-UTC sampling, capped legacy candidate preselection and missing-score limitations remain. Rules are checked at window starts; full rule evaluation at every later boundary is not claimed. Scores are heuristic support, not probabilities.
5. The default three-year scan can exhaust calls/bytes/tokens, yielding a clearly marked partial report. The agent cannot silently expand a requested horizon. Model-token reservations are conservative operational limits, not currency accounting.
6. RAG is not called by the new agent (P4). Memory, persistent structured agent traces and summaries are not implemented (P5). Existing legacy RAG is preserved behind the off/default route.
7. Existing assistant-message credit accounting remains. Total failures create no assistant message, but useful partial reports still follow existing message-count charging. Transactional credit refunds and paid-credit-loss guarantees belong to P7 and are **not certified** here.
8. No deployment, production-cache topology, live hosted corpus, real model behavior, partner flows or external service resilience was live-verified.

## Rollback and approval

Set `ASTROGPT_AGENT_ENABLED=false` (or leave it unset) and restart Django to restore legacy generation. No database rollback is required. The unavailable-chart guard remains a safety fix at the shared entry point. Do not reset the whole branch: it contains existing uncommitted user work.

**P3 offline gate: PASS. Approval requested for the next phase: YES; P4 has not been executed.**
