# M1b report: calculation settings matching the owner's Jagannatha Hora

- Branch: `claude/m1b-calculation-settings`, created from `claude/m1-calculation-integrity` at `437e8f2`.
- Scope record: [M1B_SCOPE.md](M1B_SCOPE.md), committed before any code change.
- Nothing was pushed or merged.
- No paid OpenAI calls were made.
- No new dependency was added.
- The application database was not touched.

## 1. What changed

| # | Owner decision | Implementation |
|---|---|---|
| 1 | **M1-F1 fixed: full-period birth Mahadasha** | The Mahadasha running at birth starts before birth. The elapsed part comes from the Moon's position in its nakshatra. Its antardashas divide the full period, so the antardasha at birth comes from that full division. |
| 2 | **Vimshottari uses true sidereal solar years** | New module `astrology/calculations/solar_years.py`. Dasha year *Y* is the instant when the sidereal Sun has advanced 360·*Y* degrees from its birth position, solved by Newton iteration to about 0.01 s. Mahadasha and antardasha boundaries are both computed in these years. |
| 3 | **Geometric planet positions** (Lahiri unchanged) | One shared setting, `POSITION_FLAGS`, adds `FLG_TRUEPOS`. It is used for natal positions (`charts/astro_engine.py`) and for transits (`charts/vedic_utils.py::transit_longitude`), so natal and transit positions follow the same convention. |

Unchanged by owner decision:

- True node.
- 7 Jaimini karakas.
- Whole-sign houses.
- Yogini and Chara dasha arithmetic, which keep their 365.2425-day year. They only pick up the slightly different geometric Moon and planet longitudes.

Supporting changes:

- **Method profile:**
  - `lahiri.geometric.truenode.wholesign.v2` now records the planet-position convention, the Vimshottari year, the birth-Mahadasha rule and the Yogini/Chara year.
  - The Vimshottari `method` block now describes the full-period rule and the solar year.
- **Chart template:** `CHART_TEMPLATE` is now `..._v12_jh_settings`, so each saved chart is recalculated once.
- **Chart list and PDF report:** the birth Mahadasha row reads "(running at birth)" instead of "balance", because it now starts before birth.

## 2. Changed files

| File | Change |
|---|---|
| `astrology/calculations/method_profile.py` | `SIDEREAL_MODE`, `POSITION_FLAGS` (geometric), `FIXED_DASHA_YEAR_DAYS`, profile v2 fields |
| `astrology/calculations/solar_years.py` (new) | `SiderealSolarYearClock` |
| `astrology/calculations/vimshottari.py` | Full-period birth Mahadasha; antardashas and Mahadashas in solar years; new period fields `starts_before_birth` and `balance_years_at_birth`; `years` is now the period's nominal length |
| `charts/astro_engine.py` | Uses the shared flags and sidereal mode; template bumped |
| `charts/vedic_utils.py` | Transits use the shared flags |
| `templates/charts/chart_list.html`, `templates/charts/chart_report.html` | Birth Mahadasha label |
| `astrology/test_m1.py` | Vimshottari and antardasha first-principles tests rewritten for the new conventions; new M1-F1 test; birth-instant test split (Yogini and Chara still start at birth, Vimshottari contains birth) |
| `astrology/test_m1b.py` (new) | 10 tests: geometric positions, transit/natal consistency, method profile, solar-year clock, full-period birth Mahadasha, private owner JH comparison |
| `docs/claude_migration/M1_SCOPE.md` | JH reference settings updated: Traditional Lahiri, geometric positions, 7 karakas, true sidereal solar years |
| `.gitignore` | `astrology/evaluation/private/` |

## 3. Tests

**Full suite: 353 tests, 352 passed, 1 skipped.** That is M1's 342 tests, plus 1 new M1-F1 test in `test_m1.py`, plus 10 in `test_m1b.py`.

- **The skip:** the JH comparison for R1–R5 is PENDING owner values. A skip is not a pass.
- **The private owner JH test ran and passed** on this machine. On any machine without the private file it is skipped.
- **The suite was run 5 times; one run had 1 failure.** That run's output wasn't kept, so the failing test is not identified. The following 4 runs all passed.
  - Likely cause (INFERRED, not reproduced): the existing pilot test `accounts/test_pilot.py::test_p8_07_bounded_offline_burst_limits_and_records_latency`.
  - That test sends 12 requests against a rate limiter that counts in fixed one-minute windows (`accounts/pilot_ops.py::allow_rate`). If the burst crosses a minute boundary, the expected 10 accepted and 2 rejected counts no longer hold.
  - M1b does not touch that code. Fixing the test, for example by pinning `now`, is outside this scope and is listed for owner decision.
- Synthetic and snapshot tests remain regression checks, not independent proof of astrological correctness.

Changed assertions in existing tests:

- Only in `astrology/test_m1.py`, which is M1's own file.
- The Vimshottari first-principles test, the antardasha test and the R2 birth-instant test encoded the pre-M1b conventions that the owner has now changed.
- No test outside M1's own files was changed.

