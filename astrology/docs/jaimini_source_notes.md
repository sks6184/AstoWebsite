# Jaimini Source Notes

Source file:

```text
C:\Users\Vincere\Documents\Sunny\Astrology GPT\predicting-through-jaimini-chara-dasha.pdf
```

Book:

```text
Predicting through Jaimini's Chara Dasha
K.N. Rao
```

Current extraction status:

- PDF is readable with `pypdf`.
- Page count: 136.
- Text extraction works well enough for rule and calculation review.

## Confirmed Calculation / Method Topics

The book includes deterministic material for:

- Seven Jaimini karakas, excluding Rahu and Ketu.
- Rashi-based Chara Dasha.
- Direct and indirect Chara Dasha order.
- Sub-period order where the major-period sign comes last.
- Jaimini rashi aspects.
- Karakamsha from the Navamsha sign of the Atmakaraka.
- Pada / Arudha calculation.
- Upapada calculation.
- Jaimini yogas involving Atmakaraka, Amatyakaraka, Putrakaraka, Darakaraka, fifth lord, Moon, and Venus.
- Navamsha confirmation of Jaimini yogas.
- Predictive use of Amatyakaraka.
- Predictive use of Atmakaraka dasha.

## Current Code Coverage

Already started:

- `charts/astro_engine.py` assigns seven Jaimini karakas, excluding Rahu and Ketu.
- `charts/jaimini.py` calculates Chara Dasha periods and subperiods across two repeated cycles.
- `charts/jaimini_confirmation.py` gives a starter confirmation layer using Chara Dasha, karakas, and activated houses.
- `astrology/calculations/dasha_facts.py` wraps Jaimini evidence into the new four-system JSON.

## Chapters 1-6 Mathematical Core Audit

Verified against the source:

- Seven Chara Karakas are assigned by descending longitude within the sign, excluding Rahu and Ketu.
- Major-period order uses the direct/indirect ascendant groups from the book.
- Period lengths use their separate direct/indirect sign-counting groups.
- The counted duration deducts one year, while a lord in its own sign gives twelve years.
- Chara Dasha repeats the same twelve-sign sequence for a second cycle when needed.
- Dates outside the generated cycles return no active Chara Dasha instead of falling back to the birth period.
- Subperiod order follows the major-period sign group and places the major-period sign last.
- Movable, fixed, and dual-sign Jaimini aspects match the book.
- Scorpio and Aquarius dual-lord duration rules select the outside lord when the other lord is in its own sign, give twelve years when both are in the sign, and otherwise choose strength by associations then longitude within the sign.
- Chapter 2 Sthira Karakas are exposed as unscored reference facts for later rules.

No exaltation, debilitation, or fractional-degree duration modifiers are applied because the source calculation chapter does not use them.

## Implemented Enhanced Helpers

- Rashi aspects.
- Karakamsha.
- All twelve house padas, Arudha Lagna, and Upapada Lagna.
- Chapter 7 Pada exceptions are explicitly not applied, following the source.
- Planetary padas are deferred and unscored until an explicit formula is reviewed.
- 10th from Arudha Lagna.
- Planets influencing Arudha and 10th from Arudha.
- Jaimini rajayogas from the listed AK, AmK, PK, DK, fifth-lord, Moon, and Venus combinations.
- Navamsha confirmation of all listed Jaimini rajayogas, including Moon-Venus and Moon-aspected-by-many-planets checks.
- Both possible Navamsha fifth-lord reference interpretations are exposed separately and remain unscored.
- Karaka affliction and benefic-influence facts are exposed as an unscored Chapter 8 checklist.
- Moon-aspected-by-many-planets Rajayoga signal.
- AK-AmK support and struggle relationship flags in D1/D9.
- Chapter 15 Atmakaraka Chara Dasha facts: active signs containing or aspected by AK, AK in the tenth or eighth from active signs, D1/D9 dignity, and Sagittarius references.
- Chapter 15 AK-tenth and AK/Karakamsha-Sagittarius references remain context-only; they must not become automatic rise, fall, or harmful-event predictions.
- Chapter 16 Sagittarius Chara Dasha caution flag for major periods and subperiods.
- Chapter 16 sixth/eighth subperiod-from-major caution, with a separate AK-aspect escalation flag.
- Chapter 16 sixth-house rashi-period caution for children questions only.
- Chara Dasha running-sign-as-lagna evidence for major and subperiod signs.
- Twelve-house running-sign-as-lagna snapshots for the active major period and subperiod.
- Category-specific karaka activations from the active Chara Dasha signs.
- Chapter 9 predictive checklist facts, including dasha direction and active signs' houses from birth Lagna.
- Chapter 10 child-only Gnatikaraka facts: condition, malefic influences, active Chara period matches, Putrakaraka-Gnatikaraka linkage, and Sagittarius-GK subperiod context.
- Chapter 10 childhood rules remain cautious and child-category-only; they must not generate automatic illness, accident, or harmful-event claims.
- Chapters 11-12 neutral relationship reference facts: D1 and D9 axes, Darakaraka, Upapada, Darapada, Darakaraka Navamsha, Rahu-Ketu aspects, and Darakaraka aspects.
- Chapters 11-12 active Chara Dasha relationship matches and Putrakaraka-in-fifth checks.
- Chapters 11-12 relationship-pressure facts remain caution-only and must not generate automatic separation, violence, or death claims.
- Chapter 13 Amatyakaraka facts: D1 Lagna placement, Jaimini aspects, conjunctions, benefic/malefic influences, sixth/eighth-lord connections, and important-person context.
- Chapter 13 professional timing facts: active Chara Dasha contains Amatyakaraka or places it in the tenth or eleventh house from the running sign.
- Chapter 13 difficult Amatyakaraka patterns remain caution-only and must not generate automatic failure, loss-of-office, illness, or death claims.
- Chapter 14 Rajayoga filtration facts: count the ten starter D1 pairs, retain the pairs that survive in Navamsha, and list filtered-out promises separately.
- Chapter 14 AK-AmK Navamsha relation facts, including kendra/trikona, one-eleven, and AmK-tenth-from-AK checks.
- Chapter 14 Chara timing facts: surviving Navamsha Rajayoga planets influencing the tenth house from the active major period or subperiod.
- 10th from the running Chara Dasha sign.
- 5th, 9th, and 10th from Karakamsha.
- 2nd, 10th, and 11th from Arudha Lagna.

