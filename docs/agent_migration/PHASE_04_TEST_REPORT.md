# P4 test report

**Gate recommendation: PASS for P4's mocked retrieval/provenance gate. Live corpus coverage remains explicitly UNVERIFIED. P5 has not started.**

## Branch, authorization and scope

- Branch: `feature/knowledge-tools-p4`.
- Base/current HEAD: `2312a4274ceb566ddc0d9f011516d60b459233c0`.
- User authorized P4 assuming P3 approved. No separately authorized live provider inspection was requested or performed.
- Changes remain uncommitted alongside the preserved prior working tree. No unrelated changes were reset, stashed or committed.

Delivered targeted `search_astrology_knowledge`, a replaceable hosted-file-search adapter, bounded source excerpts, available citation metadata, stable evidence IDs, request-local caching and agent integration. Retrieved viewpoints remain distinct from deterministic calculations/rules. The existing feature flag defaults off and retains the legacy pipeline. No P5 memory, P6 fluent-answer validator, P7 ledger, migrations, dependency changes, uploads or deployment work was started.

## Changed files

| File | P4 change |
|---|---|
| `astrology/rag/knowledge_contracts.py` | New typed search request, retrieval batch/protocol, tool input schema and limits |
| `astrology/rag/hosted.py` | New Responses hosted `file_search` adapter; structured results only, no generated-answer citation authority |
| `astrology/rag/knowledge.py` | New authorized session/cache, validation, snippets, metadata attribution and evidence hashes |
| `astrology/agent/orchestrator.py` | Seventh allowed tool; scope/authorization, shared retrieval budgets, returned K-reference validation |
| `astrology/agent/provider.py` | Advertise targeted knowledge function and untrusted-source policy |
| `astrology/agent/rendering.py` | Separately labeled source viewpoints, available attribution/missing metadata and explicit insufficient support |
| `astrology/test_knowledge.py` | 32 new offline P4 tests |
| `astrology/test_agent.py` | One intentional assertion update: advertised agent tools increase from six to seven |
| `KNOWLEDGE_TOOL_CONTRACTS.md` | Search/provider contracts, limits, failures, provenance and rollback |
| `docs/agent_migration/PHASE_04_PLAN.md` | Plan written before implementation |
| `docs/agent_migration/PHASE_04_KNOWLEDGE_AUDIT.md` | Local inventory separated from unverified hosted coverage |
| `docs/agent_migration/PHASE_04_TEST_REPORT.md` | This report |

A pre-P4 SHA-256 inventory captured 183 existing source/document/template/configuration files. After implementation, only four referenced files differed: the three agent modules above and the provider-schema assertion in `astrology/test_agent.py`. The other **179** matched. Existing calculation files, P2 tools, rule YAML, model schemas, migrations, settings, legacy LLM code, views, templates and dependencies were not changed by P4. New files are outside that baseline and listed above.

## Commands and actual results

```powershell
# Baseline before P4 implementation:
.\.venv\Scripts\python.exe manage.py test --verbosity 0 --noinput

# Initial focused retrieval suite:
.\.venv\Scripts\python.exe manage.py test astrology.test_knowledge --verbosity 1 --noinput

# Expanded retrieval plus existing agent suite:
.\.venv\Scripts\python.exe manage.py test astrology.test_knowledge astrology.test_agent --verbosity 1 --noinput

# Final complete discovery:
.\.venv\Scripts\python.exe manage.py test --verbosity 1 --noinput

.\.venv\Scripts\python.exe manage.py check
```

| Execution | Actual result |
|---|---|
| Baseline | **138 passed**, 71.068 seconds |
| Initial P4 suite | **29 passed**, 7.797 seconds |
| Expanded P3/P4 suite | **70 passed**, 31.486 seconds: 32 P4 plus 38 P3 |
| Final full suite | **170 passed**, 88.096 seconds; **zero skips** |
| Existing regressions within final suite | **All 138 passed** |
| New P4 tests within final suite | **All 32 passed** |
| Django system check | **No issues**, zero silenced |

