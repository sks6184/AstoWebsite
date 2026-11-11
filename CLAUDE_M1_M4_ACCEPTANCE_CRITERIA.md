# AstroGPT: Revised M1–M4 Acceptance Criteria

Status: M1, M1b and M2 are complete (see `docs/claude_migration/M*_REPORT.md`). **§5 (M3) and §6 (M4) are revised (revision 2, 2026-11-11) and await owner approval.** M3 implementation has not started.
Date: 2026-11-10. Based on the owner's M0 review, the M0 documents (`CLAUDE_AS_IS_VERIFICATION.md`, `CLAUDE_TO_BE_ARCHITECTURE_PROPOSAL.md`, `CLAUDE_MILESTONE_GAP_MAP.md`) and the preservation commit below.

---

## 0. OD-0 result: preservation commit (DONE)

| Item | Value |
|---|---|
| Branch | `preserve/p1-p8-snapshot-2026-11-10` (created from `2312a42`; checked out now) |
| Commit | `c9127ec9ae7022623d50871acbcaf375c9f02e6b` |
| Contents | 147 files, +14,853 / −212 lines: 41 modified tracked files and 106 new files |
| Migrations preserved | `accounts/migrations/0003`–`0006`; `chat/migrations/0003`–`0005` (all 7) |
| Fixtures preserved | `accounts/fixtures/p7_tariff_v1.json`; `astrology/evaluation/fixtures/p6_cases_v1.json` + `.sha256` |
| Docs preserved | Root-level P-series/architecture/diagnostic reports, `docs/agent_migration/PHASE_02`–`08` plans, contracts and test reports, and the three M0 documents |
| Excluded on purpose | `.vscode/settings.json` (local editor preference; still untracked) |
| Excluded by `.gitignore` (unchanged) | `.env`, `db.sqlite3`, `media/`, `.venv/`, `__pycache__/`, `staticfiles/`, `.tmp/`, `.claude` |
| Pre-commit scan | Regex scan for API keys, `sk-`/`sk-proj-`, vector store IDs, payment keys, private keys, tokens and bearer strings: **none**. Every `.env` value checked against the commit **without printing values**: the only match is `OPENAI_MODEL`, a model name that appears in code by design and is not a secret. Emails found: only `example.test`/`example.com` synthetic addresses. Passwords: only synthetic test passwords in test files. P6 fixture: synthetic questions only, no birth records. No PDFs, databases or binaries over 200 KB. |
| Not done | No push, no force-push, no reset, no rebase. Other branches are untouched: `feature/pilot-release-p8` still points to `2312a42`. |
| Remote | `origin = https://github.com/sks6184/AstoWebsite.git` (visibility **UNVERIFIED**). No push until the owner approves (OD-19). |

Rollback of OD-0 itself: none needed. The commit is additive, and the working tree is byte-identical to before.

This file (`CLAUDE_M1_M4_ACCEPTANCE_CRITERIA.md`) is **not** committed yet.

---

## 1. Decision ledger after the owner's review

| ID | Decision | Status |
|---|---|---|
| OD-0 | Preserve the P1–P8 work in git | **Done** (§0) |
| OD-1 | Single LLM agent inside the Django modular monolith, using direct Python tools | **Approved** |
| OD-2 | Hybrid planner: deterministic shortcut for simple factual questions, LLM-led planning for interpretive ones | **Approved** |
| OD-3 | Conversational interpretation grounded in calculated facts and retrieved literature | **Approved**. The format conflict with AGENTS.md is still open (OD-16) |
| OD-4 | Compact, expandable, traceable evidence | **Approved** |
| OD-5 | M2 evaluation of retrieval from the existing OpenAI vector store, with no independent RAG | **Approved in principle**. The specific provider calls still need approval (OD-5a) |
| OD-6 | Memory automatic within a conversation, with privacy controls and no automatic cross-conversation sharing | **Approved** (scheduled for M5; see §6) |
| OD-12 | Per-user agent rollout | **Approved**. The mechanism is still open (OD-17) |
| OD-13 | Legacy path kept for rollback; security defects fixed | **Approved** (fixes in M1) |
| OD-7, OD-8, OD-9, OD-10, OD-11, OD-14 | Models and budgets, dasha boundaries, rule de-duplication, ephemeris files, source rights, synchronous execution | **Open** (§7) |

---

## 2. Rules that apply to every milestone

### 2.1 Milestone evidence pack (required at each exit)

Each milestone ends with a report `docs/claude_migration/M<n>_REPORT.md` containing:

1. **Source changes**: file list, `git diff --stat`, and the commit hash(es) on a milestone branch `claude/m<n>-<slug>`, branched from `preserve/p1-p8-snapshot-2026-11-10`. Nothing is merged to `main` or pushed without owner approval.
2. **Test results**: full-suite command and output, with new tests listed by name. Offline tests are reported as **regression/contract evidence only**, never as proof of astrological correctness.
3. **Actual execution traces** where the milestone makes provider or UI calls. A trace records the route taken, tools called with arguments (chart ID only, no birth data), evidence IDs, retrieval hit IDs, per-round timings and the stop reason. Traces contain no secrets, no birth data and no copied book passages (hashes and locators only).
4. **Provider-reported token usage** (`usage.input_tokens`, `usage.output_tokens`, cached tokens, tool-call counts) from the API response for every paid call, next to the local estimate and the ledger cost. Local estimates are always labelled as estimates.
5. **Unresolved limitations**, labelled CONFIRMED / INFERRED / UNVERIFIED.
6. **Rollback procedure**, tested where feasible (§3–§6 give one per milestone).