## Rule Conversion Targets

Convert rule-like statements into YAML, not prompt text.

Starter rule groups:

- `JAIMINI_ASPECT_AK_AMK_001`
- `JAIMINI_AMK_POSITION_001`
- `JAIMINI_AMK_KENDRA_TRIKONA_FROM_AK_001`
- `JAIMINI_MOON_VENUS_RAJA_YOGA_001`
- `JAIMINI_NAVAMSHA_CONFIRMATION_001`
- `JAIMINI_ARUDHA_CAREER_001`
- `JAIMINI_10TH_FROM_ARUDHA_001`
- `JAIMINI_ATMAKARAKA_DASHA_CAUTION_001`

Rules added so far include the above groups where supported by current deterministic facts, including the second-pass Rajayoga pair rules, Moon aspect rule, AK-AmK struggle rule, Navamsha confirmation rule, Sagittarius dasha caution rule, dasha-sign-as-lagna rules, Karakamsha starter rules, and Pada/Arudha starter rules.

Latest category expansion:

- Precise relationship-timing rules using active Chara Dasha matches to Darakaraka, Upapada, Darapada, DKN, and D1/D9 axes.
- Relationship-pressure caution rules for sixth/twelfth links, node influence, and Darakaraka pressure.
- Upapada availability remains unscored until a specific supported relationship rule is triggered.
- Amatyakaraka placement rules for job, career, and business now use the Chapter 13 D1 Lagna method.
- Amatyakaraka Chara-timing rules score moderate professional support only when the running sign contains AmK or places it in the tenth or eleventh.
- Amatyakaraka existence for important-person questions remains zero-weight context until a specific question and corroborating evidence are available.
- Starter D1 Rajayoga pairs are promise-only context; Navamsha survival carries the scored confirmation.
- Pair-specific D1 and D9 Rajayoga rules remain zero-weight traceability markers to avoid rewarding the same yoga repeatedly.
- Active Chara tenth-house focus adds a separate moderate timing score when surviving Rajayoga planets support professional manifestation.
- AK-related Chara periods remain modest caution signals; the source explicitly rejects automatic fall predictions.
- AK in the tenth from an active Chara sign and AK/Karakamsha in Sagittarius remain zero-weight context.
- AK in the eighth from an active Chara sign and sixth/eighth Chara subperiods add modest caution scores only.
- The sixth-house rashi-period caution is restricted to children questions and still requires D7, Vimshottari, and wider-chart confirmation.
- Chapter 10 afflicted-Gnatikaraka timing adds one modest child-only caution score when an active Chara period contains Gnatikaraka.
- Chapter 10 Putrakaraka-Gnatikaraka linkage and Sagittarius-GK subperiod facts remain zero-weight trace context to avoid duplicate penalties.
- Final scoring review: broad status summaries, generic category-activation counts, raw tenth-house occupation, raw Putrakaraka placement, and Arudha/Karakamsha starter interpretations remain zero-weight context until a passage supports a narrower outcome rule.
- Final scoring review: only precise extracted conditions carry weights; zero-weight context rules are ignored by score aggregation even if malformed outcome metadata is introduced later.
- Putrakaraka placement remains available as child-related context; Chapter 10 adds the narrower scored childhood-pressure rule.
- Arudha eleventh-house and Karakamsha ninth-house starter rules remain available as context for future sourced expansion.
- Chara Dasha sign-as-lagna snapshots remain available across categories; precise supported timing rules carry the score.

## Copyright Handling

Do not copy long text from the book into code or rules.

Store:

- Short paraphrased interpretation.
- Condition metadata.
- Source book name.
- Chapter/page reference.

Use RAG only for explanation after deterministic Jaimini facts and rules have triggered.

## Recommended Next Jaimini Batch

1. Deepen Chara Dasha sign-strength rules using the running rashi dasha as lagna.
2. Add Karakamsha-specific outcome rules after selecting the next source passages.
3. Smoke-test refreshed saved charts after the core audit.
