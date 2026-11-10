# P6 plan: verifiable answer composition and locked evaluation

P6 only, authorized assuming P5 approval. Branch `feature/evidence-quality-p6`; base/current HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. Preserve prior uncommitted work. No P7 ledger, application database migrations, paid API calls or invented human evaluation results.

## Design

- Add `astrology/synthesis/verified_answer.py`: bounded claim catalog built from authorized P2/P4 envelopes; exact-value claims with tool/JSON-path provenance for positions, house lords, Dasha intervals, BAV/SAV, sampled transit segments, rules and source citations. Scores remain heuristic; native precision and coverage are preserved. No calculation rewrite.
- Compose natural short paragraphs from verified fact slots and server-owned connective/guidance phrases selected by a structured model draft. No arbitrary numerical prose, invented source/remedy or LLM rule decision is publishable. This intentionally bounded first P6 design favors auditable fluent composition over unconstrained prose; human preference remains to be measured.
- Add `astrology/validation/claim_validator.py`: validate claim identities/value equality and scope, draft structure, supported citations/remedies, and final output after deterministic insertion/post-processing. Re-render or block bad drafts; never label a failed result validated. Factual lookups bypass synthesis calls and remain short. Existing reference-only mocked provider finals remain compatible through a verified server fallback.
- Integrate optional structured draft in the existing agent provider/orchestrator under existing round/token limits. No separate paid repair loop. Preserve the detailed evidence report as an optional audit/debug artifact and existing legacy feature flag.
- Tighten legacy final post-remedy validation/cache handling: reject failed cache entries and do not cache failed post-processed output. Clearly distinguish the legacy structural checker from new agent claim-to-tool assurance; do not retrospectively call legacy outputs mathematically validated.
- Add a locked evaluation fixture with >=30 primary questions plus follow-ups, adversarial/conflict/failure cases and explicit scenario expectations. SHA-256 lock prevents silent benchmark changes. Add offline evaluation runners/adapters, blinded export/scoring and separate accuracy/privacy/preference/latency/token/cost reports. Custom GPT is optional qualitative context, never a correctness oracle.
- Add offline P6 tests plus documentation/test report. Existing calculations, rules, schemas, privacy/authorization and limits remain.

## Publication and grounding contract

A fact catalog entry carries a stable ID, source tool/evidence ID/path, exact canonical value, supported precision and server-rendered sentence. Draft paragraphs select fact IDs and assert their canonical values; server-owned narrative IDs supply nonfactual transitions/practical guidance. Unknown/mismatched claims, source IDs, numerical assertions, remedies and arbitrary prose are rejected. All final replacements must pass a second validation against the expected composition before publication. Raw retrieved text remains quoted/untrusted support, never a chart calculation or independent confirmation.

Substantive answers disclose preliminary traditional interpretation, limited confidence and non-established predictive validity. Shared inputs/rule-score overlap and conflicting evidence are made explicit. Missing methodology remains a limitation, not invented confirmation; exact muhurta remains preliminary. Latest-user correction framing is labeled separately from verified calculations. Short focused follow-ups avoid the full original reading.

## Evaluation and honest gate

Lock representative cases before implementation. Automated tests use synthetic fixtures and real existing helpers where relevant, no live providers/production records. Run the current 211-test baseline before production changes and full discovery after. Separate mock/unit metrics from real comparative evaluation.

Human preferences require actual independent blinded scores; none are available initially. Generate a scoring packet and private unblinding key from supplied response artifacts, never manufacture votes. Record missing human scores as pending, not ties or wins. The proposed >=60% preference target is unapproved pilot configuration, not evidence of astrological effectiveness. Live cost/latency comparisons require separately approved runs and agreed bounds. Therefore implementation/automated checks may pass while the full P6 rollout gate remains BLOCKED pending human evaluation and accepted performance limits. Do not start P7.

## Test map

P6-01 wrong Dasha exact-value mismatch; P6-02 wrong SAV/transit/position values and unsupported ingress precision; P6-03 D1/D10 conflicts shown; P6-04 distinct intent-responsive answers on same chart; P6-05 citation IDs/metadata only from retrieval; P6-06 concise focused follow-ups; P6-07 short factual lookup; P6-08 explicit past/future scopes and conditional language; P6-09 revalidation after remedy/citation/correction replacements and failed-cache rejection; P6-10 blinded human schema, incomplete evidence handling, independent objective/performance/cost metrics. Re-run P2–P5 authorization/privacy regressions.

## Rollback and limits

Existing feature flag defaults off; disabling returns legacy generation with its stricter failed-cache safety check. No new migration/dependency. Model quality, live corpus coverage, human preference, mathematical external oracle certification and currency/latency limits are not assumed verified. Stop after report; report the human gate honestly as pending if no scores exist.
