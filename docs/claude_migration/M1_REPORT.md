# M1 Report: Calculation Integrity, Dasha Boundaries, Security Fixes

Status: **complete, awaiting owner review**. M2 has not started.
Date: 2026-11-10. Labels: CONFIRMED (verified in source or by test), INFERRED, UNVERIFIED, PENDING (needs owner input).

| Item | Value |
|---|---|
| Branch | `claude/m1-calculation-integrity` (from `preserve/p1-p8-snapshot-2026-11-10` @ `c9127ec`) |
| Commits | `8531737` scope and fixture settings; `0de5b2e` implementation and tests; this report in the following commit |
| Pushed / merged | **No** (OD-21) |
| Paid provider calls | **None**. All tests block sockets or mock the OpenAI client. |
| Application database | Not touched. Tests use Django's temporary test database. |
| Dependencies | Unchanged. The proposed test-only library is not installed. |

---

## 1. Acceptance criteria status

| ID | Criterion | Result |
|---|---|---|
| M1-AC1 | Calculation algorithms unchanged except boundary corrections | **Met.** Planet, ascendant, varga, nakshatra, balance and sequence logic are unchanged. D1/D9/D10 and nakshatra outputs are **identical** before and after for all 5 fixture charts (§5). Only period timing (start instant, exact splits, UTC fields) and metadata changed. |
| M1-AC2 | ≥3 independent reference charts with provenance | **Partly met.** 5 synthetic charts with documented JH settings (`M1_SCOPE.md` §3). The independent formula references pass (§4.1). **JH values: PENDING** (owner). |
| M1-AC3 | D1 within 1′; D9/D10 exact except near boundaries | **Met against formula references; PENDING against JH.** 4 positions within 1′ of a D9/D10 boundary are flagged, not silently passed (§4.2). |
| M1-AC4 | Vimshottari MD/AD start dates within ±1 day | **Met against first-principles arithmetic** (≤18 s). **PENDING against JH.** See finding M1-F1 for the first Mahadasha's antardashas. |
| M1-AC5 | Yogini and Chara match a reference of the same school | Yogini: **met against first principles; PENDING against JH.** Chara: **UNVERIFIED** (no independent reference; school recorded as K.N. Rao). |
| M1-AC6 | Single selector; no inclusive selection remains | **Met.** `astrology/calculations/periods.py::select_period`; the grep test passes. |
| M1-AC7 | Day before / on / after a transition agree across surfaces | **Met** for Vimshottari (5 surfaces plus the timeline), Yogini (3) and Chara (3), on all 5 charts |
| M1-AC8 | Behaviour-change report | **Met** (§5) |
| M1-AC9 to AC12 | S-2, S-3, S-4, S-5, S-8, S-9 tested | **Met** (§3). Two extra spots of the S-2 class were also fixed. |
| M1-AC13 | Ownership tests still pass | **Met** (full suite) |
| M1-AC14 | Full suite green, no paid calls | **Met:** 342 run, 341 passed, 1 skipped (the PENDING JH test) |

---

## 2. Changed files

**New**

| File | Purpose |
|---|---|
| `astrology/calculations/periods.py` | `[start, end)` selector `select_period` (date queries by calendar date, aware datetimes by exact instant, legacy stored charts by date), birth-instant helpers, exact interval splitting, UTC/local timing fields |
| `astrology/calculations/method_profile.py` | Profile `lahiri.truenode.wholesign.v1`; `ephemeris_from_flags` detects the ephemeris actually used |
| `astrology/test_m1.py` | 34 M1 tests |
| `astrology/evaluation/fixtures/m1_reference_charts_v1.json` | 5 synthetic charts; JH slots PENDING |
| `docs/claude_migration/M1_SCOPE.md`, `M1_REPORT.md`; `CLAUDE_M1_M4_ACCEPTANCE_CRITERIA.md` | Scope record, this report, approved criteria |

**Modified**

