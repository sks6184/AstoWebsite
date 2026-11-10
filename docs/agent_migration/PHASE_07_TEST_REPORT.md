# P7 implementation and test report

**Offline implementation gate: PASS, all 269 tests. Full P7 commercial gate: BLOCKED pending a separately preapproved capped live average/P95 cost measurement and pricing review. P8 was not started.**

## Branch, authorization and scope

- Branch: `feature/usage-ledger-p7`; base/current HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`.
- User authorized P7 only, assuming P6 approval. Prior P6 human/preference/live-performance evaluations were not retroactively invented or run.
- All changes remain uncommitted alongside earlier work. No resets/stashes/commits erased previous changes.
- Delivered transactional credit reservations/settlement/refunds, user-scoped UUID idempotency, provider-attempt accounting, plan/daily spending ceilings, bounded retries/timeouts, scoped retrieval reuse/invalidation, stale-worker reconciliation and privileged aggregate contribution reporting.
- No astrology/rule rewrite, dependency change, paid provider call, public activation, production migration execution or P8 implementation.

## Changed files

| Source | Responsibility |
|---|---|
| `accounts/models.py` | Add `CreditAccount`, `UsageRequest`, `ProviderUsage` with unique user-request and provider-sequence constraints |
| `accounts/migrations/0003_usage_ledger.py`, `0004_request_stop_reason.py`, `0005_reported_search_usage.py` | Additive ledger schema; isolated test DB only |
| `accounts/usage.py:reserve`, `settle`, `refund` | Ownership, HMAC request identity, bootstrap allowance, atomic reservation/settlement, cancellation and idempotent question-credit refund |
| `accounts/usage_policy.py` | Plan ceilings, configurable model tariffs, precise Decimal rate calculation and fail-closed unknown models |
| `accounts/provider_meter.py:Budget`, `responses_create` | Shared paid-call boundary, pre-dispatch persisted liability, plan/daily caps, known versus estimated usage, cached discount/tool observations and overruns |
| `accounts/credits.py:question_credit_status` | Wallet-aware used/reserved/remaining display; preserve pre-wallet history bootstrap |
| `chat/consultation_service.py:_append_turn`, `_change_memory` | Reserve before provider work; settle in publication transaction; release and discard cancelled/stale/failed results |
| `chat/forms.py`, `chat/views.py`, `templates/chat/ask.html` | Initial-submit UUID, stable legacy-client token, duplicate/conflicting request handling and financial-retention disclosure |
| `chat/llm_engine.py` | Meter regular, periodic and repair calls; legacy client timeout/retry bounds |
| `astrology/agent/provider.py`, `astrology/agent/orchestrator.py` | Meter agent calls, conservative unknown usage, explicit spending-limit partial answers |
| `astrology/rag/hosted.py`, `astrology/rag/knowledge.py` | Meter hosted search, source-generation fingerprint and bounded authorized conversation cache |
| `accounts/reporting.py`, `accounts/views.py`, `accounts/urls.py`, `templates/accounts/contribution.html` | Superuser-only aggregate unit-economics dashboard, unknown allocations, separate estimated/invoice average/P95 costs |
| `accounts/admin.py` | Superuser-only financial records/allocations and audited credit-refund action |
| `charts/management/commands/reconcile_usage.py` | Default dry-run reconciliation; explicit apply releases stale reservations without replaying provider work |
| `accounts/fixtures/p7_tariff_v1.json`, `accounts/test_usage.py` | Published example arithmetic and 29 offline P7 tests, including real-connection concurrency |
| `PHASE_07_PLAN.md`, `PHASE_07_CONTRACTS.md`, this report | Pre-implementation plan, semantics/configuration/limits and evidence |

A content-hash inventory before production edits covered 200 source/document/template files (including the new phase plan). **186 remained unchanged; 14 intentional existing-file changes** are `accounts/admin.py`, `credits.py`, `models.py`, `urls.py`, `views.py`; `astrology/agent/orchestrator.py`, `provider.py`; `astrology/rag/hosted.py`, `knowledge.py`; `chat/consultation_service.py`, `forms.py`, `llm_engine.py`, `views.py`; and `templates/chat/ask.html`. New files are outside that inventory. Calculation engines, rule YAML/evaluators, P2 deterministic wrappers, settings, existing migrations, existing tests and earlier reports remain unchanged from the pre-P7 workspace.

## Commands actually run

```powershell
# Baseline before production changes:
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity 0

# Generate migration files, without applying them to the application database:
.\.venv\Scripts\python.exe manage.py makemigrations accounts --name usage_ledger --noinput
.\.venv\Scripts\python.exe manage.py makemigrations accounts --name request_stop_reason --noinput
.\.venv\Scripts\python.exe manage.py makemigrations accounts --name reported_search_usage --noinput

# Focused and existing regressions:
.\.venv\Scripts\python.exe manage.py test accounts.test_usage --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py test astrology.test_agent astrology.test_knowledge chat.test_memory astrology.test_quality --noinput --verbosity 0

