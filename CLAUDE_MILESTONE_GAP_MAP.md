# AstroGPT — Milestone Gap Map (M0)

**Author:** Claude Code  
**Date:** 2026-11-10  
**Purpose:** map existing P1–P8 work onto milestones M1–M9 from `ASTROGPT_CLAUDE_MILESTONE_TRACKER.md`. For each milestone it shows what can be reused, what is missing and what evidence would close it.  
**Inputs:** `CLAUDE_AS_IS_VERIFICATION.md` (cited as AS-IS §n) and `CLAUDE_TO_BE_ARCHITECTURE_PROPOSAL.md` (cited as TO-BE §n / OD-n).  
**Status:** M0 deliverable. **M1, M1b and M2 are complete.** The M3 and M4 rows were revised on 2026-11-11 (revision 2: general-purpose agent; career becomes the M4 benchmark) and await owner approval. See §8.

Size key: **S** ≈ 1–2 focused sessions · **M** ≈ 3–5 · **L** ≈ 6+.

---

## 1. M0 checklist status (tracker §M0)

| Checklist item | Where addressed | Status |
|---|---|---|
| Read code and historical artefacts; inventory present/missing files | AS-IS §3 | Done (`PHASE_01_TEST_REPORT.md`, `Yogini Dasha.pdf` NOT FOUND) |
| Exact request path from Django form to provider, agent calls, fallbacks | AS-IS §4 | Done |
| P1–P8 claims vs source (implemented/partial/disconnected/missing/unverified) | AS-IS §5 | Done |
| Calculation services, methods, source refs, tests | AS-IS §8, §9 | Done (no independent oracles found) |
| Single-agent modular monolith or justified alternative; direct Python tools, optional MCP/REST | TO-BE §2 | Proposed |
| `QuestionContext`, `ToolRequest`, `ToolResult`, `EvidenceItem`, `RetrievalHit`, `ConsultationSummary`, `BudgetState` | TO-BE §5 | Proposed (conceptual) |
| Agent-state flow | TO-BE §6 | Proposed |
| Stopping/cost, tool errors, source conflicts, missing data, history, ungrounded claims | TO-BE §7 | Proposed |
| PDF corpus inventory, indexing/search risk, staged vendor-independent retrieval | AS-IS §11; TO-BE §9 | Local inventory done; hosted inventory needs approval (OD-5) |
| Thin-slice plan + rollback/feature-flag policy | TO-BE §10 | Proposed |
| Unresolved owner decisions | TO-BE §12 | Listed (OD-0 … OD-14) |

---

## 2. Pre-M1 prerequisite (needs approval; not code)

**OD-0: repository safeguard.** All P1–P8 work is uncommitted, and all eight branches equal `2312a42` (AS-IS §2). Before any M1 change:

1. Commit the current working tree as-is to a dedicated branch (e.g. `archive/p1-p8-working-tree`). Optionally use a `.gitattributes` line-ending policy first, to avoid a CRLF-noise diff.
2. Push to `origin` if the owner agrees. This is outward-facing, so it needs explicit approval.
3. Branch M1 from that commit.

Without this, no milestone report can cite a commit hash, and rollback is impossible.

---

## 3. Milestone-by-milestone gap map

### M1 — Calculation integrity and tool contracts

