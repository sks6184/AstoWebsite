# Phase 1 — Regression Protection Plan

**Date:** 7 November 2026 (Asia/Bangkok).  
**State:** PLAN ONLY — awaiting approval; no new tests or production changes implemented.  
**Objective:** protect existing deterministic astrology and question-processing boundaries before any agent-driven conversational redesign.

## 1. Scope and stopping boundary

This plan was prepared from [ASTROGPT_ARCHITECTURE.md](ASTROGPT_ARCHITECTURE.md), the current source, test definitions, and a fresh baseline test run. The architecture document is an AS-IS description, not an independent numerical oracle. The inspected working tree includes existing uncommitted changes; it is not equivalent to HEAD `2312a4274ceb566ddc0d9f011516d60b459233c0` alone.

The [agent restructuring master plan](ASTROGPT_AGENT_RESTRUCTURING_MASTER_PLAN.md), P1, was also read for alignment. Its broader fixtures/tests/report deliverables are **not authorized by the current plan-only request**; they remain proposed follow-up work after approval. This task does not create a Phase 1 implementation test report or claim the full P1 implementation gate is complete.

**Phase 1 includes, after approval:** test isolation, reference-fixture provenance, characterization snapshots, calculation invariants/correctness checks, rule contracts, mocked existing generation paths, and chart/conversation authorization regression tests. Each proposed test must say whether it protects existing behavior or establishes an independently justified requirement.

**Excluded:** agents, tools exposed to agents, conversation-memory redesign, new APIs, background jobs, production refactoring, calculation-method changes, schema migrations, payment work, routing changes, dependency upgrades, and Phase 2 implementation. A regression plan must not silently turn into fixes. If a new test exposes an existing defect, record it and request an explicitly scoped corrective decision before changing production behavior.

**Current deliverable:** this file only. Existing application code, test files, architecture document, models, migrations, configuration and dependencies remain unchanged. Tests executed below used an isolated test database; no production migration command or live provider request was issued.

## 2. Measured baseline: existing failures reported separately

### 2.1 Run executed for this plan

```powershell
.\.venv\Scripts\python.exe manage.py test --verbosity 2 --noinput
```

| Item | Observed result |
|---|---|
| Discovery | 70 tests |
| Result | **70 passed; 0 failures; 0 errors** |
| Test execution time | 40.818 seconds, as reported by Django |
| Process exit | 0 |
| Django system checks | No issues, 0 silenced |
| Database | `file:memorydb_default?mode=memory&cache=shared`; created and destroyed by the runner |
| Migration activity | Migrations applied to the isolated in-memory test database, not the application database |
| Python | 3.11.9 |
| Installed libraries observed | Django 5.2.13; pyswisseph 2.10.3.2; PyYAML 6.0.3; OpenAI SDK 1.109.1 |

This is a working-tree baseline, not a production certification or a declaration of numerical accuracy. No live OpenAI/GeoNames request is exercised by these existing tests. Source inventory found tests only in [astrology/tests.py](astrology/tests.py) and [astrology/test_transit_timeline.py](astrology/test_transit_timeline.py); no persisted independently approved golden-fixture directory or coverage configuration was found. Lack of measured coverage must not be expressed as a percentage.

### 2.2 Existing test failures

**None in this run.** Historical failures from earlier development are not current failures. The source-review findings in section 9 are separately classified as pre-existing risks/coverage gaps; they are not reported as failed tests or regressions introduced by this task.

### 2.3 Existing suite composition

| File / class | Count | What it mainly checks |
|---|---:|---|
| `astrology/tests.py::AstrologyEngineTests` | 59 | Fact shape, selected Jaimini/Yogini rules, evidence/prompt plumbing, scoring metadata, validation and remedy examples. |
| `astrology/tests.py::RefreshChartDataCommandTests` | 1 | Dry-run command completes; no explicit assertion currently proves chart JSON was unchanged. |
| `astrology/test_transit_timeline.py::DashaTransitTimelineTests` | 9 | Synthetic boundaries, same-lord deduplication, sign re-entry, SAV sequencing, missing evidence, range clipping, weighted summary, scope, compaction and transit-lord wording. |
| `astrology/test_transit_timeline.py::RealChartTransitPipelineTests` | 1 | Real calculation → timeline → compact prompt/evidence-card consistency; not an independent ephemeris comparison. |
| **Total** | **70** | Full method inventory is in Appendix A. |

## 3. Test types: snapshots are not correctness evidence

| Type | Meaning | What it cannot establish |
|---|---|---|
| **S — behavior snapshot** | Freeze selected normalized output of the current implementation for explicit inputs, date, rules and configuration. | That the current numerical result or business/security policy is correct. |
| **I — invariant/metamorphic test** | Check continuity, bounds, ordering, deduplication, conservation or a mathematically justified transformation. | Agreement with an external chart or the full doctrine of an astrology method. |
| **C-local — independently reasoned local correctness** | Assert arithmetic, calendar, rule-DSL or security outcomes from a specification/hand derivation that does not call the subject to generate its expected value. | Complete astronomical or classical-method validation. |
| **C-ref — independently verified reference correctness** | Compare to reviewed astronomical/classical reference results, with provenance and compatible calculation settings. | Methods or settings not represented by the reference fixtures. |
| **K — integration/contract test** | Verify requests, call boundaries, persistence, provider mocks, payloads and caching. | Factual quality of model prose or hosted retrieval results. |
| **A — authorization/security correctness** | Require an authenticated owner, reject cross-user identifiers, and prohibit side effects/provider calls on rejection. | All deployment/security properties beyond the tested routes. |

An existing assertion can belong to more than one category. For example, hardcoded Chara ordering is C-local relative to the chosen specification, but still needs external-method review before being called independently verified Chara correctness. The existing annual-Yogini example is source-attributed, not a newly verified oracle: the source note itself documents an inconsistent sentence. The existing Sun-ingress test is a narrow behavioral/numerical assertion without a recorded independent export.

### Snapshot policy

- Snapshot deterministic evidence and mocked call contracts, **not live LLM prose**. Use fixture responses to test rendering/persistence without claiming the response is a correct prediction.
- Normalize dictionary ordering, timestamps/IDs and explicitly non-contractual metadata. Preserve planet codes, coordinates, period dates, signs/houses, SAV/BAV arrays, rule IDs, outcomes, selected windows and validation results where relevant. Do not normalize away discrepancies under test.
- Use synthetic or explicitly consented/redacted charts. Do not copy live users, messages, session cookies or uploaded books into fixtures.
- Label snapshots with `behavior_only`, code/fixture version and assumptions. A snapshot exported from `build_vedic_chart` is never promoted to C-ref just because it is stable.
- Unsafe current behavior may be characterized in an issue-linked diagnostic snapshot, but must not become the accepted requirement. Authorization rejection tests remain correctness gates even if the current implementation fails them.
- Snapshot updates require an explained diff and review; never regenerate expected results automatically to make a failed test pass.

Sources: [chart engine](charts/astro_engine.py), `build_vedic_chart`; [evidence service](astrology/services/prediction_service.py), `build_prediction_evidence`; [generation](chat/llm_engine.py), `generate_answer`; [annual source notes](astrology/docs/yogini_ocr_task.md), Chapter 12; [existing ingress test](astrology/tests.py), `test_midday_transit_sampling_handles_sun_taurus_ingress`.

## 4. What is already protected, and what is missing

`E` below means the named behavior has an existing assertion, not that the entire domain is covered. `P` means partial coverage; `M` means no matching automated assertion was found.

