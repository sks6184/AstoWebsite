# AstroGPT — Claude Code Milestone Tracker & Acceptance Gates

**Version:** 0.1 — proposal for architectural approval.  
**Rule:** One milestone at a time. **No implementation until M0 architecture approval.** Each milestone's completion must have test output and an actual live-path demonstration where applicable; a green unit-test count is not sufficient.

## Status key

`NOT STARTED` · `IN REVIEW` · `APPROVED` · `IMPLEMENTING` · `TESTING` · `BLOCKED` · `ACCEPTED`

| Milestone | Target outcome | Initial state | Exit evidence / acceptance gate |
|---|---|---|---|
| **M0 — Architecture audit and sign-off** | Verify P1–P8 as built; propose precise target and migration | NOT STARTED | Current route/tool inventory, integration diagrams, gap/risk register, agreed tool and data contracts, owner-approved TO-BE design; **no production changes** |
| **M1 — Calculation integrity and tool contracts** | Wrap and protect existing calculations; test correct chart isolation | NOT STARTED | Typed compact schemas, method/version metadata, date-boundary and chart-owner tests; verified independent reference fixtures clearly distinguished from snapshots |
| **M2 — Owned knowledge/retrieval interface** | Source-aware RAG abstraction and corpus inventory; independent-RAG migration plan | NOT STARTED | Each source accounted for; retrieval and citation test set, missing-source behavior; provider-independent API interface; no unverified claims of full-book coverage |
| **M3 — Minimal live agent vertical slice** | Make live UI call the **new** agent for factual + one career question | NOT STARTED | Actual Django-to-agent-to-tool trace, compact prompts, one authenticated bounded LLM test with real result, no use of legacy generator for selected test route |
| **M4 — Adaptive career consultation** | Human-derived career policy, iterative evidence, contradictions, timing | NOT STARTED | Questions discriminate job change/promotion/lateral/foreign factors; multiple relevant periods compared; optional tools triggered on evidence gaps; no invented calculations |
| **M5 — Automatic conversational continuity** | Multi-turn follow-ups without checkbox, with privacy boundaries | NOT STARTED | 3+ turn test; correct chart/topic reuse; new thread isolation; opt-out/clear/delete tested; bounded context and summary budget |
| **M6 — Validation, observability and reliability** | Grounded final answers and resilient workflows | NOT STARTED | Source/calculation claim checking, missing evidence and contradictory status, trace IDs, failure-safe timeout/retry policies, no silent fallbacks advertised as full readings |
| **M7 — Unit economics and operational hardening** | Enforced spend and quota controls for future paid use | NOT STARTED | Per-request measured tokens/tool costs/latency, concurrency & abuse limits, no charge on failed outputs, user privacy/security tests, cost distribution report |
| **M8 — Full integrated pilot evaluation** | Compare to Custom GPT and decide launch readiness | NOT STARTED | 30–50 blind/paired cases across domains and follow-ups, reference calculation checks, domain-expert quality rubric, p50/p95 costs and latency, go/no-go report |
| **M9 — Commercial rollout (later)** | Payments and B2B2C partner attribution | NOT STARTED | Requires separate approval after M8; purchase fulfillment, partner commission, refunds, legal/privacy review, operations and analytics |

## Mandatory report for every implementation milestone

File name: `M##_IMPLEMENTATION_AND_TEST_REPORT.md`, containing:

1. **Scope completed and omitted**, referencing approved requirements and files/functions changed.
2. Commands used and **actual** passed/failed/skipped/blocked test counts, with environment/version.
3. Independent numerical references versus compatibility snapshots, and unresolved reference gaps.
4. Tool traces or test artifacts proving required **live routing** (not merely class existence).
5. Token counts, API charge estimates, tool-call counts and duration for provider-facing milestones.
6. Security/privacy checks: access isolation, denial-before-provider-call, secret-free logs.
7. Regressions and known issues, including severity and mitigation.
8. **Gate decision: PASS / FAIL / BLOCKED**, and explicit approval request. Do not self-approve the next milestone.

## M0 — Detailed architecture-only acceptance checklist