| | |
|---|---|
| **Reuse (as-is)** | `astrology/tools/registry.py` (allowlist, owner check on every call, fingerprint cache); `tools/contracts.py` (frozen requests, envelopes, limits); `tools/fingerprints.py`; `astrology/test_tools.py` (30 tests); `charts/astro_engine.py`, `astrology/calculations/*` (unchanged) |
| **Gaps** | (1) No independent reference fixtures: every numeric test is legacy parity (AS-IS §8.2). (2) Dasha boundary conventions mixed across 7 call sites; the rule tool itself uses an inclusive-end selector (AS-IS §8.3, §6.1). (3) No named, versioned **method profile** (AS-IS §8.1). (4) Swiss Ephemeris path not set, so precision is undisclosed (OD-10). (5) `EvidenceItem` digest layer missing (TO-BE D3). (6) Live-path security fixes: raw exception text in `_fallback_answer`, question text in logs, unmetered intent classifier, conversation created before reservation (AS-IS §15 S-2…S-4, S-9). (7) Chart template v9/v10 mismatch causes recalculation and writes on every `GET /charts/` (AS-IS §14 P-3). |
| **Proposed scope** | Method profile + `MethodProfile` metadata on `ToolResult`. One dasha period selector (half-open, per OD-8) used by all call sites, with boundary tests (day before / on / after a transition). `EvidenceItem` builders for the existing 6 tools. Independent fixtures for 3–5 published reference charts (positions to an agreed tolerance; Vimshottari MD/AD start dates), labelled `independent` vs `snapshot`. The four live-path security fixes. The v9/v10 refresh fix. |
| **Out of scope** | Rewriting calculation algorithms; rule semantics changes. |
| **Exit evidence** | Fixture provenance table (source, tolerance); boundary tests; chart-owner and forged-ID tests (existing ones re-run plus a digest-layer test); `git diff` showing calculation modules untouched apart from the selector routing; full suite green. |
| **Risks** | Unifying the selector **changes** which period is reported on transition days in legacy answers. This is intended, but must be owner-approved (OD-8). Reference data sources need owner choice. |
| **Size** | **M–L** |
| **Depends on** | OD-0, OD-8, OD-10 |

### M2 — Knowledge/retrieval interface (hosted backend only)

| | |
|---|---|
| **Reuse** | `astrology/rag/knowledge_contracts.py::RetrievalAdapter` protocol; `rag/knowledge.py::KnowledgeSession` (ownership, snippet bounds, cache, evidence hashes); `rag/hosted.py::HostedFileSearch`; `astrology/test_knowledge.py` (32 tests); `ASTROGPT_KNOWLEDGE_VERSION` fingerprint |
| **Gaps** | (1) Hosted store contents/status unverified (AS-IS §11.2). (2) No corpus manifest; `source_id`/tradition/rights not recorded. (3) Each search costs a full LLM round + full-context reservation (AS-IS §9.2, P-5). (4) No real-query retrieval test set; P4 used synthetic passages only. (5) Missing `Yogini Dasha.pdf` locally. (6) Rights status unknown (OD-11). |
| **Proposed scope** | One approved read-only store listing, used to build `corpus_manifest.yaml`. A `RetrievalHit` contract. A measured comparison of the direct `vector_stores.search` adapter vs the forced `file_search` adapter on a locked 20–30 query set (owner rates relevance); adopt the winner behind the same protocol. Missing/failed-file behaviour. A migration-plan document for future independent RAG (**plan only**; no pgvector/Qdrant/embeddings per the M2 constraint). |
| **Exit evidence** | Manifest with every intended source accounted for (`indexed`/`failed`/`missing`); retrieval test results with actual cost; zero invented locators; adapter swap test (mock adapter passes the same suite). |
| **Risks** | Direct-search pricing or ranking may be worse than expected (fallback: keep the P4 adapter). OCR-poor PDFs may need re-upload; that is owner work. |
| **Size** | **M** |
| **Depends on** | OD-5 (listing + small paid test budget), OD-11 |

### M3 — General-purpose Vedic reasoning agent (revision 2, 2026-11-11)