| File | Change |
|---|---|
| `charts/astro_engine.py` | Dashas built from the birth instant (`utc_dt`) and chart timezone. Records `birth_instant_utc` and `calculation_method` (ephemeris from return flags). `CHART_TEMPLATE` constant bumped to `v11_exact_dasha_instants`. |
| `astrology/calculations/vimshottari.py` | Birth-instant start; exact antardasha splits; `start_utc`/`end_utc`; interval metadata. Dead helpers removed. |
| `astrology/calculations/yogini.py` | Same timing change; selector → `select_period(fallback="last")` |
| `charts/jaimini.py` | Same timing change for Chara dasha. School and `UNVERIFIED` recorded in `method`. |
| `astrology/calculations/dasha_facts.py`, `charts/jaimini_confirmation.py`, `charts/yogini_alignment.py`, `chat/prediction_context.py`, `chat/rashifal_context.py`, `chat/timing_windows.py`, `astrology/calculations/dasha_transit_timeline.py` | Local selectors replaced by `select_period`. Each keeps its previous out-of-range fallback (`{}` / first / last). |
| `astrology/tools/adapters.py`, `astrology/tools/registry.py` | Dasha tool reports exact-instant precision (or warns for pre-M1 charts). `method_profile` added to tool metadata. |
| `charts/views.py` | P-3: refresh check uses `CHART_TEMPLATE`, and reads the karaka/sign-lord fields from the first **planet** row (the Ascendant row never has a karaka, so every chart was rewritten on every visit). PDF error text hidden. |
| `chat/llm_engine.py` | S-2: `_public_provider_reason` shows only the error class; the provider message is never stored or logged |
| `chat/intent_engine.py` | S-3: no question text or exception body in logs. S-4: Responses call through `responses_create`, `timeout=10`, `max_retries=0`; skipped when no accounted request budget is active. |
| `charts/yearly_predictions.py` | S-4: metered through `responses_create`, `timeout=20`, `max_retries=0`, `max_output_tokens=1200`; no call without an accounted budget |
| `accounts/provider_meter.py` | Adds `accounted_request_active()` (read-only helper) |
| `astro_site/settings.py` | S-5: `DEBUG=False` with a missing, short or `dev-`/`django-insecure-` secret raises `ImproperlyConfigured`. Your local `.env` has `DJANGO_DEBUG=true`, so local development is unaffected. |
| `payments/views.py` | S-8: GET → 405; POST → 501; no state change |
| `chat/views.py` | S-9: a rejected first turn (403/409) deletes the just-created conversation **only** if it has no messages and no turns |
| `charts/geocoding.py` | Same class as S-2: exception detail no longer shown |
| `chat/test_runtime_failure.py` | Two P8 assertions expected the raw provider message `Request timed out` in the user's answer, which is the S-2 defect. They now require the error code and forbid the raw text. **This is the only change to a pre-existing test.** |

Commit size (`8531737..0de5b2e`): 26 files, +1,048 / −217.

---

## 3. Test results

Command: `.venv/Scripts/python.exe manage.py test --noinput` (Django test database, offline).

```
Ran 342 tests in 240.380s
OK (skipped=1)
```

- 308 pre-existing tests + 34 new. The skip is `JagannathaHoraReferenceTests.test_against_jagannatha_hora`: *"PENDING: owner has not yet supplied Jagannatha Hora values; calculations are UNVERIFIED against JH."*
- **Interpretation:** the 308 pre-existing tests are regression and contract checks against the app's own earlier behaviour, **not** independent evidence of astrological correctness. Only `IndependentFormulaReferenceTests` (and, once supplied, the JH test) are independent.

New tests by group:

| Group | Tests | What they establish |
|---|---|---|
| `IndependentFormulaReferenceTests` | 7 | §4.1 |
| `JagannathaHoraReferenceTests` | 1 (skipped) | Comparison harness, ready for owner values |
| `PeriodSelectorTests` | 6 | Half-open semantics for dates and instants; display date in the chart timezone; fallbacks; pre-M1 charts; grep for inclusive selectors |
| `ChartDashaBoundaryTests` | 4 | Shared exact boundaries; birth-instant start with a date change across UTC (R2); all surfaces agree around transitions |
| `MethodProfileTests` | 3 | Ephemeris recorded from flags (now Moshier); classification; tool metadata |
| `ChartRefreshTests` | 2 | Current chart: 0 recalculations, 0 saves over two visits. Outdated chart: exactly 1, then 0. |
| `ProviderSecurityTests` | 7 | S-2, S-3, S-4 (classifier and yearly: metered with a ledger row, no retries, no call without a budget, over-budget blocks before the network) |
| `ConfigurationAndEndpointSecurityTests` | 4 | S-5 (subprocess settings import), S-8, S-9, geocoding error text |

---

## 4. Independent-reference comparisons

### 4.1 Formula-level references (independent; lower precision than JH)

Formulas are written independently in `astrology/test_m1.py`, not taken from app code. Residual = |app − reference|:

| Chart | Sun (Meeus ch. 25, ±0.01° = 36″) | Moon (Astr. Almanac low precision, ±0.3°) | Ascendant (Meeus GMST + nutation) | Vimshottari MD starts (first principles) | Yogini MD starts |
|---|---:|---:|---:|---:|---:|
| R1 Delhi | 9.0″ | 2.4′ | 0.1″ | ≤ 7.9 s | ≤ 0.0 s |
| R2 New York | 3.2″ | 1.6′ | 0.1″ | ≤ 6.3 s | ≤ 2.4 s |
| R3 London (BST) | 25.0″ | 2.0′ | 0.1″ | ≤ 6.3 s | ≤ 0.8 s |
| R4 Sydney (AEDT) | 13.4″ | 4.2′ | 0.0″ | ≤ 18.1 s | ≤ 3.9 s |
| R5 Chennai | 13.3″ | 5.3′ | 0.1″ | ≤ 14.2 s | ≤ 4.7 s |

- **Lahiri definition:** the app's true ayanamsa at 1956-03-21 0h is 23°15′00.80″, against the definition 23°15′00.658″ (Δ 0.14″). The definition value is recalled from the Indian Astronomical Ephemeris definition; the owner should confirm it against a printed source.
- **Birth instants (DST/date change):** R2 → 1992-11-04 04:45 UTC (local 3 Nov); R3 → 1978-03-25 23:20 UTC (BST in force); R4 → 2001-01-20 03:10 UTC (AEDT). All CONFIRMED by test.
- The ascendant agreeing to 0.1″ at five latitudes, including the southern hemisphere, independently confirms the UTC conversion, sidereal time and Lahiri subtraction.
- Dasha residuals of up to 18 s come from the app rounding the balance to 1e-6 years. They don't affect any calendar date.
- **What these checks do not cover:** the other planets (Mars–Saturn), the true node, Chara dasha, or other vargas. JH (or the proposed Skyfield check, §7) is needed for those.

### 4.2 D9 / D10 against classical definitions

All non-flagged rows (50 rows across 5 charts) match the classical navamsa and dasamsa definitions. **Flagged** (within 1′ of a division boundary, so a small longitude difference between software could change the sign):

| Chart | Body | Varga |
|---|---|---|
| R1 | Jupiter | D10 |
| R3 | Venus | D9 |
| R4 | Venus | D9 |
| R5 | Jupiter | D10 |

These four are the most informative comparisons for the owner's JH values.

### 4.3 Jagannatha Hora: PENDING

Not installed here (CONFIRMED by search). Settings to use are in `M1_SCOPE.md` §3. Enter the values in `astrology/evaluation/fixtures/m1_reference_charts_v1.json` (set `status` to `"provided"`) and run:

```
.venv/Scripts/python.exe manage.py test astrology.test_m1.JagannathaHoraReferenceTests
```

Until then, D1 for Mars–Saturn and the node, Vimshottari antardashas, Yogini and Chara dasha are **UNVERIFIED against professional software**.

---

## 5. Behaviour changes (before vs after, same 5 synthetic charts)

| Output | Change |
|---|---|
| D1 longitudes, D9, D10, Moon nakshatra | **Identical** |
| Vimshottari MD dates | 0 or +1 day (later), because periods now start at the birth time instead of 00:00 |
| Vimshottari AD dates (first 2 MDs) | 0 to +2 days (R2: 23:45 birth, plus removal of whole-day truncation) |
| Yogini MD dates | 0 or +1 day |
| Chara dates | −1 to +1 day. The −1 cases (R3 London) come from DST: the date is now computed from the exact UTC instant converted to local time, instead of naive local arithmetic. |
| Transition-day lookups | On the day a new period starts, every surface now reports the **new** period (previously some reported the old one) |
| New fields | `start_utc`, `end_utc` on every period; `birth_instant_utc`, `calculation_method` on charts; `method_profile` in tool metadata |
| Stored charts | Recalculated **once** on the next chart-list visit (template v11), then never again unless the engine version changes |

---

## 6. Findings that need owner decisions (not changed in M1)

