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
| **Total recorded** | 29 | **US$0.0593 of US$1.50** |

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
| Owner relevance@5, and share of queries with a "2" | **PENDING your ratings** | **PENDING your ratings** |

- **Overlap:** the two methods share 32 of 50 hits. On Q1 the hosted method returned completely different passages, because it rewrites the query with the model before searching.
- **Low-accuracy hits:** every hit below 0.6 is from **Bhrigu Samhita**, scored 0.00–0.01 against the local file.
  - The store's text is real text but does not match the local PDF's text layer. The likely cause is a different or poor OCR text in one of the two (INFERRED).
  - These hits are listed as OCR-suspect, not as wrong files.
- **Yogini query (Q8):** both methods returned mostly `Yogini Dasha.pdf`, which is the expected source.

### M2-AC5 adoption decision: **PENDING owner relevance ratings**

The proposed rule adopts direct search if its mean relevance is no worse than hosted minus 0.1 and it costs less.

- Direct search is already **about 4× faster**, needs no model round and is no more expensive. Its accuracy on matched books is at least as good.
- The relevance comparison cannot be made without your ratings.
- **The default remains `hosted`.** Changing it means setting `ASTROGPT_RETRIEVAL_ADAPTER=direct` after you decide.

## 4. Acceptance criteria

| ID | Status |
|---|---|
| M2-AC1 manifest | **Done** (§2) |
| M2-AC2 per-adapter measures | **Partly done.** Latency, usage and cost done for 10 of the planned 24 queries; **relevance PENDING owner ratings** |
| M2-AC3 passage accuracy | **Done** for books with local text. Yogini Dasha and Comprehensive Prediction cannot be checked; the Speed of Light book has no text. |
| M2-AC4 citation fidelity | **Done.** Test: every locator comes from a returned hit; pages appear only when the provider returned them. |
| M2-AC5 adoption | **PENDING owner ratings** |
| M2-AC6 swap test | **Done.** The agent runs unchanged against hosted, direct and offline adapters (mocked provider). |
| M2-AC7 untrusted-text labelling (S-6) | **Done.** One shared policy text sits in both legacy prompts and the agent prompt, with tests. |
| M2-AC8 no hits → "no classical support was retrieved" | **Done** (tests) |
| M2-AC9 spend ≤ cap, every call in the ledger | **Done:** US$0.0593. The ledger is the private `ledger.jsonl`, summarised in §1. |
| M2-AC10 no book passages in committed files | **Done.** Leak check: no 12-word prose run from any local book appears in any tracked file. Planet and sign name lists are excluded as shared vocabulary. |

## 5. Code changes

| File | Change |
|---|---|
| `astrology/rag/direct.py` (new) | `DirectVectorStoreSearch` (adapter b); offline `StaticRetrieval`; `configured_adapter()` driven by `ASTROGPT_RETRIEVAL_ADAPTER` (default `hosted`) |
| `astrology/rag/policy.py` (new) | `SOURCE_TEXT_POLICY`: untrusted text, title plus paraphrase, never quote, say when no support was retrieved |
| `accounts/provider_meter.py` | `vector_store_search()` and `Budget.before_search`/`after_search`: direct searches are reserved, ledgered and capped like file searches. Ledger persistence was moved into `Budget._persist`, with unchanged behaviour. |
| `astrology/rag/knowledge.py` | Default adapter comes from the setting |
| `astro_site/settings.py` | `ASTROGPT_RETRIEVAL_ADAPTER` |
| `chat/llm_engine.py` | S-6 and OD-11 policy added to the legacy career and rashifal instructions |
| `astrology/agent/provider.py` | Policy added to the agent instructions |
| `astrology/synthesis/fact_catalog.py` | **OD-11:** published citation facts give attribution only. The excerpt is still sent to the model as untrusted input and still bound for verification, but it is never published verbatim. Paraphrase is left to the M3 composer. |
| `charts/management/commands/m2_retrieval_eval.py` (new) | Capped evaluation command: `--manifest`, `--run`, `--accuracy`, `--summary`, `--leakcheck`. Paid actions require `--confirm-paid`. |
| `astrology/test_m2.py` (new) | 15 tests |
| `astrology/test_knowledge.py`, `astrology/test_quality.py` | 3 assertions that required verbatim excerpts in answers now assert the OD-11 policy instead: attribution present, excerpt absent |
| `astrology/evaluation/corpus_manifest.yaml` (new) | Manifest. It holds file IDs and filenames; the store ID appears only as a hash. |

**Private, git-ignored files** in `astrology/evaluation/private/m2/`:

- `ledger.jsonl`
- `hits.jsonl` (passage text)
- `review_for_owner.csv`
- `accuracy.json`
- `summary.json`
- the extracted-text cache

## 6. Tests

**Full suite: 368 tests, 367 passed, 1 skipped.** That is M1b's 353 tests plus 15 new M2 tests.

- **The skip:** the JH comparison for R1–R5, PENDING owner values.
- **All tests are offline.** Network connections and the OpenAI client are blocked or mocked.
- **3 existing assertions changed** in `test_knowledge.py` and `test_quality.py`. They encoded verbatim excerpt publishing, which OD-11 now forbids.
- The tests are regression and contract checks. They do not measure retrieval quality; that comes from the owner ratings.

## 7. Known limitations

1. **Relevance is not yet rated.** The adoption decision waits for your ratings.
2. **10 of the planned 24 queries were run.** The other 14 need your approval for further testing.
3. **The direct-search price is unverified;** the billing-dashboard check in §1 settles it.
4. **Book coverage problems:**
   - The Speed of Light book has no usable text.
   - The Bhrigu Samhita text layers disagree.
   - Yogini Dasha and Comprehensive Prediction cannot be accuracy-checked locally.
5. **No file metadata.** Answers can cite filenames only, never chapter or page.
6. **Paraphrase is not done yet.** Under OD-11 the agent now publishes attribution only; paraphrasing source content needs the M3 composer.
7. **Latency is from one machine at one time.**

## 8. Rollback

- Set `ASTROGPT_RETRIEVAL_ADAPTER=hosted`. It is already the default.
- To undo the code: `git revert` the M2 commits. There are no migrations.
- The private files can be deleted at any time.

## 9. Owner actions

1. **Rate the hits.** Open `astrology/evaluation/private/m2/review_for_owner.csv` in Excel and fill the `rating` column (0, 1 or 2) for all 100 rows. I then run `--summary` offline, at no cost, and complete M2-AC2 and M2-AC5.
2. **Check the billing dashboard** against US$0.0593 (§1).
3. **Comprehensive Prediction.pdf:** tell me what it is and whether it should stay in the store.
4. **The Speed of Light book:** OCR it and re-upload, or accept that it can't be used.
5. **Rights classes:** confirm a rights class and display title for each file in the manifest (OD-11 follow-up).
6. **Further testing:** approve or decline the remaining 14 queries.
7. Approve M2 before M3 starts.
