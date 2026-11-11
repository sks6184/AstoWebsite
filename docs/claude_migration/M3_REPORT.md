# M3 report: general-purpose agent, offline implementation (stage 1)

- **Branch:** `claude/m3-general-agent`. The base is `bf5016c`; this report covers the work after `f08563f`.
- **Scope:** `docs/claude_migration/M3_SCOPE.md` (offline only).
- **Status:** stage 1 of the staged plan (§5.6) is complete. It awaits your review.
- **No paid calls, no live tests, no pushes or merges, and no dependency installs were made.** All M3 tests are offline: the provider is scripted, the retrieval adapter is synthetic, and the network and OpenAI client are blocked.
- **Offline tests show pipeline behaviour only.** They are not evidence of astrological correctness or of `gpt-4o-mini`'s capability.

## 1. What was built

| Scope item | Implementation |
|---|---|
| 1. Profile revision 3 | `astrology/methodology/domains.v0.yaml` (content in `f08563f`). Structural additions are in `M3_DOMAIN_PROFILE_CHANGES.md` §6: stable IDs for unavailable calculations, an `out_of_scope` question type, and user-facing disclosures (drafts) |
| 2. Profile loader and validator | `astrology/methodology/profile.py`. It checks the schema, the closed label lists, the vocabulary bounds (67 of 100), and the categories, vargas and planets the tools accept. It rejects tool-sequence and verdict wording, and never returns `research_annex` |
| 3. Read-only tools | `get_jaimini_facts`, `get_counted_sign` (OD-31), `get_natal_aspects` (OD-32), `include_yogas`, and the house from the Moon in transits (OD-33). All are in `f08563f`; parity tests are added here (§3) |
| 4. Fact catalog | `build_catalog(evidence, full=True)` is opt-in. It publishes all 12 house lords, nakshatras, retrograde state and dignity, and the fact kinds karaka, Karakamsha, pada, Jaimini yoga, counted sign, aspect, yoga and Moon-based transit house. The P3 default output is unchanged |
| 5. General agent | `astrology/agent/general.py` and `general_provider.py`:<br>- one model, with structured-output rounds that can **batch** requests;<br>- labelling folded into round 1;<br>- any authorized tool may be requested;<br>- at most 6 rounds (including one repair), 4 searches, and 25k counted input tokens per round, checked with `tiktoken` before each call;<br>- the factual shortcut (`astrology/agent/factual.py`) answers any house lord, a placement in any computed varga, or the running Vimshottari, Yogini or Chara period with **zero LLM calls** |
| 6. Retrieval | The model writes the query (at most 200 bytes). The 0.70 flag is advisory and recorded per search. The model's relevance judgements are recorded. There are three separate non-answer states with fixed wording, plus a "not searched" disclosure |
| 7. Prose validation | `astrology/validation/prose_validator.py`:<br>- claim scanner (G-1) over inline `[F…]` fact tags;<br>- citation checker (G-2), title match and 12-word copy check (OD-11);<br>- probability, certainty, diagnosis, death or longevity, fertility and remedy guards (G-3 to G-5, A8);<br>- content elements, not headings;<br>- core-factor coverage.<br>One repair round; otherwise a deterministic evidence report, marked partial and unbilled |
| 8. Routing (A7) | `chat/agent_service.py`. `ASTROGPT_AGENT_USERS` (empty by default) routes to the general agent; everyone else uses legacy. P3 is reachable only with `ASTROGPT_AGENT_P3_COMPAT=true`, which the existing P3 tests now set explicitly |
| 9. Pilot policy | `agent_pilot` in `accounts/usage_policy.py`: 6 rounds, 4 searches, US$0.05. It is reserved only for allow-listed accounts (`accounts/usage.py`) |
| 10. Tests and traces | `astrology/test_m3.py` (38 tests). There are 21 synthetic traces in `docs/claude_migration/m3_traces/`, regenerated with `ASTROGPT_WRITE_M3_TRACES=1` |

## 2. How an answer is produced

1. **Routing and shortcut.** Only an allow-listed account reaches the general agent. A plain factual question is answered from one tool result, with zero model rounds.
2. **Round 1.** The model receives:
   - the closed label menu (question types, the 16 domains with their event IDs, and the unavailable-calculation IDs);
   - the tool menu.

   It labels the question and may batch evidence requests.
3. **Later rounds.** The server sends:
   - the guidance for **only** the labelled domains and events;
   - the core factors;
   - per-evidence digests and the fact atoms;
   - the passages with scores and the advisory flag.

   The payload is rebuilt each round rather than accumulated, and is compacted once if it exceeds the limit.