| Domain | Existing assertions and classification | Missing protection / independent reference need |
|---|---|---|
| Natal D1 | **P:** `test_chart_engine_calculates_supported_vargas` checks presence/planet lists. Sample chart is calculated at runtime. | Longitude/ascendant/nakshatra/house goldens; timezone/DST; missing coordinates; normalized angles; repeated-call determinism. Numerical goldens require REF-NATAL. |
| Divisional charts | **P:** chart keys exist; `test_chart_facts_expose_varga_lookup`; selected D9/D10 interpretive tests. | Every transform and rashi/part boundary, odd/even/modality cases, D30 unequal divisions, D60 sensitivity; independent transformed placements for all supported charts. REF-VARGA required. |
| Vimshottari | **P:** lord dignity, pair/divisional facts and general dasha shape. | Moon-nakshatra balance, all nine order rotations, full MD/AD schedules, **birth-time AD within an already elapsed MD**, truncation/year conventions, exact handover behavior. REF-VIM required. |
| Yogini | **P:** active facts, contextual lord assessment, pair/baseline checks; isolated annual example. | Natal starting Yogini, full birth balance and AD schedule, all remainders, four-cycle dates, boundary resolution. REF-YOG required; annual helper must remain isolated. |
| Chara/Jaimini | **E/P:** seven karakas, two cycles, selected major/subperiod orders, several dual-lord cases, rashi aspects, outside-range lookup, many interpretive facts. | Complete independent schedule and both directions; dual-lord tie-breaks; exact date handovers; independently reviewed method choices. REF-CHARA required. |
| Transit boundaries | **E/P:** nine synthetic timeline tests plus real-chart plumbing; one actual Sun-ingress example. | Dense sign/MD/AD overlap, all lords, Moon, retrograde actual dates, noon-vs-midnight, leap day, incompatible legacy selectors, real ephemeris oracles. REF-TRANSIT required for real positions. |
| BAV/SAV | **M** direct array/totals tests; **P** mocked SAV attachment and one Sun/SAV assertion. | Seven full BAV arrays, contributor-table review, per-sign SAV sum, total 337, sign-to-house mapping, thresholds/missing/zero distinction. REF-AV required for independent correctness; totals alone are invariants. |
| Rule engine | **E/P:** current rules load; Jaimini source/ID/weight metadata; zero-weight behavior; selected fact→rule triggers. | DSL operator truth tables, nested/list paths, malformed rules, missing files, all-file IDs, signed weighted sums/clamping, deterministic replay, Python/YAML composition and prompt prioritization. No astronomy oracle needed for DSL/math; doctrine review needed for interpretations. |
| Existing question generation | **P:** payload building, prompt sections, validator examples, remedies. No test calls `generate_answer` through a mocked provider or POSTs Ask. | Authenticated form→generation→message→redirect, both branches, cache isolation, provider/config failures, repair lifecycle, same question on different charts, renderer escaping. Use mocks, not live models. |
| Chart authorization | **M:** no HTTP owner/foreign-user/anonymous route tests. The lone database test is command-related. | Owner list/Ask/create/delete, forged chart ID, foreign reading/history, GET/POST/CSRF behavior, zero writes and zero generation on rejection. No astrology oracle needed. |

Sources: Appendix A names every existing method; production anchors are in section 6. Assertions such as `assertIn`, output length or comparing facts derived from the same chart should not be relabeled as independent numerical tests.

## 5. Test inputs and independent reference protocol

### 5.1 Reusable inputs proposed after approval

| Input ID | Exact input / construction | Use |
|---|---|---|
| **F-NATAL-1** | Synthetic name; 1990-05-17, 10:30:00, Delhi; latitude 28.613900, longitude 77.209000, `Asia/Kolkata`. Already used by `sample_chart_data()`. | Stable behavior snapshot plus a separately acquired REF-NATAL comparison; expected astronomical values are **not yet approved**. |
| **F-NATAL-2** | Synthetic name; 2000-01-01, 12:00:00, Greenwich; latitude 51.477900, longitude 0.000000, `UTC`. | UTC reference, year boundary and alternate Lagna. Independent results pending. |
| **F-NATAL-3** | Synthetic name; 1995-07-15, 18:45:00, Sydney; latitude -33.868800, longitude 151.209300, `Australia/Sydney`. | Southern latitude/hemisphere and differing timezone. Independent results pending. |
| **F-CLOCK** | Freeze today to 2026-11-07 in test-local patches; use timezone-aware UTC instants for sampling tests. | Default scan ends 2029-11-07; next-year scope is 2027-01-01 through 2027-12-31; explicit May 2028 scope is 2028-05-01 through 2028-05-31. |
| **F-DASHA** | Existing `boundary_chart()`: Ke MD / Ve AD `[2027-01-01,2027-01-05)`; Ve MD / Ve AD `[2027-01-05,2027-01-08)`; Ve MD / Su AD `[2027-01-08,2027-02-01)`. | No ephemeris assumptions; exact synthetic interval oracle. |
| **F-ANGLES** | For every source rashi and each transform partition, use interior midpoint and boundary ± `1e-7` degrees; include 0, 30, 359.999999; treat exact nonbinary boundaries separately. | D1/varga sign and house boundaries with reviewed rational interval tables. |
| **F-AV** | Synthetic longitudes/signs for Sun/Moon/Mars/Mercury/Jupiter/Venus/Saturn and Lagna; independently reviewed 7×12 score table. Separate fake SAV rows with 0, 24, 25, 28, 29 and missing values. | Arithmetic/mapping/threshold tests; full reference table pending. |
| **F-USERS** | Test-database users A/B, each with a uniquely named chart; A/B conversations and unique answer markers. | Cross-user and no-side-effect assertions. Never use real accounts or chart IDs. |
| **F-QUESTIONS** | “When will I change jobs?”, “Is there a chance of job change next year?”, “Will I change jobs in May 2028?”, “Give me a yearly horoscope”, plus one ambiguous classifier input. | Event/periodic routing and fixed/default scopes, with expected mode explicitly set or classifier mocked per test. |
| **F-PROVIDER** | Local fake Responses objects containing `output_text`, `usage.input_tokens`, `usage.output_tokens`; separate fake classifier response and explicit API-error fake. | Request/caching/repair contracts without model nondeterminism or network. |

### 5.2 Oracle register — none newly verified in this planning task

| Reference ID | Independently verified material needed | Required compatibility / acceptance evidence |
|---|---|---|
| **REF-NATAL** | Export/report from a separately verified ephemeris/chart computation for F-NATAL-1/2/3. | UTC conversion, Lahiri definition, true versus mean node, coordinate precision, geocentric calculation flags, ephemeris dataset/version, whole-sign house interpretation and all nine planet/ascendant positions. |
| **REF-VARGA** | Reviewer-approved partition/rashi table for each of D2/D3/D4/D7/D9/D10/D12/D16/D20/D24/D27/D30/D40/D45/D60, and reference placements from REF-NATAL. | Name the tradition/variant, especially Hora/D30/D60. Review odd/even and modality starts; do not use `_varga_longitude` to compute expected answers. |
| **REF-VIM** | Hand-audited Moon-nakshatra birth balance, MD/AD schedule and birth-current-AD example from an independent source. | Document year length, source end inclusivity, initial balance/subperiod treatment and date truncation; do not accept date discrepancies under a blanket ±1-day tolerance. |
| **REF-YOG** | Independent natal Yogini starting period/balance and AD sequence/dates; review the annual Pingala example separately. | Eight-lord order, modulo-zero mapping, 36-year cycle, partial first period, proportional subperiods and date policy. Resolve the documented annual-book inconsistency before C-ref classification. |
| **REF-CHARA** | Complete independently reviewed schedule and synthetic dual-lord examples. | Seven-karaka convention, sign direction groupings, Scorpio/Aquarius dual-lord policy, association/degree tie-breaks, own-sign years and subperiod order. Different Chara traditions are not interchangeable oracles. |
| **REF-TRANSIT** | Independent dated longitudes/rashi samples for Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, true Rahu and opposite Ketu around handovers and retrogrades. | Same UT sampling instant and Lahiri/node settings; compare actual positions first, then the day-resolution segmentation. An exact ingress instant is not the expected output of a daily-noon sampler. |
| **REF-AV** | Separately checked contributor-house rules and full BAV/SAV arrays for at least two natal configurations. | Seven classical BAV rows; Lagna contribution convention; sum consistency and natal sign-to-house mapping. No invented Rahu/Ketu BAV. |

A second wrapper around the same Swiss Ephemeris build is useful to isolate application mapping bugs, but is only **partially independent** of the astronomical library. Record that limitation. Independent fixtures must not import AstroGPT to calculate their expected values. Book/source notes in this repository provide leads, not proof that a fixture has been independently checked.

### 5.3 Fixture manifest and tolerances

After approval, every reference fixture should carry: fixture ID; synthetic birth/UTC inputs; coordinates/timezone and timezone-data version; method settings; reference provider/tool/book and version/page; acquisition date; reviewer and review date; provenance/content hash; expected values/units; numerical tolerances; boundary convention; `approval_status` (`pending`, `approved`, `disputed`); and why any difference is acceptable. Store short paraphrases/reference coordinates, not copyrighted book passages.

Proposed tolerances, subject to reference review:

- Planet/node longitudes: circular angular difference, initially ≤1 arcsecond **only for matched settings/datasets**. Ascendant initially ≤10 arcseconds with matched coordinate/time precision. Record any justified alternative per fixture; do not widen tolerances merely to obtain a pass.
- Synthetic varga arithmetic: ≤`1e-8` degrees away from boundaries. Exact rashi/house/karaka labels remain exact categorical assertions. Compare original longitude before a boundary disagreement is classified as an error; float representation at a rational boundary needs an explicit decision.
- Dasha dates: exact ISO dates after the agreed year-length and truncation rules; underlying duration math can have a stated floating-point tolerance, not an unexplained date tolerance.
- BAV/SAV arrays, rule outcomes, selected discrete lords and authorization results: exact integers/values. Birth-time sensitivity of high vargas is a declared assumption, not a numeric tolerance.
- Unapproved expected numbers remain **pending**, never copied from current output into an “independent” fixture. A pending reference is a gate blocker, not a passing test with null expected values.

Sources: [astro_engine.py](charts/astro_engine.py); [vimshottari.py](astrology/calculations/vimshottari.py); [yogini.py](astrology/calculations/yogini.py); [jaimini.py](charts/jaimini.py); [Ashtakavarga](charts/ashtakavarga.py); [transit timeline](astrology/calculations/dasha_transit_timeline.py).

## 6. Phase 1 test-case matrix

**Legend:** `E` existing relevant test; `P` partial existing coverage requiring extension; `M` missing. All additions below are proposed, not implemented. `P0` means required protection before architectural extraction; `P1` means broader Phase 1 depth. A reference-dependent case is explicitly pending until its oracle is approved.

Source abbreviations below link to actual files and functions; existing method names resolve in Appendix A. Parameterized rows represent a family of cases rather than one assertion.

### 6.1 Natal charts

| ID / priority | Type / coverage | Inputs | Expected outcome | Source / existing coverage |
|---|---|---|---|---|
| **NAT-01 / P0** | S / M | F-NATAL-1, fixed versions/clock | Reviewed normalized snapshot of D1, planet codes, Lagna, coordinates/timezone and chart metadata. It protects compatibility, not numerical truth. | [astro_engine.py](charts/astro_engine.py), `build_vedic_chart`; existing `test_chart_engine_calculates_supported_vargas` is shape-only. |
| **NAT-02 / P0** | C-ref / M | F-NATAL-1/2/3 + REF-NATAL | Every longitude/Lagna within approved tolerance; exact signs, houses, nakshatra/pada and retrograde labels. **Expected numerical tables pending.** | `build_vedic_chart`, `_planet_row`, `_nakshatra_details`. |
| **NAT-03 / P0** | C-local / M | 1990-05-17 10:30 `Asia/Kolkata`; same date 05:00 UTC | UTC conversion is exactly 05:00 UTC; equivalent instants yield identical positions/labels for identical coordinates. | `_local_datetime_to_utc`, `build_vedic_chart`. |
| **NAT-04 / P1** | C-local + S / M | New York 2024-03-10 01:30 and 03:30; ambiguous 2024-11-03 01:30; invalid timezone | Valid cases convert to 06:30 and 07:30 UTC. Ambiguous/nonexistent-local-time policy and current invalid-zone→UTC fallback are recorded separately; no silent policy correction. | `_local_datetime_to_utc`; [forms.py](charts/forms.py), `clean_timezone`. |
| **NAT-05 / P0** | I / M | F-NATAL-1/2/3 | Nine planets exactly once plus one Asc; Ketu opposite Rahu modulo 360; houses/signs in 1–12; `_planet_row` labels agree with longitude; repeated calls do not mutate prior output. | `_planet_row`, `_assign_jaimini_karakas`, `build_vedic_chart`. |
| **NAT-06 / P0** | K + S / M | Missing latitude/longitude; chart-create form without selected coordinates | Direct calculator returns explicit calculation error; creation follows current placeholder path. No test treats placeholder as a complete natal chart. | `build_vedic_chart`, `build_placeholder_chart`; [charts/views.py](charts/views.py), `chart_create`. |
| **NAT-07 / P0** | C-local / P | Sign/nakshatra/pada interior and boundary ±epsilon; deliberate karaka ties | Correct reviewed interval labels; seven karakas exclude nodes. Tie handling is characterized and independently reviewed, not guessed. | `_sign_index`, `_nakshatra_details`, `_assign_jaimini_karakas`; existing seven-karaka order test. |

### 6.2 Divisional charts

| ID / priority | Type / coverage | Inputs | Expected outcome | Source / existing coverage |
|---|---|---|---|---|
| **VAR-01 / P0** | I + S / P | F-NATAL-1; all sixteen supported chart keys | Complete expected chart set, one Asc and nine planets per chart; houses/signs in range; normalized lookups agree with raw chart rows. | [varga.py](astrology/calculations/varga.py), `SUPPORTED_VARGAS`, `build_varga_facts`; existing supported-varga/lookup tests. |
| **VAR-02 / P0** | C-local/C-ref / M | F-ANGLES across all 12 signs and every supported transform | Correct rashi per reviewed REF-VARGA partition table before/on/after boundaries; exact boundary representation is decided explicitly. **Table approval pending.** | [astro_engine.py](charts/astro_engine.py), all `_..._longitude` transforms. |
| **VAR-03 / P0** | C-ref / M | REF-NATAL positions + REF-VARGA | D9 and D10 transformed longitudes, Lagna and houses match independent expected rows; repeat for remaining thirteen divisional transforms. **Goldens pending.** | `_build_divisional_chart`, `_navamsha_longitude`, `_dasamsa_longitude`, remaining transforms. |
| **VAR-04 / P0** | C-local/C-ref / M | D30 odd boundaries 5/10/18/25 degrees; even 5/12/20/25; ±epsilon | Correct unequal interval and destination rashi, with output degree continuity convention documented. **Method table review pending.** | `_trimsamsa_longitude`. |
| **VAR-05 / P1** | C-local/C-ref / M | D60 0.5-degree edges; D16/D20 modality starts; D24 parity; D27 element starts | Match independently approved transform tables; stable neighboring-boundary tests; birth-time sensitivity remains explicit. | `_shashtiamsa_longitude`, `_shodashamsa_longitude`, `_vimshamsa_longitude`, `_chaturvimshamsa_longitude`, `_saptavimshamsa_longitude`. |
| **VAR-06 / P0** | K / P | Absent D9/D10 and selected category charts | Normalizers/evaluators do not fabricate chart facts; missing/limited evidence remains visible. Snapshot current category requirements separately from AGENTS desired D9/D10 coverage. | `build_chart_facts`, `build_varga_assessment`; [prediction_context.py](chat/prediction_context.py), `CATEGORY_RULES`. |

### 6.3 Vimshottari, Yogini and Chara

