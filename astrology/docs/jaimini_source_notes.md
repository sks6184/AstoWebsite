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
- `charts/jaimini.py` calculates Chara Dasha periods and subperiods.
- `charts/jaimini_confirmation.py` gives a starter confirmation layer using Chara Dasha, karakas, and activated houses.
- `astrology/calculations/dasha_facts.py` wraps Jaimini evidence into the new four-system JSON.

## Gaps To Implement

High-priority deterministic helpers:

- Jaimini rashi aspects.
- Karakamsha.
- Pada / Arudha Lagna.
- Upapada Lagna.
- 10th from Arudha Lagna.
- Planets influencing Arudha Lagna.
- Amatyakaraka relationship to career houses, D10, and Arudha factors.
- Atmakaraka dasha influence and caution flags.
- Jaimini yogas as deterministic findings.
- Navamsha confirmation of Jaimini yogas.

Implemented in the enhanced Jaimini layer:

- Rashi aspects.
- Karakamsha.
- Pada / Arudha Lagna.
- Upapada Lagna.
- 10th from Arudha Lagna.
- Planets influencing Arudha and 10th from Arudha.
- Jaimini rajayogas from the listed AK, AmK, PK, DK, fifth-lord, Moon, and Venus combinations.
- Navamsha confirmation of Jaimini rajayogas.
- Moon-aspected-by-many-planets Rajayoga signal.
- AK-AmK support and struggle relationship flags in D1/D9.
- Atmakaraka Chara Dasha caution flag.
- Sagittarius Chara Dasha caution flag from the examples.
- Chara Dasha running-sign-as-lagna evidence for major and subperiod signs.
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

- Darakaraka and Upapada starter rules for relationship/marriage.
- Putrakaraka starter rules for children.
- Arudha eleventh-house rules for wealth and business visibility.
- Karakamsha ninth-house rule for spiritual direction.
- Stronger Chara Dasha sign-as-lagna timing rule across categories.

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
2. Add direct/indirect dasha order metadata to the new evidence JSON.
3. Add Scorpio/Aquarius special-case notes where the legacy dasha calculator exposes enough detail.
4. Add Karakamsha-specific outcome rules after selecting the next source passages.
5. Smoke-test against saved charts.
