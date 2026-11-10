# P6 evidence verification and publication

Implemented on `feature/evidence-quality-p6`, starting from HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. P6 only; no P7, schema migration, dependency or calculation change. Earlier uncommitted work is preserved. This extends the P3/P4/P5 contracts; the agent feature flag stays off by default.

## Calculation claims versus interpretation

`astrology/synthesis/fact_catalog.py:build_catalog` creates a bounded catalog from authorized, schema-validated tool envelopes. Each atom has an ID, kind, evidence ID, JSON-pointer bindings, canonical JSON value, server-rendered text, scope and method. Supported kinds are natal lord/position, Dasha, transit, BAV/SAV, candidate, triggered rule, conflict and retrieved citation. Maximum 128 atoms; 16 slots are reserved for conflicts/citations. Long source lists remain available in the existing bounded evidence trace even when not all are displayed. This is a bounded consultation summary, not a full ephemeris export.

`verify_atom` resolves the bindings again and compares exact canonical values. This proves agreement with tool results, **not independent astronomical correctness**. Existing precision, inherited calculation limitations and P2 boundary conventions remain unchanged. Planetary longitude stays in degrees. Native Dasha periods are calendar dates with source end exclusive; the requested range is inclusive and intersecting full source periods may extend outside it. Transit segments use the existing daily noon-UTC samples; no exact ingress time is asserted. Missing SAV/BAV remains unavailable rather than zero. Timing scores are heuristic support, not probabilities.

Rule conclusions come only from the deterministic engine. Their existing explanatory text is labeled a triggered traditional rule, not independently recomputed or scientifically verified. Shared chart/Dasha inputs and score overlap are explicitly disclosed. `build_catalog` retains actual conflict descriptions rather than inventing agreement or treating every conflict as D1 versus D10. Retrieved excerpts are separately labeled source viewpoints, with actual evidence IDs and metadata; book/page gaps stay unavailable. Numbers inside quoted source excerpts and user corrections are not certified natal calculations.

## Controlled composition

`astrology/validation/claim_validator.py:final_schema` defines strict structured output:

```json
{
  "evidence_ids": ["E1"],
  "draft": {
    "paragraphs": [{"segments": [
      {"kind": "narrative", "ref": "direct", "value": null},
      {"kind": "fact", "ref": "F<catalog ID>", "value": "<exact canonical catalog JSON string>"}
    ]}]
  }
}
```

`draft:null` requests the deterministic fallback. Existing offline provider mocks returning only evidence IDs remain supported. Drafts allow 1–6 paragraphs, 1–12 segments per paragraph and 24 segments total. Unknown IDs, wrong numeric/date values, repeated references, malformed types, free prose and invented remedies/citations fail draft validation. The provider cannot supply a new factual sentence. It selects and orders source-bound facts and server-owned narrative IDs from the current request. `provider.py:OpenAIProvider` uses Responses `text.format` JSON Schema; no additional paid repair round is introduced. API shape was checked against the installed SDK and [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs); live model/schema compatibility was not tested.

`verified_answer.py:publish_answer` adds minimum requested evidence even if the model selects less, includes available conflicts/citations, and groups facts into paragraphs. Factual lookups avoid the LLM and broad forecast. Serious answers retain limited-confidence language and the distinction between traditional interpretation and scientifically established prediction. Remedies are not invented. Timing/launch answers carry the required preliminary muhurta limitation when exact muhurta is unavailable. Current English source-owned prose is intentionally constrained; arbitrary fluent prose, automatic translation and human preference improvements are not claimed.

Bad drafts are rejected and replaced with the verified server fallback. The orchestrator reports `partial` if an otherwise successful consultation needed this fallback. An unchanged fallback can pass final validation; `draft_validation` retains the rejected issues. No retry spends extra model tokens. Provider and investigation failures use the existing bounded partial-answer behavior.

## Final publication boundary

`validate_final` checks every selected atom again, exact equality with the assembled verified answer after the optional postprocessor, and a 24 KiB UTF-8 final-text limit. A changed numerical assertion, remedy, citation or other extra prose fails. No failed final text is returned for publication. User corrections and source warnings enter the assembled text before this check and remain explicitly attributed.

Agent results add:

| Field | Meaning |
|---|---|
| `validation` | Final check: required structured validation fields plus stage |
| `draft_validation` | Draft check, or null if no model draft |
| `claims` | Selected source-bound atoms, including actual citation provenance |

Validation includes `passed`, `score`, `issues`, `missing_sections`, `generic_phrases_detected`, `unsupported_claims`, `repair_instruction`, and `stage`. Scores here describe validation, not astrological likelihood. A publication trace event records the final pass/fail. `chat/consultation_service.py` rejects a supplied failed or malformed validation result before publishing/storing an assistant message; ownership/revision/epoch checks still apply. Browser markup conversion remains the existing formatter, covered by previous security tests; it is not another mathematical calculator.

`chat/publication.py` separately fixes the legacy pipeline: final structural validation runs **after** stripping validation notes and deterministic remedy replacement, for regular and periodic readings. Failed results have status `error`, are not stored as assistant answers by existing views/services, and are not cached. Legacy cache entries require the new publication marker, a passing result and fresh structural revalidation; old/failed entries are discarded. Cached prompts are excluded. The legacy check is explicitly labeled `legacy_structural_not_tool_claim_validation`: it does not provide the new closed-slot mathematical guarantee. No claim is made that arbitrary legacy prose is now factually certified. Stricter final checks may block previously published legacy answers, including periodic readings whose payload lacks required evidence. The legacy feature-flag path remains available.

No new generic logs contain questions, birth inputs, source excerpts or raw repair errors. Existing provider payloads still include authorized evidence under the existing privacy policy. No cross-user data access, new agent tool, database write tool or background task is introduced.

## Status and limits

| Component | Status |
|---|---|
| Source-bound numerical/date claims, final validation, deterministic fallback | IMPLEMENTED; offline-tested |
| Narrow factual position/BAV/SAV and named-period Dasha routing | IMPLEMENTED; wraps existing tools |
| Locked evaluation and blinded artifact/scoring harness | IMPLEMENTED; offline-tested |
| Fluency/less repetition | PARTIALLY IMPLEMENTED through controlled paragraphs and concise follow-ups; human quality unverified |
| Legacy arbitrary prose mathematical proof | NOT IMPLEMENTED; structural validation only |
| Independent astronomical oracles beyond existing regression coverage | NOT ADDED; separate reference verification still needed |
| Actual blinded legacy/agent human comparison | PENDING; no votes fabricated |
| Approved human threshold and live performance comparison | PENDING; full rollout gate BLOCKED |
| P7 billing or credit semantics | NOT STARTED |
