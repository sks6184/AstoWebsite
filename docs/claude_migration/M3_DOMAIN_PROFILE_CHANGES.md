# M3 domain profile: revision 2 changes

- File: [`astrology/methodology/domains.v0.yaml`](../../astrology/methodology/domains.v0.yaml) (revision 2, 2026-11-11).
- **Status:** draft for your final astrological review. **No code loads it, no M3 code has been written and no paid calls have been made.**
- **Basis:** your corrections C1–C12. Each change below says what changed, why, and where its content came from:
  - **[owner]** your instruction;
  - **[code]** what the existing calculation code actually does, read from source;
  - **[app]** the existing `CATEGORY_RULES`;
  - **[draft]** my proposal, which you still need to judge.

## 1. Changes by correction

| # | Your correction | What changed in the profile | Origin |
|---|---|---|---|
| C1 | Career: houses 1, 5, 6, 8, 10, 11 and a conditional 12th; five event types; 8th-lord influence on the 10th as an investigation factor | Career `houses` now has the 10th as primary; the 1st, 5th, 6th, 8th and 11th as supporting, each with its role; and the 12th as **conditional** (foreign employment, expenditure or exit from a role). Five `event_guides`: promotion, voluntary employer change, lateral change, involuntary or disruptive change, and foreign relocation. A core factor reads: 8th-lord influence on the 10th or its lord is "an investigation factor only, never an automatic job-loss verdict". The involuntary-change guide requires mitigating factors to be stated. | [owner] |
| C1 (detail) | – | **The 2nd house** (income) was in the app's career houses but not in your list. It is kept under `retained_from_app` and marked for you to confirm or remove. | [app]; decision for you |
| C1 (detail) | – | **8th-lord *aspect* on the 10th** needs Parashari aspects. They are computed in `charts/vedic_utils.py` (full 7th for all planets; Mars 4/8, Jupiter 5/9, Saturn 3/10; nodes 7th only) but are **not exposed to the agent**. Until a read-only aspect wrapper is approved (**OD-32**), only placement and conjunction are available, and the aspect part is disclosed as unavailable. | [code] |
| C2 | Dashas and transits for the requested dates | A new `timing_principles` block: request dasha periods and transits for the user's window (the tools already take `start_date` and `end_date`); examine each sub-period in a window; use "current period" only for questions about now. Every domain's core factors now say "periods over the requested window". | [owner] + [code] |
| C2 (detail) | – | **Default window** when the user gives none: proposed as today to 12 months ahead, always stated to the user. | [draft] |
| C3 | Transits judged against natal SAV of the transited sign; high SAV strengthens existing significations and is not automatically favourable | A new `transit_sav_principle` block in your wording. It confirms that the transit tool already returns the natal SAV of each transited sign. I added the mirror statement for low SAV (it can weaken or strain significations; it is not automatically unfavourable), and that SAV never replaces the natal promise or the dasha. | [owner] + [code] + [draft] for low SAV |
| C4 | Question-type-aware investigation | A new `question_types` block with five types: `factual_lookup` (no checklist, rules, retrieval or timing; zero LLM rounds where the shortcut applies), `concept_explanation`, `natal_assessment`, `predictive_timing` and `comparative_decision`. The core factors apply only to assessment, predictive and comparative questions. | [owner] |
| C5 | Event-specific guides within domains | `event_guides` added to every primary domain: **47 in total**. Each is a `focus` (what evidence to collect) and an optional `note`. None states a conclusion; several notes explicitly forbid one ("no verdict of job loss", "no verdict of no marriage", "no statements of infertility"). | [owner] |
| C6 | Existing children: no detailed predictions about the child from the parent's chart | A new `scope_limit`: the parent's chart shows the parent's experience of children. The child's education, health and career need **the child's own chart**, which is two-chart analysis and therefore `calculation_unavailable`. The guide "concerns about a child" must disclose this. The same limit was added to the secondary `family` domain. | [owner] |
| C7 | Foreign: short travel, relocation, extended residence, permanent settlement | Four distinct event guides, each with what separates it. Short travel must not be read as settlement. Permanent settlement is the strongest claim and needs the most evidence: the 12th clearly dominant over the 4th, plus Rahu, Saturn, D4 and D9. The label now covers all four. | [owner] |
| C8 | Property: D4 primary; D16 only for vehicles or comforts | Property `vargas` split into `primary: [d1, d4]` and `supplementary: {d16: only when vehicles or comforts are relevant}`. D16 was removed from the property core factors. The secondary `vehicles` domain keeps D16. | [owner] |
| C9 | Marriage, education, wealth and business: keep event subtypes | **Marriage:** timing, nature of spouse, quality of married life, delay or obstacles, separation or divorce concerns, remarriage. **Education:** exam or admission result, higher education, field of study, study abroad, interruption. **Wealth:** income growth, savings, investment or speculation, debt, sudden gains, losses or inheritance. **Business:** starting, growth, partnership (not marriage), business versus employment, online/technology/foreign markets, losses or closure. Relationships, health, property and spirituality also got subtype guides for consistency. A principle requires the subtype to be identified first. | [owner]; houses inside the guides are [draft] |
| C9 (detail) | – | **Remarriage** houses (the 7th, 2nd and 9th) are a tentative draft and are flagged for you. | [draft] |
| C10 | Document the Jaimini conventions; house padas versus planetary padas | A new `jaimini_conventions` block, written from the source code. See §2. | [code] |
| C11 | Read-only wrappers reusing verified calculations, preserving chart authorization | No profile change. The wrappers remain as specified in the acceptance criteria §5.5, and every tool still goes through the registry's owner check. | – |
| C12 | Keep family, vehicles, legal/adversarial and general as secondary domains | All four are retained under `secondary_domains`. Two were renamed for clarity: `vehicle` → `vehicles`, and `legal_and_enemies` → `legal_and_adversarial` (still using the `legal_and_enemies` rule category). | [owner] |

