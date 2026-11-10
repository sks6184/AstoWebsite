# P8 implementation plan

Date: 8 November 2026 (Asia/Bangkok). Branch `feature/pilot-release-p8`; HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. P8 only, assuming P7 approval as explicitly requested. Preserve all prior uncommitted work. No P9, public launch, paid calls, production migration or deployment.

1. Run the existing 269-test baseline before production edits. Audit settings, chart validation, ownership, admin access, account deletion and current loading/provenance behavior.
2. Add persisted coarse request progress and owner-only status polling. Store bounded answer evidence manifests with tool/method/source fingerprints, status and actual retrieved citation metadata; do not expose raw reasoning or fabricate provenance for historical/legacy answers.
3. Add a separate fail-closed production settings profile: explicit secret/hosts/database/shared cache, HTTPS/session/CSRF, trusted proxy opt-in, restricted pilot signups/verified email and sanitized logs. Keep local development separate. Harden private admin boundaries, chart input validation and private response caching.
4. Add database-backed short-window rate controls, anonymous aggregate operational metrics, bounded satisfaction feedback, explicit account deletion and default dry-run retention cleanup. No raw chat/birth/IP data in generic telemetry.
5. Add a read-only readiness/consistency command and a concrete staging/rollback/monitoring/retention runbook. Supply additive migrations without applying them to the application database. Test legacy-message compatibility and wallet bootstrap/consistency rather than invent historical evidence.
6. Run offline signup→chart→question→follow-up flows, CSRF/host/admin/ownership/deletion/outage tests, feature-flag rollback and bounded burst tests, then the entire regression suite and schema checks.

Offline tests use isolated databases and mocked providers, no live cost. Actual production ingress/TLS/email, target-database concurrency/load thresholds and rollout approval need separate verification. P7 live average/P95 cost measurements remain unperformed. Passing code tests does not approve external rollout or public launch. Stop after the P8 report.
