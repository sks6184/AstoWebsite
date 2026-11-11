# M1 Scope and Reference-Fixture Settings (agreed)

Recorded: 2026-11-10, before any M1 code change. Branch: `claude/m1-calculation-integrity` (from `preserve/p1-p8-snapshot-2026-11-10`, commit `c9127ec`).
Authority: owner approval of OD-8, OD-10 (in principle), OD-15 (with changes), OD-20 and OD-21. The acceptance criteria are those in `CLAUDE_M1_M4_ACCEPTANCE_CRITERIA.md` §3, as refined below.

## 1. In scope

| # | Item | Owner decision |
|---|---|---|
| 1 | **Half-open dasha intervals `[start, end)` everywhere.** Exact transition instants are kept internally (`start_utc`/`end_utc`, ISO-8601 UTC). Calendar dates are derived in the display timezone. One shared selector replaces the 7 inclusive call sites. Boundary tests cover timezone and date-change cases. | OD-8 |
| 2 | **Dasha periods begin at the birth instant**, not at local midnight of the birth date. This is required for exact transition instants. Antardasha and subperiod arithmetic uses exact durations instead of whole-day truncation. | OD-8 (boundary correction) |
| 3 | **Record the actual ephemeris method** in calculation metadata, detected from Swiss Ephemeris return flags. No silent substitution: if data files are absent, the record says "Moshier". | OD-10 |
| 4 | Method profile `lahiri.truenode.wholesign.v1` stored with each chart and exposed in tool metadata | M1-AC scope |
| 5 | Reference-fixture framework, with Jagannatha Hora settings documented (§3), plus independent formula checks that need no new dependency (§4) | OD-15 |
| 6 | Security fixes S-2, S-3, S-4, S-5, S-8, S-9, each with tests | M0 / owner |
| 7 | Stop repeated chart recalculation and database writes on page visits (P-3), with regression tests | OD-20 |

## 2. Out of scope (explicitly)

- Any change to interpretation rules, rule weights or YAML rule files.
- Rewriting calculation algorithms beyond item 2. Findings that suggest an algorithm defect are **reported, not fixed** (they go to the owner as new decisions).
- Installing a dependency. Downloading Swiss Ephemeris data files.
- Paid or provider API calls.
- Updating AGENTS.md (deferred to the milestone that implements OD-16).
- Merge or push.

## 3. Jagannatha Hora reference settings (for owner-prepared values)

Jagannatha Hora is not installed on this machine (CONFIRMED by search). The owner prepares the reference values in JH using these settings, and records any setting that differs:

