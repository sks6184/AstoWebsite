# M2 report: retrieval evaluation on the existing OpenAI vector store

- Branch: `claude/m2-retrieval-eval`, created from `claude/m1b-calculation-settings` at `02c3708`.
- Scope record: [M2_SCOPE.md](M2_SCOPE.md), committed before code.
- Nothing was pushed or merged, and no dependency was added. `pypdf` 6.10.2 was already installed.
- **This report contains no book passage text.**

## 1. Spend (OD-5a: cap US$1.50)

| Item | Calls | Rated cost |
|---|---|---|
| Store listing (vector-store and file management endpoints) | 9 | US$0 (believed unbilled; **UNVERIFIED**) |
| Hosted `file_search`, adapter (a) | 10 | **US$0.0343** (provider-reported tokens + US$0.0025 per search) |
| Direct `vector_stores.search`, adapter (b) | 10 | **US$0.0250** (US$0.0025 per search, an **assumed**, **UNVERIFIED** price) |
| Post-OCR verification, direct (§3b, session cap US$0.03) | 6 | US$0.0150 (assumed, **UNVERIFIED**) |
| **Total recorded** | 35 | **US$0.0743 of US$1.50** |

How the budget was handled:

- Each call reserved its worst case first: US$0.022 for hosted and US$0.0025 for direct. The tool refuses any call whose reservation would pass the cap.
- **Batch 1** (Q1, Q6, Q9 on both adapters) cost US$0.018. The remaining 7 queries were projected at about US$0.04 (worst case US$0.17), so they were run. **10 queries were run, inside the 8–12 you approved.** The other 14 queries of the original 24 were not run.
- No model answers were generated and no other paid calls were made.
- **Owner check:** compare the OpenAI billing dashboard for 2026-11-11 with US$0.0593.
  - About US$0.034 would mean direct search is not billed per call.
  - About US$0.059 would confirm the assumed price.
  - That result settles the direct-search price.

## 2. Corpus manifest (M2-AC1) — `astrology/evaluation/corpus_manifest.yaml`

The store `AstroVectorStore` has **7 files**, all with status `completed`; none failed. No file carries attributes, so book, chapter and page metadata are unavailable: citations can name only the filename.

| Your list of seven | In store | Local copy | Note |
|---|---|---|---|
| Astrology at the Speed of Light | indexed | yes | **Indexed text size 0 bytes**, and no text can be extracted locally. It is probably a scanned image PDF, so **it never appears in any result**. It needs OCR to be usable. |
| 300 Astrology Yoga (Astrotalk) | **missing** | yes | **Not in the store.** The OD-11 removal question is therefore moot for retrieval. |
| Bhrigu Samhita (T.M. Rao) | indexed | yes | See §3: the store's text does not match the local text layer |
| Conjunctions (Speed of Light) | indexed | yes | |
| Predicting through Jaimini's Chara Dasha | indexed | yes | |
| Vargas: a Vedic approach | indexed | yes | |
| Yogini Dasha | **indexed** | **no** | It **is** in the store, which resolves the M0 question. Accuracy cannot be checked locally. |
| *(not on your list)* **Comprehensive Prediction.pdf** | indexed | no (a `.docx` of that name exists locally) | Returned in 11–12 of 50 hits per adapter. **Please confirm what it is and whether it should stay.** |

## 2a. Corpus repairs after the runs (owner, 2026-11-11, offline-verified)

