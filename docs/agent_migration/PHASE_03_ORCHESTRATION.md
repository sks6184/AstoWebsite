# P3 bounded deterministic-evidence agent

## Status and activation

Implemented behind `ASTROGPT_AGENT_ENABLED`, default **false**. The user must approve later phases separately. No hosted retrieval, memory, billing ledger or fluent prediction publication is introduced. Enabled requests return English preliminary evidence reports. Factual lookups return direct deterministic results without a provider call. Non-English agent requests return an explicit limitation.

Set the environment flag to `true` and restart the Django worker to opt in. Set it to `false` and restart to roll back. No migration or dependency installation is required. Existing one-shot generation remains in `chat/llm_engine.py`; routing is `chat/agent_service.py::generate_question_answer`. The legacy generator is not automatically retried after agent failure.

## Entry point and result

```python
from datetime import date
from astrology.agent.orchestrator import run_consultation, Limits

result = run_consultation(
    authenticated_user, authorized_chart_id,
    "Compare career timing Jan vs July 2027",
    today=date(2026, 11, 7),
    provider=offline_scripted_provider,  # omit only for an explicitly enabled live call
    limits=Limits(),
)
```

Result fields: `status` (`ok`, `partial`, `error`), `answer` (text compatible with the existing escaping Markdown formatter), `model`, `prompt_tokens`, `completion_tokens`, `evidence`, `trace`, `usage`, `stop_reason`. Evidence is keyed by stable per-run IDs (`E1`, etc.). Each entry contains tool name, bound arguments, rationale, and the unchanged versioned P2 envelope. IDs are local to a request, not persistent database identifiers. Trace and structured evidence are returned to the caller and are not persisted or logged by this phase. The existing view saves answer text/token counts only.

`partial` can mean unavailable evidence, an explicitly unsupported calculation, or a budget/provider stop after useful evidence. P2 boundary warnings are retained; their presence alone must not be mistaken for a mathematically complete or independently certified prediction. A tool envelope is schema-validated before use. Errors expose sanitized reasons, never exception details or secrets.

## Methodology

`astrology/agent/policy.py::make_plan` is a bounded English policy parser, not a general natural-language date interpreter. It identifies factual house-ruler/Dasha/transit questions, career assessments and career/business timing questions.

| Request | Minimum calls |
|---|---|
| Tenth-house ruler | D1 facts only |
| Current Dasha | Vimshottari MD/AD at the server reference date only |
| Named planet transit, including Jupiter in Leo | That planet's daily-sampled sign segments only; requested sign highlighted |
| Career/business assessment | D1/D10, reference-date Vimshottari, deterministic topic rules |
| Career/business timing | D1/D10, Vimshottari per requested window, MD/AD-lord transits for each intersecting period, BAV/SAV, independent candidate request per window, topic rules as of window start |

Timing without a date scans 1095 days forward (at most approximately three years); a whole year, named month(s) with a common year, or up to two ISO dates is supported. `Jan vs July 2027` produces two separate windows. `Jan to November 2027` produces one inclusive interval. Unsupported relative phrases such as `next month`, ambiguous years, invalid dates and excessive horizons require scope clarification rather than silent date selection. Unknown assessment topics also require clarification. Default scopes are explicit in the returned plan/answer. There is no conversation memory: a standalone transit follow-up uses its own supplied dates/default scope, not an inferred earlier conversation window (P5).

`Consultation.minimal_evidence` resolves native Vimshottari `[start,end)` periods, intersects them with inclusive requested dates, subtracts one day from exclusive source ends, and requests only the active pair's distinct lords. Ketu–Venus followed by Venus–Venus therefore requests Ketu/Venus up to the boundary, then Venus alone. No current-date lord substitutes for a future period. Existing P2 transits include legacy SAV context; the separate BAV/SAV request follows the scoped transit requests. This phase changes orchestration, not those calculations or their precision.

Rules are evaluated **as of the start of each requested window**; this is disclosed in the rationale and is not claimed as exhaustive rule evaluation at every future date. Candidate ranking remains the P2 legacy heuristic with its preselection/missing-data limitations. Both comparison windows are evaluated independently before optional investigation. Scores are not probabilities or a requirement to choose the top candidate.

## Adaptive tool calls and publication boundary

