# P4 knowledge coverage audit

## Finding

**Live corpus coverage: UNVERIFIED.** No provider inspection, file listing, book download, embedding request, upload or paid search was performed for this audit. The P4 gate explicitly permits an unverified live corpus with passing mocked retrieval tests. Local file presence and source notes are not proof of hosted indexing.

The existing application reads `OPENAI_VECTOR_STORE_ID` in `astro_site/settings.py`. `chat/llm_engine.py` configures hosted `file_search` in legacy generation. Neither the configured identifier nor successful local code inspection establishes which files have been uploaded, whether processing completed, or whether any particular chapter is retrievable. Configuration values and credentials are deliberately excluded from this document.

A local settings-only check found that both vector-store and API-key configuration are present. It did not validate those values or contact the provider. Configuration presence therefore does not change the **UNVERIFIED** coverage finding.

## Local evidence

| Repository material | What was found | Hosted index status |
|---|---|---|
| `astrology/docs/parashari_source_notes.md` | Notes naming classical and supplementary sources and earlier OCR/readability decisions | UNVERIFIED |
| `astrology/docs/jaimini_source_notes.md` | Jaimini source/extraction notes | UNVERIFIED |
| `astrology/docs/divisional_source_notes.md` | Divisional source/extraction notes | UNVERIFIED |
| `astrology/docs/yogini_ocr_task.md` | Notes describe a Yogini PDF and prior calculation/extraction work; filename is historical and is not proof OCR is currently missing | UNVERIFIED |
| `astrology/docs/architecture_todo.md` | Architecture task notes, not a book corpus | UNVERIFIED |
| Root `README.md`, `AGENTS.md`, architecture, contracts and phase/master plans | Application/development documentation, not verified astrology reference books | UNVERIFIED |
| `docs/agent_migration/*.md` | Migration plans, reports and interface descriptions added during this work | UNVERIFIED; not uploaded by this phase |
| `astrology/rules/*.yaml` | Deterministic paraphrases/source references used by the rule engine; not hosted search evidence | UNVERIFIED; rule matching remains deterministic |

The source notes refer to files outside this workspace. This audit did not open those external paths or repeat their historical readability/page-count claims as fresh findings. Their appearance in a note proves only that the note contains that reference. No full external book text was copied into source or prompts.

`astrology/rag/query_builder.py` builds legacy broad evidence terms. The existing generation path uses the provider's hosted chunking/index/search and LLM integration. Repository searches found no local `vector_stores` ingestion/upload pipeline, embeddings client, chunking worker or independently implemented reranker. This does not prove no external uploader exists. P4 adds a targeted read-only hosted adapter; it does not add ingestion or silently index local Markdown.

## What P4 verifies offline

- A targeted topic/concepts query can be sent through the configured hosted `file_search` adapter.
- Included raw search results can be normalized to bounded excerpts with returned file/metadata fields.
- Missing book/chapter/page/tradition fields remain missing and are identified explicitly.
- Different returned source viewpoints remain separate; no inferred consensus.
- Model-generated answer text/annotations do not serve as citation authority.
- Retrieved text cannot expand the agent tool allowlist or principal authority.

Mocked passages demonstrate these contracts, not actual index coverage, corpus relevance, OCR quality, rights clearance or predictive validity.

## Separately authorized live inspection procedure

Before calling coverage verified, obtain authorization for a capped read-only inspection. Retrieve only the configured store's metadata and paginated `vector_stores.files.list` results; collect file IDs, ingestion statuses, last errors, chunking information and available attributes. Resolve filenames through read-only file metadata if needed. Do not fetch whole file contents by default. Record inspection time and pagination completeness, including unavailable metadata and failed/in-progress files.

Compare that returned inventory with a user-approved source manifest. Filename similarity alone does not prove content identity; use a known manifest/content fingerprint where available, and otherwise mark identity unverified. Verify representative authorized topic queries separately with a capped search budget and inspect actual result citations. Never infer all local Markdown is indexed. A search hit verifies a returned passage at that time, not complete indexing of its entire book.

No production corpus inventory or verified manifest is created in this phase. Full hosted coverage, upload status, chapter/page metadata completeness and live retrieval quality remain **UNVERIFIED**.