| | |
|---|---|
| **Reuse** | `chat/consultation_service.py::_append_turn` (CAS, reservation, publication, settlement); `chat/agent_service.py` router; `astrology/agent/orchestrator.py` (`execute` guards, dedup, limits); `agent/provider.py`; `accounts/provider_meter.py` (now meters direct search); the M2 `direct` adapter and `SOURCE_TEXT_POLICY`; `chat/prediction_context.py::CATEGORY_RULES` (13 domains: houses, vargas, karakas); the rule engine's existing categories; `astrology/calculations/jaimini.py` (karakas, padas, karakamsha, Jaimini yogas); `chart_data['yogas']`; `synthesis/fact_catalog.py` and `validation/claim_validator.py`; P8 status polling UI |
| **Gaps** | (1) Career/business-only `ScopeError` (`agent/policy.py:92-93`). (2) Career logic hard-coded in `orchestrator.minimal_evidence()`. (3) No domain guidance data; no book-vocabulary hints. (4) The knowledge tool joins topic and concepts into a query, so the model cannot write or refine search text, and there is no "weak result" signal. (5) Non-answer states are merged: retrieval failure, no source support and unsupported calculation are not distinguished. (6) Jaimini karakas and padas, and stored yogas, are not exposed as tools. (7) The fact catalog publishes only the 2nd, 7th, 10th and 11th lords. (8) The validator expects closed slots or 12 sections, not natural prose. (9) The budget model is not fit for purpose: the free plan allows 2 rounds, 1 search and US$0.05, and pre-dispatch checks count bytes. (10) Global flag only, no per-user rollout. (11) No domain test matrix. |
| **Proposed scope** | Acceptance criteria §5 (revision 2): per-user allowlist; model-led 1–3 domain labels in the first round (12 primary domains; relationships ≠ marriage, children ≠ conception/childbirth); `domains.v0.yaml` investigation guidance (owner-reviewed; no tool sequences or interpretations; the model may request other tools); three tool wrappers over existing calculations; agent-written, iterative direct retrieval (the 0.70 score is an advisory flag; 4 searches is a ceiling); three non-answer states; compact digests with a `tiktoken` budget; natural answers validated by content elements; claim and citation checks; pilot cost envelope; a domain end-to-end matrix with a support report. |
| **Out of scope** | New calculations (muhurta and panchanga, matching, shadbala, prashna, longevity); vector-store changes; new RAG infrastructure; automatic memory (M5); paid-plan envelopes (M7). |
| **Exit evidence** | M3-AC1 to AC23 (revision 3): full offline suite for 12 domains, mixed questions and distinction pairs; **3 live consultations (career, marriage, children)** reviewed with the owner before any expansion; a labelled 44-question set only in the expansion stage; offline tests for each non-answer state; ledger extract within the M3 cap; rollback demonstrations (allowlist and adapter). |
| **Risks** | Prompt and evidence growth on mixed-domain questions; the model under-investigating thin-rule domains; claim-scanner false blocks on prose; thin corpus for childbirth, Upapada, D30 and Darakaraka/Putrakaraka. |
| **Size** | **L** (it was **M** when M3 was career-only) |
| **Depends on** | M1/M1b, M2 (done); OD-7, OD-16, OD-17, OD-22 to OD-30; owner review of `domains.v0.yaml` before the live traces |

### M4 — Career benchmark: adaptive career consultation (revision 2)

