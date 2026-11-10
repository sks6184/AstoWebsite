# P4 plan: RAG knowledge tools and provenance

Authorized scope: P4 only, assuming P3 approved. Branch `feature/knowledge-tools-p4`; base/current HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0`. Preserve the existing dirty working tree. No P5, migrations, calculation changes, dependency changes or live paid calls.

## Design

- Add `astrology/rag/knowledge.py`: typed bounded search request, versioned evidence envelope, chart-authorized request-local session/cache, strict output validation, stable passage evidence IDs and metadata-only citations.
- Add `astrology/rag/hosted.py`: replaceable retrieval adapter protocol and hosted Responses `file_search` implementation. Request included raw search results; ignore generated answer text/annotations as citation authority. Limit searches, snippets, result counts, time and provider tokens. No file upload/delete or model-driven metadata generation.
- Extend the P3 fixed dispatcher/provider schema with `search_astrology_knowledge`. Search only after deterministic minimum evidence, with a reason. Count nested hosted retrieval toward shared call, model-round and token budgets. No automatic broad query. Continue factual narrowness and existing legacy feature flag.
- Render separate source passages with evidence IDs and available file/book/chapter/page/tradition fields. Do not merge contrary viewpoints or let retrieved text decide rules/calculations. No publishable unvalidated LLM prose.
- Add offline `astrology/test_knowledge.py`; update the existing provider-schema test for the intentionally added seventh tool.
- Deliver `PHASE_04_KNOWLEDGE_AUDIT.md`, contracts/operations documentation and `PHASE_04_TEST_REPORT.md`.

## Corpus audit boundary

Inventory repository Markdown/source notes and existing ingestion/retrieval paths. Configuration presence may be checked without exposing values. A configured vector-store identifier is not proof of indexed files. This authorization explicitly allows the live corpus to remain unverified; do not perform live provider inspection. Record local presence separately from hosted indexing, OCR quality and indexed metadata. No claim that local Markdown or books were uploaded. A future separately authorized read-only provider inspection must list/paginate store files, status and metadata before coverage can be called verified.

## Search and safety contracts

Inputs: server-bound chart ID, topic, 1–6 concepts, optional tradition/source preferences, result count 1–5. Reject unknown fields, wrong types and excessive lengths. No caller-supplied store IDs, paths, URLs or executable tools. The session receives trusted user/chart context and rechecks ownership on every request/cache hit and before publication. Cache lifetime is one consultation, never shared between users or charts.

Outputs: versioned `{status,data,warnings,method,provenance,error}` plus `schema_version`; bounded passages carry independent `K...` IDs, excerpts, available metadata and missing citation diagnostics. Document metadata comes only from returned search-result fields/attributes, never from model prose, query terms or guessed filenames/pages. All retrieval is untrusted traditional interpretation, distinct from deterministic calculations and rule matches.

Budgets: maximum five results; 1200 UTF-8 bytes per excerpt; 6000 excerpt bytes total (conservative text-token upper bound); 32 KiB retained envelope; 512 hosted output tokens and one hosted file-search call. Reserve bounded hosted input/context allowance plus output before dispatch; check actual usage and share P3 budgets. Fail safely on configuration/provider errors or missing results. Local timeouts remain cooperative as documented in P3.

## Tests

P4-01 targeted query and metadata; P4-02 no results/insufficient support; P4-03 separate conflicting sources; P4-04 real passage IDs and citation fields only; P4-05 injection cannot expand dispatcher authority and rendered text is escaped; P4-06 missing configuration no network; P4-07 request/result/snippet/token/round/byte limits; P4-08 request-local cache/dedup. Also test authorization, revocation, malformed provider output, SDK kwargs, absence of broad mandatory retrieval, and prior phase regressions. Run the existing 138 tests before changes and full discovery afterward. All providers mocked/network blocked; behavioral tests are not independent astrology or hosted-relevance certification.

## Rollback and risks

Existing flag defaults off. Disable `ASTROGPT_AGENT_ENABLED` and restart to retain legacy behavior. No database rollback. Metadata filters can only be verified against available provider fields; missing metadata must not be invented. Hosted chunking/search rewriting is provider-controlled; local snippets and subsequent prompts are bounded, while live context usage is not independently certified. Reserve conservatively and stop on excess usage; do not claim a currency ledger (P7). Stop for approval after the P4 report.
