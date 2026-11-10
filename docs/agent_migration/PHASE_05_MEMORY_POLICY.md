# Conversation memory and retention policy (P5)

## Consent and scope

Conversation transcripts already persist in the application database. Contextual memory is a separate, explicit opt-in, off by default for existing conversations. The UI explains that enabling it sends a bounded selection of this conversation's prior messages and summary to the answer provider. New conversations, including another chart/person belonging to the same account, start with independent memory. There is no account-wide summary, cross-chart recall or automatic identity inference.

Enabling memory on an existing conversation starts from that point forward. Do not silently send pre-consent history. Disabling/resetting memory clears the summary and establishes a reset boundary; earlier visible messages are not silently used to rebuild it. The selected chart is fixed for the conversation. To consult about another chart/person, start a new conversation and explicitly select that chart. Birth-input corrections require editing/recalculating the saved chart; conversational assertions do not mutate calculation inputs.

## Stored categories and bounds

The versioned summary distinguishes user assertions, user corrections (including superseded-message references), deterministic evidence references and preliminary agent-interpretation references. It is assembled deterministically, without another model call. Speculative assistant predictions never become asserted user facts or permanently verified calculation values.

Only the last three turns (at most six prior messages), a compact summary and an explicitly selected older message are eligible for a provider context. Each text field and the complete context have UTF-8 byte caps. Older content is not fetched automatically. Users may select a specific visible message reference when needed; it must belong to this authorized conversation and lie after the current consent/reset boundary. Provider token budgeting includes the selected context. A summary is not a substitute for re-authorized deterministic tools.

Summary data and transcripts may contain user-supplied personal information. They stay in the application database with the conversation, not generic telemetry/logs. No raw birth chart, date/time/location inputs or book text is copied into summary evidence references. The model receives current deterministic evidence only through the existing authorized tool path. Recent user messages can contain personal information supplied by the user; consent makes that transmission explicit rather than claiming automatic PII redaction.

## View, reset and deletion

- **View memory:** an authenticated owner can inspect summary categories and consent state.
- **Reset memory:** keep the visible transcript, clear the summary, advance the memory boundary/epoch and invalidate pending results. Earlier content is excluded from subsequent context.
- **Disable memory:** reset as above and stop sending prior-message context.
- **Clear history:** remove message content and summary from the active application database, invalidate pending generation, and retain only payload-free request tombstones needed to reject duplicate submissions until the conversation itself is deleted.
- **Delete conversation:** cascade-delete its transcript, summary and turn/idempotency rows. An in-flight result cannot recreate it.

Deleting answered content does not restore question credits. A content-free per-user aggregate of erased assistant answers remains until account deletion, preserving the existing allowance calculation. It contains no chart/conversation/message IDs, question text or birth information. This is compatibility accounting, not a new billing ledger.

All changes use authenticated, CSRF-protected POST requests; GET requests do not delete data. Browser pages display the current revision so stale/simultaneous submissions can be rejected rather than intermixed. No active conversation may be rebound to another chart through a follow-up parameter.

## Retention limitations

No automatic retention TTL is introduced. Stored conversations remain until the user deletes them or their account is removed under existing cascades. This phase does not introduce a backup purge system or guarantee deletion from existing database backups. Existing provider retention settings for the legacy path remain as before; the agent adapters already use `store=False`, which must not be described as a guarantee about every provider infrastructure/abuse-monitoring retention policy. Operational backup/provider retention must be reviewed before production rollout.

Pending requests are represented by a request ID and revision. Normal provider failures release the active slot; an interrupted worker can leave a pending slot until the owner explicitly resets memory/history, invalidating that request. No automatic stale-request replay is attempted because its provider outcome may be unknown. Reusing the same request ID never intentionally triggers another answer generation. Billing/credit refunds and distributed ledgers remain P7.

## Deployment and rollback

The additive migration must be reviewed and applied by the deployment process before using the updated models. Automated tests apply it only to an isolated test database; this implementation does not run `migrate` against application data. Existing records remain memory-disabled. The existing `ASTROGPT_AGENT_ENABLED` flag preserves legacy one-shot generation; bounded contextual agent behavior is available when it is enabled. Disable the flag to stop contextual agent generation, and disable/reset stored memory per conversation if desired. Disabling a feature flag does not erase stored records.

No P6 answer-quality pipeline, P7 ledger or global conversational profile is delivered here. See the phase test report for tested behavior and remaining limitations.
