# P5 test report

**Gate recommendation: PASS for P5's offline continuity, bounded-context and privacy gate. P6 has not started.**

## Branch, authorization and scope

- Branch: `feature/conversation-memory-p5`.
- Base/current HEAD: `2312a4274ceb566ddc0d9f011516d60b459233c0`.
- User authorized P5 assuming P4 approval. Changes remain uncommitted alongside preserved earlier work; no unrelated changes were reset, stashed or committed.
- Delivered owner/chart-bound follow-ups, explicit memory consent, bounded recent context and versioned deterministic summaries, corrections/provenance, older-message references, memory/history deletion controls, revision/idempotency guards and offline tests.
- No P6 answer-quality implementation, live paid test, provider corpus inspection, new dependency, generic telemetry or application-database migration execution.

## Changed files

| File | Responsibility |
|---|---|
| `chat/models.py` | Consent/summary/epoch/revision fields, payload-free turn records, stable ordering, populated-conversation chart/owner immutability, safe object strings and erased-answer aggregate |
| `chat/migrations/0004_scoped_consultation_memory.py` | Additive memory/message/turn schema |
| `chat/migrations/0005_erased_answer_usage.py` | Content-free per-user allowance compatibility counter |
| `chat/memory.py` | Deterministic categorized summaries, last-three-turn context, byte caps and explicit older reference |
| `chat/consultation_service.py` | Authorization, short CAS transactions, guarded publication, idempotency/conflict handling, resets/deletion |
| `chat/forms.py` | Consent/follow-up/reference inputs and UTF-8 question limit |
| `chat/views.py`, `chat/urls.py` | Follow-up, memory inspection/actions, new-conversation integration, CSRF/auth boundaries and non-cacheable pages |
| `chat/agent_service.py` | Pass bounded context only to the enabled agent; preserve legacy invocation |
| `astrology/agent/continuity.py` | Focused D10, inherited periods, explicit comparisons/corrections and chart/person boundaries |
| `astrology/agent/orchestrator.py` | Validate/bind memory, include it in provider payload/budget, preserve authoritative fresh calculations |
| `astrology/agent/provider.py` | Explicit untrusted-memory/correction/speculation policy |
| `templates/chat/ask.html`, `templates/chat/history.html` | Follow-up/consent/privacy UI and continuation links |
| `accounts/credits.py` | Preserve existing allowance counts after user-requested content deletion |
| `chat/test_memory.py` | 41 new offline P5 tests |
| `KNOWLEDGE_TOOL_CONTRACTS.md` | Replace historical “P5 not implemented” wording with a link to P5 contracts |
| `docs/agent_migration/PHASE_05_PLAN.md` | Plan written before implementation |
| `docs/agent_migration/PHASE_05_MEMORY_POLICY.md` | Consent, categories, retention, reset/deletion and provider/backup caveats |
| `docs/agent_migration/PHASE_05_CONTRACTS.md` | Routes, state machine, service/summary contracts, exact bounds and deployment procedure |
| `docs/agent_migration/PHASE_05_TEST_REPORT.md` | This report |

A pre-P5 content-hash inventory captured 191 existing source/document/template files. Only 11 referenced files changed: `accounts/credits.py`, the two existing agent modules, `chat/agent_service.py`, `chat/forms.py`, `chat/models.py`, `chat/urls.py`, `chat/views.py`, the two chat templates, and `KNOWLEDGE_TOOL_CONTRACTS.md`. The other **180** matched. New files are outside that baseline. Existing calculation sources, P2 tools, rule YAML, P4 retrieval code, settings, legacy LLM engine, earlier migrations and existing tests were not changed by P5.

## Commands actually run

