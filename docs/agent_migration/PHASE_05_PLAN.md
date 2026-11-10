# P5 plan: scoped conversations and privacy-aware memory

Scope: P5 only, user authorized assuming P4 approval. Branch `feature/conversation-memory-p5`, base HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. Preserve prior uncommitted work. No P6 answer-quality work, live paid tests or application-database migration execution.

## Design/file map

- `chat/models.py` and additive migration: opt-in memory consent, compact versioned summary, revision/epoch/reset boundary, active request marker; idempotent turn records. Existing conversations default to memory disabled. Keep chart association immutable in follow-up services; do not backfill ambiguous chartless legacy rows.
- `chat/memory.py`: deterministic summary builder with separate user assertions, corrections, deterministic evidence references and preliminary interpretation references; bounded last three turns plus <=4 KiB summary and an explicitly selected older message when needed. No LLM summarization, speculative prose promoted to facts, cross-chart state or generic telemetry.
- `chat/consultation_service.py`: owner/chart authorization, short atomic optimistic compare-and-swap reservation, provider execution outside transaction, guarded finalization. UUID request keys make retries idempotent; revision/active-request conflicts explicitly return 409. Reset/deletion/revocation invalidate pending publication.
- `chat/views.py`, forms/URLs/templates: follow-up form on existing conversations; memory consent/view/reset/history-clear/delete controls, all mutations POST+CSRF. Preserve new-conversation flow and legacy feature flag. Avoid cross-chart/person continuity.
- `astrology/agent/continuity.py`, policy/orchestrator/rendering integration: use bounded context for elliptical follow-ups, focused D10, inherited transit dates and explicit comparison/correction scopes. Provider receives categorized recent messages/summary as untrusted data; its token reservation includes that context.
- `chat/test_memory.py`: offline P5 acceptance, privacy and concurrency/idempotency tests. Documentation and final report under `docs/agent_migration/`.

Necessary privacy/credit compatibility detail: deleting assistant messages would otherwise reset the existing question allowance. Add a content-free per-user erased-answer aggregate (`chat.models.ErasedAnswerUsage`) and include it in `accounts/credits.py`'s existing count. This preserves current counting while permitting deletion; it is not a transactional billing ledger or P7 implementation.

## Contracts and policy

Every conversation belongs to one explicit user and selected chart. Owner and chart ownership are checked at every service endpoint and before publishing. Birth inputs are never updated from conversational corrections: those remain user assertions requiring chart editing/recalculation separately.

Follow-up inputs: question, UUID request ID, expected revision; optional explicitly referenced older message and user-fact/correction category. No caller-selected user/summary/chart override. In-flight turn conflicts return 409; no long database lock around an LLM call. Failed turns require a fresh request ID to retry; identical request IDs never trigger another generation. Do not claim a distributed billing ledger (P7).

Memory is opt-in. Reset summary keeps visible transcript but establishes a new memory epoch/floor so old messages cannot silently rebuild it. Clear history removes message content/summary; minimal payload-free turn request tombstones may remain until conversation deletion to prevent replay. Delete conversation cascades messages, summary and turn records. All histories remain in the application database until the user deletes them; no automatic TTL/backups erasure guarantee. Explain provider-bound context and opt-out in the UI/docs. Existing legacy one-shot behavior remains available; contextual agent follow-ups require its feature flag.

## Test matrix

| ID | Case | Expected |
|---|---|---|
| P5-01 | Three-turn career consultation | Same chart/topic, relevant prior period inherited |
| P5-02 | What about D10? | Focused D10 evidence with prior topic/dates |
| P5-03 | Compare with late 2027 | Explicit Oct–Dec scope plus previous period, original topic retained |
| P5-04 | New chart/person | Fresh memory; no previous-chart context; mismatched chart follow-up denied |
| P5-05 | Cross-user conversation ID | View/follow-up/summary/reset/delete denied |
| P5-06 | Long conversation | Last three turns and compact typed summary; older material fetched only by explicit reference, bounded payload |
| P5-07 | Correction | Separate correction provenance and superseded assertion reference; no chart mutation or prediction-to-fact promotion |
| P5-08 | Reset/delete | Correct content removal/reset floor; pending result cannot recreate cleared data |
| P5-09 | Simultaneous/repeated follow-ups | CAS conflict/idempotent retry, ordered messages, one generation per request ID |

Run current full suite before changes; run focused P5 and complete regression discovery afterward. Providers/network mocked, synthetic test database only. Add migration files and test them through Django's isolated runner, not production `migrate`. Document prior failures separately, cost, limitations and rollback; stop for approval before P6.
