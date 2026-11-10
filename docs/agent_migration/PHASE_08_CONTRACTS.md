# P8 pilot experience, privacy and operational contracts

8 November 2026, Asia/Bangkok. Branch `feature/pilot-release-p8`; HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. P8 only, as authorized assuming P7 approval. No public launch, P9, paid provider call or production migration occurred. Earlier phase work remains uncommitted and preserved.

## Request experience and provenance

`UsageRequest.progress` stores an allowlisted coarse stage: queued, charts, periods, transits, rules, sources, answer or validation. `accounts/pilot_ops.py:progress` updates only the active request bound by the server's P7 budget context. `astrology/agent/orchestrator.py` and `accounts/provider_meter.py` report real processing stages; there is no timed fiction that a Dasha/transit has been verified and no private model reasoning is sent to the UI. These labels describe work underway, not a guarantee that evidence was found.

`GET /chat/requests/<uuid>/status/` requires the owner and checks current chart ownership. It returns only status, public label, active flag and credits consumed. Missing/foreign requests return 404. `request_summary` provides the same persistent status on the conversation page, including failed requests without an assistant message. A partial answer is explicitly preliminary; failed/partial/cancelled work follows P7's credit-release policy.

The Ask/follow-up script takes `FormData` before changing control state, sends one POST and polls the owned status endpoint every 1.5 seconds, at most 90 times. Polling failure never retries a paid POST. Connection failure tells the user to inspect History before retrying; UUID deduplication remains server-side. Redirects open the saved conversation. Native form submission still works without JavaScript, with final status after redirect. Progress polling needs a concurrent web worker: it cannot work responsively with a single worker blocked on generation. Error messages are rendered as text, not injected HTML. `scripts/test_pilot_ui.cjs` tests the actual script's success/progress and connection-failure protocols offline; it is not a real-browser accessibility certification.

`chat/evidence_manifest.py:manifest` stores a versioned, at-most-16-KiB audit manifest inside the existing assistant `Message.provenance`. It includes pipeline/status, validation type/result, provider/engine label, requested model names from actual P7 attempt rows where available, tool/evidence IDs, method/precision/inclusivity/reference-frame metadata, chart/engine/request/adapter fingerprints and actually retrieved citation metadata. It does not store raw model deliberation, prompt text, repeated book excerpts or the complete tool payload. Oversized lists are omitted with a truncation flag. Citation metadata is not invented for legacy `file_search` text whose retrieval records were not retained.

`GET /chat/answers/<id>/evidence/` is owner-only, checks current chart ownership and is not cacheable. The conversation UI provides collapsed evidence/status details and this link. Historical messages are left unchanged: their response explicitly says detailed provenance was not retained and validation is unknown. Fingerprints and claim IDs support audit, **not exact replay**: old complete chart/tool/source snapshots and immutable release archives are not automatically retained. `exact_replay_available` remains false. Trusted operator/database edits can invalidate historical audit assumptions; operators must not rewrite published readings as if they were newly validated.

## Authentication, ownership and production profile

The existing chart/conversation/message ownership and P7 wallet protections remain. Authenticated responses receive `Cache-Control: no-store, private` and same-origin referrer policy. Host validation runs even when a view would not normally call `get_host()`. Forwarded host trust is disabled; proxy scheme trust requires explicit `ASTROGPT_TRUST_PROXY=true` and a proxy that strips/replaces client-supplied forwarding headers.

`astro_site/production.py` is a separate fail-closed profile. It skips the development `.env`, rejects debug mode, weak/development secrets, wildcard/development/tunnel hosts and missing PostgreSQL configuration. It requires SMTP sender/host and a limited pilot invitation list. It enables HTTPS redirect, secure/HTTP-only/SameSite cookies, bounded session lifetime, HSTS, explicit HTTPS CSRF origins, content-type protection, frame denial and a shared database cache. Exact operational environment values and remaining prerequisites are in the release runbook.

Production requires verified email and restricts new password signups to the configured invite list via `PilotAccountAdapter`. Social signup requires an invited verified provider email. The old `/login/` route now uses allauth's login flow. Private chart/chat/account routes additionally deny unverified authenticated sessions under mandatory-verification settings; a pre-existing session or alternate backend cannot bypass this check. Account deletion remains available for an authenticated owner who can supply the required confirmation. Google login-on-GET is disabled in production. Actual SMTP/OAuth delivery and ingress TLS remain external staging checks.

`PilotAdminSite` permits only active staff **superusers**, including its login form. A staff account with all ordinary model permissions still cannot use the admin portal. Chart, message, conversation, profile and payment admin classes also explicitly restrict private data to superusers. Financial reporting and pilot analytics remain superuser-only. This is an operator boundary, not a new partner portal or delegated staff role system. Use ingress restrictions/MFA for operators before rollout; no new MFA service was installed.

The production log formatter emits a small JSON record with event, level, component, status, allowlisted route and elapsed time. It ignores arbitrary message text, raw URL/query/body, exception details, request objects and stack frames. Production Django/OpenAI/HTTP-client/root logging uses this formatter. Local development may still show Django debug diagnostics and is unsuitable for external users. No request/response body capture or external monitoring SDK was installed. Remote Google Fonts were removed from the shared template; system-font fallbacks avoid automatic font-service requests.

## Valid chart inputs

`SavedChartForm` validates a real calendar date/time, supported birth-date range, recognized IANA time zone, complete coordinates and geographic bounds. Missing coordinates no longer create a placeholder through the creation form. Calculation exceptions produce a clear error and no saved chart. Existing incomplete charts are not silently backfilled with invented placements; deterministic tools continue to flag missing evidence. Astrology algorithms and rule conclusions were not changed. `SavedChart.__str__` now contains only a chart ID so future generic object/audit labels do not embed names and birth dates.