### 2.2 Epistemic guardrails (all milestones; checked by validators and reviewed in each report)

| ID | Guardrail | How it is enforced |
|---|---|---|
| G-1 | No astrological value appears in an answer unless a deterministic tool produced it in this consultation | Claim scanner: every sign, house, degree, nakshatra, dasha lord, date and karaka in the answer must match an `EvidenceItem`. An unmatched value blocks publication, or the answer is repaired. |
| G-2 | No source citation unless a retrieval hit for it exists in this consultation | Citation checker: every cited source maps to a `RetrievalHit` ID. Page or chapter is shown only if the provider returned it. |
| G-3 | No event probabilities | Validator rejects percentages or odds attached to life events ("70% chance", "likely with 80% probability"). Rule scores and system agreement are never shown as probabilities. |
| G-4 | Agreement between systems is described as agreement of indicators, not as statistical confirmation | Fixed disclosure text, plus a reviewer check in the M4 rubric |
| G-5 | Confidence is a qualitative label of **evidence strength** (for example strong, moderate or limited support), with a stated reason | Validator requires a reason. Wording that implies likelihood is rejected. |
| G-6 | Interpretation is not hard-coded in Python | Python computes facts, triggers deterministic rules, enforces minimum investigation and validates. The model writes the interpretation. Methodology policies are versioned **data** (YAML), not code branches. No Python table maps chart conditions to final verdict prose. |
| G-7 | When a calculation is not implemented (for example full muhurta), the answer says so | The AGENTS.md "preliminary timing" disclosure is reused. A missing tool means a stated gap, never an invented value. |
| G-8 | The LLM never decides whether a deterministic rule applies (AGENTS.md) | The model may *request* rule evaluation. Triggering stays in `astrology/rules/engine.py`. |

---

## 3. M1: Calculation integrity, dasha boundaries, security fixes

**Goal:** keep the calculation engine as it is, prove it against independent references, give it one dasha boundary convention, and close the identified security defects in both the legacy and agent paths. No change to rule semantics. No new LLM behaviour.

### 3.1 Scope

1. **Method profile.** A named, versioned record of the method settings: `lahiri.truenode.wholesign.v1` (Lahiri ayanamsa, true node, whole-sign houses, 365.2425-day dasha year, noon-UTC transit sampling, ephemeris mode per OD-10). It is attached to every `ToolResult` (`astrology/tools/contracts.py`).
2. **Reference verification.** An independent fixture set (source per OD-15) covering D1 longitudes, ascendant, D9/D10 signs, Vimshottari MD/AD start dates, Yogini MD start dates and Chara dasha sign sequence. Each fixture records its provenance.
3. **One dasha period selector**, using the convention approved in OD-8 (recommended: half-open `[start, end)`). It replaces the 7 inclusive call sites: `astrology/calculations/dasha_facts.py:26`, `astrology/calculations/yogini.py:88`, `charts/yogini_alignment.py:26`, `charts/jaimini_confirmation.py:52`, `chat/rashifal_context.py:66`, `chat/prediction_context.py:899` and `chat/timing_windows.py:344`. It is also used by the 2 half-open sites (`dasha_transit_timeline.py`, `tools/adapters.py:71-80`).
4. **Security fixes** (legacy and agent paths):
   - S-2: raw `OpenAIError` text no longer stored or shown (`chat/llm_engine.py:960, 1038`). The user sees a generic message plus an error class code. Details go to a server log without payload.
   - S-3: question text and formatted exception bodies no longer logged (`chat/intent_engine.py:226, 230`).
   - S-4: the intent classifier call (`chat/intent_engine.py:210-218`) goes through `accounts/provider_meter.py`, with an explicit timeout and `max_retries=0`. Yearly predictions (`charts/yearly_predictions.py:523-526`) are metered as well, or fail closed if re-routed.
   - S-5: the app refuses to start with `DEBUG=False` and the default `SECRET_KEY` (`astro_site/settings.py:12-13`). Development behaviour is unchanged.
   - S-8: the payment webhook placeholder (`payments/views.py:4`) answers 405 for GET and fails closed for POST until it is implemented.
   - S-9: the conversation is created only after a successful credit reservation (`chat/views.py:125`).
5. **Optional, recommended (OD-20):** fix P-3, where `GET /charts/` recalculates and saves every chart because of a template-version mismatch (`charts/views.py:98` expects v9, `charts/astro_engine.py:406` emits v10).

### 3.2 Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| M1-AC1 | Calculation algorithms are unchanged: `git diff` of `charts/astro_engine.py` and `astrology/calculations/*` shows only selector routing and method-profile metadata | Diff in the report |
| M1-AC2 | Independent reference fixtures exist for ≥3 charts (OD-15) with recorded provenance: source software or library, its version, its settings and the tolerance used | Provenance table |
| M1-AC3 | D1 planet longitudes and ascendant match the reference within **≤1 arcminute** (proposed; owner may tighten). D9/D10 signs match exactly, **except** where a body lies within the tolerance of a sign boundary, in which case the case is flagged and not silently passed. | Fixture test output |
| M1-AC4 | Vimshottari MD and AD start dates match the reference within **±1 day** when both use the same year length. Any convention difference is documented, not hidden. | Fixture test output |
| M1-AC5 | Yogini MD sequence and start dates match the reference. Chara dasha sign sequence and lengths match a reference **of the same named school** (OD-15). If no reference for that school is available, the result is marked UNVERIFIED and not claimed verified. | Fixture test output |
| M1-AC6 | Every period lookup in the codebase uses the single selector. A grep proves that no inclusive `start <= d <= end` period selection remains. | Grep output + tests |
| M1-AC7 | Boundary tests at the day before, the day of and the day after an MD and an AD transition give the same period from every surface: tools, legacy evidence, rashifal, timing windows, Yogini and Jaimini confirmation | Test names + output |
| M1-AC8 | A **behaviour-change report** lists exactly which legacy outputs change (expected only on transition days), with examples on synthetic charts | Report section |
| M1-AC9 | S-2: a simulated provider failure produces no raw exception text in the stored message, template or JSON response | Test |
| M1-AC10 | S-3: log capture during classification shows no question text and no exception body | Test with `assertLogs` |
| M1-AC11 | S-4: the classifier and yearly-prediction calls create ledger rows, respect the budget, use the explicit timeout and do not retry. Simulated over-budget makes them fail closed without a network call. | Tests |
| M1-AC12 | S-5, S-8, S-9 each have a passing test | Tests |
| M1-AC13 | The existing ownership tests (forged chart ID, follow-up chart override, tool owner check) still pass | Full suite |
| M1-AC14 | Full suite green. **No paid provider calls in M1.** | Test output; the ledger shows zero new rows outside tests |