| Book | Problem | Repair | Verification |
|---|---|---|---|
| Astrology at the Speed of Light | Image-only PDF: 168 pages of image strips, no text. It was not an encoding or indexing fault | Owner OCR'd it with Acrobat 25 "Searchable Image" and replaced it in the store: `file-TSawiimAWugZ1piVARaPBK` | 168 pages, invisible text layer, about 48.6k words. Terms and ordinals read correctly. 97–100% word agreement with an independent Tesseract sample. Store reports **473,263 indexed bytes (was 0)** |
| Bhrigu Samhita | Local text layer did not match the indexed text | Owner re-OCR'd it with Acrobat and replaced it in the store: `file-HR68gd6Uz7rAVfjqTs2HED` | 304 pages, invisible text layer, about 66.5k words. Old store hits now match the local text at 0.77–0.96 (was 0.00–0.01) |
| Comprehensive Prediction | No local copy | **Retained** (owner: divisional-chart reference associated with V. P. Goel); local copy added | Same byte size as the store file; 23/23 hits match |
| Yogini Dasha | No local copy | Local copy added | Same byte size as the store file; 11/13 hits match. The other two are table-heavy chunks |

- All changes are recorded in `corpus_manifest.yaml`.
- **The relevance runs in §3 predate these repairs:** Speed of Light could not appear in them, and Bhrigu hits came from the old file.
- **Originals were overwritten in place by Acrobat.** A pristine Speed of Light original remains in the owner's `portable_rag_project`. For Bhrigu, only the Internet Archive ABBYY XML remains.

## 3. Retrieval results (10 queries × 5 hits × 2 adapters)

