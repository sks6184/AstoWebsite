# P8 implementation and regression report

**Offline implementation/security/billing regression: PASS. Full P8 rollout gate: BLOCKED pending schema application, target-infrastructure verification, agreed load limits and explicit rollout approval. No public launch or P9 work occurred.**

Date: 8 November 2026, Asia/Bangkok. Branch `feature/pilot-release-p8`, base/current HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. The user authorized P8 assuming P7 approval; prior human-quality/live-cost measurements were not invented. Changes remain uncommitted alongside preserved earlier work.

## Delivered implementation

| Source / function | Implemented responsibility |
|---|---|
| `accounts/models.py`, `accounts/migrations/0006_pilot_operations.py` | Coarse progress field, anonymous aggregate metrics, expiring hashed rate buckets and message-linked feedback |
| `accounts/pilot_ops.py:progress`, `request_summary`, `metric`, `allow_rate` | Real processing stages, persistent public status, bounded-field counters and shared atomic admission limits |
| `astro_site/pilot_middleware.py:PilotMiddleware`, `SafeJsonFormatter` | Host validation, private response headers, mandatory verification guard, request/rate metrics and payload-free operational logging |
| `astro_site/production.py` | Separate fail-closed production configuration: explicit secrets/hosts/PostgreSQL/email/invites, HTTPS/cookies/CSRF/shared cache and sanitized logs |
| `astro_site/admin_config.py`, `admin_site.py`; private admin classes | Operator-superuser-only admin, including login; staff model permissions cannot expose birth/chat data |
| `accounts/pilot_adapter.py`, `accounts/adapters.py`, `astro_site/urls.py` | Invited/verified signup policies; legacy login route now uses allauth |
| `accounts/apps.py`, `accounts/signals.py` | Signup aggregate and recent-login timestamp for social-account deletion |
| `charts/forms.py`, `charts/views.py`, `charts/models.py` | Valid coordinate/timezone/date inputs, clear calculation failure/no placeholder save, chart-created count and safe object label; no calculation rewrite |
| `chat/evidence_manifest.py:manifest`, `chat/consultation_service.py` | Versioned bounded publication metadata with actual method/source fingerprints, ledger-requested models and no fabricated historical provenance; continuation/outcome counts |
| `chat/views.py`, `chat/urls.py` | Owned status/evidence endpoints, persistent failed/partial state and bounded feedback |
| `templates/chat/ask.html`, `templates/base.html` | Submit/poll feedback, evidence/limitation details, optional feedback and privacy link; no automatic duplicate POST or remote font requests |
| `accounts/views.py`, `accounts/urls.py`, new account templates | Verified account deletion and superuser aggregate analytics, with no identity-based funnel tracking |
| `charts/management/commands/purge_pilot_data.py`, `pilot_readiness.py` | Default dry-run retention cleanup and read-only schema/wallet/ownership/configuration checks |
| `accounts/test_pilot.py`, `scripts/test_pilot_ui.cjs` | Twenty offline Django tests and two JavaScript protocol checks |
| `PHASE_08_PLAN.md`, `PHASE_08_CONTRACTS.md`, `PHASE_08_RELEASE_RUNBOOK.md` | Plan written before production edits; implementation semantics and concrete staging/monitoring/rollback procedure |

The pre-edit inventory covered 222 source/document/template files including the phase plan. **201 unchanged; 21 intentional existing-file changes**: five account implementation/admin/config files plus its URLs/views/provider meter (see exact list below), the agent orchestrator, chat admin/service/URLs/views, chart admin/forms/models/views, base settings/URLs, two shared templates and payment admin. New files are outside the inventory.

Exact changed paths: `accounts/adapters.py`, `accounts/admin.py`, `accounts/apps.py`, `accounts/models.py`, `accounts/provider_meter.py`, `accounts/urls.py`, `accounts/views.py`, `astrology/agent/orchestrator.py`, `chat/admin.py`, `chat/consultation_service.py`, `chat/urls.py`, `chat/views.py`, `charts/admin.py`, `charts/forms.py`, `charts/models.py`, `charts/views.py`, `astro_site/settings.py`, `astro_site/urls.py`, `templates/base.html`, `templates/chat/ask.html`, `payments/admin.py`.

Astrology calculation modules, rule YAML/evaluators, P2 wrappers, underlying provider pricing/credit math, existing tests/migrations and earlier reports were not rewritten. No dependencies were added/upgraded, secrets changed, production migrations applied or live provider/payment/email traffic initiated.

## Executed verification

```powershell
# Pre-edit baseline:
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity 0

# Generate migration file only:
.\.venv\Scripts\python.exe manage.py makemigrations accounts --name pilot_operations --noinput

# Existing safety/billing regression and new P8 coverage:
.\.venv\Scripts\python.exe manage.py test accounts.test_usage chat.test_memory astrology.test_agent --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py test accounts.test_pilot --noinput --verbosity 0
node scripts/test_pilot_ui.cjs

# Full suite and final checks:
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --noinput
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py pilot_readiness --development
```