# Full regression and framework/schema checks:
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --noinput
```

| Check | Observed result |
|---|---|
| Pre-P7 baseline | 240 passed, 131.603 s; zero existing test failures |
| P7 focused final feature suite | 29 passed, 3.535 s |
| Intermediate full regression | 261 passed, 136.440 s |
| Full regression with all new P7 tests | 269 passed, 137.458 s |
| Final full verification after status/timestamp polish | 269 passed, 135.461 s |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Tracked-file whitespace check | `git diff --check` passed (existing Windows line-ending notices only) |
| Production migration execution | Not performed |
| Live provider/corpus/payment calls | None |

Tests apply migrations to isolated Django test databases. Network use is prohibited or provider calls are explicitly mocked; the real-concurrency case only performs database work. Test durations are not production latency or live-cost measurements.

## P7 acceptance matrix

| ID | Tested evidence | Outcome / limits |
|---|---|---|
| P7-01 | Simple metered request; actual deterministic agent factual request | One reservation/settlement; factual lookup has no LLM attempt and known zero external cost |
| P7-02 | Rounds/tokens/cost/file-search/model/tool denials; real orchestrator spending-limit fallback; provider overrun | Extra paid call blocked before dispatch; explicit qualified partial result; overrun recorded and prevents further calls |
| P7-03 | Provider timeout, malformed/unknown usage, partial/failed final validation | Reserved customer credit released; sanitized error and conservative provider liability retained |
| P7-04 | Repeated initial HTTP POST, follow-up UUID retry, changed-body UUID conflict | Single provider dispatch and credit consumption; conflicting body receives 409 |
| P7-05 | Last-credit conditional reservation plus two real DB connections racing; disabled-allowance concurrency ceiling | At most one last-credit reservation, no negative/overspent wallet; SQLite contention can reject both and a fresh retry makes progress |
| P7-06 | Repeated authorized natal query; backend cache eviction/miss | Same validated output with one initial adapter evaluation; no paid call for deterministic facts |
| P7-07 | Changed chart content, owner mismatch, conversation epoch and source fingerprint changes | Old values not reused across those changes; same authorized conversation search reuses bounded passages with zero retrieval rounds on hit |
| P7-08 | `usage=None` response and timeout | Nullable actual token fields, explicit estimated/error status, upper-bound rated liability; not fabricated free usage |
| P7-09 | Two published tariff arithmetic fixtures; cached discount; observed zero file searches | Exact expected Decimal costs; reserved searches distinguished from observed calls; invoice actual remains unknown |
| P7-10 | Repeated refund, cancel before/during generation, memory deletion, abandoned worker dry-run/apply | Credit returned once; late answer blocked; financial liability retained and no automatic provider retry |
| P7-11 | Ordinary users, another user, staff versus superuser; dashboard no chart text; explicit allocation math | Unauthorized reporting denied; private/no-store aggregates; missing allocations produce unknown margin; invoice actual replaces estimate where available |

Additional tests cover historical allowance bootstrap once, cross-user reservation rejection, per-user daily provider cap across conversations, unknown tariff rejection and zero-credit loss on invalid answers. Existing P3/P4/P5/P6 regression cases remain in full discovery, including authorization, injection, deletion and concurrency behavior.

## Failures and issues, separated

**Existing failures before changes:** none; all 240 baseline tests passed.

**New regression during implementation:** the P5 in-flight-reset test initially failed because P7 returned `request_cancelled` instead of the established `conversation_changed_result_discarded`. The old external contract was restored; later full runs passed. No calculation regression was observed.

**New test/setup issues corrected:** newly created chart objects can retain string-form time values until reloaded, so reservation now reloads authorized persisted chart data before fingerprinting. The finance test initially remained signed in as the other user; it was corrected to authenticate the intended privileged principal. These are distinct from any pre-existing test failure.

**External/unverified:** no capped live average/P95 provider-cost sample was authorized or measured, no production PostgreSQL concurrency/restart validation occurred, no provider invoice reconciliation or payment-fee allocation was fabricated, and no commercial price was recommended. Defaults are ceilings, not measured profitable price assumptions. Remote vector-store mutation detection is operator-versioned plus TTL; a same-ID remote reindex requires a source-generation bump. Direct internal low-level callers outside the customer service have per-call caps but no customer ledger; future public/background entrypoints must use the documented boundary. SQLite write-upgrade contention can return 409 for both racing requests; no successful provider work is repeated automatically. A global organization-wide API cap/multi-account abuse system is not introduced; configure provider-project limits before launch.

## Gate disposition and next action

Offline billing/resilience/authorization tests pass. New schema is supplied for review and remains unapplied to the application database; follow the migration/staging procedure in the contracts before deploying. A separately approved capped live run must measure mean/P95 costs, including file-search/failed-call liability, followed by pricing review and the target production database's concurrency checks. Therefore the **full P7 gate remains BLOCKED** for external measurement/rollout verification. Next-phase approval is still required; P8 has not been executed.