```powershell
# Baseline:
.\.venv\Scripts\python.exe manage.py test --verbosity 0 --noinput

# Generate additive migration files; does not apply them:
.\.venv\Scripts\python.exe manage.py makemigrations chat --name scoped_consultation_memory --noinput
.\.venv\Scripts\python.exe manage.py makemigrations chat --name erased_answer_usage --noinput

# Existing agent regression and focused P5 runs:
.\.venv\Scripts\python.exe manage.py test astrology.test_agent --verbosity 1 --noinput
.\.venv\Scripts\python.exe manage.py test chat.test_memory --verbosity 1 --noinput

# Full regression discovery:
.\.venv\Scripts\python.exe manage.py test --verbosity 1 --noinput

.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

| Execution | Actual result |
|---|---|
| Pre-P5 baseline | **170 passed**, 67.807 seconds |
| Existing agent regression | **38 passed**, 18.415 seconds |
| Initial focused P5 suite | **32 passed**, 15.703 seconds |
| Refined focused P5 suite | **32 passed**, 16.030 seconds |
| Expanded focused P5 suite | **38 passed**, 16.381 seconds |
| Intermediate full suite | **210 passed**, 89.379 seconds (40 P5 tests) |
| Final focused P5 suite | **41 passed**, 18.417 seconds |
| Final full suite | **211 passed**, 87.730 seconds; **zero skips** |
| Existing regressions within final discovery | **All 170 passed** |
| New P5 tests within final discovery | **All 41 passed** |
| Django system check | **No issues**, zero silenced |
| Migration consistency check | **No changes detected** |

Django applied the migrations only inside its isolated test database and destroyed that database afterward. Existing chart-refresh coverage retained its original dry-run behavior. No `migrate` command was run against application data. No existing test was removed, rewritten, skipped or marked expected-failure.

## Acceptance matrix

Tests are in `chat/test_memory.py::ConversationMemoryTests`. Synthetic users/charts and mocked provider decisions are used throughout.

| ID | Expected | Actual evidence | Result |
|---|---|---|---|
| P5-01 | Coherent three-turn career consultation | `test_p5_01_three_turn_career_consultation_keeps_chart_and_period`: May-2027 promotion question → D10 follow-up → Jupiter-in-Leo follow-up; same chart, three ordered turns/six messages, transit request remains May 1–31 | PASS |
| P5-02 | Focus D10 using prior question scope | `test_p5_02_d10_followup_requests_focused_evidence`: exactly D10 facts, no broad rerun; prior career/May context and rationale retained | PASS |
| P5-03 | Compare late 2027 without losing topic | `test_p5_03_late_year_comparison_evaluates_both_periods`: separate candidate requests for prior May and Oct–Dec 2027; job topic preserved; late-year convention disclosed | PASS |
| P5-04 | No implicit chart/person carry-over | Tests verify a fresh second-chart conversation has no previous messages/assertions/topic; “my wife” asks for a new selected chart; follow-up chart override is rejected; populated model/admin save cannot rebind chart | PASS |
| P5-05 | Cross-user access denied | Other user cannot view, append, inspect summary or delete; chart-owner reassignment invalidates access; local services enforce ownership independently of view decorators | PASS |
| P5-06 | Bounded context with retained constraints | Long-history test retains Canada/May constraint with 38 transcript messages while context stays <=12,288 bytes, summary <=4096 bytes and recent messages <=6. Failed-turn test limits eligibility to three actual requests. Explicit older reference loads only its selected message; provider payload is categorized and token reservation increases with context | PASS |
| P5-07 | Corrections supersede assertions with provenance | May → July correction retains target/message provenance, marks the earlier assertion superseded and drives subsequent D10 scope. Chart data remains unchanged. Assistant possibility text never becomes a user/calculation fact; natural correction prefixes recorded. Birth correction requires chart editing, not an invented recalculation | PASS |
| P5-08 | Reset/delete removes state without stale reuse | Reset keeps transcript but removes inherited scope. Clear-history deletes content/summary; request tombstones contain no content. Delete cascades conversation/turns/messages. Reset before dispatch prevents old-context transmission; reset/delete during generation discards late results. Old request key cannot replay cleared content | PASS |
| P5-09 | Deterministic ordering/idempotence or explicit conflict | Same UUID generates once; overlapping request during first generator returns 409; stale revisions and simulated DB locks yield conflicts without retries. SQL regression verifies direct-row revision guards without update join subqueries. Completed retry works after allowance exhausted; message order has a PK tie-breaker | PASS |
| UI / privacy | Authorized controls actually work | Real Django client follow-up appends to same conversation and renders ruler; new form records opt-in consent; memory inspection/controls render and mutation endpoints work. GET mutation denied, CSRF enforced, no-store headers verified | PASS |
| Allowance compatibility | Deletion cannot restore spent allowance | Clear-history and direct deletion retain only aggregate erased-answer count; repeated clearing/deletion does not double count. Failed generation produces no assistant answer count and releases active slot | PASS |
| Injection / diagnostics | Context is untrusted and failures sanitized | Injected memory cannot add Python/tool authority; invalid summary versions/chart bindings are not reused; foreign older-message reference rejected; provider exception details not exposed; object strings omit private content | PASS |

The 41 methods include multiple assertions and parameterized paths. The overlap test intentionally interleaves a second service request while the first is outside its reservation transaction. Database contention is also mocked; a real multi-process production-database stress test was not run.

## Prior failures and new issues

**Prior test failures: none observed.** The 170-test baseline passed before implementation and all 170 passed in final discovery.

**New test failures observed: none.** All focused and full P5 runs passed. Final review tightened CAS predicates to remain on the updated row, separated short chart authorization/locking from that update, and added an SQL-shape regression test. No independently verified mathematical calculation defect was asserted or corrected.

One necessary compatibility issue was addressed during implementation: deleting counted assistant messages would otherwise reset the existing question allowance. Privacy actions now preserve a content-free per-user aggregate. This is not a new pricing engine, cost ledger or P7 implementation.

## Mocks, privacy and costs

- All model decisions are scripted/mocked. Tests block network socket connections and the OpenAI client constructor. No live provider/GeoNames/payments call was made.
- Many continuity tests invoke real P2 deterministic helpers against synthetic test charts. This verifies scope, compatibility and selected evidence; it does not independently certify astrology mathematics or predictions.
- Summaries use deterministic code, so no extra summarization API call/cost exists.
- No real-user birth records, private prompts/transcripts, credentials or book texts were placed in this report or generic logs. Model object strings no longer include message/title content.
- P4 live corpus coverage remains **UNVERIFIED**. P5 made no corpus inspection or relevance certification claim.

**Paid API calls: 0. Automated-test provider cost: $0.** No live smoke test was requested or performed.

## Retention, deployment and limitations

1. **Application migrations are pending deployment.** `0004_scoped_consultation_memory` and `0005_erased_answer_usage` are generated and tested, but have not been applied to the application database. Review/apply migrations before running the updated application. Migration consistency is not proof of production applied state.
2. Memory is opt-in, disabled by default on existing rows. Enabling later starts at the current message floor. Reset/disable excludes older material without erasing visible history; clear-history/delete provide separate removal choices. The UI and memory policy disclose provider-bound context and backup/provider retention caveats.
3. Full transcript retention has no automatic TTL. Content-free turn tombstones remain after clear-history until conversation deletion. A content-free erased-answer aggregate remains until account deletion. No database-backup purge or provider-infrastructure erasure guarantee is claimed.
4. Scope resolution is bounded English, not general autonomous memory reasoning. Late year means Oct–Dec and is stated. User facts/constraints can be labeled explicitly; automatic correction targeting defaults to the latest eligible user message unless the user selects a target. This is provenance, not independently verified semantic fact matching.
5. Summaries retain bounded latest entries, not every lifetime constraint. Older content is fetched only through an explicitly selected message reference. Autonomous unbounded history search and cross-chart memory sharing are not implemented.
6. Prior assistant interpretations stay preliminary; fresh deterministic evidence remains authoritative. Current answers retain P3/P4's evidence-report form. Full fluent claim validation is P6 and has not started.
7. A request already sent to a provider cannot be retracted. State is checked before dispatch and guarded at publication; reset/delete/revocation invalidates the late result. A worker crash can leave a pending marker requiring explicit user reset rather than automatic paid replay.
8. Default local SQLite/in-memory tests cover logical overlap, direct CAS and error handling; production cache topology, real multi-worker races, other database engines and browser automation were not live-tested. No database lock is intentionally held across provider execution by this service's own transaction blocks.
9. The existing `ASTROGPT_AGENT_ENABLED` flag still defaults off. When off, follow-ups append but legacy generation processes questions individually, as the UI states. Contextual agent continuity requires enabling that flag after deployment acceptance. Disabling it does not erase stored memory.
10. Existing allowance semantics, partial-answer counting and cross-conversation billing race limitations remain except for deletion compatibility. A full transactional usage/cost/refund ledger remains P7; no exactly-once billing or refund guarantee is claimed.

## Rollback and approval

Disable `ASTROGPT_AGENT_ENABLED` and restart to return to legacy generation. Retain the additive schema/counters during a code rollback so stored memory and erased-answer counts are not discarded. Do not reverse migrations blindly or reset the whole dirty branch; preserve prior work and review deployment backups. No application migration or reversal was executed here.

See [contracts](PHASE_05_CONTRACTS.md) and [memory policy](PHASE_05_MEMORY_POLICY.md).

**P5 offline gate: PASS. Approval requested for the next phase: YES; P6 has not been executed.**