| Check | Observed outcome |
|---|---|
| Baseline | 269 passed, 140.321 seconds; no existing test failures |
| Existing targeted billing/memory/agent regressions | 108 passed, 46.803 seconds |
| New P8 suite | 20 passed, 15.465 seconds |
| Full suite | 289 passed, 152.309 seconds |
| Latest full run including persistent request status/backfill checks | 289 passed, 159.566 seconds |
| Final model-ledger/provenance targeted checks | 2 passed, 2.688 seconds |
| Final CSRF acceptance/rejection and admin login/privacy targeted check | 1 passed, 2.719 seconds |
| JavaScript runtime protocol | 2 passed; actual template script, mocked DOM/network |
| JavaScript syntax | `node --check` passed |
| Django system/schema checks | No issues; no migration drift |
| Installed dependency compatibility | `pip check`: no broken requirements; not a vulnerability audit |
| Production profile subprocess checks | Valid synthetic configuration passes critical deploy checks; debug/tunnel/weak-secret configurations rejected |
| Intentional deployment warnings | W005 HSTS subdomains and W021 preload; neither hidden nor prematurely enabled |
| Actual application readiness, read-only | Failed safely: `migrations_current:false`, `agent_enabled:false` |

All application tests use isolated Django test databases; the migration compatibility test rolls back only that isolated schema and restores it afterward. Production-profile tests use synthetic credentials and no PostgreSQL/provider connection. Existing actual application data was not migrated or deleted. Logs emitted by these tests contain coarse routes/status/timing, not the synthetic birth inputs or question text.

## Bounded offline pilot and load observation

The synthetic signup→chart→question→D10 follow-up case completed through HTTP views, existing real chart helpers and an explicitly mocked provider. Four messages and two UUID-ledger requests were retained. Signup/chart/continuation counters were recorded. Mandatory-verification and invite-denial behavior are tested separately; actual delivery/receipt of confirmation emails remains unverified.

A dedicated reproducible burst test (`PilotTests.test_p8_07_bounded_offline_burst_limits_and_records_latency`) was also run in isolation and its aggregate result read from the test module:

| Measurement | Observed |
|---|---:|
| Requests | 12 |
| Delivered factual readings | 10 |
| Expected admission denials | 2, HTTP 429 |
| Provider calls | 0 |
| Local mean elapsed | 149.20 ms |
| Local nearest-rank P95 elapsed | 295.37 ms |
| Agreed production threshold | Not supplied |

These are local Django-client synthetic timings, including throttled requests, not real-browser or live-provider latency. They do not establish a production SLA, average/P95 API cost or profitable customer pricing. The two expected denials are not hidden application failures. Production PostgreSQL races, real traffic concurrency and bounded paid costs still need the separately approved pilot.

## P8 acceptance matrix

| ID | Evidence | Disposition |
|---|---|---|
| P8-01 | Offline signup→real synthetic chart→question→follow-up HTTP test | PASS offline; external SMTP/OAuth/browser delivery pending |
| P8-02 | Invalid calendar/time/timezone/coordinates and forced engine exception | PASS: clear errors, no saved fake chart/answer |
| P8-03 | Cross-user chart deletion/chat/summary/status/evidence/feedback access; private headers | PASS offline; no cross-user data disclosed |
| P8-04 | Enforced CSRF, invalid Host, staff-with-all-permissions admin denial, admin-login denial, verified-email guard, production profile checks | PASS offline critical checks; HSTS policy warnings and real ingress/SMTP checks documented |
| P8-05 | Provider timeout produces preliminary status and zero consumed credit; P7 failure/refund tests retained | PASS offline |
| P8-06 | Password-confirmed account deletion, stale social-session denial, linked audit/payment cleanup, conversation cleanup/retention | PASS isolated DB; external backups/provider/payment stores remain separate |
| P8-07 | Twelve-request bounded burst and rate/admission measurements | Local behavior PASS; agreed production latency/failure limits NOT VERIFIED |
| P8-08 | Toggle to legacy path and append a turn while preserving old transcript/usage | PASS offline; no schema reversal or live rollout performed |
| P8-09 | Saved owned manifest with actual fingerprints, methods and explicit historical-unknown response | PASS for practical provenance; exact replay remains unavailable |
| P8-10 | Once-per-answer feedback, anonymous daily outcome/continuation counts, restricted analytics, separate P7 cost dashboard | PASS measurement plumbing; no observed conversion/quality/profitability claim |

## Failures and limitations, separated

**Pre-existing regression failures:** none in the 269-test baseline. The audit exposed existing privacy/security gaps not covered by that suite: broad staff admin permissions, incomplete chart-form validation and a legacy login path outside the allauth verification flow. These were corrected within P8 without changing astrology math.

**New verification issue corrected:** the first production configuration test treated every HSTS warning as a failure. The profile deliberately avoids unapproved domain-wide HSTS/preload. The test now fails on critical errors and explicitly records those two expected policy warnings. This is not a claim of zero deployment warnings. No existing regression test failure remained in full runs.

**Unperformed/external:** application migration, actual hosting/TLS/static-cache provisioning, SMTP/OAuth/browser/accessibility validation, target PostgreSQL concurrency/restore checks, current dependency vulnerability audit, agreed production load limits, P6 blinded human comparison, P7 capped live cost test and actual rollout approval. No deployment, invitations, alerts or public launch were sent/executed. Monitoring schedules and external alert integrations are defined but not installed. Retention cleanup is dry-run unless explicitly applied and scheduled. Provenance hashes are audit links, not an archive guaranteeing exact replay.

## Gate recommendation

Offline implementation and tested security/privacy/billing regressions pass. The current application database has pending migrations and the agent remains disabled. Use the release runbook to review staging migration/cache readiness, external security/identity behavior, the capped pilot and operator thresholds. **Full P8 rollout gate remains BLOCKED until those checks and the rollout plan are approved.** Completing this phase does not authorize public launch or P9.
