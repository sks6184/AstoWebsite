# Scoped IPv4 transport fix

Date: 2026-11-09. Scope: implement the client-local transport recommendation in `OPENAI_TIMEOUT_DIAGNOSTIC.md`; preserve calculations, agent architecture and provider request policies.

## Result

**Implemented and verified against the real OpenAI API.** A minimal authenticated request completed with HTTP 200 in **4.830 seconds**. One bounded RAG request returned HTTP 200 in **5.958 seconds**, with **one file-search call and one retrieved result**. Both used the new IPv4 transport, the configured model/key, verified HTTPS, the existing 20-second SDK timeout, and zero SDK retries.

The RAG probe used a deliberately small 64-token output allowance and returned `status=incomplete` with 64 output tokens. This establishes working authentication, provider connectivity and actual retrieval. It does **not** establish that the complete production-sized astrology interpretation finishes within 20 seconds. No extra paid request was made to obtain a longer answer or inspect the incomplete response further.

## Confirmed problem and fix

The preceding diagnostic reproduced two IPv6 TCP timeouts before successful IPv4 connections. DNS resolution ordered IPv6 first; the installed synchronous HTTP stack tried addresses sequentially. Raising a read timeout or retry count would not address that connection-selection problem.

`accounts/provider_transport.py::IPv4HttpClient` extends the installed OpenAI SDK's `DefaultHttpxClient`. It creates the direct HTTP transport with `local_address='0.0.0.0'`, binding outgoing sockets to IPv4. Failed IPv6 source-address binds are skipped without attempting a slow IPv6 connection. Hostnames remain hostnames: the API URL is not replaced with an IP address, and TLS hostname/certificate verification remains active.