## Rate controls and operational measurement

`PilotRateBucket` provides database-shared atomic fixed-minute counters. Keys are HMACs of scope, principal and window; raw IPs/user IDs are not stored. Auth, admin-login and reset POSTs are limited to 10 per minute per socket peer; authenticated question/chart/memory/delete/feedback POST routes to 10 per user per route per minute; progress reads to 180 per minute. Database limiter failure denies the operation. A 429 includes `Retry-After: 60` and starts no reading. The 64-KiB request-body setting adds another bound. P7 per-request/two-active-request/daily-cost controls still apply when customer allowance enforcement is disabled.

These controls do not defeat distributed abuse. Without a trusted client-IP integration, users behind the same proxy share the authentication bucket. Configure ingress body limits, client rate controls, operator access controls and provider-project limits before exposure. No arbitrary `X-Forwarded-For` value is accepted as identity. Rate windows become unusable when the minute changes; physical removal of hashed expired rows requires the cleanup command.

`PilotMetric` stores only daily UTC event/outcome counts and elapsed total/max. Events include signup, chart creation, initial question, follow-up, feedback, request outcome, rate denial and account deletion. No user/conversation/chart/IP ID, birth data, question, answer or source excerpt is retained in these counters. Actual completion events are emitted once per generated turn; duplicate submission redirects do not create another completion. Daily conversion is an aggregate signup→chart→question proxy, not a linked-person funnel or causal attribution claim.

`POST /chat/answers/<id>/feedback/` records one optional helpful/unhelpful/unsure vote on an owned assistant message; free text is not accepted. Repeated votes do not inflate counts. Feedback is not a human correctness oracle or P6's blinded evaluation. Message-linked votes delete with the message; unlinked daily counts remain until aggregate expiry.

`/accounts/pilot/analytics/` provides privileged aggregate operations/continuation/feedback/error counts and links to P7 cost/contribution reporting. Generic structured request logs support external latency percentiles; total/max counters alone do not establish a production P95. There is no invasive individual analytics tracker. Missing revenue/cost allocations remain unknown under P7 rules.

Cost dashboards query retained financial rows. Because current account deletion also removes those rows, these are not an immutable all-time spend ledger; reconcile provider invoices separately and do not infer all-time profitability after account deletions.

## Deletion and retention

| Data | Default policy / implemented behavior |
|---|---|
| Conversation text, summaries, message-linked feedback | User reset/clear/delete controls remain; inactive conversations become eligible for cleanup after 30 days |
| Aggregate operational counters | Eligible for deletion after 90 days; no direct identity fields |
| Rate buckets | Minute-scoped; eligible for physical deletion after two minutes |
| Financial UUID/credit/provider records | Survive conversation/chart deletion per P7; deleted with account under the current model policy |
| Chart inputs/calculated data | Retained until chart/account deletion; no automatic chart expiry is introduced |
| Shared knowledge/deterministic caches | Existing scoped keys and TTLs; deleted/reset ownership context prevents reuse; backend entries expire separately |
| Backups, provider records and external payment records | Not directly erased by an app-row deletion; operator/provider retention and restore procedures apply |

Deleting a chart alone does not delete existing conversation text derived from it; delete those conversations or the account to remove that retained consultation content.

`purge_pilot_data` is dry-run by default. Explicit `--apply` removes expired inactive conversation content using the existing guarded deletion service, old counters and expired rate rows. It skips active conversations; reconcile stale P7 requests first. No scheduler was installed, so a configured retention window is not a promise of deletion until the operator schedules and verifies cleanup. An operator should retain only encrypted bounded backups and prevent deleted data from silently reappearing after restore.

`/accounts/privacy/delete/` requires POST, CSRF, typed DELETE and the current password, or a social-only sign-in within 15 minutes. It acts only on the current user. In one transaction it removes linked app payment payloads, historical admin audit entries for the owner's chart/chat/profile/account objects, and the account's cascading charts, conversations, summaries, feedback and credit/usage data. Anonymous daily counts remain. The session is logged out. It does not call a payment gateway or issue a cash refund. Provider/backups/external payment deletion requires the separate documented process. Actual user accounts were not deleted during implementation; tests use synthetic accounts.

## Schema, consistency and gate

`accounts/migrations/0006_pilot_operations.py` adds the progress field and three pilot models. Existing answers are preserved without fabricated provenance; the migration test also preserves old financial usage/credits and gives existing usage rows the neutral queued progress default. Terminal labels still derive from actual terminal status. No historical tool evidence is reconstructed from current calculations.

`pilot_readiness` is read-only: migration state, reserved-credit consistency, consumed-credit lower-bound consistency and chart/conversation ownership. Production mode additionally checks debug/cookies/HTTPS/PostgreSQL/verification/invites/limits/shared-cache configuration. It prints booleans and a feature flag, no personal data or secrets. It does not prove correct ingress TLS, SMTP deliverability, dependency security, cache-table readiness, production isolation or complete historical billing truth. The current application check returns `migrations_current:false`; no migration was applied to that database.

Offline acceptance includes 20 P8 tests, existing billing/privacy regressions, two Node UI protocol checks, a 12-request synthetic burst and production configuration subprocess checks. `check --deploy` reports intentional W005/W021 HSTS subdomain/preload warnings; neither is hidden or automatically enabled without domain-wide approval. Production load/latency thresholds, real-browser/mobile/accessibility checks, PostgreSQL race/restore tests, provider-cost pilot measurements and rollout-plan approval remain external gates. Passing offline tests does not authorize deployment, invite delivery or public launch. P9 has not started.
