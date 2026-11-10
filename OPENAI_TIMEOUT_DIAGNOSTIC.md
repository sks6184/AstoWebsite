# OpenAI timeout diagnostic

Date: 2026-11-09. This is a diagnostic-only follow-up to `POST_P8_RUNTIME_FAILURE_REPORT.md`. No architecture, calculations, production timeout/retry limits, retrieval configuration, validation, credit policy, feature flags or network configuration were changed.

## Conclusion

**The application still uses the legacy single-shot pipeline. A concrete local connectivity fault was reproduced: DNS prioritizes two IPv6 endpoints that time out, while both IPv4 endpoints accept TCP connections in approximately 5 ms.** The installed synchronous HTTP transport tries resolved addresses sequentially. Its connection timeout applies to each socket attempt; SDK retry count zero does not eliminate those address-family attempts.

This is the strongest measured explanation for the stalled minimal and RAG probes. It is **not proof that OpenAI's vector store or generation service is broken**. The historical application stores only `provider_failure`, losing the underlying timeout subtype. Consequently, its exact connect/read/write/pool stage cannot be recovered retrospectively. Large prompt size is independently confirmed, but has not been proven to cause the reported timeout.

Recommended first intervention, **not applied here**: repair IPv6 connectivity or use a narrowly scoped IPv4-bound HTTP transport for the OpenAI client while preserving hostname verification, TLS, credits and budgets. Do not increase read timeout, change models, add retries, enable the agent or restructure RAG before addressing this observed network fault.

## Evidence and limitations

The latest provider-backed request was read from the actual local database. Its request status is `partial_free`; its one provider event is `error` with `error_code=provider_failure`, unknown input/output token usage, zero consumed customer credits and one released reservation. Saved assistant provenance explicitly reports `pipeline=legacy`, `validated=false`, and `status=legacy_unvalidated`. No customer identifiers, birth details, question text, key, store ID, IP address, source text or complete prompt were printed or copied into this report.

The actual affected chart was inspected in memory only for the offline replay. Its original question was not dumped; the replay used the already reported fixed example question. Replay called the real deterministic pipeline and spending guard with no request database binding and a mocked provider boundary. It used a separate in-memory cache and blocked sockets. It neither submitted a customer request nor mutated financial/history records.

Only a reloaded shell's effective settings and the stored request can be inspected here, not the environment snapshot of an independently running server worker. The observed response format, persisted provenance and default-off router agree with the legacy path.

## 1. Live request path

```text
chat.views.ask_question
  -> AskQuestionForm / owned chart
  -> chat.consultation_service.append_turn / _append_turn
     -> ownership, idempotence, revision and credit reservation
     -> consent-scoped context construction
     -> chat.agent_service.generate_question_answer
        -> ASTROGPT_AGENT_ENABLED=False
        -> generate_placeholder_answer / chat.llm_engine.generate_answer
           -> rule-based specific intent
           -> deterministic evidence + compact legacy prompt
           -> accounts.provider_meter.responses_create / Budget.before
           -> OpenAI.responses.create: file_search + synthesis in ONE request
           -> OpenAIError -> deterministic fallback
     -> fallback persisted as preliminary; credit reservation released
  -> 302 conversation redirect; history/status render with HTTP 200
```

`chat/agent_service.py::generate_question_answer()` selects legacy directly when the flag is false. It does not try the new agent first. The profiling spy observed **zero** calls to `run_consultation()`. Thus there was no agent planning loop, optional agent tool sequence or repeated agent call to diagnose in this request.

The new agent's separate implementation remains in `astrology/agent/orchestrator.py`, `astrology/agent/provider.py` and `astrology/rag/hosted.py`. Those components were not the route used by the reported failure.

## 2. Measured durations

### Persisted historical request: actual timestamps

| Interval | Seconds | What is actually known |
|---|---:|---|
| Usage request creation to final update | 31.005512 | Financial/request lifecycle, not complete browser wall time. |
| Usage request creation to provider reservation | 4.258255 | Includes calculations, context, client/prompt preparation and meter preparation. Cannot subdivide retrospectively. |
| Provider reservation to settlement | 26.747257 | Includes SDK/network time, error handling, fallback and persistence. **Not** an exact measurement of file search, generation, or the SDK call alone. |

The provider-event model has a creation timestamp but no completion timestamp or timeout subtype. Historical request/response timings cannot be reconstructed more precisely from these rows. The earlier console logs showing HTTP 302/200 are transport success, not successful interpretation.

### Instrumented offline replay: actual local measurements

Two profiles ran without an API call. The second, more detailed run measured:

| Stage / function | Milliseconds |
|---|---:|
| `build_chart_facts` | 0.516 |
| `build_dasha_facts` | 11.207 |
| `build_parashari_facts` | 0.245 |
| `build_varga_assessment` | 0.020 |
| `build_transit_facts` | 183.621 |
| `run_rule_engine` | 653.856 |
| `aggregate_scores` | 0.302 |
| `build_timing_window_selection` | 0.070 |
| `build_evidence_card` | 0.146 |
| Internal synthesis prompt builder | 0.463 |
| Entire deterministic evidence build | 882.695 |
| Entire legacy prompt build | 882.970 |
| Provider boundary with immediate simulated SDK timeout | 685.053 |
| Entire replay | 1,629.852 |

The first profile measured deterministic evidence at 764.648 ms and overall replay at 1,350.514 ms. These are local replay timings, not the original live request or a performance percentile. Parent totals include children; rows must not be added together. Other deterministic work and serialization are included in the parent totals. First-use tokenizer initialization and token estimation contribute to the simulated provider-boundary duration; it contains **no remote waiting**.

| Requested stage | Observation |
|---|---|
| Agent planning | Not executed; zero agent calls. |
| Each agent tool | Not executed; this route calls local deterministic functions instead. Measured functions are above. |
| Hosted `file_search` | Not individually observable in the non-streaming combined Responses request. Neither bounded live probe returned retrieval events/results. No duration invented. |
| Final model synthesis | Not separable from retrieval/network waiting in this route. No completed remote answer observed. |
| Legacy answer validation / repair | Zero calls on the timeout branch. `_fallback_answer()` returns before these stages. |
| Credit settlement | Verified by ledger and isolated regression; no precise standalone historical duration available. |

## 3. Request and SDK settings

| Item | Measured / inspected value |
|---|---|
| Model | `gpt-4o-mini` |
| Installed SDK | `openai==1.109.1` |
| HTTP client | `httpx==0.28.1` |
| Legacy client timeout | `timeout=20` |
| SDK retries | `max_retries=0` |
| HTTP-core connection retries | Installed default `retries=0`; distinct from sequential resolved-address attempts. |
| Legacy structured payload | 255,850 UTF-8 bytes |
| Serialized SDK request after meter settings | 319,547 bytes; not an exact wire-body measurement of the historical request. |
| Conservative input estimate | 101,573 tokens, including serialized-request overhead and 4,096-token allowance. Not provider-reported usage. |
| Output maximum | 1,200 tokens, injected by the free-plan meter. |
| Reasoning effort / maximum reasoning tokens | Not explicitly sent. No separate reasoning ceiling was configured in this request. |
| Retrieval configuration | One `file_search` definition; `max_num_results=8`. |
| Built-in call maximum | `max_tool_calls=1`, injected by the meter. |
| Storage | `store=False`, injected by the meter. |
| Streaming / background mode | Not requested. |
| Proxy environment | None of `HTTP_PROXY`, `HTTPS_PROXY` or `ALL_PROXY` present in the inspecting process. This does not exclude VPNs, OS firewalls or transparent network controls. |

Relevant sources: `chat/llm_engine.py::generate_answer()`, `accounts/provider_meter.py::Budget.before()`, `accounts/token_budget.py::input_token_bound()` and `accounts/usage_policy.py`.

The legacy route has no separate enforced overall application deadline around this SDK call. The agent's 60-second consultation limit is irrelevant when the agent is disabled. A float HTTPX timeout configures connect/read/write/pool timeouts; it is not a single total wall-clock budget. This was verified in installed `httpx/_config.py::Timeout` and `httpcore/_backends/sync.py::SyncBackend.connect_tcp()`.