HTTPX documents this binding mechanism in its [transport documentation](https://www.python-httpx.org/advanced/transports/). The implementation and tests were checked against installed `httpx==0.28.1` and `openai==1.109.1`.

No global DNS monkeypatch, OS networking change, dependency installation, feature-flag change or architecture rewrite was made.

## Changed source and call-site coverage

| Source | Change |
|---|---|
| `accounts/provider_transport.py::IPv4HttpClient` | Shared client-local IPv4 direct transport, retaining SDK defaults, TLS options, proxy discovery and cleanup. |
| `chat/llm_engine.py::generate_answer()` | Passes the scoped HTTP client to the legacy question-generation OpenAI client. |
| `chat/llm_engine.py::_generate_rashifal_answer()` | Applies the same transport to periodic readings. |
| `astrology/agent/provider.py::OpenAIProvider.complete()` | Supplies the transport without changing orchestration, tool schemas or budgets. |
| `astrology/rag/hosted.py::HostedFileSearch.retrieve()` | Supplies the transport without changing retrieval queries, result limits, metadata handling or provenance. |
| `chat/intent_engine.py::_llm_classify()` | Covers the auxiliary OpenAI classifier; preserves its existing request arguments and SDK timeout/retry defaults. |
| `charts/yearly_predictions.py::_llm_month_predictions()` | Covers the auxiliary yearly/monthly text-generation client, preserving existing provider defaults. |
| `scripts/diagnose_openai_timeout.py::live_worker()` | Verifies the same production transport class rather than a separate diagnostic transport. |
| `accounts/test_provider_transport.py` | Eight new offline regressions covering IPv4, TLS, authentication, defaults, proxies and cleanup. |

The production-source search found six OpenAI client-construction sites; all six now supply `IPv4HttpClient`. Test-only SDK clients intentionally retain mock transports. The existing `responses_create()` spending meter and transactional credit settlement were not bypassed or modified.

## Behavior and security preserved

- API keys, base URL/hostname, model, organization/project handling and authentication headers remain the SDK's responsibility. Keys and store IDs were never printed.
- Direct transports retain `verify`, certificate/custom-CA configuration, environment trust, HTTP protocol settings and SDK connection limits. Real live requests used the unchanged default verified TLS configuration.
- Legacy synthesis retains `timeout=20, max_retries=0`; agent and hosted retrieval retain their supplied timeout and zero-retry policy. The two auxiliary callers retain their pre-existing SDK defaults rather than acquiring a new timeout/retry policy.
- `DefaultHttpxClient` retains SDK connection pooling and redirect defaults. Agent/hosted retrieval still explicitly close clients; legacy cleanup mirrors the SDK's former default wrapper.
- Simply passing a custom `transport=` to HTTPX disables its automatic environment-proxy discovery. To avoid silently changing that behavior, the helper overrides only HTTPX's direct-transport initializer. Environment proxy selection, `NO_PROXY` and explicit mock transports continue to work.
- Proxy connections intentionally keep HTTPX's existing proxy transport. The scoped IPv4 binding applies to direct connections, not a forced bypass of a configured proxy. The inspected live environment had no proxy variables set.
- Astrology calculations, deterministic rule evaluation, prompt content, retrieval result limits, validation/repair, credits, usage ceilings and agent feature flags remain unchanged.

The helper uses HTTPX's protected `_init_transport` extension point to preserve proxy behavior. This creates a small version-compatibility dependency; the regression suite instantiates and exercises it against the installed version. Future HTTPX/SDK upgrades should run these tests.

## Real connectivity and RAG verification

The user explicitly requested real verification. Exactly one minimal authenticated API request and one bounded RAG request were attempted. Both used synthetic text only. No chart, birth data, question history, user identifier, source passage, API key or vector-store identifier was logged.

Both ran in isolated diagnostic subprocesses with a 40-second wall-clock watchdog, in addition to the unchanged 20-second SDK timeout. Each allowed 64 output tokens and no retries. The RAG request forced file search and requested one result, with at most one built-in tool call. This smaller retrieval/output scope belongs only to the diagnostic; production retrieval limits remain unchanged.

| Measurement | Minimal connectivity | Bounded RAG |
|---|---:|---:|
| Model | `gpt-4o-mini` | `gpt-4o-mini` |
| HTTP status | 200 | 200 |
| API response status | `completed` | `incomplete` |
| Outgoing body size | 109 bytes | 529 bytes |
| HTTP request-start timestamp from probe start | 1,560.390 ms | 1,537.058 ms |
| Response headers from probe start | 4,716.297 ms | 5,847.267 ms |
| Request-start to headers | 3,155.907 ms | 4,310.209 ms |
| Total elapsed | 4,830.090 ms | 5,958.293 ms |
| Provider-reported input tokens | 12 | 2,073 |
| Provider-reported output tokens | 2 | 64 |
| File-search calls observed | 0 | 1 |
| Retrieved results observed | 0 | 1 |
| SDK retries allowed | 0 | 0 |

These are one-shot measurements, not latency percentiles. They include client initialization; retrieval and model time cannot be separated from the combined non-streaming response. The response's exact incomplete reason was not retained by this metadata-only helper; using all 64 output tokens is consistent with the diagnostic output cap, but no separate reason code is claimed.

The spending guard's combined conservative preflight reservation was **US$0.02239615**, below the **US$0.03** verification ceiling. Applying the configured standard tariff to reported tokens and one file-search call gives a combined **US$0.00285235** usage-rated estimate before possible cached-token discounts. This is an estimate, not the provider invoice. These maintenance probes had no customer usage-request binding and consumed no customer's question credits.

The prior two diagnostic attempts hit their 40-second watchdogs. The two new scoped-IPv4 probes returned within approximately five and six seconds without increasing the SDK timeout. Together with the prior per-family TCP measurements, this supports the scoped transport fix rather than a claim that the RAG store needed rebuilding.

## Regression verification

Eight new tests in `accounts/test_provider_transport.py` cover:

1. Direct pool binds to IPv4, with hostname checking and `CERT_REQUIRED` enabled; transport retries remain zero.
2. SDK timeouts, connection limits and redirect defaults are retained; explicit request timeout/retry settings survive.
3. Environment HTTPS proxy and `NO_PROXY` routing remain active.
4. Custom trusted CA context is forwarded unchanged.
5. A real SDK request over a mock transport retains HTTPS hostname, bearer authentication and all four 20-second timeout settings.
6. Certificate rejection still propagates as a connection error, with no retry or TLS bypass.
7. An IPv6-first synthetic DNS result causes no IPv6 `connect()` attempt when an IPv4 source is bound; IPv4 connects instead. No live sockets are used.
8. Closing the client closes its transport lifecycle.

The existing real-SDK simulated connect/read timeout regressions additionally verify failed requests do not consume completed-reading credits. Existing agent, knowledge, authorization, cache, validation and ledger regressions are included in the relevant/full suites.

| Check | Result |
|---|---|
| Targeted transport/runtime/billing/knowledge suite | **PASS: 80 tests in 33.039 seconds**, no failures or errors. |
| Full Django regression suite | **PASS: 308 tests in 227.957 seconds**, no failures or errors. |
| `manage.py check` | PASS: no issues. |
| `node --test scripts/test_pilot_ui.cjs` | PASS: two UI protocol checks. |
| `manage.py pilot_readiness --development` | PASS: migrations current, wallets consistent and chart/conversation ownership consistent. Agent remains disabled. |
| `git diff --check` on touched tracked source | PASS; only existing line-ending notices. |
| Real minimal authenticated API request | PASS: completed, HTTP 200. |
| Real bounded RAG retrieval | PASS for connectivity and retrieval: HTTP 200, one returned result. Full prose completion not established by the capped probe. |

## Remaining scope and reload

Reload/restart the intended Django worker to ensure it imports the updated clients. No independently running worker was killed or restarted by this task. The verification calls exercised the actual transport class in separate processes.

The agent feature flag remains unchanged. This fix makes no claim that agent orchestration is now enabled. The large legacy prompt, preliminary fallback presentation issues and other limitations recorded in the timeout diagnostic remain separate concerns.

A full customer-chart reading was not sent as an additional paid smoke test. Successful bounded retrieval does not guarantee every large production response will finish before its existing read timeout or pass validation. No calculation logic or agent architecture was changed, and no P9 work was started.
