# AstroGPT: Revised M1–M4 Acceptance Criteria

Status: **proposal, awaiting owner approval**. No application code has been changed.
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

## 5. M3: A working LLM-led agent in the real Django UI

**Goal:** an authorized pilot account uses the actual `/chat/` UI. Its questions go to the agent, not the legacy pipeline. It receives at least one **natural-language interpretive consultation** written by the model from calculated facts and M2-retrieved literature, validated and bounded in cost. This change from the gap map moves a **minimal** grounded-prose composer and claim scanner from M4 into M3.

### 5.1 Scope

1. **Per-user routing** (OD-17): only allow-listed users reach the agent (`chat/agent_service.py`). Everyone else stays on legacy.
2. **Planner:**
   - The deterministic shortcut is extended to all house lords and simple placement or dasha lookups, with zero LLM calls.
   - Interpretive questions get an LLM scope proposal. The minimum investigation set comes from a draft `career.general.v0` policy file, and the model may request additional tools.
3. **Compact evidence:** `EvidenceItem` digests are sent to the model, not raw tool output. The model can expand one by ID. The payload is per round, not cumulative. The pre-dispatch check counts tokens with `tiktoken`, not bytes (fixes `astrology/agent/orchestrator.py:204-209`, `astrology/agent/provider.py:48-51`).
4. **Iterative calls:** the model may alternate deterministic tool calls and retrieval calls (M2 adapter), within round, search and token limits.
5. **Answer composition:** the model writes the prose with inline fact tags. The claim scanner (G-1) and citation checker (G-2) verify it. A failed check triggers one repair round; if that fails too, the user gets the deterministic evidence report, marked partial and **unbilled** (existing behaviour in `chat/consultation_service.py:132-135`). The closed-slot `astrology/synthesis/verified_answer.py` stays only as that fallback.
6. **Budgets** (OD-7): a per-consultation envelope for the pilot plan, sized so that a career consultation fits. This fixes the conflict between 2 rounds / 1 search / 160k tokens and a 128k reservation per search (`accounts/provider_meter.py:38`). The search reservation is based on the measured search cost from M2, not the full context.
7. **Memory:** the existing opt-in P5 memory (`chat/memory.py`) works unchanged for follow-ups. Automatic memory remains M5.

### 5.2 Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| M3-AC1 | Routing proof: for the allow-listed account, the trace shows the agent path and **zero** calls into `chat/llm_engine.py::generate_answer`. For a non-allow-listed account, legacy is used. | Trace + test |
| M3-AC2 | Factual shortcut: "Who is my 7th lord?" and "Where is Saturn in D10?" are answered through the UI with **zero** LLM calls, and the values match the M1 reference fixtures | Trace |
| M3-AC3 | **Interpretive consultation:** at least one career question, for example "How does my career look over the next two years, and is a change likely to help?", is answered in natural-language prose. The answer: is not assembled from canned sentences; cites specific tool-computed factors (houses, lords, D10, the current MD/AD); and uses ≥1 retrieved passage from the store, cited by source. | Trace + stored answer + rendered UI screenshot |
| M3-AC4 | The claim scanner reports 0 unverified astrological values in the published answer. A seeded test with an invented placement is blocked. | Trace + test |
| M3-AC5 | The citation checker reports 0 citations without a matching hit. A seeded invented citation is blocked. | Trace + test |
| M3-AC6 | Guardrails G-3 to G-5 pass (no event probabilities; confidence given as evidence strength with a reason) | Validator output |
| M3-AC7 | Provider-reported tokens are recorded per round. Proposed targets: the largest round ≤ **25k input tokens**, ≤4 model rounds, ≤2 searches per consultation. The 101,573-token legacy estimate is not repeated. | Usage table |
| M3-AC8 | Cost per consultation ≤ the approved cap (proposed **US$0.25**). Total M3 paid spend ≤ the approved cap (proposed **US$5**). Every call is in the ledger, and no call bypasses the meter. | Ledger extract |
| M3-AC9 | Failure paths, tested offline and observed at least once live if it occurs naturally: provider timeout, retrieval empty, validator failure. Each yields a partial, unbilled answer with no raw error text. | Tests (+ trace if observed) |
| M3-AC10 | Ownership: a forged chart ID in a tool argument is overridden to the session chart, and a follow-up chart change is rejected. Existing tests pass. | Tests |
| M3-AC11 | Latency is recorded (end to end and per round) and reported. There is no pass/fail threshold until OD-14 sets one. | Trace |
| M3-AC12 | Rollback demonstrated: removing the account from the allowlist sends its next question through legacy, with no deploy | Trace |
| M3-AC13 | Full suite green | Test output |