## 4. Reference comparisons

### 4.1 Owner's Jagannatha Hora (owner's real chart; data git-ignored, not committed)

JH settings: Traditional Lahiri, true sidereal solar years.

| Check | Result |
|---|---|
| 7 planets (Sun–Saturn) | Largest difference **0.44″** (tolerance 2″) |
| 9 Mahadasha starts + 9 birth-MD antardasha starts | App is **1.28–1.39 h earlier** than JH on all 18 (tolerance 3 h) |
| Antardasha at birth | **Mercury–Ketu**, matching JH. Before M1b the app said Mercury–Mercury. |
| Lagna | **Not compared.** JH showed 20 Le 22′ 30″ in one screenshot and 20 Le 39′ 15″ in another; the app gives 20 Le 38′ 37″. A JH birth-data entry change is suspected. |
| Rahu | **Not compared.** The JH screenshot used the mean node; the owner's convention is the true node. |

**The constant 1.3 h offset is INFERRED, not proven.** The Moon differs from JH by about 0.4″, and with this chart's Moon 0.4″ is roughly 1.3 h of dasha time. The likely cause is that the app runs on the Moshier ephemeris, because no Swiss data files are installed (M1-F2). JH likely uses the Swiss data files.

The test `OwnerPrivateJagannathaHoraTests` repeats these checks. It reads `astrology/evaluation/private/owner_jh_reference.json`, which exists only on this machine, and is skipped elsewhere.

### 4.2 Independent formula check (synthetic charts R1–R5)

The test recomputes the solar-year clock from the Meeus low-precision Sun and compares it with the app:

- Largest difference: **744 s** on Mahadasha starts and **1,139 s** on antardasha starts.
- Tolerance: 3,600 s.
- The Meeus formula's own accuracy is about 0.01°, which is about 15 minutes of solar motion.

Birth Mahadasha and antardasha at birth for the synthetic charts:

| Chart | Birth MD (start) | Antardasha at birth |
|---|---|---|
| R1 | Moon (1984-04-06) | Moon–Mars |
| R2 | Rahu (1991-01-19) | Rahu–Rahu |
| R3 | Mars (1976-01-18) | Mars–Jupiter |
| R4 | Mercury (1999-02-14) | Mercury–Mercury |
| R5 | Sun (1968-03-17) | Sun–Rahu |

The JH values for R1–R5 are still **PENDING**. Until the owner supplies them, the synthetic charts are checked only against independent formulas.

## 5. Behaviour changes users will see

- **Every chart's Vimshottari dates move.**
  - Typically by a few days, from the solar-year change.
  - For anyone still in their birth Mahadasha, antardasha dates move by up to about two years, from the M1-F1 fix.
- **Planet longitudes change by up to 42″ on R1–R5** (aberration and light-time are no longer applied).
  - A sign, nakshatra or varga can change only for a planet within that distance of a boundary.
  - On R1–R5, no D1 sign, nakshatra, pada, D9 or D10 sign changed (checked by script against the apparent positions).
- **Yogini and Chara periods** keep their method. They may shift by seconds to minutes because the Moon and other planets moved slightly.
- **Dates before birth now fall inside the birth Mahadasha.** A query for a date between that Mahadasha's start and birth returns it. Previously such a query returned nothing.

## 6. Known limitations

1. **Ephemeris:** the app still runs on Moshier (M1-F2, AGPL and data-file decision still open). This is the likely cause of the 1.3 h offset.
2. **One reference chart:** the owner's JH comparison rests on one real chart. JH values for R1–R5 would broaden it.
3. **Lagna discrepancy:** the 16′ difference between the two JH screenshots is unresolved. The owner should re-check JH's birth data.
4. **Pratyantardashas** are still not generated.
5. **Leftover field name:** the internal field `balance_lord` keeps its old name. Its meaning, the Mahadasha lord at birth, is unchanged.
6. **Intermittent pilot test:** `test_p8_07` probably fails when its burst crosses a minute boundary (INFERRED, §3). It predates M1b.

## 7. Rollback

- **Before merge:** discard the branch with `git checkout claude/m1-calculation-integrity && git branch -D claude/m1b-calculation-settings`.
- **After merge:** `git revert` the M1b commits. Reverting also restores `CHART_TEMPLATE` v11, so saved charts recalculate back to the M1 conventions on their next chart-list visit.
- The private reference file is git-ignored and unaffected by either step.

## 8. Owner actions

1. Review this report, then approve M1b or ask for changes.
2. Decide when saved charts are recalculated.
   - Default: once, on their owner's next chart-list visit.
   - Or run `manage.py refresh_chart_data`, which writes to the database.
3. Check JH's birth data for the Lagna discrepancy (optional).
4. Still open from M1:
   - M1-F2: licence and ephemeris files.
   - JH values for R1–R5.
   - Whether to install skyfield as a test-only dependency.
   - Before M2: OD-5a and OD-11.