New/affected Python files were also parsed successfully with Python's AST parser. No dependencies were installed. Django created/destroyed its isolated test database; no migration command was run against the application database. Existing chart-refresh regression coverage remained its original dry-run test.

## Acceptance matrix

Tests are in `astrology/test_knowledge.py::KnowledgeTests` unless stated otherwise. Synthetic passages are authored test fixtures, not quotations from private books.

| ID | Expected | Actual test evidence | Result |
|---|---|---|---|
| P4-01 | Topic-specific passages and available metadata | `test_p4_01_targeted_query_returns_passage_and_available_metadata` verifies career/D10/tenth-lord terms, returned excerpt/book/page/ID, untrusted-text label and unverified coverage. Agent integration test verifies search follows deterministic facts/Dasha/rules and is optional | PASS, mocked relevance |
| P4-02 | No matching source means insufficient support | `test_p4_02_empty_results_mean_insufficient_support` asserts partial/insufficient and no passages. Filter tests verify an unavailable requested source/tradition does not become fabricated support; renderer explicitly says insufficient support | PASS |
| P4-03 | Distinct contrary viewpoints | `test_p4_03_contrary_sources_remain_distinguishable` retains separately identified Parashari/Jaimini fixtures, contrasting text and source-specific attribution; output explicitly declines assumed agreement | PASS, synthetic viewpoints |
| P4-04 | Cite actual retrieved evidence, never invented metadata | Tests verify filename/query/source text cannot supply missing book/chapter/page, missing citations are explicit, document title stays a document rather than an invented book, SDK-generated prose/annotations are ignored, changed citation cannot reuse an old K ID, and invented agent K references are rejected | PASS |
| P4-05 | Retrieved injection cannot override behavior | `test_p4_05_injected_passage_cannot_expand_authority` passes a malicious excerpt to the next planner round; proposed Python action is rejected by server allowlist, no extra action dispatched, text is labeled and script markup escaped by existing formatter | PASS |
| P4-06 | Missing store configuration is safe | `test_p4_06_missing_configuration_never_calls_provider` tests absent key/store and each individually missing. Returns `knowledge_not_configured`, no data and no provider construction/network call | PASS |
| P4-07 | Bound result/snippet/token usage | Tests verify five results, Unicode-safe 1200-byte snippets/6000-byte total/32-KiB envelope, request bounds, conservative token reservation before paid dispatch, actual usage/overrun handling, shared planner/retrieval round/token limits and stop after hosted overrun. SDK test verifies one forced file-search invocation and 512 output tokens | PASS; hosted input caveat below |
| P4-08 | Repeat search reuses request-local results | Tests verify normalized case/order duplicates reuse session cache with zero new usage, copies prevent caller mutation, no cross-consultation cache reuse, adapter/version change misses cache, and repeated agent search deduplicates without another paid retrieval | PASS |
| Additional safety | Ownership and server-only store scope | Anonymous/cross-user/missing chart cases return no evidence/provenance. Cache-hit revocation and ownership loss during retrieval deny results. Agent cannot change chart, topic, vector store or advertised tools. Empty/malformed/incomplete/provider-error results are explicitly handled | PASS |
| Regression | Preserve prior behavior | All 138 prior tests pass, including P2 compatibility/authorization and P3 feature-flag/factual narrowness. The only prior-test edit reflects the intentionally added seventh agent function | PASS |

The 32 methods include parameterized subcases; acceptance IDs are not a claim of only eight assertions. Local deterministic tools still run without an LLM. Hosted retrieval is separately injectable and fully mocked in automated tests.

## Existing failures versus new issues

**Prior failures observed: none.** All 138 baseline tests passed before implementation.

**New test failures observed: none.** Initial 29-test retrieval suite, expanded 70-test agent/retrieval suite and final 170-test discovery all passed. Citation integrity, document-title preservation and hosted-overrun stopping received additional explicit tests before the final full run. No legacy numerical expectation was changed or hidden with a skip/expected failure.