## 2. Jaimini conventions documented (C10), all read from code

| Item | Convention in the app | Source |
|---|---|---|
| Chara karakas | **7 karakas**, Sun to Saturn, with Rahu and Ketu excluded (your M1b decision). Ranked by degrees within the sign (sidereal longitude modulo 30), highest = Atmakaraka. Exact ties are not specially resolved (**UNVERIFIED** as a source rule). | `charts/astro_engine.py::_assign_jaimini_karakas` |
| Rasi drishti | Movable signs aspect the fixed signs except the adjacent one; fixed signs aspect the movable signs except the adjacent one; dual signs aspect the other duals. A planet influences a sign by occupying it or by aspecting it from its own sign. | `astrology/calculations/jaimini.py::jaimini_aspected_signs` |
| House padas | **All 12** (A1–A12): count from the house to its lord, then the same distance from the lord. **The classical exceptions are not applied**: the source says to ignore the disputed exceptions. AL = A1, Darapada = A7, UL = A12. | `jaimini.py::build_padas` |
| **Planetary padas** | **Unavailable.** Deferred in code, because the reviewed source chapter gives no explicit formula. *Difference:* house padas are arudhas of houses (house → its lord); planetary padas would be arudhas of planets (planet → the signs it rules). Only house padas exist. | `build_padas` (`planetary_padas.calculation_status = "deferred"`) |
| Karakamsha | The D9 sign of the Atmakaraka. The 5th, 9th and 10th from it are computed, with occupants and influences read in the **D1** chart. **The 12th from Karakamsha is not computed.** | `jaimini.py::build_karakamsha` |
| Arudha-derived points | The 2nd, 10th and 11th from AL are computed. UL and Darapada are available as references. **The 2nd from UL is not computed.** | `jaimini.py::build_arudha_factors` |
| Chara Dasha | K.N. Rao school, as declared from *Predicting Through Jaimini's Chara Dasha*, **not independently verified**. Year = 365.2425 days, the convention you kept in M1b. | `charts/jaimini.py::build_chara_dasha` |