| ID | Finding | Evidence | Recommendation |
|---|---|---|---|
| **M1-F1** (High) | **Antardashas of the Mahadasha running at birth are computed on the balance only, starting from the MD lord.** The common method (believed to be used by JH and other major software; INFERRED until your JH values arrive) divides the **full** MD from its theoretical start before birth and drops the elapsed antardashas. The same applies to Yogini subperiods of the first Yogini period. | `vimshottari.py::generate_mahadasha_timeline` → `generate_antardashas(lord, start, end)` with `start` = birth. Measured AD start differences in the first MD: R1 395 d, R2 554 d, R3 525 d, R4 605 d, R5 348 d. The AD running at birth also differs for R1, R3 and R5. | Confirm with JH values (requested in `M1_SCOPE.md` §3). If confirmed, approve a correction as a scoped follow-up. It affects users still in their birth Mahadasha (young users, or long birth MDs such as Venus 20 y or Saturn 19 y). |
| **M1-F2** (High, legal/commercial) | Ephemeris: no `.se1` files exist, so Swiss Ephemeris silently used **Moshier**. This is now recorded, not hidden. `pyswisseph` is **AGPL-3.0** (package classifier CONFIRMED). Swiss Ephemeris is offered under AGPL or a paid professional licence. | `MethodProfileTests`; package metadata | Decide the licence route (AGPL source-offer obligations for a network service versus a professional licence) before commercial launch (not legal advice). Then decide whether to add `.se1` files. Moshier's documented precision is at arc-second level for modern dates (INFERRED from SE documentation), well inside the 1′ tolerance. |
| M1-F3 (Medium) | **No per-user timezone exists**, so dasha dates display in the **chart's** (birth-place) timezone | `charts/models.py:31` only | Add a user display-timezone preference in a later milestone (needs a migration). |
| M1-F4 (Medium) | Existing saved charts hold pre-M1 dasha data until recalculated. Ask-flow tools read stored data without recalculating. | `registry.py` (no regeneration by design) | After review, run `manage.py refresh_chart_data --dry-run`, then without `--dry-run`. This writes to the app DB, so it's your call. Visiting the chart list also recalculates each chart once. |
| M1-F5 (Low) | Out-of-range fallbacks still differ by caller (`{}`, first or last period), which can substitute a period for dates before birth | `select_period(fallback=...)` call sites | Standardise on "unknown" (`{}`) in M3/M4, where answers are rebuilt. Kept as-is in M1 to avoid behaviour changes beyond boundaries. |
| M1-F6 (Low) | Chara dasha second cycle repeats first-cycle durations. Some schools use 12 minus the first-cycle years. | `charts/jaimini.py` `repeat_rule` | Confirm against your K.N. Rao reference when providing JH Chara values. |
| M1-F7 (Low) | The intent classifier now uses the Responses API via the meter, which adds `max_tool_calls=1` and `store=False`. This is not verified live (no paid calls allowed). If the API rejects the shape, the classifier falls back to the rule result. | `provider_meter.responses_create` | Verify during the first approved paid call in M2/M3. |

---

## 7. Known limitations

1. JH comparison PENDING. Chara dasha UNVERIFIED (no independent reference of the declared school).
2. Formula references are low precision (Moon ±0.3°) and cover only the Sun, Moon, ascendant, ayanamsa, dasha arithmetic and D9/D10. Mars–Saturn and the true node have no independent check yet. Proposed: `skyfield` (MIT) + `jplephem` (MIT) + JPL DE421 as a **test-only** dependency (`M1_SCOPE.md` §5). Not installed; awaiting your approval.
3. Pratyantardashas are not generated (unchanged).
4. Transit sampling remains daily at 12:00 UTC (unchanged; outside M1).
5. S-6 (labelling retrieved book text as untrusted in the legacy prompt) is scheduled for M2 (M2-AC7), not M1.
6. The `"No credit was used."` text in the provider-failure message relies on the existing settlement rule (failed results are never billed). It is confirmed by the updated P8 timeout tests, but it is a user-facing statement to keep true if billing changes.

---

## 8. Rollback

M1 has **no database migrations**.

1. **Code:** `git switch preserve/p1-p8-snapshot-2026-11-10` (pre-M1 state), or on this branch `git revert 0de5b2e` (keeps the scope documents).
2. **Stored charts:** charts recalculated under M1 carry extra fields (`start_utc`, `calculation_method`). Pre-M1 code ignores the extra fields. Because pre-M1 code also has the P-3 defect, it recalculates every chart in its own format on the next chart-list visit. No manual data repair is needed.
3. **Configuration:** nothing to undo. S-5 only affects deployments that set `DJANGO_DEBUG=false`, which production already guards in `astro_site/production.py`.

---

## 9. Owner actions requested before M2

1. Review this report and branch `claude/m1-calculation-integrity` (not merged or pushed).
2. Supply the JH reference values (settings in `M1_SCOPE.md` §3), especially the AD starts of the birth Mahadasha, to settle M1-F1.
3. Decide on M1-F1 (correct the balance-period antardashas?) and M1-F2 (licence route and `.se1` files).
4. Approve or decline the test-only `skyfield` dependency.
5. Decide whether and when to run `refresh_chart_data` on the application database (M1-F4).
6. M2 prerequisites (from the accepted criteria): OD-5a (one read-only vector-store listing plus the paid evaluation cap) and OD-11 (source rights).