- [ ] Read code and attached historical artifacts; inventory present/missing files.
- [ ] Record exact request path from Django form to provider, actual agent calls and fallback paths.
- [ ] Compare current P1–P8 claims against source and existing tests (`implemented`, `partial`, `disconnected`, `missing`, `unverified`).
- [ ] Map current calculation services, astrology methods, source references and tests.
- [ ] Propose a **single-agent modular monolith** or justify an alternative; direct Python tools with optional external MCP/REST adapter.
- [ ] Define `QuestionContext`, `ToolRequest`, `ToolResult`, `EvidenceItem`, `RetrievalHit`, `ConsultationSummary`, `BudgetState` contracts and ownership boundaries (conceptual schemas acceptable at M0).
- [ ] Define agent-state flow: scope → baseline evidence → targeted RAG/calculation loop → contradiction/coverage check → final answer or safe incomplete result.
- [ ] Define stopping/cost policies, handling of tool errors, source conflicts, missing data, history boundaries and ungrounded claims.
- [ ] Provide a canonical PDF corpus inventory, indexing/search quality risk assessment and staged vendor-independent retrieval option.
- [ ] Propose a thin-slice integration plan and rollback/feature-flag policy.
- [ ] List each unresolved decision for owner review. **Do not implement.**

**M0 outputs:** `CLAUDE_AS_IS_VERIFICATION.md`, `CLAUDE_TO_BE_ARCHITECTURE_PROPOSAL.md`, `CLAUDE_MILESTONE_GAP_MAP.md`.

## Example automated and manual acceptance scenarios (starter suite)

| ID | User scenario | Expected observation |
|---|---|---|
| A-01 | `Who is my 10th lord?` | Authorized chart lookup, concise deterministic response; no unnecessary search/deep loop |
| A-02 | `Can I get a new job next year?` | Year resolved correctly, MD/AD for target period, relevant D1/D10/Chara evidence, targeted retrieval; trace proves actual tools |
| A-03 | `Is it promotion or employer change?` | Differentiates advancement, separation and disruption heuristics; explains uncertainty; no certain job-loss claim |
| A-04 | `What if Jupiter enters Leo?` | Follow-up retains chart and prior career topic, calls targeted transit/SAV tool, does not require checkbox |
| A-05 | `What evidence contradicts the first reading?` | Explicitly assesses neutral versus opposing evidence, not just repeats previous conclusion |
| A-06 | User A passes User B's chart ID | Reject before tool or provider calls; no disclosure or credit consumption |
| A-07 | Provider timeout, RAG empty, calc unsupported | Explicit incomplete state; no fabricated positions, no paid-answer debit |
| A-08 | Long repeated follow-up discussion | Bounded context, no indefinite tool loop, measured usage within cap |
| A-09 | Marriage/education/children questions | Appropriate domain policy; no inappropriate reuse of career/D10 mandatory checks |
| A-10 | High-cost ambiguous question | Hard budget cap enforced by application, controlled partial response and no runaway spending |

## Cross-cutting constraints

- Keep original calculation methods and choose/record variant, ayanamsa, timezone, time resolution and reference frame.
- Maintain reproducible test fixtures, avoiding fake `correctness` assertions from outputs generated by the same code under test.
- Distinguish **astronomical factual accuracy**, **faithful traditional interpretation**, and **real-world predictive validity**; never express heuristic support scores as statistically calibrated probabilities.
- Do not require all three Dasha systems to concur, or count `neutral` / `unavailable` as opposing. Track shared underlying facts to avoid double counting.
- Full PDFs may remain the source corpus; Markdown is optional for curated rules/corrections. Commercial-use rights need review before distributing source-derived material.
- No deployment of Django development settings or publicly exposed debug tracebacks.
- User retains approval over scope, spend, credentials, data migration and external service changes.

## Prompt for authorizing a milestone after M0

> Read the approved architecture proposal, milestone tracker and preceding milestone report. Implement **M[NUMBER] only** to its stated acceptance gate. Preserve existing calculations and access controls. Run focused, integration and regression tests; document changes, traces, actual cost/latency and blockers in `M##_IMPLEMENTATION_AND_TEST_REPORT.md`. Do not begin the next milestone. Stop for owner review.