| ID / priority | Type / coverage | Inputs | Expected outcome | Source / existing coverage |
|---|---|---|---|---|
| **VIM-01 / P0** | C-local/C-ref / M | Moon 0 degrees and 20/3 degrees within Ashwini | Under reviewed nakshatra/7-year Ketu convention, first balance is 7 years and half-balance is 3.5 years. Confirm against REF-VIM; this does not validate birth AD scheduling. | [vimshottari.py](astrology/calculations/vimshottari.py), `moon_nakshatra_details`, `birth_mahadasha`. |
| **VIM-02 / P0** | I + C-local / M | All nine MD-lord rotations; **full** 120-day synthetic MD; no first-balance ambiguity | Nine ADs in correct rotation; durations proportional to reviewed year weights; contiguous underlying periods and final end equal supplied MD end. Full-cycle weights sum 120. | `vimshottari_sequence_from`, `generate_antardashas`, `generate_mahadasha_timeline`. |
| **VIM-03 / P0** | C-ref / M | F-NATAL-1/2/3 + REF-VIM, including birth in the middle of MD | Full starting balance, actual AD at birth, future MD/AD transition dates and all periods match reference. **Pending; do not assume restarting AD order over a remaining MD is correct.** | `generate_antardashas`, `generate_mahadasha_timeline`, `build_vimshottari_dasha`. |
| **VIM-04 / P0** | I + S / M | Adjacent periods ending/starting on 2027-01-05; lookups on Jan 4/5/6 and outside schedule | New half-open selector returns new lord on Jan 5; legacy inclusive selector currently can return old lord. Capture divergence explicitly; no claim of one shared behavior. Desired normalization needs approval. | [dasha_facts.py](astrology/calculations/dasha_facts.py), `_current_period`; [timing_windows.py](chat/timing_windows.py), `_vimshottari_at`. |
| **VIM-05 / P1** | I + S / M | Leap-year births, one/two cycles, dates beyond generated timeline | Periods remain ordered; no invented later period; precision/year-length/date truncation are documented. Reference dates require REF-VIM. | `generate_mahadasha_timeline`, `_add_years`; source default one-cycle horizon. |
| **YOG-01 / P0** | C-local/C-ref / M | Nakshatra numbers 1–27, including modulo-zero case; full/half birth arc | Reviewed modulo mapping, correct Yogini/lord and remaining balance. Independently approve REF-YOG table rather than derive expectations from constants under test. | [yogini.py](astrology/calculations/yogini.py), `_yogini_for_nakshatra`, `build_yogini_periods`. |
| **YOG-02 / P0** | I / P | Full major periods and four-cycle schedule; partial birth major | Eight subperiods, contiguous dates and correct order; full-cycle nominal duration 36 years; birth-balance treatment checked separately by YOG-03. | `_subperiods`, `build_yogini_periods`; existing `test_yogini_is_active` is mostly presence. |
| **YOG-03 / P0** | C-ref / M | F-NATAL-1/2/3 + REF-YOG at birth and transitions | Independently verified major/AD at birth, full schedule and boundary behavior. **Expected dates pending.** | `build_yogini_periods`, `build_yogini_facts`; [yogini_alignment.py](charts/yogini_alignment.py). |
| **YOG-04 / P1** | C-local + S / E/P | Existing annual case: nakshatra 13, age 26, remaining fraction 0.8, start 1994-01-26 | Existing expectations: remainder 2, Pingala, 16-day balance, annual end 1995-01-21, eight ADs, isolated/unscored status. Recheck source independently before C-ref label; do not connect to annual predictions. | Existing `test_chapter_twelve_annual_yogini_matches_pingala_example`; [annual_yogini.py](astrology/calculations/annual_yogini.py). |
| **CHA-01 / P0** | C-local + I / E/P | Seven-planet synthetic order, Aries/Taurus Lagna, two cycles | Existing seven-karaka exclusion, direct `[1,2,3]`/reverse `[2,1,12]` starts, 24 periods/two cycles, major sign last in its AD order. Extend to all twelve starts. | Existing karaka/order/cycle tests; [charts/jaimini.py](charts/jaimini.py), `build_chara_dasha`, `_subperiods`. |
| **CHA-02 / P0** | C-local/C-ref / P | Existing Scorpio/Aquarius own-sign/association cases; add equal-association unequal-degree and exact-degree ties | Existing selected lords/rule labels stay stable; added ties follow reviewed REF-CHARA convention. Do not infer doctrinal correctness from current tie-break code. | Existing dual-lord test; `_lord_for_sign_details`, `_stronger_dual_lord_details`, `_period_calculation`. |
| **CHA-03 / P0** | C-ref / M | F-NATAL-1/2/3 + REF-CHARA | Complete major/subperiod sign/date schedule matches independently approved method; exact transitions and cycle wrap. **Goldens pending.** | `build_chara_dasha`; [dasha_facts.py](astrology/calculations/dasha_facts.py), `build_jaimini_facts`. |
| **CHA-04 / P1** | I + C-local / P | Empty schedule and before/after dates; one-day adjacent periods | No arbitrary first/last period outside coverage in the normative lookup; characterize legacy fallbacks separately. Existing outside-range test covers only one selector. | Existing `test_jaimini_current_period_is_empty_outside_generated_range`; `chat.rashifal_context._current_period` differs. |

### 6.4 Transit boundaries and Ashtakavarga

| ID / priority | Type / coverage | Inputs | Expected outcome | Source / existing coverage |
|---|---|---|---|---|
| **TRN-01 / P0** | C-local + I / E | F-DASHA, range Jan 2–9 2027; mocked constant positions | Exactly Jan 2–4 Ke/Ve, Jan 5–7 Ve/Ve, Jan 8–9 Ve/Su. Same-lord interval has one movement series and both roles. | Existing `test_md_ad_boundaries_and_unique_same_lord_transit`; [timeline](astrology/calculations/dasha_transit_timeline.py), `build_dasha_transit_timeline`. |
| **TRN-02 / P0** | C-local + I / E | Mock rashi sequence 2→3→2; two active lords | Re-entry produces three segments per lord; SAV looked up only after all movement calculations. | Existing `test_transit_reentry_and_sav_attached_after_positions`. |
| **TRN-03 / P0** | C-local + I / P | One-day range; Feb 28–Mar 1 2028; end<start; MD boundary same day as ingress | Inclusive requested final day appears once; clipped rows stay in interval; invalid range raises documented `ValueError`; simultaneous boundaries neither leak old lords nor omit day. | Existing single-day/clipping test; `segments_in_range`, `build_dasha_transit_timeline`. |
| **TRN-04 / P0** | C-ref / P | REF-TRANSIT on both sides of real ingresses/retrogrades; actual Sun example plus all nine lords | Noon-UTC samples match independent positions/rashis; segment dates follow samples. Midnight/noon discrepancy is intentional and independently checked, not “fixed” by changing expected dates. **Reference expansion pending.** | Existing `test_midday_transit_sampling_handles_sun_taurus_ingress`; `charts.vedic_utils.transit_longitude`. |
| **TRN-05 / P0** | K + I / E/P | Eleven Sun and three Jupiter rows; best Sun/Jupiter window; unrelated Sun/Rahu range-start facts | All fourteen rows survive compaction/selection/prompt; window rows contain only applicable lords/dates; base snapshot cannot replace window evidence. Existing synthetic compaction and real pipeline tests cover part. | `_compact_future_window`, `_compact_transits`, `_transit_basis`; existing compaction/pipeline tests. |
| **TRN-06 / P0** | C-local + K / E/P | F-CLOCK and F-QUESTIONS; window starts after current AD | 36-month default, exact next-year/May bounds, no dates outside request. Explicit MD/AD pair at requested period wins over today's pair. Existing scope test covers three phrases, not generation/provider payload. | Existing `test_default_three_years_and_explicit_month`; `detect_question_scope`, `build_prompt_payload`. |
| **TRN-07 / P0** | I + K / E/P | Missing dasha/Lagna/SAV; 9 days score 0 + 1 day score 20 | Missing evidence stays preliminary/unavailable; weighted score exactly 2, not 10 or 20; final evidence card/confidence discloses gaps. Extend existing unit tests through service. | Existing missing-coverage/SAV/weighted-score tests; `summarize_segments`, `build_prediction_evidence`. |
| **TRN-08 / P1** | S + K / M | Same request on event, annual rashifal and monthly report branches; AD changes within range | Separate approved snapshots expose current branch differences. They must not falsely assert all three use the new timeline or silently align them in Phase 1. | `chat.rashifal_context._build_dasha_lord_transit_arc`; `charts.yearly_predictions._period_for_month`; `build_timing_windows`. |
| **AV-01 / P0** | I / M | F-NATAL-1/2/3 and synthetic F-AV | Seven BAV row totals `[48,49,39,54,56,52,39]` in Su/Mo/Ma/Me/Ju/Ve/Sa order; per-sign SAV equals BAV column sum; total 337; scores integer/in allowed contribution range. These code/table invariants do not certify the table's tradition. | [ashtakavarga.py](charts/ashtakavarga.py), `EXPECTED_TOTALS`, `build_ashtakavarga`. |
| **AV-02 / P0** | C-ref / M | Approved REF-AV for at least two charts | Exact full 7×12 BAV and 12-value SAV arrays match reviewed external tables, not just totals. **Expected arrays pending.** | `BENEFIC_HOUSES`, `build_ashtakavarga`. |
| **AV-03 / P0** | C-local + I / M | Asc sign 5; distinct SAV value per rashi; rotate all natal signs and Asc by +1 | Leo row maps to house 1, Aries to house 9; all house rows map correctly; rotation shifts rashi arrays while preserving corresponding house-relative totals. | `build_ashtakavarga`; `charts.vedic_utils.get_sarvashtakavarga_points`. |
| **AV-04 / P0** | C-local / P | Fake SAV 0/24/25/28/29 and missing entry | 0 and 24 weak; 25/28 moderate; 29 strong; missing is unavailable/None. Legacy absent→0 lookup behavior recorded separately. Existing test checks only missing attachment. | Timeline SAV pass; `charts.vedic_utils.get_sarvashtakavarga_points`, `_transit_score`. |
| **AV-05 / P0** | I + K / M | Rahu/Ketu as active MD/AD lords | Natal-house SAV support may be attached; no invented eighth/ninth classical BAV array or planet-specific node BAV. Both node positions follow true-node/opposition conventions. | `build_ashtakavarga`; timeline `ashtakavarga_model`; `charts.vedic_utils.transit_longitude`. |

### 6.5 Rules, evidence and timing ranking