The installed SDK catches `httpx.TimeoutException` and raises `APITimeoutError` **from** that exception in `openai/_base_client.py`. With retries zero it does not perform the normal automatic SDK retry. The cause chain can distinguish `ConnectTimeout`, `ReadTimeout`, `WriteTimeout` and `PoolTimeout` if captured before the fallback discards it. The official [Python SDK reference](https://developers.openai.com/api/reference/python) also documents timeout configuration and disabling retries; the locally installed version was treated as authoritative for exact behavior.

## 4. Payload audit

The outgoing payload's top-level fields are `user_question`, `depth_level`, `answer_language`, `answer_style`, `cost_control` and `evidence_payload`. The builder passes normalized/derived evidence rather than directly serializing the complete `SavedChart.chart_data` object. It does not append the entire conversation. The legacy router ignores consultation context even when memory consent is enabled.

Major evidence fields, measured as independently serialized UTF-8 JSON:

| Field | Bytes | Finding |
|---|---:|---|
| Jaimini | 88,085 | Includes 30,215 bytes of `dasha_sign_as_lagna`, plus relationship, childhood and multiple supporting assessments. These broad assessments are candidates for topic selection on a job question. |
| Timing selection | 44,062 | Best window 11,131; secondary windows 10,652; system intersections 21,863. |
| Transits | 41,040 | Detailed future-timing windows and scoped dasha/transit timeline remain present. |
| Triggered rules | 25,003 | 40 selected rules: 22 D10, 12 D1, six without a chart label. These counts do not prove individual rules unnecessary. |
| Evidence card | 13,671 | Summarizes timing already represented in selection/transit structures; semantically overlapping data can add prompt weight. |
| Parashari | 12,412 | Detailed derived evidence. |
| Yogini | 9,458 | One overlapping parent period after the previous incident's scope fix; the entire lifetime schedule is no longer sent. |
| Vimshottari | 8,819 | Derived dasha/current snapshot and assessment. |

Instruction text is additionally approximately 33 KB and contains many question-category instructions unrelated to the particular job question. It is counted in the request/token measurements. There is no reason to feed unrelated category instructions or broad childhood/relationship assessments into every career answer; these are measured reduction opportunities, **not proof of the network timeout's cause**. No further compaction was implemented here.

The old fallback also reads `evidence_payload.system_evidence.transits`, while the current compact payload stores `transits` directly. That explains why fallback text may say no windows were calculated despite prepared windows existing. It is a separate fallback presentation defect, not a cause of an SDK timeout. It was documented rather than changed in this diagnostic-only task.

## 5. Authorized live probes and cost bound

The user explicitly authorized **one minimal authenticated API test and one bounded RAG test**, with synthetic text, zero retries and combined estimated cost at most **US$0.03**. No personal chart or conversation was sent to either probe. No extra paid attempts were made after these probes.

Preflight through the existing spending meter reserved a combined conservative estimate of **US$0.02239615**, including a full-context input allowance for the RAG probe, at most one search, and 64 output tokens per probe. This is a worst-case reservation using the application's configured tariff, not an invoice. The [official model page](https://developers.openai.com/api/docs/models/gpt-4o-mini) lists the corresponding input/output token prices and context; the [official pricing page](https://developers.openai.com/api/docs/pricing) lists file-search call charges. Remote usage and any billing remain unknown when no response returns.

| Probe | Configuration | Actual result |
|---|---|---|
| Minimal authenticated Responses attempt | Synthetic "OK" request; no tools; 64 output tokens; timeout 20; retries zero. | Child process hit the diagnostic **40-second wall-clock deadline**. No final response or exception chain was returned. |
| Bounded RAG Responses attempt | Synthetic tenth-house concept query; configured store; forced file search; one result; one built-in call; 64 output tokens; timeout 20; retries zero. | Child process hit the same **40-second wall-clock deadline**. No passages, model answer or usage were received. |

The subprocess watchdog terminates the diagnostic worker; it does not establish that a remote request was accepted, cancelled or unbilled. **These are attempted authenticated probes, not successful authentication verification.** At that point the initial diagnostic helper only emitted detailed metadata on completion; termination lost intermediate progress. The helper was subsequently improved to flush stage metadata and preserve partial stdout at a deadline, but the paid probes were **not rerun**. Thus there is no measured HTTP request-start/header timestamp for those two attempts, and no claim that file search actually started.

## 6. Network isolation: no HTTP/API calls

Additional probes sent no credentials, HTTP requests or model inputs. They performed only DNS lookup, TCP connect and a TLS handshake to the standard API hostname; neither IPs nor certificates were logged.

### Aggregate connection probe

| Event | Elapsed from probe start |
|---|---:|
| DNS complete; four candidate addresses | 67.166 ms |
| TCP connected using `socket.create_connection(..., timeout=5)` | 10,097.181 ms |
| TLS context ready | 10,156.890 ms |
| TLS handshake complete; TLS 1.3 | 10,173.438 ms |

A socket timeout of five seconds still yielded roughly ten seconds to connect. Inspecting Python's installed `socket.create_connection()` showed that it iterates all `getaddrinfo()` results and sets the timeout on **each new socket**.

### Per-address-family probe

| DNS order | Family | Result with 2-second socket timeout | Duration |
|---:|---|---|---:|
| 0 | IPv6 | `TimeoutError` | 2,006.394 ms |
| 1 | IPv6 | `TimeoutError` | 2,000.740 ms |
| 2 | IPv4 | TCP connected | 4.830 ms |
| 3 | IPv4 | TCP connected | 4.825 ms |

The two failed IPv6 connections account for the aggregate probe's delay. Installed `httpcore/_backends/sync.py::SyncBackend.connect_tcp()` uses `socket.create_connection()`, and thus inherits this sequential behavior. Two unsuccessful 20-second address attempts can exhaust a 40-second diagnostic deadline before useful IPv4 traffic. This is a source-backed explanation consistent with the live-probe stalls, **not a recovered trace of those terminated workers**.

Constructing an ordinary HTTPX client without any request took 1,216.110 ms total including a 316.318-ms HTTPX import. Local client setup therefore also contributes some latency, but was far smaller than the measured IPv6 stalls.

### Classification

- **Confirmed network issue:** first two IPv6 TCP candidates time out; IPv4 TCP/TLS works.
- **Confirmed diagnostic application deadline:** both authorized child processes were stopped at 40 seconds.
- **Historical SDK timeout:** the displayed "Request timed out" is consistent with SDK `APITimeoutError`; the saved ledger lacks its HTTPX cause. The original exact network phase remains unknown.
- **Not established:** OpenAI service outage, vector-store corruption/unavailability, invalid API key, invalid model access, file-search duration or synthesis latency. No HTTP status response established any of these.

## 7. Smallest proposed fix and follow-up measurements

1. **Address the demonstrated network path first.** Repair the machine/network's IPv6 route or, for an application-local change, test an IPv4-bound HTTP transport (for example a transport using the installed `httpcore` `local_address` support). Preserve the original hostname, TLS verification, authorization, no-retry policy and all financial limits. Do not replace the URL with a bare IP, disable certificate checks, globally monkeypatch DNS or change OS networking as part of this report.
2. Before another paid experiment, capture safe connect/read/write/pool exception **types**, elapsed durations and response-header presence. The standalone helper now supports progress before termination; production logging still lacks that detail. Retain no exception text, request body, headers, birth data or retrieved snippets.
3. With working connectivity and a newly authorized small budget, repeat the smallest request before a RAG request. If minimal works and RAG fails, then investigate retrieval. If both work, measure the real synthesis request before deciding on read timeout.
4. Reduce redundant/topic-irrelevant legacy evidence and instructions as a separate measured optimization: Jaimini broad assessments, repeated timing representations and 40 full rules are the largest candidates. Preserve requested-period coverage, contrary evidence, provenance and validation inputs. Do not truncate calculated results indiscriminately.
5. Keep retries disabled for the diagnosis. Raising total timeout now would extend known IPv6 stalls. Change read timeout only if later traces establish successful connection/upload followed by a slow provider response. No agent-loop correction is relevant to this legacy request.

No proposed runtime fix was applied. In particular, this report does not claim that a customer can now receive a successful RAG answer.

## 8. Regression tests and changes

Files added/updated for this task only:

- `scripts/diagnose_openai_timeout.py`: default offline, metadata-only profiling; explicit authorized-live mode with two synthetic attempts, preflight cost check, no retries, subprocess wall deadline, safe progress and exception-type capture. This helper is not exposed through any agent tool registry or production endpoint.
- `chat/test_runtime_failure.py`: two regressions using the **real installed OpenAI SDK** over HTTPX `MockTransport`, separately raising `ReadTimeout` and `ConnectTimeout`. Both follow the shared meter, actual legacy fallback and actual transactional settlement. No live network or paid call is used.
- This diagnostic report.

Each new regression verifies one transport attempt, no repair attempt, no completed/validated answer marker, provider-event error with unknown tokens, **zero consumed credits**, released reservation and zero outstanding wallet reservations. A fallback can be stored as a preliminary assistant message / `partial_free`; neither `TurnOutcome.state=complete` nor the presence of that message means a paid completed reading. The real ledger must be checked.

| Check | Result |
|---|---|
| `manage.py test chat.test_runtime_failure accounts.test_usage --noinput --verbosity 0` | **PASS — 40 tests, 8.023 seconds**, including both new timeout regressions. |
| Earlier intermediate run with read-timeout regression only | PASS — 39 tests, 6.085 seconds. |
| `manage.py check` | PASS — no issues. |
| Offline affected-chart profiles | PASS — no remote requests; metadata and real deterministic stage timings captured. |
| DNS/TCP/TLS baseline | PASS for DNS and IPv4 TLS; IPv6 failure reproduced. |
| Authenticated minimal and RAG availability | **INCONCLUSIVE / BLOCKED** by the 40-second diagnostic deadlines; no successful remote response. |
| Production fix / repeated paid probes | NOT RUN — outside this diagnostic stop point. |

No pre-existing failure was observed in the relevant 40-test run. The previous turn's 298-test full-suite result belongs to the earlier incident fix; it is not represented as a newly rerun full suite for this diagnostic-only task. No P9 work was started.