## Corpus audit and provenance boundary

See [knowledge audit](PHASE_04_KNOWLEDGE_AUDIT.md).

- A local settings-only check found vector-store and API-key configuration present. Values were not printed, validated or used for live calls.
- Local Markdown contains source/extraction notes and application/migration documentation. This is not evidence of uploaded/indexed books. No local Markdown was uploaded by P4.
- No live vector-store inventory, pagination, processing-status/metadata audit or relevance query was performed. **Actual indexed books/Markdown, chapter coverage, OCR quality and live retrieval quality remain UNVERIFIED.**
- Source notes reference external book files; those files and their historical page/readability claims were not independently rechecked.
- Future live inspection requires separate authorization and a capped read-only scope. The audit documents that procedure. A single returned passage would verify that hit, not coverage of an entire book.

P4 gate permits unverified live coverage when explicitly identified, so this does not prevent the **mocked** phase gate from passing. It does prevent claiming the live corpus is complete or live retrieval quality certified.

## Mocks, cost and privacy

- All hosted retrieval and planner decisions are mocked; the SDK-specific test uses a fake client and synthetic credentials/store identifiers.
- Tests block socket connections and the default OpenAI constructor. The adapter test temporarily supplies a fake client inside that block.
- No OpenAI, GeoNames or payments API call occurred. No files were uploaded/deleted, no embeddings were created, and no paid smoke test was run.
- Deterministic integration uses synthetic test-database chart data, not real-user records. No production birth records, full private prompts, book texts, transcripts or credentials were written to logs/reports.
- External official documentation was read to confirm the provider interface; that is not live corpus/API verification.

**Paid API calls: 0. Automated-test provider cost: $0.**

## Limits and unresolved risks

1. Hosted input/context usage is provider-controlled. The wrapper reserves a conservative context allowance, bounds requested search count/output, checks actual usage and stops after an overrun. It cannot retrospectively prevent tokens already consumed by an unexpectedly large hosted context. Exact currency budgets/refunds remain P7; no absolute hosted-input spend guarantee is claimed.
2. Local excerpt/result/envelope limits are enforced and Unicode-safe. Returned metadata may be incomplete or incorrect at source. It is preserved/flagged, not independently certified. Missing fields are never derived from filenames, query terms or LLM prose.
3. Metadata filters are verified post-retrieval. If relevant files lack requested tradition/source metadata, the tool can report insufficient support rather than assume a match. It does not silently make additional searches to compensate.
4. No live corpus relevance, permissions, ingestion completeness, source identity or OCR quality was verified. Mocked topical relevance does not certify real-world retrieval quality.
5. Retrieved text may contain malicious or incorrect claims. It remains labeled source text; the server controls tool authority and publication of calculated facts. Separate viewpoints are not treated as independent predictive confirmation or consensus.
6. P3 cooperative timeouts and preliminary evidence-report format remain. Full fluent answer validation is P6. Agent trace/evidence is returned in memory; persistent conversational memory is P5 and was not implemented.
7. Request-local cache is intentionally short-lived. A live index could change during a consultation; the cache does not claim durable content freshness. No cross-user or cross-question cached source state is introduced.
8. Default P3 model rounds/tokens may stop a consultation after useful source retrieval but before another planner finish round. Evidence remains available and the report marks the partial stop. No automatic paid legacy retry occurs.
9. Existing message-count credit accounting remains, including partial-answer behavior. A transactional ledger and billing guarantees are outside P4.

## Rollback and approval

Leave `ASTROGPT_AGENT_ENABLED` unset/false, or set it to false and restart Django, to use the preserved legacy pipeline. No database or dependency rollback is required. Do not reset the whole branch because it contains preserved uncommitted work from earlier tasks. If removing P4 manually, use the exact file map above and retain earlier P2/P3 changes.

**P4 mocked gate: PASS. Live corpus: UNVERIFIED. Approval requested for the next phase: YES; P5 has not been executed.**
