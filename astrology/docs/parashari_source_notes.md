# Parashari Source Notes

Primary source files checked:

```text
C:\Users\Vincere\Downloads\पराशरहोराशास्त्र Brihat Parashar Hora Shastra _hocr_searchtext.txt\fts.txt
C:\Users\Vincere\Downloads\Phal Dipika_hocr_searchtext.txt\fts.txt
```

Supplementary source files checked:

```text
C:\Users\Vincere\Documents\Sunny\Astrology GPT\Book. Bhrigu Samhita T.M.Rao_text (1).pdf
C:\Users\Vincere\Documents\Sunny\Astrology GPT\conjunctions___the_speed_of_light.pdf
C:\Users\Vincere\Documents\Sunny\Astrology GPT\250256424-Astrology-at-the-Speed-of-Light-pdf.pdf
```

## Readability

- Brihat Parashar Hora Shastra OCR text is readable with UTF-8 decoding, but OCR is uneven.
- Phal Dipika OCR text is readable with UTF-8 decoding and is organized enough for practical rule extraction.
- Bhrigu Samhita PDF has extractable English text and can support ascendant-wise planet-in-house rules later.
- Conjunctions at the Speed of Light has extractable text but is modern interpretive material, not a core Parashari source.
- Astrology at the Speed of Light has no extractable text through `pypdf` and needs OCR before use.

## Current Extraction Decision

Use Phal Dipika and Brihat Parashar Hora Shastra as the classical Parashari source base.

Start with deterministic rules for:

- Lagna lord strength.
- Tenth house and tenth lord for career/profession.
- Second, sixth, tenth, and eleventh houses for income/service/career/gains.
- Seventh house for business, clients, contracts, and partnership.
- Ninth-tenth lord connection as dharma-karma style support.
- Dusthana pressure through 6th, 8th, and 12th house links.
- Vimshottari dasha activation of relevant house lords.

## Rule Extraction Policy

- Store only short paraphrased interpretations and source references.
- Do not copy long Sanskrit/Hindi/English passages into rule files.
- The rule engine decides applicability from calculated chart and dasha facts.
- RAG can later retrieve passages from these sources for explanation after deterministic rules have triggered.

## Rules Added So Far

- First source-referenced Parashari career/business rule batch in `astrology/rules/parashari_rules.yaml`.
- Dasha lord D1 dignity added to `parashari_vimshottari.dasha_lord_facts`.
- Deterministic Parashari helper layer added in `astrology/calculations/parashari.py`.
- Helper facts now include lord factors, Rajayoga factors, Dhana yoga factors, category lord relations, dusthana pressure, and dasha activation.
- Evidence payload now exposes `parashari` separately from `parashari_vimshottari`.
- Multi-category Parashari rules added for marriage, children, education, property, family, health/risk, and wealth.

## Next Parashari Batch

1. Add more precise Phal Dipika house-result rules by chapter.
2. Add BPHS dasha/antardasha result rules.
3. Add deterministic Rajyoga and Dhanayoga pattern detection helpers where YAML path checks are not enough.
4. Add source-backed tests for career, business, money, education, children, health, property, and family categories.
