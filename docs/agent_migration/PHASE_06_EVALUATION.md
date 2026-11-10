# P6 locked evaluation protocol

## Fixed sample and purpose

The versioned fixture is `astrology/evaluation/fixtures/p6_cases_v1.json`: **36 primary questions and 12 follow-ups**, locked before implementation. Both the code constant and `.sha256` sidecar require SHA-256 `03049e821e46f75027ef84b855d0d619c7a899f98927f577e7e38e500ffd9b9e`. Do not adjust questions to improve a score. Changes require a reviewed, new fixture version and a fresh comparison. This sample evaluates product behavior and grounding, not astrology's predictive effectiveness.

| Cases | Coverage |
|---|---|
| Q01–Q06 | D1/D10 rulers/positions/longitude, SAV/BAV factual lookups |
| Q07–Q09 | Current/future Vimshottari and Yogini facts |
| Q10–Q13 | Career/business assessment and contrary D1/D10 signals |
| Q14–Q17 | Promotion/job change, next year and month/range comparisons |
| Q18–Q20 | Historical scope and focused Jupiter/Saturn transits |
| Q21–Q24 | Missing SAV, RAG, Dasha and natal evidence |
| Q25–Q29 | Unsupported level, excessive horizon, cross-user access, provider failure and injection |
| Q30–Q36 | Business launch/muhurta caveat, resignation with conflict, missing facts and past comparisons |
| F01–F12 | Focused D10, late-year comparison, transit context, corrections, mixed evidence, other person, current Dasha, third-window clarification, private testing, reset and fresh-chart boundaries |

`astrology/test_quality.py:QualityTests.test_locked_48_cases_publish_only_tool_bound_claims` runs the agent offline against a synthetic saved chart and scenario-specific missing/contrary evidence, mocked retrieval/provider behavior and consent-shaped bounded context. It verifies every emitted mathematical atom against its tool source and cross-user output isolation. Malicious retrieved text remains a labeled quotation, never a command or a verified numerical claim. Existing P3/P4/P5 tests also exercise dispatcher budgets, authorization, live-context races and deletion. This regression run is **not a blinded comparison** and is not an independent ephemeris oracle. Human quality, latency and cost require the separate process below.

## Collect comparable artifacts

Use synthetic or explicitly consented chart data. Keep chart facts, settings, reference dates, prior-turn inputs and questions identical between systems; the new agent's follow-ups should receive its own preceding answers and the legacy benchmark should receive equivalent question context through an explicit trusted runner. If legacy cannot support that context, record the limitation. Include failure results rather than dropping cases. Capture model/settings/code versions and source manifest in a private run manifest; do not put birth inputs in general telemetry. A custom GPT may be an additional qualitative comparator only, never a calculation oracle.

`harness.collect_responses({'legacy': legacy_runner, 'agent': agent_runner})` accepts trusted local callables. It does not import a runner from a string, invoke providers by default, or change database rows. Callers must explicitly approve any live costs before supplying live runners. Use an isolated test database and chart owners. Caller-owned adapters should preserve P5 follow-up context; the generic harness does not create conversations or consent automatically.

One response record has exactly these keys:

```json
{
  "case_id": "Q01",
  "system": "agent",
  "answer": "The actual supplied response",
  "metrics": {
    "latency_ms": 123,
    "input_tokens": null,
    "output_tokens": null,
    "cost_amount": null,
    "currency": null,
    "measurement": "unverified_runner"
  },
  "objective": {
    "critical_calculation_errors": null,
    "privacy_errors": null,
    "validation_passed": null
  }
}
```

`system` is `legacy` or `agent`. Missing/unreviewed values stay null, never fabricated zero. `collect_responses` measures elapsed time and reads supplied usage/cost/objective fields. Critical errors mean published invented or wrong calculation values/dates, not an unfavorable traditional interpretation. Source agreement and independent calculation correctness must be audited separately. Privacy errors mean unauthorized chart/conversation disclosure. Set counters only after actual checks; the harness cannot establish truth from unaudited caller counters. Do not label a mock as `live_verified`. Prices are not guessed from tokens; supply audited actual cost and a supported explicit currency. Metrics remain separate from quality/preference. Each answer is limited to 32 KiB and the set to 96 unique records.