| ID / priority | Type / coverage | Inputs | Expected outcome | Source / existing coverage |
|---|---|---|---|---|
| **RUL-01 / P0** | K + S / P | All seven checked-in YAML files | Current load produces 223 entries/no load errors; snapshot IDs/content hashes as inventory, not correctness. Global uniqueness/source completeness checked across all systems, extending Jaimini-only checks. | [loader.py](astrology/rules/loader.py), `load_rules`; existing load/Jaimini-metadata tests. |
| **RUL-02 / P0** | C-local / M | Handwritten tiny evidence and each DSL operator; nested `all`/`any`, missing path, list index and list member | Exact truth table for `exists`, equality/inequality, membership, contains/contains_any and numeric comparisons; missing path fails; supported numeric zero is not “missing.” | [engine.py](astrology/rules/engine.py), `_values_at_path`, `_compare`, `evaluate_condition`. |
| **RUL-03 / P0** | C-local + K / P | One career-only rule, one children-only, general rule, category list; true/false predicates | Exactly applicable IDs emitted; no raw question or LLM decision changes applicability; match reasons remain traceable. Extend selected Jaimini category tests. | `_category_matches`, `run_rule_engine`; existing children/relationship trigger tests. |
| **RUL-04 / P0** | C-local / P | Outcome contributions +`3×4`, -`2×5`, weight 0×99, negative weight, saturation cases | Shared outcome totals 2 for first two; zero/nonpositive weight ignored; separate cases clamp at 0 and 100. Not all negative-polarity rules automatically subtract. | [scoring.py](astrology/rules/scoring.py), `aggregate_scores`; existing zero-weight test. |
| **RUL-05 / P0** | S + K / M | Duplicate IDs/overlapping Python+YAML outcomes; repeated identical evidence | Capture current composition once, deterministic replay, prompt dedup distinct from score aggregation. Do not freeze double weighting as doctrinal correctness; issue-link overlaps. | `prediction_service.build_prediction_evidence`, `aggregate_scores`, `synthesis.prompt_builder._select_rules`. |
| **RUL-06 / P1** | S + K / M | Temporary fixture directory: missing/malformed YAML, invalid entry, unsupported operator/type | Current missing-file/loader-error/advisory-validation/raised-error behavior recorded exactly. Required hardening decisions remain separate from this plan; no broad catch added. | `loader._load_yaml_file`, `_validate_rule`, `run_rule_engine`, `_compare`. |
| **RUL-07 / P0** | C-local + S / P | Synthetic windows with 3/2/1-system support, tied scores; frozen start/date penalty; >8 candidates | Reviewed ranking arithmetic/intersection priority; snapshot candidate cap and tie order; compare final selector/evidence card/confidence source explicitly. Divergence is an issue, not silently normalized. | `timing_windows.build_timing_windows`, `_build_convergence_window`; `timing_window_service._ranking_score`; `confidence_scorer.build_confidence_summary`; existing intersection test. |
| **RUL-08 / P0** | K + S / P | Valid chart, then missing D10/SAV; controlled triggered rules | Required evidence fields/types present; no fabricated facts; zero-weight context remains unscored; snapshots retain rule IDs, sources, conflicts, scores and timing. | `PredictionEvidence`; `build_prediction_evidence`; existing evidence/rule/prompt tests. |
| **RUL-09 / P1** | C-local + K / P | Requested category charts with >40 candidate rules, duplicate selected IDs | Existing per-chart reservations/weight ordering and selected-ID dedup operate as specified; exact content selected is snapshot-reviewed. | `synthesis.prompt_builder._select_rules`; existing section tests do not assert prioritization. |

### 6.6 Existing question generation and presentation

All cases use fake provider responses, fixed clock/cache and an isolated test DB. They test the existing synchronous application, not an agent implementation.

| ID / priority | Type / coverage | Inputs | Expected outcome | Source / existing coverage |
|---|---|---|---|---|
| **GEN-01 / P0** | K / M | Logged-in A POST with owned chart, English, event question; mock `chat.views.generate_placeholder_answer` | One A conversation, one user and one assistant message, correct owned chart/language/FULL depth; supplied chart data reaches mock; token/model metadata saved; redirect to owned reading. | [chat/views.py](chat/views.py), `ask_question`; [models.py](chat/models.py); payload test does not exercise this path. |
| **GEN-02 / P0** | K / M | Invalid/empty question, unsupported language, absent chart ID | Visible form/message error; **zero generation calls and zero new messages/conversations**. Assert question/language/selection preservation where supported; characterize any discrepancy. | `AskQuestionForm`, `ask_question`; [ask.html](templates/chat/ask.html). |
| **GEN-03 / P0** | K / M | Valid event payload, fake Responses, passing fake validator | Configured model and vector-store ID; JSON facts and hosted `file_search` passed; token counts parsed; no LLM-computed placement step; only one generation call. | [llm_engine.py](chat/llm_engine.py), `generate_answer`, `_usage_counts`, `_system_instructions`. |
| **GEN-04 / P0** | K / M | Periodic keyword case; ambiguous intent with fake classifier; fake periodic response | Correct existing event/periodic routing; classifier receives classification task only; no hidden live call. Periodic branch uses its current payload/tool limit and does not falsely claim event validation occurred. | `intent_engine.classify_intent`, `_llm_classify`; `_generate_rashifal_answer`. |
| **GEN-05 / P0** | K + S / M | Missing API key, missing store ID, explicit provider error | Current diagnostic fallback returned without unintended provider calls; distinguish no-call cases from API-failure cases; record persisted fallback/credit behavior, not endorse it as valid prediction. | `_fallback_answer`, `generate_answer`, `accounts.credits.successful_answer_count`, `ask_question`. |
| **GEN-06 / P0** | K / M | Fail first validation, pass second; then fail both; then repair API error | At most one repair; original evidence/draft/issues passed; usage sums correctly. **Characterize current fail-open return/cache on final failure as an issue-linked S assertion, not a pass-before-publication requirement.** | `generate_answer`, `_repair_answer`; existing validator tests do not cover repair orchestration. |
| **GEN-07 / P0** | K / M | Same payload twice; different chart/language/date/model/store/version | Same payload cache hit avoids synthesis call; changed inputs separate keys. Clear test cache; assert payload construction currently precedes lookup, rather than inventing compute caching. | `_cache_key`, `generate_answer`, `_generate_rashifal_answer`. |
| **GEN-08 / P0** | C-local + K / P | Sun/Jupiter selected window versus Sun/Rahu base facts; fake draft with wrong remedies | Selected-window deterministic remedies replace draft; both lords' transit evidence is present; no range-start lord substituted. Current base-specificity mismatch is separately reported if it appears. | `_compact_live_evidence`, `_apply_deterministic_remedy`; existing remedy and transit-lord tests. |
| **GEN-09 / P1** | K + C-local / M | Fake answer containing `<script>`, HTML attributes, headings/bullets/bold; reading page GET | User/provider text escaped; approved Markdown-like formatting/collapsed sections render; stored answer read without regeneration. | [chat_formatting.py](chat/templatetags/chat_formatting.py), `_inline_format`, `astro_answer`; `conversation_detail`. |
| **GEN-10 / P0** | K / M | Enforced credits at zero; enforcement off; one successful vs one fallback assistant response | At zero/enforced, no generation/write and pricing redirect; off permits existing behavior. Snapshot current lifetime assistant-message accounting separately from desired billing semantics. | `accounts.credits.question_credit_status`; `ask_question`. |
| **GEN-11 / P1** | K + S / M | Provider/calculation exception after user message saved | Record current incomplete-conversation behavior and no assistant on uncaught exception; no transaction/refactor introduced. Treat as lifecycle debt with explicit issue ID. | `ask_question` write order; `generate_answer`. |
| **GEN-12 / P1** | K + S / M | Monthly report helper with fake provider, 13 months; resolver lookup of report route names | Report helper reuses DB rows; no event RAG/validation claimed; report URLs remain absent in current routing snapshot. Do not add routes to make a test pass. | `charts.yearly_predictions.get_or_create_yearly_predictions`; [charts/urls.py](charts/urls.py); report views. |
| **GEN-13 / P0** | K / M | Browser DOM harness/native FormData on form submission with selected chart/language | POST data still includes `chart_id` and `answer_language`; submit disables duplicate action and shows overlay; invalid chart reports an error. Django Client alone cannot catch the original disabled-dropdown bug. Harness/tool selection needs approval; no browser dependency added now. | [templates/chat/ask.html](templates/chat/ask.html), submit handler. |

### 6.7 Chart and conversation authorization

All expected rejection outcomes are **security requirements**, not snapshots of whatever the view currently does. A foreign ID must not trigger a provider call, create an empty-chart conversation or disclose another user's data. If current code fails, record an existing defect and block release/extraction of that boundary until an approved fix; do not approve the unsafe behavior via a golden file.