### 3.3 Rollback

Revert the M1 commit(s) on the milestone branch. No migrations are expected in M1. If one becomes necessary, it will be reversible and listed explicitly.

---

## 4. M2: Retrieval evaluation on the existing OpenAI vector store

**Goal:** measure, for our own questions, how relevant and accurate the passages returned from the existing AstroVectorStore (the seven PDFs) are. Then put the better retrieval method behind the existing `RetrievalAdapter` (`astrology/rag/knowledge_contracts.py:32-37`). **No** independent RAG, pgvector, Qdrant, embedding pipeline or separate server.

### 4.1 Scope

1. One approved read-only **store listing** (OD-5a). It produces `corpus_manifest.yaml`: file IDs, filenames, processing status, byte size and any attributes, plus owner-supplied tradition, rights class (OD-11) and display title. It resolves whether `Yogini Dasha.pdf` is in the store (it is missing locally).
2. A **locked query set** of 24 queries (drafted by Claude, approved by the owner): 6 career-factual, 6 career-predictive, 4 Jaimini/Chara, 4 Yogini, 4 varga/D10. Each is tagged with the book(s) expected to answer it.
3. Two adapters, compared on the same query set:
   - (a) the current forced `file_search` via the Responses API (`astrology/rag/hosted.py`);
   - (b) direct `client.vector_stores.search` (SDK `openai 1.109.1`), which returns chunks with no model generation round. Its pricing is **UNVERIFIED** and will be measured.
4. **Owner relevance labelling.** For each query, the top 5 hits from each adapter are shown to the owner as file plus short locator and passage text **in a private local review file that is never committed**. The owner rates each hit 0 (irrelevant), 1 (partly relevant) or 2 (directly relevant).
5. **Passage accuracy check.** Where the local PDF text can be extracted, each returned chunk is matched against the corresponding local book by normalised text similarity. This detects OCR corruption and wrong-file attribution. Reports contain match scores and hashes only, never passage text.

### 4.2 Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| M2-AC1 | Every intended source in the manifest is accounted for as `indexed`, `failed` or `missing`, and the result is compared with the owner's list of seven PDFs | Manifest |
| M2-AC2 | For both adapters on all 24 queries: mean owner relevance@5, the share of queries with ≥1 hit rated 2, latency, and provider-reported usage/cost per query | Results table |
| M2-AC3 | Passage accuracy: share of hits whose text matches the attributed local book above an agreed similarity threshold. Mismatches and OCR-poor files are listed. | Results table |
| M2-AC4 | Citation fidelity is 100%: every locator emitted by the adapter corresponds to a returned hit. Page numbers are emitted **only** when the provider returned them. | Automated test |
| M2-AC5 | Adoption rule (proposed): adopt (b) if its mean relevance is **no worse than (a) − 0.1** and its cost per query is lower. Otherwise keep (a). Owner confirms the choice. | Decision record |
| M2-AC6 | Swap test: the agent and its tests run unchanged against (a), (b) and an offline mock adapter | Tests |
| M2-AC7 | Retrieved text is labelled as untrusted source material in every prompt (S-6), including the legacy path | Test |
| M2-AC8 | Missing or failed-file behaviour: the answer states that no classical support was retrieved instead of inventing support | Test |
| M2-AC9 | Total paid spend in M2 ≤ the approved cap (proposed **US$3**). Every call appears in the ledger. | Ledger extract |
| M2-AC10 | No book passages appear in committed files, reports or logs | Grep check |

### 4.3 Rollback

The adapter is selected by one setting. Rollback means setting it back to the current `HostedFileSearch`. No migrations.

---

## 5. M3: General-purpose Vedic astrology reasoning agent in the real Django UI

> **Revision 2 (2026-11-11), awaiting owner approval.** This replaces the career-first M3 of 2026-11-10. It carries the owner's ten M3 requirements (R1–R10, §5.0). Career moves to M4 as the detailed benchmark, not the product boundary. **No M3 implementation has started.**

**Goal:**

- An allow-listed pilot account uses the real `/chat/` UI. Its questions are answered by **one LLM agent** that works across the major life domains, including mixed-domain questions.
- The agent uses the existing Python calculation tools and the M2 direct retrieval adapter.
- Answers are natural conversational prose. They are grounded in calculated facts and retrieved literature, validated automatically, and bounded in cost.

### 5.0 Owner requirements (2026-11-11) and where each is met