### 5.3 Rollback

Remove the user from the allowlist, or set `ASTROGPT_AGENT_ENABLED=false`. Revert the M3 commits if needed. Any migration added for the allowlist is reversible.

---

## 6. M4: Career methodology and answer quality

**Goal:** detailed career consultations that investigate the four owner-named situations, using Vimshottari, D10, Chara, Yogini and transits **selectively**, according to the question and the evidence found. Methodology is guidance plus minimum investigation, not fixed predictions.

### 6.1 Scope

1. **Methodology policies as data:** `astrology/methodology/career.*.v1.yaml`, one per sub-question: `promotion`, `voluntary_change`, `involuntary_change` (disruption or job loss) and `foreign_relocation`. Each lists:
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

Pin the policy version back to `career.general.v0` (M3 behaviour) by setting, or remove users from the allowlist. Revert the M4 commits if needed.

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
| **OD-7** | Model(s) and budgets. Only `gpt-4o-mini` is priced today (`accounts/usage_policy.py:5-7`). Natural interpretive prose may need a stronger model. | Planner and repair on `gpt-4o-mini`, composer model chosen after a small M3 comparison. You supply current prices for the tariff file. Caps: US$0.25 per consultation, US$5 for M3 in total. | M3 start |
| **OD-17** (new) | Allowlist mechanism | Setting-based list of user IDs for M3 (no migration). Move to an admin-managed flag in M7. | M3 start |
| **OD-16** (new) | Answer format vs AGENTS.md. AGENTS.md requires 12 mandatory sections. You asked for conversational interpretations. | The answer is conversational prose that must still **contain** a direct answer, timing (when asked), the factors used, conflicts and an evidence-strength label. The per-system basis (Parashari, Jaimini, varga, Yogini, RAG) moves into an expandable evidence panel. AGENTS.md is updated to match once you approve. | M3 start |
| **OD-14** | Synchronous execution with status polling; background worker only if p95 latency exceeds your threshold | Approve. Set the threshold after M3 latency data is available. | M3 end |
| **OD-9** | Count agreement by independent roots in the agent; leave legacy scores untouched | Approve | M4 start |
| **OD-18** (new) | Your review time for the 4 career policies and the 12-answer rubric review, and approval of the rubric itself | Plan about 2 review sessions | M4 |
| **OD-19** (new) | Remote push: verify whether `github.com/sks6184/AstoWebsite` is private and is the intended destination, before any push | Claude can check visibility read-only via `gh` when you ask; no push without your approval | Any time |
| OD-21 (new) | Branch/merge policy | Milestone branches from the preservation branch; merge into local `main` only after your sign-off at each milestone | M1 start |

Unchanged in placement: automatic memory (OD-6) stays in **M5**. M3 keeps the existing opt-in memory working, so M3 does not have to deliver the privacy controls for automatic memory.

---

## 8. Differences from `CLAUDE_MILESTONE_GAP_MAP.md`

| Area | Gap map | Revised |
|---|---|---|
| M1 | Calculation integrity and contracts | Adds all legacy-path security fixes (S-2, S-3, S-4, S-5, S-8, S-9) and explicit reference tolerances |
| M2 | Retrieval interface | Owner relevance labelling, plus a passage-accuracy check against the local books |
| M3 | Kept the closed-slot composer; prose deferred to M4 | **Natural interpretive prose + minimal claim and citation validation brought into M3** |
| M4 | General career policies | Four named sub-question policies (promotion, voluntary change, involuntary change, foreign relocation), interpretive-support validation, and an astrologer rubric |
| All | Exit evidence per milestone | Standard evidence pack (§2.1) and epistemic guardrails G-1 to G-8 |

---

**Next step:** after you approve or amend this document and decide OD-8, OD-10, OD-15, OD-20 and OD-21, M1 begins on `claude/m1-calculation-integrity`. Until then no application code will be modified.