| ID / priority | Type / coverage | Inputs | Expected outcome | Source |
|---|---|---|---|---|
| **AUTH-01 / P0** | A / M | Anonymous GET/POST to registered chart and chat protected routes | Redirect to login as appropriate; no object changes or generation/provider calls. Use authenticated CSRF tests separately to avoid middleware-order ambiguity. | `login_required` on [charts/views.py](charts/views.py) and [chat/views.py](chat/views.py); URL modules. |
| **AUTH-02 / P0** | A / M | A GET Charts, Ask and History with A/B objects | Only A chart/conversation markers appear; B IDs/options/answers absent. Patch recalculation where needed so list GET does not introduce unrelated ephemeris work. | `chart_list`, `ask_question`, `question_history` user filters. |
| **AUTH-03 / P0** | A + K / M | A POST Ask using B's valid numeric chart ID | Reject with a form-level error or 403/404 (choose exact contract before implementation); no new conversation/message, no generation call, B unchanged. **Static code suggests current failure: owner filter yields None then generation continues with `{}`.** | `ask_question`: `charts.filter(id=chart_id).first()`; `chart.chart_data if chart else {}`. |
| **AUTH-04 / P0** | A + K / M | A POST Ask with nonexistent numeric chart ID; missing/noninteger ID | Reject; no chartless generation, provider call or ORM writes. Nonexistent and foreign numeric IDs must not reveal ownership/existence differences through content. | `AskQuestionForm.chart_id`, `ask_question`. |
| **AUTH-05 / P0** | A / M | A GET B's conversation URL and nonexistent conversation URL | 404 for both; no B question/answer leaked, no generation call. Own reading remains accessible. | `conversation_detail`, `get_object_or_404(... user=request.user)`. |
| **AUTH-06 / P0** | A / M | A POST B's chart-delete URL; A POST owned chart; A GET owned delete URL | Foreign deletion 404/no change; owned POST deletes only A chart; GET does not delete. Other user's rows unchanged. | `charts.views.chart_delete`; `SavedChart`/`Conversation` deletion relationships. |
| **AUTH-07 / P0** | A + K / M | A valid chart-create POST including forged `user` field naming B | Created chart belongs to A; posted ownership ignored; chart form field set excludes user. No query/provider to B. | `SavedChartForm.Meta.fields`, `chart_create` assigns `request.user`. |
| **AUTH-08 / P0** | A / M | Authenticated A; `Client(enforce_csrf_checks=True)`; no token on chart create/delete and Ask POST | 403 and no writes/generation; valid-token request reaches expected owner-scoped path. | `astro_site.settings.MIDDLEWARE`, templates' CSRF tokens, chart/chat views. |
| **AUTH-09 / P1** | A + K / M | Direct RequestFactory call to existing report views as A using B chart ID | Owner filter rejects before report/PDF/provider processing. Keep distinct from routed integration because report URLs are absent; no routes added in Phase 1. | `chart_report`, `chart_report_pdf` owner `get_object_or_404`; `charts.urls`. |
| **AUTH-10 / P0** | A + K / M | A/B each ask same text using different natal charts; controlled cache/provider | Each receives facts/result for the selected owned chart; no cached response crosses differing payloads. Do not require user-ID-specific keys for identical public/synthetic evidence unless policy says so. | `_cache_key`, `ask_question`, `_compact_live_evidence`. |

## 7. Implementation sequence after approval

This is a proposed **Phase 1 test-only implementation order**, not permission to perform it now.

1. **Baseline and isolation:** retain all 70 tests; add a test-local fixed clock, cache isolation and network-denial guard. Use Django's existing runner/TestCase/SimpleTestCase and unittest mocks; no new dependency needed for Python tests. Record source hashes/library versions and keep suite discovery explicit because `astrology` is not an installed Django app.
2. **Protect the public boundary first:** AUTH-01–08/10 and GEN-01–07/10/13. Mock the symbol actually looked up (`chat.views.generate_placeholder_answer` for HTTP tests; `chat.llm_engine.OpenAI`, classifier and validator for generation tests). Assert both HTTP outcome **and absence of side effects/calls** for denials. Browser-harness installation, if needed, is a separate approval choice.
3. **Protect deterministic contracts:** NAT/VAR structural and local arithmetic tests, dasha/transit synthetic boundaries, AV invariants/thresholds, rule DSL/scoring and evidence snapshots. These do not require an external book/service to run.
4. **Acquire and review independent references:** collect REF-NATAL/VARGA/VIM/YOG/CHARA/TRANSIT/AV fixtures, method assumptions and reviewer approval. Do not compute their expected values from production functions. Reference acquisition is an explicit work item, not something completed by this plan.
5. **Add C-ref goldens and cross-layer checks:** approved reference comparisons, selected-window preservation, output contracts and cache separation. Keep behavior snapshots and independently verified goldens in separate directories/manifests.
6. **Run full Phase 1 suite and triage:** retain baseline/new-test failures in separate reports. Do not alter existing expectations to accommodate a discrepancy without review. Document blocked reference tests and known defects explicitly.
7. **Present results for review:** test-only diff, baseline versus new results, fixture provenance, unresolved issues and gate decision. Stop again; do not proceed into agent-driven redesign or Phase 2 automatically.

Suggested future locations (not created by this task): `astrology/test_natal_regression.py`, `test_varga_regression.py`, `test_dasha_regression.py`, `test_ashtakavarga_regression.py`, `test_rule_contracts.py`; `chat/test_generation_contracts.py`, `chat/test_authorization.py`; `charts/test_chart_authorization.py`; separate `fixtures/behavior/` and `fixtures/reference/` under a clearly test-owned directory. Existing modules remain in place. Avoid moving `astrology/tests.py` into a same-name package during protection work.

## 8. Harness requirements and release gates

### 8.1 Deterministic, isolated execution

- Use the isolated Django test DB only; no real user records, chart regeneration against the application database, or live OAuth/provider calls.
- Block outbound network by default in the new test harness; explicitly mock OpenAI constructors, GeoNames and provider errors. Existing engine computation may use installed ephemeris data but must not fetch a corpus or call a model.
- Freeze every relevant clock lookup: `date.today` references in each importing module, `timezone.localdate`, and generation date-dependent cache inputs. Patch locally with test helpers; do not introduce a production clock abstraction in Phase 1.
- Clear/override test cache per case. Separate identical-payload hits from changed-chart/date/language misses. Do not patch a production function so broadly that the unit under test no longer runs.
- Replay under UTC and a non-UTC test timezone where behavior depends on localdate. Record ephemeris flags/data availability and timezone database version; do not promise arbitrary-platform bit equality without matching them.
- Treat rule-file counts and full evidence snapshots as versioned compatibility artifacts. Numeric correctness must use an independent arithmetic/ref oracle. Use mutation sanity checks in tests (change one mocked position, period boundary, SAV value, rule weight or chart owner) to show the assertion detects the intended change; no mutation-testing dependency is required.
- No live LLM prose snapshots or live-book assertions are required for this gate. Hosted retrieval quality/model evaluation needs a separately approved scope; this phase protects request/evidence boundaries.

### 8.2 Approval gates

| Gate | Pass condition | Blocking rule |
|---|---|---|
| **G0 — baseline** | Existing 70 tests stay green with documented runtime and no application-data changes. | Any existing-test failure is reported before attributing it to new work. Current G0 baseline is green. |
| **G1 — owner boundaries** | Every P0 authorization rejection has no generation/cross-user disclosure/writes; own-chart happy path passes. | Known authorization failure is a blocker, not an accepted snapshot or broad xfail. Corrective production scope requires explicit approval. |
| **G2 — deterministic integrity** | P0 local math/invariants pass; every requested date/lord/segment retained; rule engine/caches/contracts protected. | A mismatch is triaged as a new test exposing existing behavior versus a regression introduced by later work. |
| **G3 — numerical reference status** | Available approved references pass; every unavailable/disputed reference is explicitly reported. Full numerical certification additionally requires approved source settings and passing comparisons for every P0 C-ref family. | Pending C-ref cases remain **blocked for correctness certification**, not silently passed. A behavior-protection phase can be accepted only with explicit acknowledgment of these limitations; do not require speculative goldens or silently turn reference acquisition into algorithm changes. |
| **G4 — generation contracts** | Event/periodic routing, provider mocks, repair cap, form submission, persistence and failure paths are covered without network. | Fail-open validation is explicitly recorded; do not claim a hard quality gate exists unless separately authorized and implemented. |
| **G5 — handoff** | Test/fixture/report-only diff, all outcomes explained, remaining risks approved in writing. | No Phase 2 or production redesign is authorized merely because Phase 1 tests pass. |