**Consequence:** my first draft listed "2nd from Upapada" (marriage) and "12th from Karakamsha" (spirituality). **Neither is computed.** They are now marked unavailable. Adding them would be a small new counting computation, which needs your approval (**OD-31**). Until then the agent must disclose them, not work them out itself.

## 3. Other corrections to my first draft

- **Children:** the 2nd house from the app's list is omitted for existing children and kept for conception (as an addition to the family). Please confirm.
- **Health:** the Moon is no longer mentioned as a draft karaka addition. The core factors still include the Sun and the Moon; please confirm.
- **Yogas:** named only where the app actually detects them. Dhana and Lakshmi (wealth) and Saraswati and Budhaditya (education) are among the app's 23 yoga types (`charts/yogas.py`).
- **Vocabulary:** unchanged apart from dropping one D16 term from property. That leaves 67 hints, at most 6 per domain, all with corpus counts.

## 4. New decisions for you

| ID | Decision | Recommendation |
|---|---|---|
| OD-31 | Add derived Jaimini counting points (the 12th from Karakamsha, the 2nd from UL, and possibly others) to the `get_jaimini_facts` wrapper. They are new computations, though trivial sign counting. | Approve only the two named points. Each needs a test against a hand-counted example on the synthetic charts. |
| OD-32 | A read-only wrapper exposing the existing Parashari natal aspects (`charts/vedic_utils.py`) | Approve. It is an existing computation, and it is needed for the 8th-lord aspect factor (C1) and other aspect-based factors. |
| – | Career: keep the 2nd house (income) from the app's list? | Your call |
| – | Default predictive window when none is given: today to 12 months ahead | Approve, or set another |
| – | Low-SAV mirror statement (§1, C3) | Approve or delete |
| – | Remarriage house draft | Review |

## 5. Budget and limits, as you set them

- **Initial live testing: at most US$0.15 in total and US$0.05 per consultation**, on synthetic charts only.
- The remaining proposed M3 budget is **not** authorized without separate approval.
- These limits are recorded in `CLAUDE_M1_M4_ACCEPTANCE_CRITERIA.md` (§5.6 and OD-27).

## 6. Revision 3: implementation changes (M3 offline build, 2026-11-11)

Revision 3's methodology content (M3-1, M3-4 to M3-8, OD-31 to OD-33) is in commit `f08563f`. The offline build then made the following **structural** changes. No house, karaka, varga, core factor or event guide was changed.

| Change | Why | Needs your review |
|---|---|---|
| `declared_unavailable` turned into a mapping with stable IDs (`muhurta`, `kundli_matching`, `shadbala`, `prashna`, `longevity`, `planetary_padas`, `kp`, `strength_conditions`). `longevity` carries `declined_by_policy: true` | The model names a missing calculation by ID, and the server publishes the fixed `calculation_unavailable` wording. The descriptions are unchanged | No |
| New question type `out_of_scope` [draft] | Lets the agent decline a non-chart question after one round, without investigating | Yes: the wording |
| New user-facing `disclosure` text [draft] for health, conception_childbirth, children, wealth and business | The server appends these notes to every answer in those domains (A8, OD-23, C6). The existing `sensitivity` notes remain instructions to the model | **Yes: the exact wording of each note** |
| Removed the stale "not yet exposed" comment on `parashari_aspect_convention` | OD-32 now exposes the aspects | No |

The loader `astrology/methodology/profile.py` validates the file on every load:
- the schema and the closed label lists;
- at most 8 vocabulary terms per domain and 100 in total (currently 67);
- rule categories, vargas, planet codes and dasha systems that the tools actually accept;
- no tool-sequence markers and no verdict markers in any guidance text.

`research_annex` is never returned to the model.