4. **Final answer.** The model returns a direct answer, a body, conflicts, an evidence-strength label with a reason, core-factor coverage, the unavailable-calculation IDs it needs, and a `no_source_support` flag.
5. **Validation and publication.** The validator checks the final answer, and the server then renders it. Fact tags become `[n]` references with a fact list at the end. Source tags become "(source: title, chapter n)". The server adds the fixed disclosures:
   - the non-answer states;
   - the AGENTS.md preliminary-timing text for timing and comparative questions;
   - the G-4 agreement note;
   - the attestation note when a labelled event has a `basis_note`;
   - the domain disclosures.

## 3. Acceptance criteria (offline evidence; live items not run)

| ID | Offline result | Live part |
|---|---|---|
| AC1 Routing | **Pass.** An allow-listed account goes to the agent; `chat.llm_engine.generate_answer` is patched to fail and is never called; others use legacy | Not run |
| AC2 Factual shortcut | **Pass.** The 7th and 4th lords (checked against an independent sign-lord count), Jupiter in D9, and the current Vimshottari and Yogini periods each take 0 rounds. Also tested through the `/chat/` UI for an allow-listed account | – |
| AC3 Labelling | **Offline pass.** A locked set of 48 questions (`astrology/evaluation/fixtures/m3_labelled_questions_v1.json`): ≥3 per primary domain, 6 mixed, 4 out of scope and 4 distinction pairs. Unknown labels are rejected; the strict schema uses the same closed enumeration. **The expected labels are my draft and need your review** | Stage 2 only |
| AC4 No career boundary | **Pass.** Every primary domain reaches investigation and publication | – |
| AC5 Guidance is data | **Pass.** Schema and bounds tests; injected tool-sequence and verdict wording is rejected. A grep test shows no domain-name literals in the general agent, profile, validator or shortcut code. A model-chosen tool outside the suggestions (`get_ashtakavarga` for marriage) is accepted. **Your approval of the profile (OD-24) is still open** | – |
| AC6 Wrapper parity | **Pass on R1–R5:**<br>- Jaimini karakas (7, no nodes), Karakamsha, all 12 padas and Jaimini yogas are identical to `jaimini.py`;<br>- yogas are identical to `chart_data['yogas']`;<br>- the 12 lords equal an independent sign-lord count;<br>- counted signs equal a hand count (inclusive);<br>- aspects equal `vedic_utils`;<br>- unsupported requests (pratyantardasha, an unknown reference, shadbala) return `unsupported`.<br>The `git diff` of `charts/astro_engine.py`, `charts/yogas.py` and `astrology/calculations/` since `bf5016c` lists only the new, additive `counted_signs.py` | – |
| AC7 Core-factor coverage | **Offline pass.** A missing factor fails validation; "unavailable" with a reason is accepted | Not run (needs live traces) |
| AC8 Targeted search terms | **Offline pass.** The trace queries equal the model's text; the refined weak-topic search uses "Pada" and "AmK" | Not run |
| AC9 Iterative retrieval | **Pass for (a) to (d):**<br>- (a) a weak result is refined;<br>- (b) a 0.55-score passage judged relevant is used with no further search;<br>- (c) one search ends retrieval in 3 rounds;<br>- (d) the 5th and 6th searches are refused at the ceiling | Not run |
| AC10 Non-answer states | **Pass.** `retrieval_failed` (adapter timeout), `no_source_support` (searches succeeded, judged not relevant) and `calculation_unavailable` (muhurta, kundli matching, shadbala, and a tool `unsupported` result) each have their own wording. Longevity is declined by policy | – |
| AC11 Claim scanner | **Pass.** A seeded invented placement (the 7th lord in Scorpio in the 12th) and an untagged "Moon in Leo" in a marriage answer go to repair; if the repair repeats them, a server report is published instead | Not run |
| AC12 Citations | **Pass.** An invented K ID and an uncited book mention are blocked, a cited title that does not match the hit is blocked, a copied 12-word run is detected, and a correct citation passes | Not run |
| AC13 Guardrails | **Pass.** Probabilities, certainty, illness naming, death or maraka, infertility and gemstone remedies are blocked; "no guarantee" and the sign Cancer are not. The health and fertility disclosures are present | – |
| AC14 Natural answers | **Pass.** A heading-free answer passes; a missing direct answer, a missing strength reason, missing coverage or a `#` heading fails | – |
| AC15 Domain matrix | **Offline pass:** 12 domains, 3 mixed questions and 2 distinction pairs. **Every domain's grade is "Not yet demonstrated"** (§5.4) | Stages 1 and 2 not run |
| AC16 Tokens | **Pass.** Each round records the counted and provider-reported tokens and the latency; 6 rounds at most; an oversized round is refused before any call. Largest counted round in the traces: **16,223 tokens** (a three-domain mixed question) | Not run |
| AC17 Cost | **Offline:** allow-listed reservations use `agent_pilot` (US$0.05, 6 rounds, 4 searches); a meter refusal gives a partial, unbilled answer. The worst-case reservation per consultation is about US$0.043 (6 × (29.4k in + 1.8k out) at the published tariff, plus 4 × US$0.0025 per search) | Not run |
| AC18 Failure paths | **Pass.** Provider timeout, spending refusal, provider error, retrieval failure and validator failure all give a partial result with no raw error text | – |
| AC19 Ownership | **Pass.** A forged chart ID is overridden and traced; a follow-up about another person is rejected; an ownership change mid-consultation publishes nothing | – |
| AC20 Latency | Recorded per round and in total | Not run |
| AC21 Rollback | **Pass.** An empty allowlist or `ASTROGPT_AGENT_ENABLED=false` routes to legacy; `ASTROGPT_RETRIEVAL_ADAPTER=hosted` selects the hosted adapter | Not run |
| AC22 Full suite | See §4 | – |
| AC23 Model capability | – | Not run (needs live consultations) |