| Measure | Hosted `file_search` (a) | Direct search (b) |
|---|---|---|
| Queries completed | 10/10 | 10/10 |
| Mean latency | **8.7 s** | **2.2 s** |
| Cost per query | US$0.0034 (measured) | US$0.0025 (assumed) or less |
| Mean input tokens | 4,733 | 0 (no model round) |
| Passage accuracy: hits matching the attributed local book at a 5-word-shingle score of 0.6 or more (M2-AC3) | 28/33 = **84.8%** | 28/31 = **90.3%** |
| Hits from books with no local copy (Yogini Dasha, Comprehensive Prediction) | 17 | 19 |
| Misattributed hits (text matching a *different* local book) | **0** | **0** |
| Mean relevance@5 (0–2 scale, 50 rated hits each) | 0.88 | **0.94** |
| Mean relevance@3 (the agent's default `result_count` is 3) | 0.90 | 0.93 |
| Mean relevance of the rank-1 hit | **1.20** | 0.90 |
| nDCG@5 within each list (ranking quality) | **0.877** | 0.750 |
| Hits rated 1 or more | 62% | 64% |
| Queries with at least one hit rated 2 | 6/10 | **7/10** |
| Queries with no hit rated 1 or more in the top 3 | 0 | 0 |

- **Overlap:** the two methods share 32 of 50 hits. On Q1 the hosted method returned completely different passages, because it rewrites the query with the model before searching.
- **Low-accuracy hits:** every hit below 0.6 is from **Bhrigu Samhita**, scored 0.00–0.01 against the local file.
  - The store's text is real text but does not match the local PDF's text layer. The likely cause is a different or poor OCR text in one of the two (INFERRED).
  - These hits are listed as OCR-suspect, not as wrong files.
- **Yogini query (Q8):** both methods returned mostly `Yogini Dasha.pdf`, which is the expected source.

### 3a. Relevance evaluation (owner-supplied, AI-assisted ratings)

**Source of ratings:** `review_for_owner_rated.csv` (private). The owner states it was rated **with ChatGPT's assistance**, so these are **preliminary AI-assisted ratings, not independent expert validation**.

- **Integrity check:** the same 100 rows as the generated sheet; no passage, filename, score or question changed; every rating is 0, 1 or 2.
- **Distribution:** 37 zeros, 35 ones, 28 twos.
- **Computed offline** with `m2_retrieval_eval --summary --review review_for_owner_rated.csv`. No provider call was made, and the ledger is unchanged at US$0.0593.

**Is the difference real?** No, at this sample size.

| Measure | Result |
|---|---|
| Per-query difference, direct minus hosted | −0.4 to +0.8 |
| Mean difference | +0.06 |
| Paired bootstrap 95% CI over the 10 queries | **−0.12 to +0.28** |
| Query wins (direct / hosted / tie) | 3 / 3 / 4 |

- **Relevance is statistically indistinguishable.**
- Hosted ranks better at the top: its rank-1 mean is 1.20 against 0.90, and its nDCG is 0.877 against 0.750. This is plausibly because it rewrites the query with the model before searching (INFERRED).
- Direct catches up by rank 3, which is what the agent uses by default.

**Coverage by topic (both adapters pooled, 0–2):**

| Topic | Queries | Mean | Hits rated 2 | Assessment |
|---|---|---|---|---|
| Varga (D9/D10) | Q9, Q10 | 1.25 | 9/20 | Good |
| Jaimini: Amatyakaraka | Q6 | 1.20 | 5/10 | Good |
| Career predictive | Q4, Q5 | 1.00 | 6/20 | Mixed: Q4 (10th-lord mahadasha) is good at 1.6; **Q5 (Rahu antardasha, business and foreign) is weak at 0.4** |
| Yogini | Q8 | 0.80 | 2/10 | Mixed: direct 1.2, hosted 0.4 |
| Career factual | Q1–Q3 | 0.73 | 6/30 | **Weak:** Q2 (Saturn aspecting the 10th) 0.3; Q1 (10th lord in the 11th) 0.7 |
| **Jaimini: Chara Dasha** | Q7 | **0.40** | **0/10** | **Weakest topic.** No hit rated 2 on either adapter |

**Coverage by source (pooled):**

| Book | Hits | Mean | Zeros | Note |
|---|---|---|---|---|
| Comprehensive Prediction (V. P. Goel) | 23 | **1.30** | 5 | Most useful source |
| Predicting through Jaimini's Chara Dasha | 16 | 1.19 | 3 | |
| Yogini Dasha | 13 | 1.08 | 3 | |
| Vargas: a Vedic approach | **35** | 0.66 | **18** | **Over-retrieved.** It fills all 5 slots for Q1 on both adapters and most of Q2. Its general house text crowds out career-specific sources |
| Bhrigu Samhita | 8 | 0.62 | 3 | Ratings predate the re-OCR'd replacement |
| Conjunctions (Speed of Light) | 5 | **0.00** | 5 | Off-topic for these questions |
| Astrology at the Speed of Light | 0 | – | – | No text when the runs happened (since fixed) |

**Why career methodology and Chara Dasha are weak (INFERRED):**

1. **Q7 depends on a reference point.** Chara Dasha of the 10th sign from Arudha Lagna needs that frame. The Chara Dasha book was retrieved (4 of 10 slots, all rated 1), but the passages were general method text, not career-event timing from the AL.
2. **The sources lack the material.** Career-factual questions such as Saturn's aspect on the 10th, or the 10th lord in the 11th, are classical-rules material. The current corpus is light on it, so the store falls back to the Vargas book.
3. **One query rewrite is not enough.** The Rahu antardasha question combines dasha, business and foreign themes; neither adapter found a direct source.

These are **corpus and query gaps, not adapter faults:** both adapters fail on the same queries.

**Ratings to review personally (borderline or ambiguous):**

1. **Two inconsistent pairs.** The same passage was given different ratings on the two adapters:
   - Q4 (Chara Dasha book): hosted rank 4 rated **2**, direct rank 5 rated **1**.
   - Q6 (Chara Dasha book): hosted rank 5 rated **2**, direct rank 5 rated **0**.
   - Both pairs affect the comparison: the scores above use the ratings as given. If both were set to the higher value, direct would gain 0.06; if set to the lower value, hosted would lose 0.06. **The conclusion is unchanged either way.**
2. **Nine rank-1 hits rated 1:** Q2 hosted, Q3 both, Q4 hosted, Q5 both, Q7 hosted, Q8 both. Rank-1 drives answer quality, so these are the most consequential borderline calls.
3. **All 7 Q7 (Chara Dasha) rows rated 0 or 1.** This is the topic you said matters most, and the place where an expert view is most valuable.
4. **The 18 zeros given to Vargas-book hits on career questions.** Some may be general house significations that an astrologer would count as partly relevant.

### M2-AC5 adoption decision: **recommend `direct`, for owner approval**

**The pre-agreed rule** (proposed in this report before the ratings existed) adopts direct search if its mean relevance is no worse than hosted minus 0.1 and it costs less.

- **Relevance:** direct 0.94 against a threshold of 0.88 − 0.1 = 0.78. **Passes.** Not because direct is "better": the measured difference is within noise.
- **Cost:** direct is US$0.0025 per query at the assumed price (UNVERIFIED), against a measured US$0.0034 for hosted. Hosted spends a model round of about 4,700 input tokens per search. **Passes**, provided billing confirms the direct price. If direct searches turn out not to be billed per call, it costs about US$0.
- **Latency:** 2.2 s against 8.7 s, about 4×. Not part of the rule, but material to user wait time.
- **Trade-off:** hosted's better rank-1 ordering is real in this sample. If the agent ever requests a single result (`result_count` = 1), hosted would be ahead; at the default of 3 they are level.

**Recommendation:** set `ASTROGPT_RETRIEVAL_ADAPTER=direct`, subject to two conditions:

1. **Owner approval** of this recommendation.
2. **Billing check.** The OpenAI dashboard for 2026-11-11 is reconciled against US$0.0593, confirming direct search is not dearer than assumed.

Keep `result_count` ≥ 3, and keep hosted as the one-line rollback. **The default remains `hosted` until you approve.**

## 3b. Close-out: adapter switch and post-OCR verification (owner-approved, 2026-11-11)

**Adapter switch (provisional).**

- `ASTROGPT_RETRIEVAL_ADAPTER` now defaults to **`direct`**: `astro_site/settings.py` and `.env.example`.
- **Hosted search is kept** as an immediate rollback: set `ASTROGPT_RETRIEVAL_ADAPTER=hosted` and restart. No code change is needed.
- There is **no automatic fallback** to hosted on a direct-search failure. It was not added, because it would be new infrastructure and could double-bill a failed request. The knowledge tool's existing error path still reports that no classical support was retrieved.

**Minimum 3 passages.**

- `MIN_RESULTS = 3` in `knowledge_contracts.py`.
- `knowledge.prepare` raises any request for 1-2 passages to 3. Requests outside 1-5 are still rejected.
- Tests: `M2CloseOutTests`.

**Verification run.**

- 6 direct searches: Q1, Q2, Q5 and Q7 re-run, plus 2 probes aimed at the repaired Speed of Light book:
  - S1: Saturn in the 10th for career.
  - S2: Rahu in the 10th or 11th for business, gains and foreign work.
- Run under a **separate US$0.03 session cap** on top of the overall cap.
- Results were written to separate private files (`hits_post_ocr.jsonl`, `review_post_ocr.csv`), so the rated M2 baseline is untouched.

| Measure | Result |
|---|---|
| Spend | **US$0.0150** (6 x US$0.0025 assumed, UNVERIFIED), within the US$0.03 session cap |
| M2 total | **US$0.0743 of US$1.50** |
| Mean latency | 2.5 s |
| Passage accuracy | **30/30 hits** match their attributed local book at 0.86-1.00; no misattribution |
| Q1, Q2, Q7 | **Exactly the baseline passages.** The repairs did not affect these queries |
| Q5 (Rahu antardasha, business/foreign) | **3 new passages:** Speed of Light at ranks 1 and 5 (career by houses; foreign settlement), Bhrigu Samhita at rank 4 (planet-in-house results naming business and foreign work; text match 1.00) |
| S1, S2 probes | The **Vargas book took 7 of 10 slots** (mostly worked example charts). Comprehensive Prediction took 2 and Conjunctions 1. **Speed of Light did not appear**, although it has planets-in-houses material |

**Relevance of new passages (Claude's preliminary assessment, not owner-rated).** Unchanged passages keep their AI-assisted ratings.

| Query | Baseline (direct) | After repair | Note |
|---|---|---|---|
| Q5 Rahu antardasha | 0.4 [1,0,0,1,0] | **about 0.8** [1,1,0,1,1] | All three new passages are partly relevant (1). None addresses Rahu's sub-period directly |
| S1 Saturn in the 10th | - | about 0.4 [1,0,1,0,0] | Comprehensive Prediction D10 passages are partly relevant; Vargas example charts are not |
| S2 Rahu in the 10th/11th | - | about 0.6 [1,0,0,1,1] | Partial only: Dasamsa business and service houses; a Saturn-Venus conjunction in the 10th/11th |
| Q1, Q2, Q7 | 0.8, 0.2, 0.4 | unchanged | |

**Conclusion.**

- The repaired books are **retrievable and correctly attributed**. Speed of Light now contributes, and Bhrigu text matches.
- The repairs **do not fix the weak topics**. Q1, Q2 and Q7 are unchanged, and the targeted probes are still dominated by the Vargas book's example charts.

## 3c. Weak topics: decomposed query examples (prepared offline, not evaluated)

**Why the weak queries fail.** An offline term count over the local book texts shows that the books use different words from our queries:

- The Chara Dasha book never uses "Arudha Lagna". It uses **"Pada"** (49 times).
- It prefers **"AmK"** (86) to "Amatyakaraka" (38).
- Across the books, **"sub-period"** (328) far outnumbers "antardasha" (24), and no book uses "bhukti".
- Bhrigu Samhita is structured as **"Saturn in the Xth House"** with Roman numerals (921 such headings).

**The proposal: decompose.** Split one compound question into 3-4 single-concept searches. Phrase them in each book's own vocabulary, and fill them from **deterministic chart facts** (the rule engine supplies the signs and houses, never the LLM). Merge and de-duplicate the hits, keeping at least 3 passages. Example placeholders are in braces.

**Chara Dasha career timing (Q7)**

| # | Search | Purpose |
|---|---|---|
| 1 | `Chara Dasha of the 10th sign from the Pada, career results` | Book vocabulary: "Pada", not "Arudha Lagna" |
| 2 | `Chara Dasha of {Capricorn} sign, AmK placed in {Capricorn}` | Ties the running dasha sign to the AmK |
| 3 | `Chara Dasha sub-period of {Leo} for change of job or promotion` | Timing; "sub-period" is the book's term |
| 4 | `planets aspecting the Chara Dasha sign by Rasi drishti, profession` | Jaimini sign aspects |

**Saturn's influence on the 10th house (Q2)**

| # | Search | Purpose |
|---|---|---|
| 1 | `Saturn in the {IVth} House` (Bhrigu style) **or** `Saturn in the {4th} house results` | The placement that produces the aspect, computed by the engine |
| 2 | `Saturn's third, seventh and tenth aspects` | The aspect rule, kept separate from the career theme |
| 3 | `Saturn as karaka of profession, service and hard work` | Significator |
| 4 | `10th house aspected by a malefic, effect on career` | Generic house rule |

**Rahu antardasha for business and foreign work (Q5)**

| # | Search | Purpose |
|---|---|---|
| 1 | `Rahu sub-period in {Jupiter} Mahadasha results` | Dasha pair; "sub-period" vocabulary |
| 2 | `Rahu in the {7th} house, business and partnerships` | The engine-supplied placement |
| 3 | `Rahu and foreign travel, 12th house and foreign settlement` | Foreign theme (Speed of Light now covers it) |
| 4 | `Rahu dasha results for career and gains` | General Rahu dasha |

**Cost and limits.**

- With direct search, each extra search costs US$0.0025 (assumed) and no model tokens. A 4-way decomposition costs about US$0.01 per question, against US$0.0034 for one hosted search.
- **This is unevaluated.** Measuring whether it helps needs a separate approved run, for example the 3 weak questions x 4 searches = 12 searches, about US$0.03.
- Implementing it belongs in M3's agent query construction, not new infrastructure.
- Two other levers would further reduce the Vargas book's crowding but change the live store:
  - source filtering by file `attributes`;
  - excluding worked-example-chart chunks.

## 4. Acceptance criteria

| ID | Status |
|---|---|
| M2-AC1 manifest | **Done** (§2) |
| M2-AC2 per-adapter measures | **Done for 10 of the planned 24 queries.** Latency, usage, cost and relevance (AI-assisted owner ratings, §3a) |
| M2-AC3 passage accuracy | **Done.** Local copies of Yogini Dasha and Comprehensive Prediction were added later (§2a): 11/13 and 23/23 of their hits match at 0.6 or more. Bhrigu Samhita's re-OCR'd text matches its old hits at 0.77–0.96. |
| M2-AC4 citation fidelity | **Done.** Test: every locator comes from a returned hit; pages appear only when the provider returned them. |
| M2-AC5 adoption | **`direct` adopted provisionally** by the owner on 2026-11-11 (§3b), with hosted kept as rollback. The billing check is still open. |
| M2-AC6 swap test | **Done.** The agent runs unchanged against hosted, direct and offline adapters (mocked provider). |
| M2-AC7 untrusted-text labelling (S-6) | **Done.** One shared policy text sits in both legacy prompts and the agent prompt, with tests. |
| M2-AC8 no hits → "no classical support was retrieved" | **Done** (tests) |
| M2-AC9 spend ≤ cap, every call in the ledger | **Done:** US$0.0743 in total (US$0.0593 evaluation + US$0.0150 verification). The ledger is the private `ledger.jsonl`. |
| M2-AC10 no book passages in committed files | **Done.** Re-run after the repairs against the current book texts (354,470 runs, up from 253,272): no matches. The earlier check had used a stale text cache keyed only by filename; it is now keyed by file size and modification time. |

## 5. Code changes

| File | Change |
|---|---|
| `astrology/rag/direct.py` (new) | `DirectVectorStoreSearch` (adapter b); offline `StaticRetrieval`; `configured_adapter()` driven by `ASTROGPT_RETRIEVAL_ADAPTER` (default `hosted`) |
| `astrology/rag/policy.py` (new) | `SOURCE_TEXT_POLICY`: untrusted text, title plus paraphrase, never quote, say when no support was retrieved |
| `accounts/provider_meter.py` | `vector_store_search()` and `Budget.before_search`/`after_search`: direct searches are reserved, ledgered and capped like file searches. Ledger persistence was moved into `Budget._persist`, with unchanged behaviour. |
| `astrology/rag/knowledge.py` | Default adapter comes from the setting |
| `astro_site/settings.py`, `.env.example` | `ASTROGPT_RETRIEVAL_ADAPTER`; **default `direct` since close-out**, `hosted` as rollback |
| `astrology/rag/knowledge_contracts.py`, `astrology/rag/knowledge.py` | `MIN_RESULTS = 3`: requests for fewer passages are raised to 3 |
| `chat/llm_engine.py` | S-6 and OD-11 policy added to the legacy career and rashifal instructions |
| `astrology/agent/provider.py` | Policy added to the agent instructions |
| `astrology/synthesis/fact_catalog.py` | **OD-11:** published citation facts give attribution only. The excerpt is still sent to the model as untrusted input and still bound for verification, but it is never published verbatim. Paraphrase is left to the M3 composer. |
| `charts/management/commands/m2_retrieval_eval.py` (new) | Capped evaluation command: `--manifest`, `--run`, `--accuracy`, `--summary`, `--leakcheck`. Paid actions require `--confirm-paid`. `--label` keeps verification runs separate from the baseline; `--session-cap` adds a per-run cap; the text cache is keyed by file version; Comprehensive Prediction is now an owner book. `--review <file>` (offline) picks the rated sheet; it is restricted to the private folder. The summary adds hits rated 1 or more, rank-1 mean and per-query ratings. |
| `astrology/test_m2.py` (new) | 18 tests |
| `astrology/test_knowledge.py`, `astrology/test_quality.py` | 3 assertions that required verbatim excerpts in answers now assert the OD-11 policy instead: attribution present, excerpt absent |
| `astrology/evaluation/corpus_manifest.yaml` (new) | Manifest. It holds file IDs and filenames; the store ID appears only as a hash. |

**Private, git-ignored files** in `astrology/evaluation/private/m2/`:

- `ledger.jsonl`
- `hits.jsonl` (passage text)
- `review_for_owner.csv` and `review_for_owner_rated.csv`
- `accuracy.json`
- `summary.json`
- the extracted-text cache

## 6. Tests

**Full suite: 371 tests, 370 passed, 1 skipped.** That is M1b's 353 tests plus 18 M2 tests (15 at evaluation, 3 at close-out: the default adapter and rollback, the 3-passage floor, and the session cap refusing before any call).

- **The skip:** the JH comparison for R1–R5, PENDING owner values.
- **All tests are offline.** Network connections and the OpenAI client are blocked or mocked.
- **3 existing assertions changed** in `test_knowledge.py` and `test_quality.py`. They encoded verbatim excerpt publishing, which OD-11 now forbids.
- The tests are regression and contract checks. They do not measure retrieval quality; that comes from the owner ratings.

## 7. Known limitations

1. **The ratings remain preliminary.** The baseline ratings are AI-assisted (ChatGPT); the section 3b assessments of new passages are Claude's. Neither is independent expert validation. Two internal inconsistencies and the borderline rows are flagged in section 3a.
2. **Small sample:** 10 queries x 5 hits per adapter, plus a 6-search verification. The relevance difference between adapters is within noise (95% CI -0.12 to +0.28).
3. **The direct-search price is unverified.** The billing dashboard for 2026-11-11 should show about US$0.074 in total, or about US$0.034 if direct searches are not billed per call.
4. **Weak topics persist on both adapters:** Chara Dasha career timing, Saturn's influence on the 10th, and career rules (the 10th lord in the 11th). The Rahu antardasha question improved to about 0.8 after the repairs. The decomposed queries in section 3c are untested.
5. **The Vargas book is over-retrieved.** Its worked example charts are dense in house and planet terms and outrank prose explanations, including Speed of Light's planets-in-houses material.
6. **No automatic fallback to hosted.** The rollback is a setting change.
7. **No file metadata.** Answers can cite filenames only, never chapter or page, and retrieval cannot filter by source.
8. **10 of the planned 24 queries were run.** The other 14 were declined by the owner.
9. **Original PDFs were overwritten by the Acrobat OCR.** A Speed of Light original survives elsewhere; for Bhrigu only the ABBYY XML survives.
10. **Paraphrase is not done yet.** Under OD-11 the agent publishes attribution only; paraphrasing needs the M3 composer.

## 8. Rollback

- Set `ASTROGPT_RETRIEVAL_ADAPTER=hosted` in `.env` and restart. This returns to the pre-M2 retrieval behaviour.
- The 3-passage floor is independent of the adapter. To undo it, set `MIN_RESULTS = 1`.
- To undo the code: `git revert` the M2 commits. There are no migrations.
- The private files can be deleted at any time.

## 9. Proposed next steps (each needs approval)

1. **Billing check** (owner): reconcile the dashboard with US$0.0743. This settles the direct-search price.
2. **Decomposed-query evaluation** (paid, small): 3 weak questions x 4 searches on direct, about US$0.03. Run before or inside M3.
3. **Store metadata:** add `attributes` (book title, tradition) to the 7 files. This is free metadata but changes the live store. It enables source filtering against Vargas crowding, and citation by title.
4. **Expert spot-check** of the flagged ratings (section 3a), especially Chara Dasha.
5. **M3:** build the decomposed, fact-filled query construction into the agent, plus the paraphrasing composer (OD-11).

## 10. Owner actions

1. **Check the billing dashboard** against US$0.0743.
2. **Review the flagged ratings** (section 3a), especially Q7.
3. **Rights classes and display titles** for each manifest file (OD-11 follow-up).
4. **Approve or decline** next steps 2-3.
5. **Approve M2** before M3 starts.