| # | Requirement | Met by |
|---|---|---|
| R1 | General-purpose: career, business, marriage, relationships, children/childbirth, education, wealth, health, foreign settlement, property and spirituality, including mixed-domain questions | §5.1 items 2–3; M3-AC3, AC4, AC15 |
| R2 | One LLM agent with the existing Python tools and OpenAI-hosted direct retrieval | §5.1 items 1, 4, 5; M3-AC1, AC6 |
| R3 | Targeted searches in the books' own terminology, synonyms and abbreviations | §5.1 item 5; M3-AC8 |
| R4 | Iterative retrieval: refine or decompose a weak search within budget | §5.1 item 5; M3-AC9 |
| R5 | No hard-coded synonym tables and no career-specific tool sequences in Python | §5.1 item 3; M3-AC5 |
| R6 | Distinguish retrieval failure, missing source support and unavailable calculations | §5.1 item 6; M3-AC10 |
| R7 | Compact evidence, source attribution, automatic factual validation, strict cost limits | §5.1 items 7–8; M3-AC11, AC12, AC16, AC17 |
| R8 | Representative end-to-end tests across all major domains, reported as supported, partial or unsupported | §5.1 item 10; M3-AC15, §5.4 |
| R9 | Career kept as a detailed M4 benchmark, not the product boundary | §6 |
| R10 | Natural conversational answers, not fixed 12-section responses | §5.1 item 9; M3-AC14; OD-16 |

### 5.1 Scope

1. **Per-user routing (OD-17).** Only allow-listed users reach the agent (`chat/agent_service.py`); everyone else stays on legacy.

2. **Domain recognition by the model, not regex.**
   - In its first round, the agent labels the question with **1–3 domain IDs** from a closed list (OD-22). The list is built from the 13 categories that already exist in `chat/prediction_context.py::CATEGORY_RULES`, plus `general`.
   - Unknown labels are rejected by schema. An unclear question falls back to `general`, a broad D1 and dasha investigation.
   - Labelling is **folded into the first agent round**, so it adds no extra paid call.
   - The career/business-only `ScopeError` (`astrology/agent/policy.py:92-93`) is removed. The deterministic factual shortcut stays, extended to all house lords, placements and current periods, with zero LLM calls.

   | Owner domain | Existing category | Main varga | Notes |
   |---|---|---|---|
   | Career | `career` / `job` | D10 | M4 benchmark |
   | Business | `business` | D10 | Houses 2, 7, 10, 11 |
   | Marriage | `marriage` | D9 | Upapada and Darakaraka need the new Jaimini tool |
   | Relationships (non-marital) | `marriage` (OD-22) | D9 | No separate rule set; 5th house and Venus via guidance |
   | Children / childbirth | `children` | D7 | Putrakaraka via the Jaimini tool; childbirth timing uses dasha and transits |
   | Education | `education` | D24 | |
   | Wealth | `money` | D2 | |
   | Health | `health` | D30 | Sensitive-domain policy (OD-23) |
   | Foreign settlement | `foreign_travel` | D4, D9 | 12th house; Rahu |
   | Property | `property` (+ `vehicle`) | D4, D16 | |
   | Spirituality | `spirituality` | D20, D9 | |
   | Also available | `family`, `legal_and_enemies` | D3/D12, D30 | Kept unless the owner removes them (OD-22) |

3. **Domain guidance as data, not code** (R5, G-6).
   - One versioned file, `astrology/methodology/domains.v0.yaml`, has one compact entry per domain:
     - relevant houses, natural karakas and vargas (seeded from `CATEGORY_RULES`);
     - relevant Jaimini points (for example AmK for career, DK and UL for marriage, PK for children);
     - dasha systems to consider;
     - a **minimum investigation** list, written generically (for example "domain houses and their lords; domain varga; current Vimshottari MD/AD; deterministic rules for the category");
     - **source hints** and a **short book-vocabulary note**: at most 8 terms per domain and 100 in total (for example "Pada", "AmK", "sub-period"). These are hints the model reads, **not a Python replacement table**.
   - **One generic routine** applies the minimums to any domain. Python has no per-domain branches and no career-specific tool sequence; `minimal_evidence()` in `astrology/agent/orchestrator.py` is replaced by the data-driven routine.
   - The owner reviews the file's astrological content before live traces (OD-24). It is not treated as validated by default.

4. **Tools.** The existing 6 deterministic tools plus knowledge search stay. Three **wrappers over existing calculations** are added. None of them adds a new astrological calculation (OD-25):

   | New or changed tool | Source (already computed) | Needed for |
   |---|---|---|
   | `get_jaimini_facts`: 7 Chara karakas (M1b), karakamsha, padas (AL, UL, A1–A12), Jaimini aspects and yogas, AK–AmK relation | `astrology/calculations/jaimini.py` (`build_karakas`, `build_karakamsha`, `build_padas`, `build_jaimini_yogas`, …) | Marriage (UL, DK), children (PK), career (AmK, AL), spirituality (karakamsha) |
   | Yogas in `get_chart_facts` | `chart_data['yogas']` (stored; not exposed today) | All domains |
   | Fact catalog: **all 12 house lords** | `astrology/synthesis/fact_catalog.py` publishes only the 2nd, 7th, 10th and 11th lords today | Non-career domains (4th, 5th, 6th, 8th, 9th, 12th lords) |

   **Declared unavailable in M3.** These return `calculation_unavailable`, never an invented value (G-7):
   - muhurta or panchanga;
   - two-chart compatibility (kundli matching);
   - shadbala and other strength metrics;
   - prashna;
   - longevity (OD-23);
   - planetary aspects as a standalone fact list. They are used inside rules but not exposed (INFERRED); a wrapper is possible only if an existing computation is confirmed.

