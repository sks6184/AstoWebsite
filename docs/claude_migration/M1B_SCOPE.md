# M1b: calculation settings to match the owner's Jagannatha Hora — agreed scope

Branch: `claude/m1b-calculation-settings`, created from `claude/m1-calculation-integrity` at commit `437e8f2`.
Date: 2026-11-11.

## 1. Owner decisions

| # | Decision | Evidence |
|---|---|---|
| 1 | **M1-F1 fix: full-period birth mahadasha.** The mahadasha running at birth is treated as a full period that started before birth. The elapsed part comes from the Moon's position in its nakshatra. The antardashas divide that whole period, so they are not compressed into the remaining balance. | The owner's JH places the birth inside Mercury–Ketu. The app placed it inside Mercury–Mercury, which was more than two years wrong for that antardasha. |
| 2 | **Vimshottari uses true sidereal solar years.** Dasha year *Y* is reached when the Sun's sidereal longitude has advanced 360·*Y* degrees from its birth position. Antardasha fractions are measured in these years, not in fixed days. | JH reports "Using true sidereal solar years". The prototype matched the owner's JH dates to within about one hour. |
| 3 | **Geometric planet positions.** Planets use `FLG_TRUEPOS`, so positions are not corrected for light-time or aberration. The ayanamsa stays Lahiri (`SIDM_LAHIRI`, JH "Traditional Lahiri"). Natal and transit positions use the same flags. | With `SIDM_LAHIRI` plus `FLG_TRUEPOS`, all seven planets match the owner's JH to within 0.4″. With apparent positions the difference was up to 37″. |

Settings that stay as they are, by owner decision:

- True node.
- Seven Jaimini karakas, Rahu excluded.
- Whole-sign houses.
- **Yogini and Chara dasha calculation.** They keep their current method and their 365.2425-day year. They do pick up the slightly different Moon and planet longitudes from decision 3.

## 2. Out of scope

- Other ayanamsas.
- The mean node.
- Eight karakas.
- Any change to Yogini or Chara arithmetic.
- Interpretation rules.
- M2 work.
- Push or merge.
- Paid calls.
- New dependencies.

## 3. Reference data and privacy

- **The owner's real chart is never committed.**
  - Its JH values, together with the birth inputs needed to reproduce them, may be placed in a git-ignored local file: `astrology/evaluation/private/owner_jh_reference.json`.
  - The test reads that file when it exists and is skipped otherwise.
- Repository tests use only the synthetic charts R1–R5, plus independent formulas:
  - the solar-year mapping is checked with the Meeus solar longitude;
  - the antardasha arithmetic is checked from first principles.
- The JH reference settings in `M1_SCOPE.md` §3 are updated as follows:
  - Ayanamsa: Traditional Lahiri.
  - Positions: geometric.
  - Node: true node.
  - Karakas: 7.
  - Vimshottari year: true sidereal solar year.

## 4. Data effect

- `CHART_TEMPLATE` is bumped, so each saved chart is recalculated once, on its owner's next visit to the chart list. The owner may instead run `manage.py refresh_chart_data`.
- The method profile ID changes to `lahiri.geometric.truenode.wholesign.v2`.