Completion is measured by the named cases and reviewed reference data, not an invented coverage percentage or a larger number of tests. Do not use blanket expected-failure markers to advertise a green regression gate.

## 9. Findings separated from test results

### 9.1 Newly introduced issues in this task

**None identified:** this task adds only the plan; no production logic, tests or dependencies are changed. New test-case proposals are not executed tests and are not counted as passes/failures. The current baseline remains the 70-test result in section 2.

### 9.2 Pre-existing source findings / gaps to expose after approval

These are not baseline test failures. “Static” means the relevant branch is visible in source; “needs reference” means correctness is not adjudicated here.

| Issue ID | Evidence / classification | Planned exposure | Phase 1 handling |
|---|---|---|---|
| **ISS-01** | **Static:** non-owned/nonexistent numeric `chart_id` resolves to None; Ask can create a chartless conversation and invoke generation with `{}`. No evidence of returning B's natal data through this particular branch. | AUTH-03/04 | Security requirement remains rejection/no calls/no writes. Record likely red test; request a scoped fix rather than approve unsafe behavior. |
| **ISS-02** | **Static:** exclusive new dasha endpoints versus inclusive legacy selectors; rashifal can fall back to the first period outside coverage. | VIM-04, CHA-04, TRN-08 | Characterize discrepancy; choose a uniform policy only through an approved correction. |
| **ISS-03** | **Needs reference:** first partial Vimshottari MD is passed to the same proportional AD generator; initial Yogini balance likewise needs AD-schedule scrutiny. Existing tests do not certify correct birth-current AD. | VIM-03, YOG-03 | Independent reference required; do not assert a traditional method is wrong merely from a differing implementation. |
| **ISS-04** | **Static:** a failed second validation/repair error still returns/caches an answer; periodic/report paths do not share event validation. | GEN-04/06/12 | Behavior-only diagnostic protection; no hard-gate claim and no production repair in this planning task. |
| **ISS-05** | **Static:** chart refresh expects template v9 while chart engine emits v10, enabling repeated recalculation/writes on chart list GET. | NAT-01, AUTH-02; add refresh idempotence characterization alongside existing dry-run test | Patch calculator in unrelated route tests, separately expose refresh behavior; do not change version strings now. |
| **ISS-06** | **Static:** raw range-start facts, selected windows, two ranking stages and confidence sources coexist. Full window narrative can inherit representative micro-period metadata. | TRN-05/06, RUL-07, GEN-08 | Compare sources explicitly and retain discrepancies in issue report, rather than adjusting expected lords opportunistically. |
| **ISS-07** | **Static:** overlapping YAML/Python rules aggregate without global dedup; invalid rules may still be evaluated. | RUL-05/06 | Snapshot composition/error behavior; independent scoring/loader policy decision before correction. |
| **ISS-08** | **Static:** fallback expects a nested evidence shape absent from the live compact payload; summarized transit checks omit fields the RAG term extractor still reads. | GEN-05, RUL-08; add payload-shape assertions | Report empty/malformed fallback/query terms as uncovered existing behavior, not an astronomy-oracle failure. |
| **ISS-09** | **Static:** report functions exist without report URL routes; default chat is one exchange, not conversational memory. | GEN-09/12, AUTH-09 | Test existing entry points appropriately. Do not add routes or conversation-memory behavior under regression protection. |
| **ISS-10** | **Coverage gap:** BAV/SAV complete arrays and numerical natal/varga/dasha goldens are absent; existing generated fixtures can share production bugs. | NAT-02, VAR-02–05, VIM-03, YOG-03, CHA-03, AV-02 | Block C-ref certification until references are reviewed; green internal tests alone are insufficient. |
| **ISS-11** | **Static:** credits count all assistant messages, including fallbacks; check/write lifecycle is non-atomic and can leave user-only conversations. | GEN-05/10/11 | Record observed accounting/lifecycle separately; no billing/schema/transaction redesign now. |

Sources: [AS-IS risk register](ASTROGPT_ARCHITECTURE.md); [chat/views.py](chat/views.py), `ask_question`; [charts/views.py](charts/views.py), `_refresh_chart_calculation`; [chat/llm_engine.py](chat/llm_engine.py), `_fallback_answer`, `generate_answer`; [dasha selectors](astrology/calculations/dasha_facts.py); [rashifal selector](chat/rashifal_context.py); [rule loader](astrology/rules/loader.py); [RAG query builder](astrology/rag/query_builder.py); [dasha generation](astrology/calculations/vimshottari.py), `generate_antardashas`.

### 9.3 Failure-report format for the later test implementation

Record each failure with: case ID; command/environment; actual versus expected; source/fixture versions; test type; reproducibility; whether the test existed at baseline; whether production changed; classification (`existing-test failure`, `new test exposing pre-existing defect`, `new regression`, `reference disagreement`, `environment issue`); and next decision. A source suspicion is not “reproduced” until its test/probe has actually run. Never combine independent-reference disagreements with application compatibility diffs in one unexplained failure total.

## 10. Approval requested

Approve this **Phase 1 regression-protection plan** before test/fixture implementation. Approval would authorize test-only protection and reference collection described here, not automatic production fixes or Phase 2. The anticipated chart-ID rejection defect and any independently verified numerical discrepancy require a separate, concrete corrective proposal if exposed.

**Stopping point:** plan delivered; no agents, conversational redesign, production edits or Phase 2 work started.

### Crosswalk to the master plan's P1 scenarios

| Master P1 ID | Detailed cases in this plan |
|---|---|
| P1-01 — D1 | NAT-01–07 |
| P1-02 — D9/D10/vargas | VAR-01–06 |
| P1-03 — Vimshottari MD/AD | VIM-01–03, VIM-05 |
| P1-04 — dasha boundary | VIM-04, CHA-04, TRN-01/03/08 |
| P1-05 — Yogini/Chara | YOG-01–04, CHA-01–04 |
| P1-06 — transit/retrograde | TRN-01–08 |
| P1-07 — BAV/SAV | AV-01–05, TRN-07 |
| P1-08 — YAML/Python rules | RUL-01–09 |
| P1-09 — existing career answer | GEN-01–03, GEN-05–11, GEN-13 |
| P1-10 — periodic answer | GEN-04/07/09, TRN-08 |
| P1-11 — invalid birth inputs | NAT-04/06, VAR-06, TRN-07 |
| P1-12 — cross-user chart access | AUTH-01–10 |

Unresolved authorization defects must be flagged before exposing agent tools, as the roadmap requires. Completing this planning artifact or accepting documented reference gaps does not authorize tool exposure or Phase 2.

## Appendix A — Complete existing test inventory

The inventory below lists all 70 currently discovered test methods. It is a coverage index, not an assertion that each method independently verifies astrology correctness. `AstrologyEngineTests` and `RefreshChartDataCommandTests` live in [astrology/tests.py](astrology/tests.py); the two transit classes live in [astrology/test_transit_timeline.py](astrology/test_transit_timeline.py).

### astrology/tests.py ? AstrologyEngineTests (59 tests)

