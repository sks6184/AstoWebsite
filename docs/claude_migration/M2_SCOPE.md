# M2: retrieval evaluation on the existing OpenAI vector store — agreed scope

- Branch: `claude/m2-retrieval-eval`, created from `claude/m1b-calculation-settings` at `02c3708`.
- Date: 2026-11-11.
- The owner's instruction to "start M2" is taken as acceptance of M1b for branching purposes. Merge approval is still pending.

## 1. Owner decisions recorded at M2 start

| ID | Decision (owner's words summarised) |
|---|---|
| **OD-5a** | Approved, with a **strict maximum OpenAI spend of US$1.50 for the whole of M2**, from an available balance of US$2.35. Conditions: (1) start with **8–12 representative queries** instead of 24, using both retrieval methods where affordable; (2) **measure actual cost before proceeding** to further queries; (3) **stop before any call that might exceed the remaining M2 budget**; (4) no automatic credit top-up and no unrelated paid model calls; (5) report incomplete coverage transparently; (6) any further testing needs explicit owner approval. |
| **OD-11** | **Cite by book title and paraphrase only.** No verbatim quotations in user-facing answers until rights are confirmed. The Astrotalk website-capture PDF is flagged for possible removal; **nothing is deleted** from the vector store in M2. |

## 2. Budget control

- **Before each paid call**, an M2 ledger reserves a conservative worst-case cost. The call is refused if the reservation would push cumulative M2 spend past US$1.50.
  - Hosted `file_search` (adapter a): the existing meter's reservation rule, i.e. the full 128k-token context at the `gpt-4o-mini` tariff, plus US$0.0025 per search.
  - Direct `vector_stores.search` (adapter b): US$0.0025 per call. This price is **UNVERIFIED**. It is a conservative assumption equal to the published file-search tool-call price, to be compared with the billing dashboard.
- **After each call**, the ledger records provider-reported tokens and the rated cost.
- The ledger lives in a git-ignored private folder. The report contains only aggregate figures, never passage text.
- **Batch 1:** the store listing, then 3 queries through both adapters. The measured cost decides how far the remaining queries can go within the 8–12 total.
- **The store listing** uses vector-store and file management endpoints (`retrieve` / `files.list` / `files.retrieve`). These are believed to be unbilled (UNVERIFIED); they are counted in the ledger at US$0.

## 3. Scope

1. **Corpus manifest.** One read-only store listing produces `astrology/evaluation/corpus_manifest.yaml`: file IDs, filenames, status, byte size and attributes. It is compared with the owner's list of seven PDFs and resolves whether `Yogini Dasha.pdf` is indexed. Tradition, rights class and display title are owner-supplied fields, pre-filled as `pending_owner`.
2. **Query set.** 10 queries (§4), drafted by Claude. The owner may edit them; any edit after a paid run requires a re-run within the cap.
3. **Adapters.**
   - (a) The existing `HostedFileSearch`.
   - (b) A new `DirectVectorStoreSearch`, which calls `client.vector_stores.search` with no model round.
   - An offline `StaticRetrieval` mock.
   - Selected by the single setting `ASTROGPT_RETRIEVAL_ADAPTER`. The default stays `hosted`.
4. **Owner relevance labelling.** The top 5 hits per adapter per query go into a **private, git-ignored** review file, which the owner rates 0, 1 or 2.
5. **Passage accuracy.** Each hit is matched by normalised text similarity against the local PDF with the same filename, using `pypdf` 6.10.2, which is already installed and is **not a new dependency**. Results record scores and hashes only.
6. **Safety and policy, testable offline.**
   - S-6: retrieved text is labelled untrusted in the legacy prompts too.
   - OD-11: legacy and agent instructions say title plus paraphrase, no verbatim quotes. The agent's citation facts publish attribution only, not the excerpt.
   - Missing or failed retrieval states that no classical support was retrieved.
   - Citation fidelity: every locator corresponds to a returned hit, and pages appear only when the provider returned them.
   - Swap test across the a, b and mock adapters.

Out of scope:

- Changing the default adapter. The owner decides that after the results (M2-AC5).
- Deleting files from the store.
- Independent RAG.
- New dependencies.
- M3 work.

## 4. Query set (10 queries; expected books in brackets)

| # | Category | Query | Expected source |
|---|---|---|---|
| Q1 | career-factual | Results of the 10th lord placed in the 11th house for career and gains | Speed of Light; 300 Yogas |
| Q2 | career-factual | Saturn aspecting the 10th house and its effect on profession | Speed of Light; Bhrigu Samhita |
| Q3 | career-factual | Raja yoga formed by lords of the 9th and 10th houses | 300 Yogas |
| Q4 | career-predictive | Mahadasha of the 10th lord and timing of career rise | Speed of Light |
| Q5 | career-predictive | Antardasha of Rahu for business and foreign work | Speed of Light; Conjunctions |
| Q6 | Jaimini | Amatyakaraka and its role in profession in Jaimini astrology | Jaimini Chara Dasha |
| Q7 | Jaimini | Chara dasha of the 10th sign from Arudha Lagna and career events | Jaimini Chara Dasha |
| Q8 | Yogini | Results of Sankata yogini dasha and its ruling planet | Yogini Dasha (store only) |
| Q9 | varga | Interpreting the 10th lord of the Dasamsa (D10) chart for career | Vargas Vedic Approach |
| Q10 | varga | Strength of a planet in the Navamsa (D9) confirming the Rasi promise | Vargas Vedic Approach |

## 5. Deliverables

- `M2_REPORT.md` (no passage text).
- `corpus_manifest.yaml`.
- The adapters and the evaluation command.
- Tests.
- The private review file, for the owner's rating only.