## Blind human review

```powershell
.\.venv\Scripts\python.exe manage.py p6_evaluate --responses <private-responses.json> --output-dir <fresh-private-directory> --seed <private-random-seed>
```

This artifact-only command makes no provider calls or database writes. It accepts response input up to 8 MiB, scores up to 1 MiB and policy up to 4 KiB. It refuses to overwrite prior artifacts. Keep the directory access-controlled: answers can contain sensitive information even though input schemas exclude raw prompts/birth fields. No evaluation files are served through a web route or placed in static assets.

Outputs:

- `blind_packet.json`: anonymous A/B answers, question, parent question and same-system parent answer for follow-up context. System labels, timings, tokens, costs, seed and unblinding mappings are excluded. Writing style may still suggest a system; metadata blinding is not a guarantee against recognition.
- `PRIVATE_unblinding_key.json`: local mapping for the evaluator, **never sent to graders**.
- `evaluation_report.json`: objective counters, human preference/quality/error summaries, separate performance totals/medians and gate reasons. No answer text or birth fields.

Independent human graders read every pair in randomized A/B order. Rate each side from 1 to 5 for accuracy, grounding, responsiveness, clarity and concision. Record factual errors separately and prefer A, B or tie. Check facts against the private authoritative tool evidence/reference ledger, not prose from the other system. Record conflicts, date responsiveness, unsupported citations/remedies and whether follow-ups repeat the whole reading. Use assessor pseudonyms rather than personal information. LLM judgments may assist diagnostics but must not enter `source:human` records.

Each score has exactly:

```json
{
  "pair_id": "<actual packet pair ID>",
  "assessor": "<human assessor pseudonym>",
  "source": "human",
  "preference": "tie",
  "quality": {
    "A": {"accuracy": 3, "grounding": 3, "responsiveness": 3, "clarity": 3, "concision": 3},
    "B": {"accuracy": 3, "grounding": 3, "responsiveness": 3, "clarity": 3, "concision": 3}
  },
  "errors": {"A": 0, "B": 0}
}
```

These numbers illustrate the schema; **they are not actual scores**. Do not submit the example. Duplicate assessor/pair votes, unknown pairs, non-human source markers and malformed ratings are rejected. Human identity/independence is a procedural attestation, not automatically provable by a JSON field. Prefer a consistent assessor panel so unequal vote counts do not dominate the aggregate; the report counts non-tied votes, not unique case wins.

Re-run into another fresh directory with the same private seed, `--human-scores <actual-scores.json>` and optionally `--policy <previously-agreed-policy.json>`. A policy can contain `preference_target`, `threshold_agreed`, `latency_ratio_limit`, `cost_ratio_limit`. Supplying a file records an agreement already made; it does not create user approval. No such agreement or live run was made during implementation.

## Gate semantics

Full gate requires all 48 paired cases, known agent automatic safety outcomes with zero critical errors/privacy failures/failed final validation, complete actual human review with a non-tied preference sample, agreed preference target, accepted performance bounds and verified live measurements/currency. Human-observed errors require review. Unknowns block; actual critical failures fail. Performance uses complete paired coverage and median new/legacy ratios; approved limits must be positive, and a zero/unknown legacy denominator remains unverified. Do not aggregate mixed currencies as if interchangeable.

The proposed 0.60 non-tied preference target remains an **unapproved pilot target**, not evidence of effectiveness. Offline mock token/time records cannot satisfy live cost/latency gates. Missing votes are pending, not ties. No actual blinded comparison, source-corpus inspection, custom-GPT benchmark or paid provider run occurred in P6 implementation. Current full gate remains **BLOCKED** for those external evaluation requirements. Do not start P7 on the basis of passing unit tests alone.
