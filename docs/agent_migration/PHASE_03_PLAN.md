# P3 implementation plan

Scope: P3 only, authorized assuming P2 approval. Branch `feature/bounded-agent-p3`, base commit `2312a4274ceb566ddc0d9f011516d60b459233c0`. Existing uncommitted work is preserved.

## Design and file map

- `astrology/agent/policy.py`: deterministic classification and explicit date windows; narrow factual requests, minimum career evidence, scoped MD/AD transit follow-up.
- `astrology/agent/orchestrator.py`: trusted principal/chart, fixed P2 dispatcher, deduplication, evidence references, reasoned optional calls, bounded rounds/calls/bytes/horizon/tokens/time and partial results.
- `astrology/agent/provider.py`: injectable provider protocol and OpenAI Responses adapter, no retrieval or executable tools, no hidden retries. Model output is untrusted; final output selects existing evidence references, never supplies publishable calculated values.
- `astrology/agent/rendering.py`: server-rendered factual extracts and preliminary evidence report; no unvalidated model prose published. Full fluent synthesis/claim validation remains P6.
- `chat/agent_service.py`, `chat/views.py`, `astro_site/settings.py`: disabled-by-default feature flag; retain legacy call path; reject unauthorized chart before conversation creation. Do not silently fall back to a second paid pipeline after failure.
- `astrology/test_agent.py`: offline mocked orchestration, real P2 authorization/integration and legacy route checks.

## Contracts and safety

The orchestrator accepts a trusted authenticated Django user and chart ID, question, explicit reference date and immutable server budgets. Returns answer/model/token counts plus status, evidence, trace, stop reason and usage. Provider requests can only propose one of the six P2 tools with JSON arguments and a nonempty rationale. Chart identity is server-bound; foreign IDs rejected. Additional windows must remain inside planned scope. Factual lookup cannot broaden methodology. Tool payloads and questions are data, never executable instructions. Response rendering resolves only validated evidence references; arbitrary model prose/calculations are discarded.

Initial limits: 4 model rounds, 24 tool calls, 512 KiB cumulative tool output, 1097-day calendar envelope, 100,000 conservatively reserved model tokens, 60-second consultation deadline and 15-second tool deadline. Provider HTTP calls have timeout and zero retries. Local synchronous calculations cannot be forcibly preempted safely; deadline is checked before/after each read-only call, and no further work starts after expiry. P2 independently limits individual ranges/samples. This is a documented cooperative time limit, not a process-isolation guarantee.

## Test matrix

| ID | Scenario | Expected |
|---|---|---|
| P3-01 | Tenth lord | D1 only, no provider/RAG |
| P3-02 | General career | D1/D10, current Vimshottari and rules, recorded reasons |
| P3-03 | Promotion timing | Scoped periods; MD/AD lords' transits clipped at each boundary; alternatives retained |
| P3-04 | Conflicting evidence | Provider may request D9/Yogini/Chara with rationale |
| P3-05 | Jupiter in Leo | Jupiter transit only, explicit scope |
| P3-06 | Current Dasha | Deterministic one-day schedule query only |
| P3-07 | Jan versus July 2027 | Two independent requested windows evaluated |
| P3-08 | Unsupported level | Explicit unsupported evidence, never guessed |
| P3-09 | Repeated call/round, token, byte, horizon limits | Deduplication or traceable partial stop |
| P3-10 | Timeout/provider failure/empty evidence | Useful partial result, no retry/fallback paid call |
| P3-11 | Injected payload / foreign chart / unlisted tool | Rejected, no action or leakage |

Run the existing 100-test suite before implementation and all tests afterward. Tests use synthetic rows in Django's test database, network blocked, mocked provider; no live smoke test authorized. Distinguish behavioral regression from independently verified astronomical correctness (not established).

## Risks, phase boundaries and rollback

English deterministic scope parser is intentionally limited: ambiguous/unsupported dates must request clarification rather than guess. Legacy boundary/missing-data/ranking limitations remain labeled in P2 outputs. No P4 RAG, P5 conversational memory, P6 production-quality fluent synthesis or P7 billing ledger is added. The enabled path produces preliminary evidence reports, not release-ready forecasts. Existing credit-count architecture is not certified; failed runs create no assistant message. Disable `ASTROGPT_AGENT_ENABLED` and restart to restore legacy generation. No migrations or calculation changes. Deliver test report and stop for approval.