5. **Agent-led, iterative retrieval (R2–R4).**
   - The knowledge tool takes a **search text written by the model** (at most 200 bytes), searched through the M2 `direct` adapter. Hosted search remains the manual rollback.
   - The instructions tell the model to use the books' terminology, synonyms and traditional abbreviations, guided by the domain vocabulary notes.
   - A search is reported as **weak** when its best score is below τ (proposed 0.70, OD-26) or the model judges the passages irrelevant. The M2 calibration supports a threshold of this kind: direct hits below 0.70 averaged 0.4 relevance against about 1.0 above, but on only 50 hits.
   - After a weak search, the model may **refine** it (different wording) or **decompose** it (narrower single-concept searches, filled with calculated facts), up to the per-consultation search cap.
   - Duplicate passages are merged. At least 3 passages are kept per search (M2 close-out floor).

6. **Three distinct non-answer states (R6).** Each has its own code, evidence status and disclosure wording, and none produces invented content:

   | State | Trigger | Disclosure (draft) |
   |---|---|---|
   | `retrieval_failed` | Provider error, timeout, budget refusal or store not configured | "The classical library could not be searched for this question." |
   | `no_source_support` | Searches succeeded, but no passage was relevant after refinement | "No classical support was retrieved for this point." |
   | `calculation_unavailable` | A needed calculation is not implemented or the tool returned `unsupported` | "This needs [named calculation], which the app does not yet calculate." |

7. **Compact evidence and validation** (from the 2026-11-10 M3, kept):
   - `EvidenceItem` digests, expandable by ID; payload per round, not cumulative.
   - The pre-dispatch check counts tokens with `tiktoken`, not bytes.
   - Claim scanner (G-1) and citation checker (G-2).
   - One repair round. On failure, the deterministic evidence report is published, marked partial and unbilled.
   - Source attribution follows OD-11: books are cited by title (filename until display titles are set) and paraphrased, never quoted.

8. **Strict cost limits (OD-7, OD-27).** A pilot envelope per consultation sets maximum rounds, searches, the largest-round input and a cost cap. The search reservation uses the M2 measured direct-search cost (US$0.0025, still to be reconciled with billing), not a full-context reservation. Paid-plan envelopes are left to M7.

9. **Natural answers (R10, OD-16).**
   - The answer is conversational prose with no fixed headings.
   - The validator checks **content elements**, not sections:
     - a direct answer;
     - the calculated factors used;
     - conflicting signals where they exist;
     - an evidence-strength label with its reason (G-5);
     - the relevant disclosures (non-answer states, preliminary-timing disclosure, sensitive-domain note).
   - The per-system basis (Parashari, Jaimini, varga, Yogini, sources) goes in the expandable evidence panel.
   - AGENTS.md is amended to match once the owner approves (OD-16).

10. **Domain end-to-end matrix (R8)** (§5.4).
    - Offline scripted tests for every domain and for mixed-domain questions.
    - A small set of live traces on synthetic charts (OD-28).
    - A support report grading each domain supported, partial or unsupported.

11. **Memory:** the existing opt-in P5 memory works unchanged. Automatic memory stays in M5.