| | |
|---|---|
| **Reuse** | `agent/policy.py` windows logic; `continuity.py` comparisons; `synthesis/fact_catalog.py`; `validation/claim_validator.py`; P6 locked fixtures (`astrology/evaluation/fixtures/p6_cases_v1.json`); `harness.py`; Chara/Yogini/transit/SAV tools |
| **Gaps** | (1) No methodology policy registry; career logic is hard-coded in `minimal_evidence` (TO-BE §8). (2) The closed-slot composer cannot interpret (AS-IS §1.3). (3) No root/independence tracking, so double counting is possible (AS-IS §9.1). (4) No discrimination between promotion, voluntary change, disruption and the foreign dimension (handover §3 step 3). (5) Rules are evaluated at window start only, not across the window. |
| **Proposed scope** | Career is the **detailed benchmark** of the general M3 agent, not the product boundary. Four sub-question policies (promotion, voluntary change, involuntary change, foreign relocation) extend the `domains.v0.yaml` career entry (owner-reviewed); the M2 weak-topic decomposition (Chara Dasha via Pada/AmK, Saturn's 10th-house influence, Rahu sub-period) is evaluated here. Earlier draft scope, kept: `career.predictive.v1` + `career.factual.v1` policies (owner-reviewed). Model scope proposal (D1). Grounded prose with fact tags + claim scanner (D2). `roots`-based agreement counting. Event-pattern heuristics labelled as owner heuristics. Multiple-period comparison. Optional tools triggered by evidence gaps. |
| **Exit evidence** | A-02, A-03, A-05 traces; the claim scanner catches seeded invented values (reuse P6-01/02 cases); policy-coverage report per answer; astrologer review of 10 career answers against a rubric. |
| **Risks** | Claim-scanner false positives/negatives (mitigation: pattern test corpus). Owner time for policy review. |
| **Size** | **L** |
| **Depends on** | M2 (for source support), M3, OD-3, OD-9 |

### M5 — Automatic conversational continuity

| | |
|---|---|
| **Reuse** | `chat/memory.py` (bounded context, deterministic summary, epochs, reset/clear/delete); `consultation_service._change_memory`; `continuity.py` (chart/person boundary checks); `chat/test_memory.py` (41 tests) |
| **Gaps** | (1) Opt-in default off + per-conversation checkbox (AS-IS §12). (2) Manual message-number fields. (3) Summary topic limited to job/business/general. (4) Regex-only elliptical follow-ups. (5) Context is dropped on the legacy path (by design while legacy remains). |
| **Proposed scope** | Account-level memory preference + per-conversation toggle (OD-6). Remove the number fields; let the model resolve references within bounded turns while corrections are still recorded deterministically. `ConsultationSummary` v2 (domain-generic, open questions). Summary-budget enforcement. |
| **Exit evidence** | A-04 and a 3+ turn test on the real slice; new-conversation isolation; opt-out/clear/delete; context byte/token budget in the trace. |
| **Size** | **M** |
| **Depends on** | M3, OD-6 |

### M6 — Validation, observability, reliability

| | |
|---|---|
| **Reuse** | `chat/publication.py` (final legacy check, no failed-answer cache); `verified_answer.publish_answer` fallback; `accounts/pilot_ops.py` progress/metrics; `SafeJsonFormatter` |
| **Gaps** | (1) Legacy validator is keyword-based; the agent claim validator only fits closed slots. (2) Provider error subtype is lost (`provider_failure` only; diagnostic §1). (3) No trace ID linking view → tools → rounds → ledger. (4) Silent legacy fallback persists raw error text (fixed in M1, verified here). (5) Retry/timeout policy not unified across call sites. |
| **Proposed scope** | Finalize the claim scanner for prose. Safe-incomplete state. Exception-type capture (`ConnectTimeout`/`ReadTimeout`…) without bodies. Trace IDs. One timeout/retry policy for all provider calls. |
| **Exit evidence** | A-07 (timeout, empty RAG, unsupported calc): explicit incomplete, no charge; trace sample; no raw prompt/question in logs (log-scan test). |
| **Size** | **M** |

### M7 — Unit economics and operational hardening

| | |
|---|---|
| **Reuse** | P7 ledger (`CreditAccount`, `UsageRequest`, `ProviderUsage`), `reconcile_usage`, contribution dashboard, P8 rate limits, `pilot_readiness` |
| **Gaps** | (1) Two unmetered call sites (fixed in M1; verify here). (2) No measured mean/p95 cost. (3) Only one priced model. (4) File-search reservation equals full context. (5) SQLite `select_for_update` is a no-op, so PostgreSQL concurrency is untested. (6) No organisation-level provider spend cap. (7) Synchronous worker occupancy under load. |
| **Proposed scope** | Measured cost distribution on the M8 case set; plan envelopes from data; PostgreSQL staging concurrency test; provider-project hard limits configured (owner action); decide on the background worker (OD-14). |
| **Exit evidence** | Per-request tokens/cost/latency table; A-08, A-10; concurrency test on PostgreSQL; zero charges on failed outputs. |
| **Size** | **M** |

### M8 — Integrated pilot evaluation

| | |
|---|---|
| **Reuse** | P6 harness (blind packets, attested scores), 48 locked cases, P8 feedback capture and analytics |
| **Gaps** | Zero human ratings to date; no Custom-GPT comparison; single synthetic chart in fixtures; no non-career domain policies (A-09 needs at least an explicit "not yet supported" behaviour or reviewed policies). |
| **Exit evidence** | 30–50 paired blind cases; reference-calculation checks; expert rubric; p50/p95 cost and latency; go/no-go report. |
| **Size** | **L** (mostly owner/expert time) |

### M9 — Commercial rollout (later)

| | |
|---|---|
| **Reuse** | `payments/models.py::PaymentEvent`, plan/credit fields, P8 privacy and deletion |
| **Gaps** | Webhook is a placeholder (`payments/views.py:4`); no checkout, signature verification, entitlement fulfilment, partner attribution, refunds or legal review. |
| **Size** | **L**; requires separate approval after M8 |

---

## 4. Acceptance scenarios: current state vs gap

| ID | Scenario | Today (live = legacy) | Agent code today (disconnected) | Closed in |
|---|---|---|---|---|
| A-01 | "Who is my 10th lord?" | Full legacy evidence build + one large LLM call with file_search (size varies by category; not measured for this question) | **Passes**: D1 only, zero LLM (P3-01) | M3 (live trace) |
| A-01b | "Who is my 7th lord?" | Legacy LLM | **Fails**: regex knows only the 10th, so `ScopeError` | M1/M3 fast path |
| A-02 | "Can I get a new job next year?" | One-shot legacy; context ignored | Plan resolves 2027; D1/D10, MD/AD, transits, SAV, candidates. **Free-plan budget likely exhausted (INFERRED, unmeasured)**; output is canned slots | M3 (route/budget), M4 (quality) |
| A-03 | "Is it promotion or employer change?" | Legacy | Treated as `timing` with the default **3-year** window; no 5/8/12-house discrimination | M4 |
| A-04 | "What if Jupiter enters Leo?" | Independent legacy answer, no context | Focused transit plan; context only if memory is enabled | M5 |
| A-05 | "What evidence contradicts the first reading?" | No context | No dedicated plan; becomes an assessment | M4/M5 |
| A-06 | User A passes User B's chart ID | **Denied** (view + service) | **Denied** at every tool | Already met; re-verify in M1 |
| A-07 | Provider timeout / RAG empty / unsupported calc | Fallback stored **with raw error text**, uncharged | Partial evidence report, uncharged | M1 (text fix), M6 |
| A-08 | Long follow-up discussion | Each turn independent | Bounded (≤6 messages, 12 KB) | M5/M7 |
| A-09 | Marriage/education/children/health/foreign/property/spirituality and mixed-domain questions | Legacy answers using broad evidence | `ScopeError` "career/business only" | **M3 (revision 2)**: general agent with a graded support report; deeper domain policies after M4 |
| A-10 | High-cost ambiguous question | Meter caps; may fail with `input_limit` | Limits + meter; partial | M3 (pilot envelope), M7 (plans) |
| A-11 (new) | A question needing an unimplemented calculation (muhurta, kundli matching, shadbala) | Varies | Unsupported or generic | M3: `calculation_unavailable` with its disclosure |
| A-12 (new) | Library unreachable vs nothing relevant found | Not distinguished | Not distinguished | M3: `retrieval_failed` vs `no_source_support` |

---

## 5. Reuse inventory (what not to rebuild)

| Asset | Location | Reuse verdict |
|---|---|---|
| Natal/varga/dasha/transit/BAV-SAV engines | `charts/*`, `astrology/calculations/*` | Keep unchanged (selector routing only) |
| YAML + Python rule engines | `astrology/rules/*`, `calculations/d*_rules.py` | Keep; add dedup at the evidence layer |
| Tool registry, contracts, fingerprints, cache | `astrology/tools/*` | Keep; extend the envelope with the method profile |
| Agent guards (allowlist, scope, dedup, limits) | `astrology/agent/orchestrator.py::execute` | Keep; refactor the loop/payload |
| Regex planner | `agent/policy.py` | Keep as the factual fast path; demote for other questions |
| Closed-slot composer | `synthesis/verified_answer.py` | Keep as the **safe-incomplete** renderer; replace for normal answers |
| Fact catalog + claim validator | `synthesis/fact_catalog.py`, `validation/claim_validator.py` | Keep; extend to tagged prose |
| Knowledge session + adapter protocol | `astrology/rag/*` | Keep; add the direct-search adapter |
| Consultation service (CAS, idempotency, settlement) | `chat/consultation_service.py` | Keep |
| Memory bounds, epochs, deletion | `chat/memory.py` | Keep; change defaults/UI |
| Usage ledger, meter, tokenizer guard, IPv4 transport | `accounts/usage*.py`, `provider_meter.py`, `token_budget.py`, `provider_transport.py` | Keep; meter the two bypasses |
| Production profile, middleware, admin restriction, deletion | `astro_site/production.py`, `pilot_middleware.py`, `accounts/*` | Keep |
| Evaluation harness + locked cases | `astrology/evaluation/*` | Keep for M4/M8 |
| Legacy one-shot pipeline | `chat/llm_engine.py`, `chat/prediction_context.py`, `chat/timing_windows.py` | Freeze as rollback (OD-13) |

---

## 6. Risk register (ranked)

| # | Risk | Likelihood | Impact | Mitigation | Milestone |
|---|---|---|---|---|---|
| R1 | Loss of uncommitted P1–P8 work | Medium | Critical | OD-0 commit + push | Pre-M1 |
| R2 | Agent prompt growth recreates the 100k-token, timeout and cost failures | High | High | Digests (D3), tokenizer guard, per-round measurement | M1/M3 |
| R3 | Product answers stay robotic (closed slots), so no advantage over a Custom GPT | High | High | Grounded prose with claim scanner (D2) | M4 |
| R4 | Free/basic plan budgets block agent consultations | High | High | Per-question-type envelopes from measurement | M3/M7 |
| R5 | Unmetered paid calls and raw error leakage on the live path | Confirmed | Medium–High | Fix in M1 | M1 |
| R6 | Hosted corpus incomplete or poorly indexed; citations unverifiable | Medium | High | Manifest + retrieval test set | M2 |
| R7 | Dasha transition-day disagreement across paths | Confirmed | Medium | Single selector (OD-8) | M1 |
| R8 | Rule double counting inflates confidence | Likely | Medium | Root-based agreement | M4 |
| R9 | No independent numerical verification | Confirmed | High (trust) | Reference fixtures | M1 |
| R10 | Source licensing for commercial use | Unknown | High (legal) | OD-11 before quoting to paying users | M2/M9 |
| R11 | Synchronous worker saturation under real load | Medium | Medium | ≥2 workers; background worker decision | M7 |
| R12 | Claim-scanner errors (false blocks / misses) | Medium | Medium | Pattern corpus + P6 seeded cases | M3/M4/M6 |
| R13 (new) | Iterative retrieval and mixed-domain questions multiply rounds, searches and tokens | High | Medium | Per-consultation envelope (≤6 rounds, ≤4 searches, ≤25k largest round, ≤US$0.05); per-round payload; search cap | M3 |
| R14 (new) | The model under-investigates thin-rule domains, or overstates them | Medium | High | Data-driven minimums; Partial grading with disclosure; claim scanner | M3 |
| R15 (new) | Thin corpus for some domains (childbirth, UL, D30, DK/PK) gives `no_source_support` | High | Medium | Honest disclosure; corpus additions are owner work after M3 | M3+ |
| R16 (new) | Sensitive-domain harm (health, fertility, longevity) | Medium | High | OD-23 policy plus validator checks | M3 |
| R17 (new) | Limited API balance (about US$2.27 remaining, INFERRED) | Confirmed | Medium | M3 cap of US$1.00 on `gpt-4o-mini`; no stronger model without approval | M3 |

---

## 7. Recommended sequence

`OD-0 commit` → **M1** (integrity + live-path security fixes + digests) → **M2** (retrieval evaluation, manifest) running in parallel with **M3** (live slice, deterministic + existing P4 adapter) → **M4** → **M5** → **M6** → **M7** → **M8** → (M9 after a separate decision).

The only deviation from the tracker is letting M3 start before M2 is fully closed. M3 can prove routing, cost and safety using the existing P4 adapter (or with retrieval disabled for the slice), and M2's adapter choice then slots in behind the same protocol. This is an owner decision; strictly sequential M2 → M3 also works and costs roughly one milestone of calendar time.

**Stop point:** M0 is complete with these three documents. Awaiting owner approval of OD-0 … OD-14 before any M1 work.

---

## 8. Revision 2 (2026-11-11): general-purpose M3

**Owner direction:** AstroGPT is a general-purpose Vedic astrology reasoning agent. Career is the M4 benchmark, not the product boundary. The details are in `CLAUDE_M1_M4_ACCEPTANCE_CRITERIA.md` §5.0–§5.4.

### 8.1 Missing tools and capabilities

| Item | Status | M3 action |
|---|---|---|
| Jaimini facts (7 karakas, karakamsha, AL/UL/A-padas, Jaimini yogas) | Computed in `astrology/calculations/jaimini.py`; **not exposed** as a tool | New wrapper `get_jaimini_facts` (OD-25) |
| Classical yogas | Stored in `chart_data['yogas']`; **not exposed** | Add to `get_chart_facts` |
| All 12 house lords as published facts | The fact catalog publishes only the 2nd, 7th, 10th and 11th lords | Generalize the catalog |
| Model-written search text and a weak-result signal | Missing (query joined from topic and concepts) | Change the knowledge-tool contract; τ = 0.70 plus the model's judgement |
| Distinct non-answer states | Missing | `retrieval_failed` / `no_source_support` / `calculation_unavailable` |
| Domain guidance data | Missing | `domains.v0.yaml` (owner-reviewed) |
| Planetary aspects as a fact list | Used inside rules; not exposed (INFERRED) | Wrapper only if an existing computation is confirmed; otherwise declared unavailable |
| Muhurta and panchanga | **NOT FOUND** (only the AGENTS.md disclosure text exists, in `synthesis/verified_answer.py:7`) | `calculation_unavailable` (OD-29) |
| Kundli matching (two charts) | NOT FOUND | `calculation_unavailable` |
| Shadbala and other strength metrics | NOT FOUND | `calculation_unavailable` |
| Prashna | NOT FOUND | `calculation_unavailable` |
| Thin rule sets: foreign (3), spirituality (3), education (7), wealth (7), health (9) | CONFIRMED (counts of rules tagged per category) | Graded Partial with disclosure; new rules only with owner approval after M4 |

### 8.2 Expected cost risks (estimates; prices UNVERIFIED until OD-30)

- **Typical consultation on `gpt-4o-mini`:** about 5 rounds × about 12k input tokens, about 4k output tokens and 3 direct searches. That comes to **about US$0.02**: roughly US$0.009 input, US$0.002 output and US$0.0075 search.
- **Envelope ceiling:** 6 rounds × 25k tokens and 4 searches, about **US$0.035**, under the proposed US$0.05 cap.
- **Cost drivers:**
  - Each refinement search adds US$0.0025 plus up to about 1.5k tokens of passages (the 6 KB snippet budget) in later rounds.
  - Mixed-domain questions add tool evidence.
  - A repair round adds about one round.
  - Rolling back to hosted search adds about 4.7k input tokens per search.
- **M3 live budget (approved, A9):** US$1.00 in total and US$0.05 per consultation. Stage 2 runs 3 consultations (career, marriage, children; about US$0.06–0.15). Expansion (the remaining domains, mixed questions and the labelling check) runs only after review. A stronger composer model could multiply per-consultation cost by an order of magnitude (INFERRED from list prices, UNVERIFIED). It is therefore not used in M3 without approval.
- **The current plans cannot run the agent:** the free plan allows 2 rounds, 1 search and US$0.05. M3 uses a pilot-only envelope; plan envelopes are set from M3 data in M7.

### 8.3 Decisions needed before M3 starts

After revision 3, still open: the owner review of `domains.v0.yaml` (OD-24) and the §5.5 tool contracts; the secondary-domain part of OD-22; OD-28; OD-29; OD-30. OD-7, OD-16, OD-17, OD-23, OD-25, OD-26 and OD-27 are approved or approved as amended (§7).