| Existing method | Source line |
|---|---|
| `test_chart_engine_calculates_supported_vargas` | [astrology/tests.py:64](astrology/tests.py#L64) |
| `test_jaimini_seven_karakas_exclude_nodes_and_follow_degree_order` | [astrology/tests.py:71](astrology/tests.py#L71) |
| `test_jaimini_chara_dasha_repeats_second_cycle_and_exposes_math` | [astrology/tests.py:96](astrology/tests.py#L96) |
| `test_jaimini_chara_dasha_major_and_subperiod_orders` | [astrology/tests.py:107](astrology/tests.py#L107) |
| `test_jaimini_dual_lord_edge_cases_follow_chapter_six` | [astrology/tests.py:118](astrology/tests.py#L118) |
| `test_jaimini_current_period_is_empty_outside_generated_range` | [astrology/tests.py:149](astrology/tests.py#L149) |
| `test_jaimini_rashi_aspects_follow_sign_modalities` | [astrology/tests.py:154](astrology/tests.py#L154) |
| `test_jaimini_sthira_karakas_are_exposed_as_unscored_reference` | [astrology/tests.py:159](astrology/tests.py#L159) |
| `test_chart_facts_expose_varga_lookup` | [astrology/tests.py:166](astrology/tests.py#L166) |
| `test_yogini_is_active` | [astrology/tests.py:173](astrology/tests.py#L173) |
| `test_yogini_lord_quality_is_contextual_not_fixed_by_yogini_name` | [astrology/tests.py:185](astrology/tests.py#L185) |
| `test_yogini_alignment_exposes_chapter_three_lord_assessments` | [astrology/tests.py:204](astrology/tests.py#L204) |
| `test_yogini_lord_assessment_uses_dispositor_for_rahu` | [astrology/tests.py:213](astrology/tests.py#L213) |
| `test_yogini_lord_assessment_surfaces_raja_yoga_activation` | [astrology/tests.py:233](astrology/tests.py#L233) |
| `test_chapter_five_divisional_confirmation_checks_active_lord_in_d10` | [astrology/tests.py:247](astrology/tests.py#L247) |
| `test_chapter_six_dasha_pair_support_and_pressure` | [astrology/tests.py:269](astrology/tests.py#L269) |
| `test_vimshottari_facts_expose_pair_and_divisional_confirmation` | [astrology/tests.py:297](astrology/tests.py#L297) |
| `test_chapter_seven_yogini_pair_matrix_is_complete_and_low_weight` | [astrology/tests.py:305](astrology/tests.py#L305) |
| `test_chapter_eight_snapshot_checklist_is_explanatory_only` | [astrology/tests.py:313](astrology/tests.py#L313) |
| `test_chapter_nine_event_confirmation_ranks_three_system_intersection_first` | [astrology/tests.py:323](astrology/tests.py#L323) |
| `test_chapter_ten_reference_frames_include_moon_karaka_and_d10_lagna` | [astrology/tests.py:335](astrology/tests.py#L335) |
| `test_chapter_eleven_transit_convergence_is_confirmation_only` | [astrology/tests.py:345](astrology/tests.py#L345) |
| `test_dasha_facts_expose_chapter_nine_and_ten_evidence` | [astrology/tests.py:353](astrology/tests.py#L353) |
| `test_chapter_twelve_annual_yogini_matches_pingala_example` | [astrology/tests.py:360](astrology/tests.py#L360) |
| `test_chapter_thirteen_themes_are_experimental_and_unscored` | [astrology/tests.py:380](astrology/tests.py#L380) |
| `test_vimshottari_dasha_lord_facts_include_dignity` | [astrology/tests.py:388](astrology/tests.py#L388) |
| `test_prediction_evidence_includes_parashari_ledger_and_contradictions` | [astrology/tests.py:393](astrology/tests.py#L393) |
| `test_enhanced_jaimini_fields_exist` | [astrology/tests.py:402](astrology/tests.py#L402) |
| `test_chapter_eight_navamsha_confirmation_includes_full_pair_list` | [astrology/tests.py:435](astrology/tests.py#L435) |
| `test_upapada_availability_rules_are_unscored` | [astrology/tests.py:464](astrology/tests.py#L464) |
| `test_chapters_eleven_twelve_relationship_factors_use_reference_axes` | [astrology/tests.py:472](astrology/tests.py#L472) |
| `test_chapters_eleven_twelve_rules_use_precise_timing_and_caution` | [astrology/tests.py:512](astrology/tests.py#L512) |
| `test_chapters_eleven_twelve_relationship_rules_trigger_from_normalized_facts` | [astrology/tests.py:523](astrology/tests.py#L523) |
| `test_chapter_thirteen_amatyakaraka_facts_expose_placement_influences_and_timing` | [astrology/tests.py:541](astrology/tests.py#L541) |
| `test_chapter_thirteen_rules_use_normalized_amatyakaraka_facts` | [astrology/tests.py:571](astrology/tests.py#L571) |
| `test_chapter_fourteen_rajayoga_factors_filter_through_navamsha_and_time_tenth_focus` | [astrology/tests.py:600](astrology/tests.py#L600) |
| `test_chapter_fourteen_rules_score_filtered_survival_and_timing_once` | [astrology/tests.py:648](astrology/tests.py#L648) |
| `test_chapters_fifteen_sixteen_expose_guarded_atmakaraka_and_period_cautions` | [astrology/tests.py:670](astrology/tests.py#L670) |
| `test_chapters_fifteen_sixteen_rules_keep_context_unscored_and_cautions_scoped` | [astrology/tests.py:715](astrology/tests.py#L715) |
| `test_chapter_ten_childhood_factors_use_gnatikaraka_only_as_child_caution` | [astrology/tests.py:747](astrology/tests.py#L747) |
| `test_chapter_ten_rules_trigger_only_for_children_and_score_pressure_once` | [astrology/tests.py:774](astrology/tests.py#L774) |
| `test_rules_load_without_errors` | [astrology/tests.py:802](astrology/tests.py#L802) |
| `test_jaimini_rules_have_sources_and_consistent_scoring_metadata` | [astrology/tests.py:807](astrology/tests.py#L807) |
| `test_zero_weight_rules_never_change_summary_scores` | [astrology/tests.py:824](astrology/tests.py#L824) |
| `test_broad_jaimini_reference_rules_remain_unscored` | [astrology/tests.py:839](astrology/tests.py#L839) |
| `test_prediction_evidence_triggers_rules_scores_and_rag_query` | [astrology/tests.py:857](astrology/tests.py#L857) |
| `test_rag_query_uses_triggered_rules_not_raw_question_only` | [astrology/tests.py:869](astrology/tests.py#L869) |
| `test_prompt_builder_requires_strict_sections` | [astrology/tests.py:875](astrology/tests.py#L875) |
| `test_live_chat_payload_uses_hybrid_evidence_systems` | [astrology/tests.py:887](astrology/tests.py#L887) |
| `test_validator_rejects_generic_answer` | [astrology/tests.py:907](astrology/tests.py#L907) |
| `test_validator_accepts_evidence_based_answer` | [astrology/tests.py:915](astrology/tests.py#L915) |
| `test_deterministic_remedy_replaces_missing_mantra_text` | [astrology/tests.py:962](astrology/tests.py#L962) |
| `test_deterministic_remedy_replaces_llm_remedy_with_actual_beej_mantra` | [astrology/tests.py:982](astrology/tests.py#L982) |
| `test_midday_transit_sampling_handles_sun_taurus_ingress` | [astrology/tests.py:1003](astrology/tests.py#L1003) |
| `test_weak_business_timing_answer_fails_quality_validator` | [astrology/tests.py:1024](astrology/tests.py#L1024) |
| `test_stronger_business_timing_answer_passes_quality_validator` | [astrology/tests.py:1053](astrology/tests.py#L1053) |
| `test_validator_rejects_contradictory_timing_without_clarification` | [astrology/tests.py:1072](astrology/tests.py#L1072) |
| `test_validator_rejects_vimshottari_as_system_language` | [astrology/tests.py:1092](astrology/tests.py#L1092) |
| `test_validator_allows_contradictory_timing_with_soft_launch_clarification` | [astrology/tests.py:1108](astrology/tests.py#L1108) |

### astrology/tests.py ? RefreshChartDataCommandTests (1 tests)

| Existing method | Source line |
|---|---|
| `test_refresh_chart_data_dry_run` | [astrology/tests.py:1132](astrology/tests.py#L1132) |

### astrology/test_transit_timeline.py ? DashaTransitTimelineTests (9 tests)

| Existing method | Source line |
|---|---|
| `test_md_ad_boundaries_and_unique_same_lord_transit` | [astrology/test_transit_timeline.py:29](astrology/test_transit_timeline.py#L29) |
| `test_transit_reentry_and_sav_attached_after_positions` | [astrology/test_transit_timeline.py:43](astrology/test_transit_timeline.py#L43) |
| `test_single_day_inclusive_end_and_clipping` | [astrology/test_transit_timeline.py:70](astrology/test_transit_timeline.py#L70) |
| `test_missing_sav_is_preliminary_not_zero` | [astrology/test_transit_timeline.py:77](astrology/test_transit_timeline.py#L77) |
| `test_missing_dasha_coverage_is_explicit` | [astrology/test_transit_timeline.py:87](astrology/test_transit_timeline.py#L87) |
| `test_duration_weighted_scores_use_full_period` | [astrology/test_transit_timeline.py:96](astrology/test_transit_timeline.py#L96) |
| `test_default_three_years_and_explicit_month` | [astrology/test_transit_timeline.py:105](astrology/test_transit_timeline.py#L105) |
| `test_compaction_keeps_both_lords_and_every_segment` | [astrology/test_transit_timeline.py:116](astrology/test_transit_timeline.py#L116) |
| `test_validator_rejects_wrong_window_lords` | [astrology/test_transit_timeline.py:122](astrology/test_transit_timeline.py#L122) |

### astrology/test_transit_timeline.py ? RealChartTransitPipelineTests (1 tests)

| Existing method | Source line |
|---|---|
| `test_real_chart_timeline_reaches_prompt_and_evidence_card` | [astrology/test_transit_timeline.py:132](astrology/test_transit_timeline.py#L132) |

