# P4 knowledge tool contracts

## Scope and entry points

`search_astrology_knowledge` is the seventh explicitly allowed **agent** tool. The six P2 deterministic tools and their pure local dispatcher remain unchanged. Knowledge retrieval is not a calculation, rule evaluator or probability estimator.

- Agent dispatch: `astrology/agent/orchestrator.py::Consultation.execute`.
- Authorized local interface: `astrology/rag/knowledge.py::KnowledgeSession(user, chart_id, adapter=None).search(arguments, token_budget=40000, timeout=15)`.
- Input/schema discovery: `astrology/rag/knowledge_contracts.py::SearchRequest`, `tool_definition`.
- Pluggable provider: `RetrievalAdapter.retrieve(query, request, timeout=...) -> RetrievalBatch`.
- Initial adapter: `astrology/rag/hosted.py::HostedFileSearch`.

Construct a fresh session per consultation. An adapter receives the bounded topic/concepts query, not birth coordinates, raw chart data or the full user question. The configured store is a server-owned shared knowledge corpus, not an agent-selectable user upload store. Do not place private user records into it without separate access controls.

## Inputs

| Field | Type / bounds |
|---|---|
| `chart_id` | Positive integer, authenticated owner's chart; bound by server |
| `topic` | Nonempty text, at most 80 UTF-8 bytes |
| `concepts` | 1–6 nonempty terms, at most 80 UTF-8 bytes each |
| `tradition` | Optional/null; at most 80 UTF-8 bytes |
| `source` | Optional/null; at most 120 UTF-8 bytes |
| `result_count` | Integer 1–5, default 3; booleans rejected |

No unknown arguments, store ID, path, executable code, URL-fetch action or database mutation. No control characters in query terms. Request body limit is the existing P2 parser's 8192 bytes. Terms are trimmed/case-folded; concepts sorted/deduplicated for stable request-local cache reuse. In agent calls, a nonempty reason is required and removed by the provider adapter before dispatch.

The agent enforces topic containment and preserves factual lookup narrowness. Search is optional and occurs after deterministic minimum evidence. A requested source/tradition is included in the targeted query and checked against **actual returned metadata**. Source checks may match returned file ID, filename, document title or book metadata. Tradition requires matching returned tradition metadata. Unverifiable/nonmatching results are omitted with a warning; the query itself is never proof of source membership. No extra broad search is silently sent to fill gaps.

## Envelope and passages

The result uses `schema_version: "1.0"`, `status`, `data`, `warnings`, `method`, `provenance`, `error`. `validate_knowledge` validates every live/cache result. Error responses contain null data and a machine-readable `{code,message}`. Status is `ok`, `partial` or `error`.

Successful/partial data:

```json
{
  "passages": [
    {
      "evidence_id": "K<content-and-citation-digest>",
      "snippet": "Short retrieved source excerpt",
      "citation": {
        "file_id": "file-returned-by-provider",
        "filename": "returned-document.md",
        "document": null,
        "book": null,
        "chapter": null,
        "page": null,
        "tradition": null
      },
      "citation_available": true,
      "truncated": false,
      "score": 0.8,
      "trust": "untrusted_source_text"
    }
  ],
  "support_status": "retrieved",
  "query": "bounded topic/concepts/filter JSON",
  "usage": {"input_tokens": 200, "output_tokens": 10, "provider_rounds": 1},
  "viewpoint_policy": "Sources are separate viewpoints; agreement and predictive validity are not inferred."
}
```

The illustration is a schema example, not a real corpus citation. `score` is provider retrieval relevance (or null), **not** predictive probability. `K...` IDs are deterministic hashes of the retained excerpt and citation object; validation rejects a changed citation reusing the old ID. `E...` IDs identify tool results in the surrounding consultation. Agent final references must resolve to returned E/K IDs; arbitrary model prose or invented references are rejected. The server renders all minimum evidence and retrieved viewpoints rather than allowing reference selection to hide conflicts.

`document` preserves returned `document`, `document_title` or `title` attributes; it is not promoted to a book claim. Book/chapter/page/tradition come from corresponding returned attributes only. Missing values stay null. No filename parsing, query inference, free-text page extraction or generated-answer citation reconstruction. Provider metadata is preserved as supplied, not independently certified as bibliographically accurate. If there is no source locator/title, explicitly say citation unavailable; otherwise identify the missing citation fields. A file ID by itself identifies a returned file, not a chapter/page.

