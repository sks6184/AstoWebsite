# P8 limited-pilot release runbook

Status: reviewable procedure, **not executed or approved for rollout**. Date: 8 November 2026 (Asia/Bangkok). This is a limited B2C pilot; public launch and P9 remain separate decisions. P6 human-quality comparisons and P7 capped live cost measurements were not manufactured by P8.

## Required decisions before deployment

Record the operator, hosting target/region, exact HTTPS domains, invited participants, provider project/model/tariff/source-index versions, email sender, backup retention, incident contact, request/load thresholds and explicit cost ceiling. Keep the invitation list and secrets outside source control. Agree what counts as a meaningful failure; distinguish expected 429/credit denials from application errors. No production latency/failure target has yet been agreed, so no test here claims to satisfy one.

Use a reviewed, versioned release artifact and a supported production WSGI/ASGI platform, PostgreSQL and shared cache. Provision/pin the web server in the deployment environment; this repository did not install or launch one. Do not use Django `runserver`, a debug server or ngrok for production. The profile/checklist follows [Django 5.2's official deployment guidance](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## Configuration inventory

Set these through the deployment secret/configuration system, not a committed `.env`:

```text
DJANGO_SETTINGS_MODULE=astro_site.production
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<unique high-entropy production secret, at least 50 characters>
DJANGO_ALLOWED_HOSTS=<exact approved DNS hostname(s), comma separated>
DATABASE_URL=<private PostgreSQL URL>
EMAIL_HOST=<approved SMTP host>
EMAIL_PORT=587
EMAIL_HOST_USER=<SMTP identity if required>
EMAIL_HOST_PASSWORD=<SMTP secret if required>
DEFAULT_FROM_EMAIL=<verified sender>
ASTROGPT_PILOT_EMAILS=<explicit invited addresses, comma separated>
ASTROGPT_AGENT_ENABLED=false
OPENAI_API_KEY=<dedicated approved API project credential>
OPENAI_MODEL=<reviewed model with configured tariff/context bounds>
OPENAI_VECTOR_STORE_ID=<reviewed source store>
```

The production module does not load development `.env` values. Django settings overrides can configure the P7 policy/tariff/daily cap and source generation; review those values explicitly. Rotate credentials and never paste them into logs/reports. API spending is separate from ChatGPT/Codex allowances; any promotional API credit is account funding, not a reliable production-cost assumption.

Trust `X-Forwarded-Proto` only if the controlled ingress strips/replaces client values; then set `ASTROGPT_TRUST_PROXY=true`. Forwarded-host trust stays disabled. Reject unknown hosts at ingress too. Enforce TLS, redirect HTTP, cap bodies at 64 KiB, restrict operator admin access and require operator MFA at the ingress/identity layer. Avoid proxy retries of question POSTs. Do not log bodies, query strings, raw client IPs, birth fields or chats in proxy/APM logs. Use method/status/duration with collector timestamps and route-level app metrics.

Serve `STATIC_ROOT` through the web server/CDN after `collectstatic`; keep private media and backups nonpublic. At least two concurrent workers are needed for status polling while a synchronous reading is running. Choose worker/network timeouts to exceed the documented bounded consultation envelope while retaining cancellation/reconciliation. Validate actual worker saturation in staging; do not infer it from local HTTP-client tests.

## Staging migration and consistency sequence

1. Back up the current database with encryption/access controls; verify a restore using synthetic or appropriately consented data in an isolated environment. Inventory existing pending P5/P7 migrations as well as P8's `accounts/0006_pilot_operations.py`.
2. With the feature flag off, run `python manage.py showmigrations --plan` against staging and review the plan. Run `python manage.py migrate` only after the backup/review decision. Do not execute migration commands against a guessed database URL.
3. Create the production database-cache table: `python manage.py createcachetable pilot_cache`. This is a staging/deployment database action, not something executed by implementation tests against the application DB.
4. Run `python manage.py collectstatic --noinput`, `python manage.py check --deploy --fail-level ERROR`, and `python manage.py pilot_readiness`. Resolve critical errors; verify the shared cache table is actually readable/writable by the application role. Readiness's cache-backend setting check is not a table probe.
5. Review W005/W021: HSTS subdomain coverage/preload are intentionally off. Do not claim control of every subdomain or preload a trial domain blindly. Record the chosen HSTS rollout/approval; stricter preload is a separate domain-wide decision.
6. Inspect a synthetic historical reading: content unchanged, old provenance explicitly unknown. Confirm old wallet usage is not reset/recharged; active reservations equal outstanding usage rows. The consistency command checks a historical consumed-credit lower bound, not a full audited backfill.
7. Confirm valid chart creation and clear invalid-date/time/timezone/coordinate errors. Confirm wrong-user charts/conversations/summaries/manifests/status requests return no data. Confirm staff permissions cannot reveal the admin portal and unverified sessions cannot access private chart/chat routes.

Application-database migrations were **not executed** in this implementation. Its read-only development readiness check reports pending migrations and agent flag off; do not treat the local web app as a released P8 instance until schema/configuration are deliberately applied.

## Bounded validation and pilot activation

Offline reproducible commands:

```powershell
.\.venv\Scripts\python.exe manage.py test accounts.test_pilot --noinput --verbosity 0
node scripts/test_pilot_ui.cjs
.\.venv\Scripts\python.exe manage.py test --noinput --verbosity 0
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --noinput
.\.venv\Scripts\python.exe -m pip check
```

The offline pilot signs up a synthetic user, calculates a real synthetic chart through existing helpers, asks with a mocked provider, follows up, validates ownership, records optional feedback, exercises outage/refund policy and tests cleanup/migration compatibility. It makes no external API/payment/email call. The Node checks exercise the actual submit/poll script with mocks; they do not replace Chrome/Firefox/mobile/screen-reader checks.

Before invited external use, verify SMTP ownership-confirmation and password-reset delivery, CSRF with HTTPS/SameSite cookies, OAuth if enabled, real-browser polling and accessibility, target PostgreSQL concurrency and restored-backup consistency. Review dependency vulnerabilities/current supported versions separately; `pip check` is only an installed-dependency compatibility check, not a CVE audit. No dependency upgrades were made, preserving calculation results.

For a live capped smoke test, obtain a separate explicit approval identifying participant accounts, maximum requests, API project/model, calendar horizon and total provider-cost ceiling. For example, a **proposal only** could limit one operator to ten requests and a USD 0.50 configured request-budget total; this is not approval or a measured-cost claim. Reconcile the provider's actual usage/rated costs and uncertainty, and do not assume provider dashboard budget alerts are hard spending cutoffs. Keep P7's per-request/day guards and account/ingress limits active. Do not fund or dispatch the test until approved.

Only after staging checks and the rollout plan are approved, temporarily enable `ASTROGPT_AGENT_ENABLED=true` for the explicitly invited pilot environment and gracefully restart workers. Keep the legacy path available. Record the release/source/package/source-store/tariff versions and enablement time. Capture actual answer outcomes, continuation/helpfulness (not predictive effectiveness), cost, latency and failures without copying raw consultations into analytics. Decide prices from measured costs; do not infer profitability from synthetic zero-provider tests.

## Monitoring, alerting and maintenance

Use `/accounts/pilot/analytics/`, `/accounts/contribution/`, sanitized JSON logs and provider-attempt statuses. Restrict dashboards to operators; do not expose them to customers/partners. Structured logs omit arbitrary error messages and bodies, so investigate individual failures only through authorized scoped records and provider diagnostics under the privacy policy. Never enable blanket HTTP body/debug/APM capture to troubleshoot a pilot.

The following are **proposed operational triggers requiring owner agreement**, not tested production SLOs:

| Signal | Proposed response |
|---|---|
| Any cross-user disclosure or unsupported critical calculation claim | Stop new agent traffic, preserve minimal authorized incident evidence, investigate before resuming |
| Wallet inconsistency or duplicate consumption | Disable new submissions, reconcile credits/provider liability; never blindly replay |
| Repeated provider errors, sustained 5xx/partial increase or limiter failures | Operator reviews bounded aggregate deltas; pause agent traffic if unexplained |
| Approaching approved provider ceiling or usage overrun | Stop new paid work and reconcile; leave customer reservations correctly released |
| Growing stale active requests | Reconcile older bounded workers; check saturation before raising limits |
| Latency above the agreed threshold | Reduce admission/concurrency or roll back; do not expand budgets automatically |

Configure an external monitor/notification target only after approval. No email/Slack/SMS alerts were sent or integrated here. Upstream monitoring should add UTC timestamps and derive rolling rates/percentiles; daily counters alone do not provide a five-minute error rate or P95. Separate intentional 429 throttling from unexpected failures.

Suggested operator schedule, not installed: review stale requests every few minutes; run `reconcile_usage` dry-run and explicitly apply only beyond its safe age; run `purge_pilot_data` daily and verify effects; purge expired rate rows frequently enough for expected traffic; run `clearsessions` regularly; check source-generation bumps after any remote reindex; review cost/credit consistency daily during the pilot. Backups and caches can retain deleted data separately; enforce finite backup expiry and apply deletion records when restoring.

## Rollback and incidents

1. Stop accepting new agent traffic if privacy/billing correctness is uncertain. Keep current schema and P7 guards.
2. Set `ASTROGPT_AGENT_ENABLED=false` in the **current P8 release**, gracefully restart workers and let bounded in-flight requests finish or cancel/reconcile them. Do not retry paid requests automatically.
3. Verify a new synthetic legacy turn, correct credits and unchanged earlier transcript/evidence links. The offline rollback test covers routing/history/ledger continuity, not live legacy prose quality or provider availability.
4. Run the consistency command and inspect reserved/consumed/released totals. Refund customer question credits idempotently where policy requires; retain actual provider liability.
5. Do not reverse migrations or roll code back to a schema-incompatible old build during traffic. Feature-flag rollback is the tested path. Disaster recovery requires a matched build/database snapshot, maintenance window and reconciliation of work after the snapshot; restore must not resurrect deleted private data unnoticed.

## Approval record

Rollout approver, host/domain, participant list, agreed latency/failure limits, paid smoke-test cap, current dependency audit, backup/restore proof, HSTS decision, provider-cost results and enablement time: **not supplied / not approved here**. Actual public launch remains a separate explicit decision. P9 has not started.