## 4. Tests

- `astrology.test_m3`: **38 tests, all pass.**
- Full suite: **409 tests, OK (1 skipped)**. The baseline before this work was 371. The skip is the pending Jagannatha Hora reference test (M1), and a skip is not a pass.
- Existing P3 tests are unchanged, apart from adding `ASTROGPT_AGENT_P3_COMPAT=True` next to `ASTROGPT_AGENT_ENABLED=True` (5 files). That is the explicit compatibility setting the scope requires.

## 5. Findings for your decision

| # | Finding | Recommendation |
|---|---|---|
| M3-F1 | The career-only `ScopeError` in `astrology/agent/policy.py` remains in the **P3 compatibility path**, which spec §5.1 item 2 said to remove. It can no longer be reached by default or for allow-listed users. Removing it would change P3 behaviour that its tests pin | Keep it until P3 is retired; delete it together with P3 after M4 |
| M3-F2 | The claim scanner is pattern-based. It recognises English and common Sanskrit planet, sign, nakshatra and varga names, ordinals, "house N", dates and numbers. It may **over-block** derived-house sentences ("the 12th from the 10th"), because both ordinals must appear in the tagged facts. It cannot judge meaning | Accept for M3. Measure the over-blocking in the live traces before adjusting |
| M3-F3 | The AGENTS.md checks for spelling and grammar are not implemented (they cannot be done deterministically) | Leave them to the M4 rubric |
| M3-F4 | AGENTS.md still mandates 12 fixed sections, but M3 publishes natural prose (R10, OD-16). AGENTS.md was **not** edited | Approve the OD-16 amendment wording separately |
| M3-F5 | The hosted rollback works, but each hosted search is a full-context model call (about US$0.019 reserved), which uses up the 6-round and US$0.05 envelope faster | Accept: hosted is a rollback only |
| M3-F6 | New user-facing disclosure texts, the `out_of_scope` wording, the 12-month default window and the labelled-set expected labels are all **drafts** | Review the wording (`M3_DOMAIN_PROFILE_CHANGES.md` §6) |
| M3-F7 | Follow-up continuity in the general agent passes conversation memory to the model as untrusted context and rejects chart changes. It does not inherit P3's date windows or topic | Accept for M3; automatic memory is M5 |

## 6. Privacy and content

- Only synthetic charts (the sample chart and R1–R5) and synthetic passages written for the tests are used. The owner's chart is not used.
- No book text is committed.
- The traces contain only synthetic data.

## 7. Rollback

- Leave `ASTROGPT_AGENT_USERS` empty (the default), or set `ASTROGPT_AGENT_ENABLED=false`.
- Retrieval: `ASTROGPT_RETRIEVAL_ADAPTER=hosted`.
- Revert the M3 commits if needed. There are no migrations.

## 8. Next step (needs your approval)

**Stage 2 (A9):** three live consultations (career, marriage, children) on synthetic charts.
- Limits: at most US$0.05 each and US$0.15 in total, with `gpt-4o-mini`.
- The allowlist would hold a synthetic pilot account only.
- Then review the answers, traces, model-capability notes (AC23) and the actual spend with you before any expansion.

Before stage 2, please confirm:
- the profile (OD-24);
- the draft disclosure wording;
- findings M3-F1 to M3-F7.
