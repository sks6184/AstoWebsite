# AstroGPT — Agentic Restructuring Master Plan

**Version:** 1.0  
**Date:** 7 November 2026  
**Status:** Implementation roadmap for Codex; no code changes authorized by this document alone  
**Reference:** `ASTROGPT_ARCHITECTURE.md` (AS-IS snapshot dated 7 November 2026)

## 1. Product goal

Move AstroGPT from a mostly one-shot, rules-first astrology answer generator to a **bounded conversational astrology agent** that can:

- Understand a question and its scope (factual / interpretive / predictive; topic; date range; follow-up context).
- Ask deterministic Python tools for chart, Dasha, transit, Ashtakavarga, yoga and rule evidence as needed.
- Retrieve relevant astrology literature already held in the OpenAI vector store (including the user's Markdown-derived content); verify what is actually indexed before claiming coverage.
- Re-investigate when evidence is missing or contradictory rather than always accepting a pre-ranked best period.
- Maintain conversational continuity for the same saved birth chart, with user-controlled history and privacy.
- Return fluent, useful answers, distinguishing astronomical calculations, traditional interpretation and predictive uncertainty.
- Operate within measurable per-question limits on model tokens, tool calls, time and cost.

**Target business model:** standalone B2C service, potentially distributed by astrologer partners (B2B2C). Partner billing and attribution come after technical validation.

**Important:** Accurate *calculation* is an engineering goal; astrological *prediction* is not scientifically established as a reliable way to forecast personal events. The product must not present its internal heuristic scores as probabilities or make absolute guarantees.

## 2. Evidence from the current codebase

The AS-IS document reports:

- Django server-rendered monolith with `accounts/`, `charts/`, `chat/`, `payments/`, and a Python `astrology/` domain package.
- Swiss Ephemeris-based natal and divisional chart calculations; Vimshottari, Yogini, Chara, transit, BAV/SAV and interpretive rule components.
- Seven YAML rule files (223 rule entries), plus Python rule evaluators.
- Current production Q&A is synchronous and one-shot; conversation history is saved but is **not** passed into later model calls.
- Live interpretation uses OpenAI Responses with hosted `file_search` where configured; local indexing and knowledge-corpus inspection were not verified.
- Several domain modules import `chat` helpers and vice versa. Timing systems and Dasha boundary semantics are not fully unified.
- A ranking stage selects candidate windows before LLM synthesis. The LLM cannot currently invoke additional calculations in a tool loop.
- Credit enforcement is based on assistant-message counts rather than a transactional usage ledger; errors may consume credit.
- Final validation is not an unconditional publication gate, and the separate periodic/report paths do not use all event-question checks.

These are **source-inspection observations**, not assertions that running deployments or external vector-store contents were independently tested.

## 3. Decisions already agreed

1. **Modular monolith first.** Keep Django and local Python calculation functions; do not introduce microservices by default.
2. **Adaptive question policy.** Tool selection is determined by question type, topic, requested time horizon, existing evidence, and remaining budget—not merely `career -> D10` for every question.
3. **Minimum methodological evidence for substantive predictions.** Example: a *predictive career* consultation normally includes D1, D10, relevant Vimshottari, and timing transits when needed. A factual question such as “Who rules my tenth house?” needs only D1.
4. **Additional investigation is conditional.** D9, Jaimini, Yogini, specialized vargas or extra time windows are requested for a reason, not indiscriminately. The agent records the reason.
5. **Calculations are deterministic.** The LLM may request or interpret; it may not invent planetary data, Dasha boundaries, SAV points or unsupported methods.
6. **Preserve existing engine and legacy answer path** until a gated replacement is demonstrably better.
7. **RAG is a tool, not the agent.** The agent orchestrates calculation tools and targeted retrieval; book passages are untrusted reference material, not executable instructions.
8. **Memory is bounded and chart-scoped.** Recent messages + concise summaries; no accidental leakage between users/charts.
9. **Every phase stops for explicit approval.** Finishing P1 never authorizes P2. No automatic progression even if all tests pass.

## 4. Global rules for Codex (apply to every phase)

- **Read this file and `ASTROGPT_ARCHITECTURE.md` first.** Inspect real code paths; do not assume file/function names from examples exist.
- **Work on exactly one phase** specified by the user. Do not begin any later phase, even if obvious or easy.
- Work in an isolated feature branch (suggested `feature/agentic-astrogpt`); record branch/commit hashes. Do not overwrite uncommitted changes or alter secrets.
- Before changes, write or update `docs/agent_migration/PHASE_XX_PLAN.md` with scope, file map, contracts, risks, rollback, and test list.
- Tests must not call paid OpenAI APIs, GeoNames, live payments or production databases. Mock external clients for CI; live tests require separate opt-in and budget.
- Preserve existing calculation outputs unless an independently verified defect is approved for correction. Snapshot tests are not correctness proofs.
- No production secret keys, `.env` contents, birth records, full prompts or personal chat transcripts in logs or reports.
- Use precise schema validation, explicit unsupported/error responses, and user/chart authorization on every exposed service.
- Run the phase-specific tests **and relevant existing regression tests**; report commands, pass/fail counts, skips, coverage limitations and unresolved defects.
- Keep a legacy feature-flag/rollback path until user acceptance in P8. Avoid big-bang migrations.
- Deliver `docs/agent_migration/PHASE_XX_TEST_REPORT.md` with evidence and a final **PASS / FAIL / BLOCKED** recommendation. **Stop and wait for user approval.** Do not claim PASS for tests not run.
- If a blocking design choice is unknown, document the alternatives and make the smallest reversible choice; do not silently implement speculative business rules.

### Required phase report template

```markdown
# Phase XX Test Report
- Branch / commit:
- Scope delivered:
- Changed files:
- Test commands actually run:
- Test matrix (ID | expected | actual | PASS/FAIL/BLOCKED):
- Prior failures vs newly introduced failures:
- Tests mocked vs live-verified:
- Coverage / unresolved risks:
- API calls and cost (should be $0 for automated tests):
- Rollback instructions:
- Phase gate: PASS / FAIL / BLOCKED
- Approval requested for next phase: YES (do not execute it)
```

## 5. Phase index and dependencies

| Phase | Deliverable | Exit gate |
|---|---|---|
| **P1** | Baseline + regression protection | Known calculations and current flows recorded and tests executed |
| **P2** | Typed deterministic tool interfaces | Agent-ready tools function offline with authorization and bounded outputs |
| **P3** | Bounded agent orchestrator | Multi-step career consultation invokes the right tools safely |
| **P4** | Targeted RAG + source grounding | Evidence retrieval is relevant, inspectable and cannot inject instructions |
| **P5** | Multi-turn conversations + memory | Follow-up questions retain scope while isolating users and charts |
| **P6** | Answer quality + factual validation | Evaluated against current system/custom-GPT style without fabrication |
| **P7** | Usage/cost/credit and resilience controls | Real usage is tracked and spending limits are enforced |
| **P8** | Pilot-ready UX, security, operations | End-to-end limited beta meets agreed release gates |
| **P9** | Commercial B2C/B2B2C rollout (later) | Payment, referral, settlements and business metrics verified |

**Sequence:** P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → [optional P9]. Each requires a phase report and explicit approval. A failure sends work back to the **same** phase.

---

## P1 — Baseline and regression protection

**Purpose:** Establish the current behavior and verified reference cases without prematurely refactoring calculation code.

**Implementation scope**
- Inventory actual entry points and existing test coverage; identify live production path versus disconnected/legacy modules.
- Capture representative **golden snapshots** of deterministic output, with calculation configuration, timezone and reference date.
- Identify independently verified test fixtures and label all unverified snapshots as *regression-only*.
- Add/organize isolated tests for chart mathematics, Dasha boundaries, transit/SAV, rule triggering, current answer flow and access control.
- Record existing defects separately, including Dasha end-date semantics, invalid chart selection, rule duplicates and current fallback-credit behavior.
- Do **not** change underlying astrology algorithms during this phase except a separately approved minimal testability fix.

| ID | Test scenario | Acceptance criterion |
|---|---|---|
| P1-01 | D1 known natal chart | Match independent reference where available; otherwise labeled snapshot |
| P1-02 | D9, D10 and varga sample | Chart output stable; independent fixture status explicit |
| P1-03 | Vimshottari MD/AD | Lords/dates match verified reference where available |
| P1-04 | Dasha boundary | Test just before, on, and after transition; identify current inclusive/exclusive inconsistencies |
| P1-05 | Yogini and Chara | Stable periods, with method/version annotated |
| P1-06 | Transit/retrograde timeline | Representative signs and ingress segments; reference resolution noted |
| P1-07 | BAV/SAV | Invariants and natal house mapping verified; no missing-data-to-zero substitution |
| P1-08 | YAML/Python rule evaluation | Stable trigger set and scores; identify duplicate outcomes |
| P1-09 | Existing career answer path | Mock model response; no paid API; proper persistence |
| P1-10 | Periodic reading path | Mock response; no paid API; renders correctly |
| P1-11 | Missing/invalid birth inputs | Existing documented behavior captured without invented calculations |
| P1-12 | Cross-user chart access | Denied; if failing in baseline, classify critical existing defect and flag for fixing before exposing agent tools |

**Gate P1:** All new tests run and are classified; no new regressions; unresolved existing failures explicitly tracked. Any unverified math remains unverified—not silently marked correct. Deliver `PHASE_01_PLAN.md`, fixtures/tests, `PHASE_01_TEST_REPORT.md`.

**Codex invocation:** `Implement P1 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md. Produce P1 tests and report, stop for approval. Do not start P2.`

---

## P2 — Reusable deterministic tool interfaces

**Purpose:** Wrap existing code in typed, testable, safe local tools. Do not rewrite the underlying calculations.

**Initial tool contracts (names proposed; adapt to actual modules):**

| Tool | Inputs | Structured outputs |
|---|---|---|
| `get_chart_facts` | authorized `chart_id`, requested charts e.g. D1/D9/D10 | chart system, calculated placements, units, method, warnings |
| `get_dasha_periods` | chart, system, date range, granularity | periods with exact supported precision, inclusivity convention, source/method |
| `get_transits` | chart, selected planets, start/end, resolution | positions or segments, reference-frame information, coverage |
| `get_ashtakavarga` | chart, selected planet/sign/house | BAV/SAV points and mapping, missing-data status |
| `evaluate_astrology_rules` | chart, category/question-specific evidence | matched rule IDs, reasons, conflicts, provenance (no fabricated probability) |
| `get_timing_candidates` | chart, topic, date range, evidence policy | ranked hypotheses with heuristic scores clearly labeled |

**All tool returns:** consistent versioned envelope `{status, data, warnings, method, provenance, error}`; schema-validated, size-limited and deterministic. The caller must not be able to retrieve another user's chart. No arbitrary Python execution, filesystem access or mutable database operations through the agent tool registry.

| ID | Test | Acceptance criterion |
|---|---|---|
| P2-01 | Each tool valid request | JSON-serializable, typed, stable structure |
| P2-02 | Invalid arguments | Explicit machine-readable validation error |
| P2-03 | Cross-user chart ID | Authorization failure, no data leakage |
| P2-04 | Unsupported method/level (e.g. Pratyantardasha if missing) | `unsupported`, not guessed data |
| P2-05 | Boundary/precision | Dasha and transit time conventions explicit |
| P2-06 | Large date range | Bounded response or clear range-limit error |
| P2-07 | Compare legacy computation | No unintended mathematical changes |
| P2-08 | Missing coordinates / partial chart | Incomplete evidence clearly flagged |
| P2-09 | Caching and invalidation | Chart/version/settings fingerprint prevents stale reuse |

**Gate P2:** All exposed tools callable through local tests with no LLM; safe authorization; documented schema and method semantics; no regressions. Deliver a `TOOL_CONTRACTS.md` and report.

**Codex invocation:** `Implement P2 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P1 is approved. Create deterministic tool contracts/wrappers and tests. Do not start P3.`

---

## P3 — Bounded agent orchestration and adaptive methodology

**Purpose:** Introduce a tool-calling agent that selects evidence based on **question type + topic + time horizon + available evidence**, while preserving a minimal methodology for *substantive* predictions.

**Behavioral policy:**
- Factual lookup: fetch the narrowest necessary evidence (e.g. tenth lord → D1 only).
- Interpretive assessment: fetch relevant natal and specialized chart evidence, with a short rationale.
- Predictive/timing question: retrieve minimal relevant natal, varga, Dasha and scoped transit evidence; optionally investigate conflicts with extra systems.
- Agent may request D9, Jaimini, Yogini, extra Vargas or windows only when it records a reason and budgets permit.
- Treat timing scores as heuristic support, **not** probabilities or mandates. Agent can consider alternative candidate windows and contrary evidence.
- Bound number of LLM rounds, tool calls, tool-output bytes, calendar horizon and model-token budget; on limit, return a clear partial evidence-based answer.
- Handle provider failure, unsupported tools and empty evidence gracefully.
- Use an explicit tool allowlist and server-side tool dispatcher. No unrestricted command execution or agent-initiated database writes.
- Keep current one-shot pipeline behind a feature flag.

| ID | Question / case | Expected behavior |
|---|---|---|
| P3-01 | “Who rules my 10th house?” | D1 only, no unnecessary D10/RAG |
| P3-02 | “Is my career generally promising?” | D1/D10 and relevant Dasha evidence; method explained |
| P3-03 | “When might I get promoted?” | Adds relevant scoped periods/transits; does not just echo one default window |
| P3-04 | D1/D10 conflict | Investigates reason and may fetch D9/other support with justification |
| P3-05 | “What about Jupiter in Leo?” | Requests the relevant transit for context, not a generic rerun |
| P3-06 | “Which Dasha am I in now?” | Direct deterministic query without broad forecast |
| P3-07 | Compare Jan vs July 2027 | Evaluates *both* requested periods, not only top-ranked window |
| P3-08 | Unsupported calculation | Explicit limitation; no invented result |
| P3-09 | Agent loops/repeats tool call | Deduplicated or stopped by budget and traceable reason |
| P3-10 | Tool timeout/provider unavailable | Useful error or qualified partial answer, no paid-credit loss in later P7 |
| P3-11 | Prompt-injected tool payload | Cannot trigger unauthorized tool/action |

**Gate P3:** Mocked multi-step career consultation works, agent trace shows justified calls, limits respected, no fake calculation, legacy path still available. No live cost required to pass unit tests; optional separately approved capped smoke test.

**Codex invocation:** `Implement P3 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P2 is approved. Add bounded agent planner/orchestrator and tests; preserve legacy feature flag. Do not start P4.`

---

## P4 — RAG knowledge tools and provenance

**Purpose:** Make the agent query relevant astrology literature on demand and distinguish source-based interpretation from calculations.

**Implementation scope**
- Audit which Markdown/book knowledge actually exists in the configured OpenAI vector store; **never** assume all local `.md` files are indexed.
- Define `search_astrology_knowledge` tool with topic, concepts, optional tradition/source and result count.
- Prefer targeted retrieval over repeatedly sending a broad prewritten query; include citation metadata and evidence IDs.
- Keep provider-hosted `file_search` initially; introduce an adapter interface so hosted retrieval can later be replaced without changing agent logic.
- Treat retrieved text as untrusted data; block prompt-injection instructions from altering system/tool behavior.
- Preserve attribution to document/book/chapter/page when available; if no citation is available, say so.
- Avoid copying whole texts into prompts; enforce snippet and result budgets.

| ID | Test | Acceptance criterion |
|---|---|---|
| P4-01 | Topic-specific retrieval | Returns relevant passages with available metadata |
| P4-02 | No matching source | Clearly says insufficient retrieved support |
| P4-03 | Contrary traditions/claims | Returns distinguishable viewpoints without pretending agreement |
| P4-04 | Source citation | Identifies actually retrieved evidence, not invented book/page |
| P4-05 | Malicious text in retrieved file | No instruction override/tool misuse |
| P4-06 | Missing vector-store configuration | Safe fallback and clear diagnostic |
| P4-07 | Oversized retrieval | Enforces result/token limit |
| P4-08 | Same search repeated | Reuses request-level cache when appropriate |

**Gate P4:** Mocked retrieval tests pass; live corpus index coverage is either verified (through separately authorized provider inspection) or explicitly marked unverified. No invented citations.

**Codex invocation:** `Implement P4 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P3 is approved. Add RAG tool, grounding and tests. Do not start P5.`

---

## P5 — Conversational continuity and privacy-aware memory

**Purpose:** Move from one-question conversations to coherent, scoped, multi-turn consultations.

**Implementation scope**
- Add endpoint/UI to append follow-ups to an existing authorized `Conversation`; retain optional new conversation creation.
- Tie every conversation to a selected chart and explicit user; avoid implicit cross-chart memory.
- Send last *N* relevant turns plus a compact, versioned consultation summary; fetch older material only as needed.
- Maintain a distinction between facts supplied by user, deterministic calculations, agent interpretations and user corrections.
- Ensure summarization does not permanently turn speculative predictions into factual memory.
- Permit view, deletion and appropriate reset of conversation-level summaries; document retention choices and consent.
- Do not store sensitive birth data in generic telemetry or logs.

| ID | Test | Acceptance criterion |
|---|---|---|
| P5-01 | Three-turn career consultation | Follow-up refers to prior period/chart correctly |
| P5-02 | “What about D10?” | Reuses question context and requests focused evidence |
| P5-03 | “Compare with late 2027” | Changes requested dates without losing original topic |
| P5-04 | Start new chart/person | No carry-over from previous chart unless explicitly authorized |
| P5-05 | Cross-user conversation ID | Access denied |
| P5-06 | Long conversation | Bounded context, summary retains key constraints |
| P5-07 | User corrects an earlier fact | Subsequent answers use correction; provenance retained |
| P5-08 | Delete/reset conversation | History/summary removed per policy; no stale cached leakage |
| P5-09 | Simultaneous follow-ups | Deterministic ordering/idempotence or explicit conflict handling |

**Gate P5:** A realistic three-turn conversation is coherent and secure; token context bounded; ownership enforced.

**Codex invocation:** `Implement P5 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P4 is approved. Add multi-turn UI/backend and scoped memory tests. Do not start P6.`

---

## P6 — Evidence verification, answer quality and evaluation

**Purpose:** Produce fluent, less repetitive, better-grounded consultations, with validated mathematical claims.

**Implementation scope**
- Establish a locked evaluation set (at least 30 representative questions plus follow-ups) spanning factual, interpretive and predictive cases; include contradictory evidence and failure cases.
- Compare **legacy AstroGPT vs new agent** using blinded human scoring and objective measures. Optionally use the user's custom GPT as a qualitative benchmark, but do not treat it as ground truth.
- Test claim-to-tool validation for planet positions, Dasha dates, SAV numbers and transit windows; reject or rewrite unsupported factual assertions.
- Ensure rule/score overlap is explicitly noted rather than silently treated as independent confirmation.
- Distinguish traditional astrology interpretation from scientifically established prediction; avoid certainty and unjustified numerical likelihood.
- Natural conversation style with concise explanation and useful follow-up, not forced repetitive section templates.
- Apply final post-processing validation (including remedies and citations) before answer publication where possible; never cache failed answer as a validated result.

| ID | Test | Acceptance criterion |
|---|---|---|
| P6-01 | Wrong Dasha in synthetic draft | Detected and corrected or blocked |
| P6-02 | Invented transit/SAV number | Detected; no unsupported numerical claim published |
| P6-03 | Conflicting D1/D10 indications | Presents both and explains limitations |
| P6-04 | Two different questions same chart | Answers are substantively responsive, not identical date boilerplate |
| P6-05 | Missing RAG evidence | No fabricated citation |
| P6-06 | Follow-up conversational tone | Responds to follow-up without repeating full original reading |
| P6-07 | Factual lookup | Short answer, minimal investigation |
| P6-08 | Historical/predictive question | Correct date scope, appropriate conditional language |
| P6-09 | Final post-processed answer | Revalidated after deterministic replacements |
| P6-10 | Blind evaluation | Record preference, quality, errors, latency and token cost separately |

**Proposed gate P6:** Zero critical invented-calculation errors in the locked regression sample; no new privacy failures; agreed human-quality threshold (e.g., new agent preferred in >=60% of non-tied comparisons), plus no material cost/latency regression outside approved limits. The preference threshold is a **pilot target**, not evidence of effectiveness. Any misses are documented.

**Codex invocation:** `Implement P6 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P5 is approved. Add factual validation and evaluation harness. Do not start P7.`

---

## P7 — Cost accounting, credits, resilience and profitability guardrails

**Purpose:** Prevent unbounded provider spending and incorrect customer charging.

**Implementation scope**
- Introduce transactional request/usage ledger (request ID, user/chart, plan, status, token usage, tool charges, model, estimated/actual provider cost, credits reserved/consumed/released).
- Define per-plan per-request token, rounds, file-search and estimated-cost ceilings; stop gracefully at limits.
- Use provider-reported usage when available; separately record estimates, cached discounts and provider errors.
- Cache safe immutable natal facts, scoped transit results, and per-conversation retrieval appropriately; version/invalidate on chart/method/model/source changes.
- Define retry, timeout, cancellation, idempotency and concurrency policies; prevent double spending on duplicate submissions.
- Establish contribution-margin dashboard: price minus variable LLM/tools, payment fees and allocated infrastructure (before marketing/tax unless explicitly included).
- Distinguish ChatGPT subscription/Codex allowance from **API billing** used by customers.

| ID | Test | Acceptance criterion |
|---|---|---|
| P7-01 | Simple question | Stays under configured maximum budget |
| P7-02 | Deep question/loop | Hard budget halts extra tool/model calls |
| P7-03 | Provider timeout/failure | Proper ledger status, no consumed customer credit unless policy permits delivered value |
| P7-04 | Duplicate HTTP submit | Idempotent; single charge |
| P7-05 | Concurrent last-credit requests | No overspend/negative credits |
| P7-06 | Repeated cached deterministic query | Correct cache hit, no stale chart values |
| P7-07 | Expired/changed chart or knowledge index | Relevant cache invalidated |
| P7-08 | Model returns unknown usage | Conservative estimated cost, clearly flagged |
| P7-09 | Provider cost calculation | Matches published test tariff fixture; pricing is configurable |
| P7-10 | Refund/cancel | Reserved credits released appropriately |
| P7-11 | Admin reporting | No private details exposed to wrong users/partners |

**Gate P7:** All billing/concurrency tests pass; no unbounded requests; live average and P95 cost measured in a separate, preapproved capped test; pricing decisions based on measured costs, not assumptions.

**Codex invocation:** `Implement P7 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P6 is approved. Add bounded usage ledger and resilience tests. Do not start P8.`

---

## P8 — Pilot-ready experience, privacy and operational release

**Purpose:** Make the agent safe and usable for limited external B2C testing; no mass launch yet.

**Implementation scope**
- Show step/progress feedback (not raw chain-of-thought), clear source/calc provenance, response status and graceful partial answers.
- Secure chart ownership, chat permissions, admin boundaries, CSRF, host validation and production secrets handling; do not use Django debug/ngrok setup as production hosting.
- Add structured operational metrics without logging raw user birth details and chats by default.
- Define data retention, deletion, abuse/rate controls, monitoring, alerting and rollback procedure.
- Test migration/backfill, database consistency and temporary feature flag enablement.
- Run the full regression suite and bounded end-to-end pilot.

| ID | Test | Acceptance criterion |
|---|---|---|
| P8-01 | Sign up → chart → question → follow-up | Complete end-to-end flow |
| P8-02 | Invalid chart/time/date | Clear user-visible error; no fake answer |
| P8-03 | Authorization/privacy | Cannot read other users' charts, chats or summaries |
| P8-04 | CSRF, session, configuration | Secure production settings documented and checked |
| P8-05 | Provider outage/partial response | Clear failure handling and correct credits |
| P8-06 | Delete account/conversation | Documented deletion behavior verified |
| P8-07 | Load/burst test | Meets agreed latency and failure thresholds within budgets |
| P8-08 | Rollback | Flip to legacy path without losing user data |
| P8-09 | Reproducibility | Saved answer links to calculation/tool versions and source evidence where practical |
| P8-10 | Pilot analytics | Conversion, satisfaction, continuation, cost and errors measurable without invasive logging |

**Gate P8:** All critical security/privacy and billing tests pass, rollout plan approved, legacy rollback works, and bounded pilot is ready. An actual public launch is a separate decision.

**Codex invocation:** `Implement P8 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, assuming P7 is approved. Prepare pilot-ready UI, security, deployment and full regression report. Do not start P9 or launch publicly.`

---

## P9 — Optional B2C / astrologer-partner commercialization

**Only start after P8 approval and separate business decisions.** Product technology is owned by AstroGPT operator; astrologers are potential non-exclusive distribution partners, not automatically owners of the IP.

**Scope**
- Prepaid packs/pricing/entitlements; actual Stripe/Razorpay flows and verified signed webhooks.
- Referral links/codes, eligible receipts, refund-adjusted commission ledger, partner dashboard and settlement exports.
- Partner agreements, attribution window, privacy disclosures and customer consent, dispute handling and applicable tax/compliance review.
- Small partner-led pilot alongside a small direct B2C group; test paid conversion and repeat use rather than assuming an audience will convert.

| ID | Test | Acceptance criterion |
|---|---|---|
| P9-01 | Successful payment | Entitlement created once after verified webhook |
| P9-02 | Replayed/forged webhook | No double credit / no unauthorized fulfillment |
| P9-03 | Referral attribution | Correct partner and attribution window |
| P9-04 | Refund/chargeback | Commission and credit reconciled |
| P9-05 | Multiple partners | Strict data isolation; correct settlement |
| P9-06 | Unit economics | Positive measured contribution under defined usage pattern |
| P9-07 | Pilot success | Report paid conversion, retention, support load and customer preference |

**Gate P9:** Only launch/expand after business, security, payment and legal sign-off. No promised profitability without measured demand.

**Codex invocation:** `Implement P9 only from ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md, after explicit approval and validated commercial requirements. No production activation without separate authorization.`

---

## 6. Final, cross-phase evaluation (after P8)

When P1–P8 have individually passed and the user requests final review, produce `ASTROGPT_AGENT_FINAL_ACCEPTANCE.md` containing:

1. Side-by-side legacy vs agent outputs for a locked set of representative user questions, evaluated blindly where feasible.
2. Objective calculation correctness against independent fixtures and any remaining unverified methods.
3. Tool-call traces showing adaptive choice (factual questions should not trigger all charts; predictive queries should gather minimally sufficient evidence).
4. Three-turn conversation tests, chart/user isolation and deletion tests.
5. Source/citation audit showing exactly what hosted Markdown/book corpus was actually searchable.
6. Safety, privacy, reliability, security and rollback evidence.
7. Real token/tool usage and cost distribution (mean, median, P95) with estimates separated from reported charges.
8. Launch recommendation: **GO**, **CONDITIONAL GO** or **NO GO**, with blockers and remediation.

**Do not imply that completing phases proves commercial product-market fit.** A paid B2C/B2B2C pilot is required to test willingness to pay.

## 7. Simple handoff procedure for the owner

1. Put this Markdown file in the repository root next to `ASTROGPT_ARCHITECTURE.md`.
2. Send Codex: **“Implement P1 only from `ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md`. Run the required tests, write the report and stop.”**
3. Check `PHASE_01_TEST_REPORT.md`. If it is PASS and you accept it, send **“P1 approved. Implement P2 only from the master plan, run tests, report, and stop.”**
4. Repeat through P8. A Codex-reported PASS is not a substitute for your approval; you can ask for a failing or ambiguous test to be corrected first.
5. After P8, request the final cross-phase acceptance review. Decide separately whether to begin P9/commercial rollout.

**Key rule: One phase → implementation → test evidence → explicit owner approval → next phase.**