`method` identifies the adapter, role and limits; corpus coverage remains `unverified`. `provenance` contains authorized chart ID, adapter/config fingerprint, request-local cache flag, retained passage IDs and bounded actual hosted query strings. No API key, raw store ID, chart birth data or unbounded prompts are included. Provenance is returned to server code, not automatically written to logs.

## Hosted adapter and limits

The initial adapter uses Responses hosted `file_search`, forced via `tool_choice`, with one hosted search invocation and requested `max_num_results`. It requests `include=["file_search_call.results"]` and reads only those structured result fields. Generated response prose/annotations are discarded as citation authority. Provider storage and retries are disabled. Hosted chunking, embeddings and ranking remain provider-managed; no local ingestion or reranking is introduced.

| Resource | Bound |
|---|---:|
| Retained results | 5 maximum; caller may request fewer |
| Per-excerpt UTF-8 bytes | 1200 |
| Total excerpt UTF-8 bytes | 6000 |
| Retained envelope | 32 KiB |
| Citation field | 256 UTF-8 bytes; invalid/oversized fields unavailable |
| Actual hosted queries retained | At most 6, each shortened to 512 characters |
| Hosted output-token request | 512 |
| Hosted calls in one search | 1 |
| HTTP timeout | Caller/server remaining budget, default 15 seconds |
| Retries | 0 |

Excerpts are cut on a UTF-8 boundary and explicitly marked truncated. Duplicate passage IDs are collapsed. Empty/malformed results are omitted, not fabricated. Unicode byte budgets conservatively bound excerpt text tokens without installing a tokenizer. They do not claim an exact provider token count.

Before a paid search, reserve 32,768 hosted input/context tokens plus UTF-8 query bytes, 1024 overhead and 512 output tokens. This is a conservative operational allowance, **not proof** of a provider-side hard input/context limit: hosted rewritten queries/chunks are provider-controlled. Check actual reported input/output usage after return; overruns stop further agent work. The agent shares P3's cumulative token, model-round, tool-call, output-byte and elapsed-time limits. A hosted search consumes a model round in addition to planner rounds. Local deadlines retain P3's cooperative limitation. Currency accounting/refunds remain P7.

## Failure and cache semantics

| Condition | Result |
|---|---|
| Missing vector-store/key configuration | `knowledge_not_configured`, no provider call |
| No matching/usable passages | `partial`, `support_status: insufficient`, explicit warning |
| Missing citation details | Retained if useful, explicit unavailable fields; no guessed book/page |
| Requested filter unverified | Omit those passages and warn |
| Provider failure/timeout | `knowledge_unavailable` / `knowledge_timeout`, sanitized message |
| Insufficient/exceeded token allowance | `knowledge_token_limit`; agent stops further model work |
| Invalid arguments/provider result | Explicit validation error / `invalid_retrieval` |
| Unauthorized, missing, revoked chart | Same `chart_not_found` response, no passages/provenance |

Request-local cache keys include owner, chart-bound normalized request and adapter/corpus-configuration fingerprint. Cache hits recheck ownership, validate/copy the result and report zero new provider usage. They reserve no new hosted tokens in the agent. A new consultation creates a new cache. Configuration/version changes invalidate matching keys; no cross-user/global cache exists. A configured store may change content during a request; cache reuse is limited to that request and does not claim durable index freshness.

Retrieved text remains untrusted even if it is classical literature. It cannot override system policy, choose a principal/store, add a tool, execute code, write database rows, determine a deterministic rule match or supply calculated facts. Every optional action still passes the server allowlist and scope checks. Rendered excerpts are labeled source text and escaped by the existing page formatter; separate viewpoints are not presented as agreement.

## Audit, deployment and verification

See [corpus audit](docs/agent_migration/PHASE_04_KNOWLEDGE_AUDIT.md). Local Markdown/source-note presence does **not** establish uploaded corpus coverage. Live file inventory/status/metadata and retrieval quality remain **UNVERIFIED**; no provider inspection occurred.

P4 uses the existing `ASTROGPT_AGENT_ENABLED` flag, default false. Disable it and restart to restore legacy generation; existing legacy file-search behavior is preserved. P4 did not add memory or migrations. See [P5 conversation contracts](docs/agent_migration/PHASE_05_CONTRACTS.md) for the subsequently added scoped memory and its deployment requirements.

Provider interface sources: [official file-search guide](https://developers.openai.com/api/docs/guides/tools-file-search) and installed SDK types in `openai/types/responses/response_file_search_tool_call.py`, `file_search_tool_param.py`, and `response_create_params.py`. Tests mock retrieval/SDK calls and block network; see the P4 test report for results. No live model/corpus quality is implied by mocked relevance tests.