| Setting | Required value | Why |
|---|---|---|
| JH version | Record the exact version | Provenance |
| Ayanamsa | **Traditional Lahiri** (updated by M1b, 2026-11-11; previously "Lahiri (Chitrapaksha)") | Matches `swe.SIDM_LAHIRI` |
| Planet positions | JH default. The app uses geometric positions (`FLG_TRUEPOS`), which match JH Traditional Lahiri to within 0.4″ (M1b) | Owner decision M1b |
| Jaimini karakas | **7 karakas** (Rahu excluded) | Owner convention |
| Rahu/Ketu | **True node** | Matches `swe.TRUE_NODE` |
| Time zone | Enter the **explicit UTC offset** of the fixture (including DST), not JH's atlas lookup | Removes atlas/DST ambiguity |
| Coordinates | Exactly as in the fixture file (decimal degrees) | |
| Rasi (D1) | Sign positions; record planet and ascendant longitudes to arc-seconds | |
| Navamsa (D9), Dasamsa (D10) | Standard Parashara D9 and D10 | Matches `charts/astro_engine.py` definitions |
| Vimshottari | Moon-based, standard 120-year scheme. **True sidereal solar years** (updated by M1b; JH "Using true sidereal solar years") | App: `astrology/calculations/solar_years.py` |
| Vimshottari values | Each MD start date/time, plus AD start dates for the MD running at birth and the next MD | Checks balance and antardasha logic |
| Yogini | Standard Yogini dasha (Moon nakshatra based, 36-year cycle); MD start dates for 2 cycles | |
| Chara dasha | **The variant following K.N. Rao, "Predicting Through Jaimini's Chara Dasha"** (the app's declared source, `charts/jaimini.py:172`). Record JH's exact menu label. If JH has no matching variant, the app's Chara dasha stays **UNVERIFIED**. | OD-15: school recorded explicitly |
| Output | Export or transcribe into `astrology/evaluation/fixtures/m1_reference_charts_v1.json` under `jagannatha_hora.expected` | |

The fixture charts are **synthetic** (invented, not real people), chosen to cover timezone and date-change cases:

| ID | Local birth | Zone | Why |
|---|---|---|---|
| R1 | 1985-07-14 06:30 | Asia/Kolkata (+05:30) | Baseline, northern India |
| R2 | 1992-11-03 23:45 | America/New_York (−05:00) | Local date ≠ UTC date (next day in UTC) |
| R3 | 1978-03-26 00:20 | Europe/London (BST +01:00) | DST in effect; UTC date is the previous day |
| R4 | 2001-01-20 14:10 | Australia/Sydney (AEDT +11:00) | Southern hemisphere, east of UTC with DST |
| R5 | 1969-09-02 12:00 | Asia/Kolkata (+05:30) | Southern India; older epoch |

## 4. Independent references usable without a new dependency

These are **formula-level** checks written independently in test code. They are lower precision than JH and are labelled as such:

1. **Lahiri definition:** true ayanamsa = 23°15′00.658″ at 1956-03-21 0h, from the Indian Astronomical Ephemeris definition (value recalled; owner to confirm against a printed source). Tolerance 1″.
2. **Sun:** Meeus *Astronomical Algorithms* ch. 25 low-precision apparent longitude (±0.01°).
3. **Moon:** Astronomical Almanac low-precision lunar longitude (±0.3°). Tolerance 0.5°, which is about 1 hour of motion and detects timezone/DST errors.
4. **Ascendant:** Meeus GMST and the ecliptic-horizon intersection (±1′).
5. **Nakshatra and Vimshottari/Yogini balance, MD sequence and start instants:** computed from first principles in the test.
6. **D9/D10 signs:** computed from the classical definitions in the test.

## 5. Proposed test-only astronomy library (NOT installed; awaiting approval)

| Library | Proposed pin | Licence | Purpose |
|---|---|---|---|
| `skyfield` | 1.49 (confirm the latest stable release on PyPI before install) | MIT | Independent apparent geocentric longitudes of Sun–Saturn and the Moon from JPL ephemerides |
| `jplephem` (Skyfield dependency) | as required by Skyfield | MIT | Reads JPL kernels |
| JPL `de421.bsp` data file (≈17 MB) | DE421 | JPL ephemeris, US-government work | Ephemeris data for 1900–2050 |

The true node is not provided directly by Skyfield, so the node would still rely on JH. The library would go in a `requirements-dev.txt`, never in production `requirements.txt`.

## 6. Ephemeris facts recorded at scope time (CONFIRMED)

- `pyswisseph 2.10.3.2` (Swiss Ephemeris 2.10.03). Licence classifier: **GNU AGPL v3**. Swiss Ephemeris is distributed under AGPL or a paid professional licence. This has commercial and SaaS implications for the owner to review (not legal advice).
- No `.se1` data files exist in the project, the venv, the user profile or Program Files. `swe.calc_ut` with `FLG_SWIEPH` returns the **Moshier** flag: the engine currently falls back silently to the built-in Moshier ephemeris.
- Lahiri check: Swiss Ephemeris mean ayanamsa plus nutation at 1956-03-21 0h = 23°15′00.80″, against the definition value of 23°15′00.658″ (Δ ≈ 0.14″).