`Consultation.investigate` provides accumulated evidence, scope, prior trace and remaining calls to an injectable provider. The provider may propose additional supported Vargas, Chara/Yogini, narrower timing candidates, transits or Ashtakavarga evidence, each with a nonempty rationale. Server policy checks chart identity, date containment, topic and supported chart divisions. It does not permit a factual lookup to become an unrestricted forecast. Every optional call still passes the fixed six-tool P2 registry and its authorization/schema limits. The model cannot change budgets, principal, tools, source code, files or database rows.

The provider protocol has `name`, `request_size(payload)` and `complete(payload, max_output_tokens=..., timeout=...)`. Reply shape:

```json
{
  "calls": [{"name": "get_chart_facts", "arguments": {"charts": ["d9"]}, "reason": "Investigate conflicting D1/D10 evidence."}],
  "final": null,
  "input_tokens": 100,
  "output_tokens": 20
}
```

Finish with empty calls and `final: {"evidence_ids": ["E1", "E4"]}`. All references must exist. The server always renders the minimum evidence as well, so selection cannot hide a requested comparison window or contrary evidence. Free-form model prose, model-supplied numbers and non-reference final objects are not published. `rendering.py::render_evidence` builds a preliminary report from the actual tool data. Comprehensive claim-level fluent-answer validation is P6, not claimed here.

`provider.py::OpenAIProvider` uses the installed Responses SDK and six function schemas, adds the required rationale, disables retries and provider storage, and closes the client. Each round is a fresh bounded request with the local evidence/trace, avoiding provider-held conversation state. Reference: [official OpenAI function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling). No file-search, Python, shell, browser, filesystem or database-write tool is advertised.

Questions, stored facts and provider replies are untrusted data. Injection may influence proposed requests but cannot expand server authority. Rejected actions terminate with partial evidence rather than execute. Text passes through `chat/templatetags/chat_formatting.py::astro_answer`, which escapes markup. Chart ownership is checked before planning, inside every P2 invocation including cache hits, and before publication; ownership loss clears accumulated evidence.

## Limits and failure behavior

| Budget | Default | Enforcement |
|---|---:|---|
| LLM rounds | 4 | Stop before another request |
| Unique tool invocations | 24 | Canonical JSON-key dedup; no further dispatch |
| Retained cumulative tool output | 512 KiB | Validate/measure envelope; discard overflow and stop |
| Calendar envelope | 1097 inclusive days | Validate before tool execution; optional dates contained in planned windows |
| Cumulative model tokens | 100,000 | Reserve complete UTF-8 payload/schema/instruction byte count plus overhead and output allowance before each request; check reported usage too |
| Per-round output tokens | 1200 | Provider parameter plus reported-usage check |
| Consultation elapsed time | 60 seconds | Check before/after calls and each round |
| Local tool elapsed time | 15 seconds | Cooperative deadline after the synchronous read-only helper returns |
| Provider HTTP timeout | Up to 20 seconds | Also capped by remaining consultation time; zero retries |
| Provider reply | 32 KiB | Reject oversized parsed reply |

P2 additionally enforces per-request/response bytes, supported calendar years, samples, data schemas and chart size. UTF-8 reservations conservatively bound text tokens; they are operational limits, not a verified currency-cost ledger. Unexpected provider usage stops further work. A duplicate-only round stops immediately; mixed rounds remain bounded by rounds and calls.

**Time limitation:** local synchronous Python calculations cannot be forcibly interrupted by this wrapper. A slow helper can overrun its deadline before the result is discarded. The HTTP timeout is an SDK transport timeout; this is not hard process isolation or an absolute end-to-end wall-clock SLA. No worker thread continues on a detached ORM connection. Hard cancellation/worker isolation is not claimed.

Provider failure or timeout returns useful collected evidence with an explicit stop reason; no second paid legacy request occurs. Empty schedules and unsupported levels retain explicit limitations. An entirely failed run creates no assistant message in the view. A useful partial report still follows existing message-count credit behavior: transactional credit refunds and billing guarantees are P7 and remain unimplemented.

## Verification and scope boundaries

Tests use synthetic charts, mocked providers and blocked network. They verify behavior, authorization, bounds, request ordering and compatibility; they are not independent astronomy certification or a live provider-quality evaluation. See `PHASE_03_TEST_REPORT.md` for actual results.

No new RAG ingestion/retrieval, external corpus audit, memory, summaries, billing ledger, launch-quality answer validator, deployments or live paid smoke test. Existing calculations, YAML rules, dependencies, schema and legacy LLM implementation are preserved.