### 5.2 Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| M3-AC1 | **Routing.** For the allow-listed account, the trace shows the agent path and zero calls into `chat/llm_engine.py::generate_answer`. A non-allow-listed account uses legacy. | Trace + test |
| M3-AC2 | **Factual shortcut, all domains.** For example "Who is my 7th lord?", "Where is Jupiter in D9?" and "What is my current mahadasha?" are answered through the UI with zero LLM calls, and the values match the M1/M1b references. | Trace + test |
| M3-AC3 | **Domain recognition.** On a locked set of ≥40 synthetic questions (≥3 per owner domain, ≥6 mixed-domain, ≥4 out of scope), labels match the expected domains in ≥90% of single-domain questions. Every mixed question receives ≥2 correct domains. Run once live on the M3 model, cost-capped (OD-27). | Labelled-set report |
| M3-AC4 | **No career boundary.** No code path rejects a question for not being career or business. Offline tests cover a question in every owner domain reaching investigation. | Grep + tests |
| M3-AC5 | **Guidance is data.** `domains.v0.yaml` is schema-validated and covers every domain. Vocabulary notes stay within ≤8 per domain and ≤100 in total. The orchestrator and planner contain **no** domain-name branches and no domain-specific tool sequences, and Python has no synonym replacement table. | Schema test + grep test + code-review note |
| M3-AC6 | **New tool wrappers.** `get_jaimini_facts` returns the 7 karakas and AL/UL identical to the existing calculations (parity tests on R1–R5). Yogas and all 12 lords appear as facts. **No calculation module changes:** `git diff` of `charts/astro_engine.py` and `astrology/calculations/*` is empty. | Tests + diff |
| M3-AC7 | **Minimum investigation.** In every trace, the guidance minimums for the labelled domains are satisfied before publication. In ≥3 traces the model requests an optional tool beyond the minimums, showing it is not a fixed script. | Policy-coverage report |
| M3-AC8 | **Targeted search terms.** Search texts are written by the model, not template-joined. In the weak-topic traces (Chara Dasha, Saturn's 10th-house influence, Rahu antardasha), at least one search uses book vocabulary identified in M2 ("Pada", "AmK", "sub-period" or "Xth House"). | Traces |
| M3-AC9 | **Iterative retrieval.** An offline test seeds a weak first result (all scores below τ) and shows a refined or decomposed second search. Searches stop at the cap. ≥1 live trace shows a refinement. Every search is in the ledger. | Test + trace + ledger |
| M3-AC10 | **Three non-answer states.** Offline tests produce each of `retrieval_failed`, `no_source_support` and `calculation_unavailable` (the latter for at least muhurta, kundli matching and shadbala). Each publishes its own disclosure wording. None publishes an invented value, citation or calculation. | Tests |
| M3-AC11 | **Claim scanner (G-1)** reports 0 unverified astrological values in every published answer. Seeded invented placements, including in a non-career domain, are blocked. | Traces + tests |
| M3-AC12 | **Citations (G-2, OD-11).** 0 citations without a matching hit. No published answer contains a 12-word run copied from a retrieved passage (M2 leak check applied to answers). Books are named, never quoted. | Traces + tests |
| M3-AC13 | **Guardrails.** G-3 to G-5 pass: no event probabilities; confidence given as evidence strength with a reason. The sensitive-domain policy (OD-23) holds: health answers make no diagnosis and include the agreed note; no death or longevity prediction; fertility and childbirth wording follows the agreed policy. | Validator output + tests |
| M3-AC14 | **Natural answers.** Published answers carry no mandatory section headings. The validator passes answers that contain the required content elements (§5.1 item 9) and fails answers that lack them. A test shows a heading-free answer passing. | Tests + sample answers |
| M3-AC15 | **Domain end-to-end matrix (§5.4).** Offline: one scripted end-to-end test per owner domain (11) plus ≥3 mixed-domain tests, all green. Live: one consultation per owner domain plus 2 mixed-domain ones (13 in all) on synthetic charts. The report grades each domain using the §5.4 definitions. | Tests + traces + support report |
| M3-AC16 | **Tokens.** Provider-reported tokens are recorded per round. Envelope (proposed, OD-27): the largest round ≤25k input tokens, ≤6 model rounds and ≤4 searches per consultation. | Usage table |
| M3-AC17 | **Cost.** Each consultation ≤ the per-consultation cap. M3 total paid spend ≤ the M3 cap (OD-27). Every call is in the ledger; no call bypasses the meter. | Ledger extract |
| M3-AC18 | **Failure paths.** Provider timeout, retrieval failure and validator failure each give a partial, unbilled answer with no raw error text. | Tests (+ trace if observed) |
| M3-AC19 | **Ownership.** A forged chart ID is overridden to the session chart, and a follow-up chart change is rejected. Existing tests pass. | Tests |
| M3-AC20 | **Latency** is recorded end to end and per round. There is no pass/fail threshold until OD-14. | Traces |
| M3-AC21 | **Rollback.** Removing the account from the allowlist routes its next question to legacy with no deploy. Setting `ASTROGPT_RETRIEVAL_ADAPTER=hosted` switches retrieval. Both are demonstrated. | Traces |
| M3-AC22 | Full suite green | Test output |

### 5.3 Rollback

- Remove the user from the allowlist, or set `ASTROGPT_AGENT_ENABLED=false`.
- Retrieval: set `ASTROGPT_RETRIEVAL_ADAPTER=hosted`.
- Guidance: pin `domains.v0.yaml` to its previous version.
- Revert the M3 commits if needed. Any allowlist migration is reversible.

### 5.4 Domain support grading and expected starting position

**Definitions** used by the M3 support report:

- **Supported:** the domain's core factors are computed: domain houses and lords, the domain varga, and the current dasha. The deterministic rule category has ≥5 rules. The live trace retrieves ≥1 passage judged relevant, and validation passes without repair.
- **Partial:** answerable and validated, but with at least one gap:
  - fewer than 5 rules for the category;
  - a varga with no rules;
  - no relevant retrieval (`no_source_support`);
  - a secondary calculation unavailable (for example compatibility matching).
  The answer must disclose the gap.
- **Unsupported:** a core calculation is missing. The agent declines that part with `calculation_unavailable`.

**Expected starting position (INFERRED from the code inventory; to be confirmed by M3 traces).** Rule counts are rules tagged with the category across the YAML rule files.

| Domain | Rules | Varga rules | Book coverage (local text, offline count) | Expected grade | Main gap |
|---|---|---|---|---|---|
| Career | 63 | D10 (Python + YAML) | Strong | Supported | Weak topics from M2 (Chara Dasha, Saturn on the 10th) |
| Business | 15 | D10 | Good | Supported | |
| Marriage | 12 | D9 | Strong; UL and DK thin (1 book) | Supported once the Jaimini tool is added | Compatibility matching unavailable |
| Relationships (non-marital) | via marriage | D9 | Moderate | Partial | No dedicated rules |
| Children | 12 | D7 | Strong | Supported or Partial | PK needs the Jaimini tool |
| Childbirth timing | via children | D7 | **Thin** (≈40 mentions, 1 book) | Partial | Timing relies on dasha and transits only |
| Education | 7 | D24 | Good | Partial | Thin rules |
| Wealth | 7 | D2 | Strong | Partial | Thin rules |
| Health | 9 | D30 | Good; D30 thin | Partial | Sensitive-domain policy; no strength metrics |
| Foreign settlement | 3 | D4, D9 | Good | Partial | Very few rules |
| Property | 11 | D4, D16 | Good | Supported | |
| Spirituality | 3 | D20 | Moderate | Partial | Very few rules |
| Muhurta, matching, prashna, longevity | – | – | – | **Unsupported** | Not calculated, or excluded by policy |

"Partial" is an acceptable M3 outcome when the gap is disclosed. Closing gaps means owner-approved rules (post-M4) and corpus work, not prompt changes.

---

## 6. M4: Career methodology benchmark and answer quality

> **Revision 2 (2026-11-11).** Career is the **detailed benchmark** that tests how deep the general agent can go. It is not the product boundary (R9). The scope and criteria below are otherwise unchanged from 2026-11-10, except that the career policies now **extend** the general `domains.v0.yaml` guidance rather than replacing it.

**Goal:** detailed career consultations that investigate the four owner-named situations. They use Vimshottari, D10, Chara, Yogini and transits **selectively**, according to the question and the evidence found. The methodology is guidance plus minimum investigation, not fixed predictions.

### 6.1 Scope

1. **Methodology policies as data:** `astrology/methodology/career.*.v1.yaml`, one per sub-question. They extend the general `domains.v0.yaml` career entry from M3: `promotion`, `voluntary_change`, `involuntary_change` (disruption or job loss) and `foreign_relocation`. Each lists:
   - **minimum investigation requirements**: factors that must be checked before an answer can be published;
   - **optional factors** the model may request;
   - **conflict-handling guidance**;
   - **source hints** (which books to search).
   Claude drafts them from the existing rule files and the books, paraphrased with references only. **The owner approves each policy's astrological content before use** (OD-18). They are not treated as validated by default.
2. **Sub-question classification** by the model, with a deterministic fallback. Mixed questions (for example "should I move abroad for a better job?") combine policies.
3. **Selective systems:** the agent chooses Vimshottari MD/AD/PD, D10, Chara (with Amatyakaraka and Arudha Lagna), Yogini and transits according to the policy minimums and the evidence gaps. A Yogini or Chara check that the policy does not require is not forced into every answer.
4. **Independence-aware agreement** (OD-9): evidence items carry `roots`, so the same underlying factor (for example the 10th lord in the D1 rule set and again in the D10 Python rules) is not counted as two agreements (`astrology/rules/scoring.py:10-20`; `astrology/services/prediction_service.py:152-163`). Legacy scores are left untouched.
5. **Interpretive-support validation** (extends M3):
   - each conclusion must link to ≥1 evidence ID;
   - strong conclusions need ≥2 independent roots, or must be stated with hedged wording;
   - a literature-based claim must cite a retrieved hit;
   - contradictions between systems must be stated, not omitted.
6. **Time windows:** multiple-period comparison for "when" questions, with the AGENTS.md preliminary-muhurta disclosure where it applies (G-7).

### 6.2 Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| M4-AC1 | Four owner-approved policy files exist, versioned, with changelogs. Python contains no event-type-to-verdict mapping (G-6). | Files + code review note |
| M4-AC2 | For each of the 4 sub-questions, ≥3 real UI traces on synthetic or owner-consented charts, 12 or more in total. Each trace shows the policy minimums satisfied, plus ≥1 model-requested optional tool in at least 4 of the traces (the method is not a fixed script). | Traces + policy-coverage report |
| M4-AC3 | Selective system use is visible: traces show different system combinations for different sub-questions. Each answer explains why each system used is relevant. | Traces |
| M4-AC4 | Claim scanner: 0 unverified values in all published answers. The P6 seeded-error cases (`astrology/evaluation/fixtures/p6_cases_v1.json`) are all blocked. | Harness output |
| M4-AC5 | Interpretive-support validator: 0 unsupported conclusions in published answers. Seeded unsupported conclusions are blocked. | Harness output + tests |
| M4-AC6 | Double counting: a test chart where one factor appears in both YAML and Python rules is reported as **one** independent root | Test |
| M4-AC7 | Where systems disagree, the answer contains an explicit conflicting-signals passage (checked by validator and rubric) | Validator + rubric |
| M4-AC8 | **Astrologer review:** the owner scores the 12+ answers on a rubric with six dimensions, each scored 1–5: factual accuracy, methodological appropriateness, use of literature, handling of contradictions, clarity/naturalness, and no overclaiming. Proposed pass level: mean ≥4.0, no dimension below 3 on any answer, and zero factual errors. | Completed rubric |
| M4-AC9 | Cost and size: provider-reported usage per consultation is within the OD-7 envelope for every trace. Outliers are explained. | Usage table |
| M4-AC10 | The report explicitly states that the rubric scores are expert judgement on a small sample, not empirical validation of predictive accuracy | Report text |
| M4-AC11 | Full suite green, with the M3 criteria re-run | Test output |

### 6.3 Rollback

Pin the career guidance back to the general `domains.v0.yaml` career entry (M3 behaviour) by setting, or remove users from the allowlist. Revert the M4 commits if needed.

---

## 7. Remaining owner decisions

| ID | Decision | Recommendation | Needed by |
|---|---|---|---|
| **OD-8** | Dasha boundary convention for all surfaces | Half-open `[start, end)`: a new period begins on its start date and the old one ends the day before | M1 start |
| **OD-10** | Swiss Ephemeris data files (`.se1`) vs the built-in Moshier mode | Provision `.se1` files and set the path. Otherwise accept Moshier and disclose it in the method profile. | M1 start |
| **OD-15** (new) | Source of reference calculations for M1 | (a) You supply printouts from established software (for example Jagannatha Hora) for 3–5 synthetic or public-record charts, with the settings stated, **and** (b) planetary longitudes are cross-checked against a second astronomical library added as a **test-only** dependency (needs your approval as a dependency change). Name the Chara dasha school to verify against. | M1 start |
| **OD-20** (new) | Include the chart-recalculation-on-GET fix (P-3) in M1 | Yes: small, low risk | M1 start |
| **OD-5a** | Approve one read-only vector-store listing call, plus a paid M2 evaluation cap | Approve, with a cap of US$3 | M2 start |
| **OD-11** | Source rights: which books may be quoted or cited to paying users, and whether `300 Astrology Yoga _ … _ Astrotalk.pdf` (an apparent website capture) stays in the store | Cite by title and paraphrase only until rights are confirmed. Consider removing the website capture. | M2 end / before M3 user-facing citations |
| **OD-7** (revised) | Model(s) and prices. Only `gpt-4o-mini` is priced today (`accounts/usage_policy.py:5-7`). | **`gpt-4o-mini` for every M3 round** (agent, labelling, repair). Compare a stronger composer only in M4, with separate approval and prices you supply. | M3 start |
| **OD-17** | Allowlist mechanism | Setting-based list of user IDs for M3 (no migration). Move to an admin-managed flag in M7. | M3 start |
| **OD-16** (now required by R10) | Answer format vs AGENTS.md. AGENTS.md requires 12 mandatory sections and names career/business as the MVP scope. | Amend AGENTS.md: answers are conversational prose that must **contain** a direct answer, timing (when asked), the factors used, conflicts and an evidence-strength label. The per-system basis moves to the evidence panel. The MVP clause becomes "general-purpose; career is the M4 benchmark". The "mandatory evidence by question type" lists become the minimum-investigation data in `domains.v0.yaml`. | M3 start |
| **OD-14** | Synchronous execution with status polling; background worker only if p95 latency exceeds your threshold | Approve. Set the threshold after M3 latency data is available. | M3 end |
| **OD-9** | Count agreement by independent roots in the agent; leave legacy scores untouched | Approve | M4 start |
| **OD-18** (new) | Your review time for the 4 career policies and the 12-answer rubric review, and approval of the rubric itself | Plan about 2 review sessions | M4 |
| **OD-19** (new) | Remote push: verify whether `github.com/sks6184/AstoWebsite` is private and is the intended destination, before any push | Claude can check visibility read-only via `gh` when you ask; no push without your approval | Any time |
| OD-21 (new) | Branch/merge policy | Milestone branches from the preservation branch; merge into local `main` only after your sign-off at each milestone | M1 start |
| **OD-22** (new) | Domain list and mapping (§5.1 item 2). Relationships map to `marriage`, childbirth to `children`, foreign settlement to `foreign_travel`, wealth to `money`. Should `family`, `vehicle` and `legal_and_enemies` stay? | Approve the mapping and keep all 13 categories plus `general`. Re-split relationships from marriage only once dedicated rules exist. | M3 start |
| **OD-23** (new) | Sensitive-domain policy | **Health:** no diagnosis or treatment advice, plus a short note recommending a qualified professional. **Death and longevity:** decline. **Fertility and childbirth:** no certainty claims; supportive wording; timing only as indications. **Legal:** no legal advice. You approve the exact wording. | M3 start |
| **OD-24** (new) | Review of the astrological content of `domains.v0.yaml` (houses, karakas, vargas, Jaimini points, minimums, vocabulary) | Claude drafts it from `CATEGORY_RULES`, the rule files and the M2 term counts; you review it before live traces. About one review session. | Before M3 live traces |
| **OD-25** (new) | New tool wrappers: `get_jaimini_facts`, yogas in chart facts, all 12 house lords in the fact catalog | Approve. They expose existing calculations only; no calculation code changes. | M3 start |
| **OD-26** (new) | Retrieval limits: weak threshold τ and the search cap | τ = 0.70 (weakly supported by M2) **plus** the model's judgement; at most 4 searches per consultation; at least 3 passages per search | M3 start |
| **OD-27** (new) | M3 budgets | **Per consultation:** ≤6 rounds, ≤4 searches, largest round ≤25k input tokens, ≤US$0.05. **M3 total paid cap: US$1.00** (about US$2.27 of your API balance is estimated to remain, INFERRED). Covers 13 live end-to-end traces, the 40-question labelling check and repair or retry headroom. | M3 start |
| **OD-28** (new) | Charts for live traces | Synthetic reference charts R1–R5 only. Your own chart only with explicit per-run consent; never committed. | M3 start |
| **OD-29** (new) | Out of scope for M3, declared `calculation_unavailable` | Muhurta and panchanga, kundli matching, shadbala, prashna, longevity | M3 start |
| **OD-30** (new) | M2 billing reconciliation | Compare the OpenAI dashboard for 2026-11-11 with US$0.0743. It settles the direct-search price used in budgets. | Before the M3 live phase |

Unchanged in placement: automatic memory (OD-6) stays in **M5**. M3 keeps the existing opt-in memory working, so M3 does not have to deliver the privacy controls for automatic memory.

---

## 8. Differences from `CLAUDE_MILESTONE_GAP_MAP.md`

| Area | Gap map | Revised |
|---|---|---|
| M1 | Calculation integrity and contracts | Adds all legacy-path security fixes (S-2, S-3, S-4, S-5, S-8, S-9) and explicit reference tolerances |
| M2 | Retrieval interface | Owner relevance labelling, plus a passage-accuracy check against the local books |
| M3 | Kept the closed-slot composer; prose deferred to M4 | **Revision 2:** a general-purpose multi-domain agent with model-led domain labelling, data-driven guidance, agent-written iterative retrieval, three non-answer states, natural answers, and a domain end-to-end matrix. Prose and claim/citation validation stay in M3. |
| M4 | General career policies | Career is the **detailed benchmark**: four named sub-question policies extending the general guidance, interpretive-support validation, and an astrologer rubric |
| All | Exit evidence per milestone | Standard evidence pack (§2.1) and epistemic guardrails G-1 to G-8 |

---

**Next step:** you approve or amend revised §5–§6 and decide OD-7, OD-16, OD-17 and OD-22 to OD-30. M3 then starts on `claude/m3-general-agent` with a scope record (`docs/claude_migration/M3_SCOPE.md`). Until then no M3 application code is written.
