# Astrology Engine TODO

## Completed

- [x] Git checkpoint before architecture work.
- [x] Add `AGENTS.md`.
- [x] Create `astrology/` package skeleton.
- [x] Add refined JSON dataclasses / structures.
- [x] Add Varga / divisional fact extractor.
- [x] Add Dasha fact extractor.
- [x] Add Yogini skeleton with `calculation_status = "skeleton"`.
- [x] Add OCR task note for `Yogini Dasha.pdf`.
- [x] Read OCR text from `Yogini Dasha.pdf`.
- [x] Implement deterministic Yogini Dasha calculation.
- [x] Add current Yogini major period and subperiod.
- [x] Add Yogini lord facts in D1/D9/D10.
- [x] Add starter active Yogini YAML rules.
- [x] Add `PyYAML` dependency.
- [x] Add formal rule loader.
- [x] Add deterministic rule engine.
- [x] Add score aggregation engine.
- [x] Add starter YAML rule files.
- [x] Populate `triggered_rules` from deterministic rule evaluation.
- [x] Populate `summary_scores` from triggered rules.
- [x] Add active transit wrapper using existing transit priority logic.
- [x] Add Varga assessment with D9/D10 findings and cross-chart confirmations.
- [x] Add focused tests for current deterministic engine.
- [x] Add chart refresh command for saved chart JSON.
- [x] Add RAG query builder from triggered rules and calculated facts.
- [x] Wire RAG query into prediction evidence JSON.
- [x] Add 3-year future transit/timing scan to new engine.
- [x] Include future transit windows, dasha-lord transits, years, and Sarvashtakavarga terms in RAG query.
- [x] Inspect readable divisional chart DOCX.
- [x] Add divisional source notes and varga chapter map.
- [x] Expand chart engine to calculate D3, D12, D16, D27, D40, D45, and D60.
- [x] Expand Varga facts to expose all supported divisional charts.
- [x] Add first extracted D10/Dashamsha rules from the divisional book.
- [x] Inspect readable Jaimini source book.
- [x] Add Jaimini source notes.
- [x] Implement Jaimini rashi aspects.
- [x] Implement Karakamsha.
- [x] Implement Pada / Arudha Lagna.
- [x] Implement Upapada Lagna.
- [x] Implement 10th from Arudha Lagna.
- [x] Implement Jaimini yoga detection for starter Rajayoga patterns.
- [x] Wire enhanced Jaimini facts into four-system JSON.
- [x] Add stronger Jaimini YAML rules.
- [x] Inspect readable Parashari source files.
- [x] Add Parashari source notes.
- [x] Add first source-referenced Parashari career/business rule batch from Phal Dipika and BPHS.
- [x] Add deterministic Parashari helper layer.
- [x] Add normalized evidence ledger across Parashari, Vimshottari, Jaimini, Yogini, Varga, and Transit.
- [x] Add contradiction resolver for cross-system mixed signals.
- [x] Upgrade prompt payload to include first-class Jaimini and Yogini sections.
- [x] Upgrade validator to reject answers that ignore available Jaimini/Yogini evidence.

## Partially Done

- [~] Four-system verification JSON
  - [x] Parashari/Vimshottari: active starter layer.
  - [x] Jaimini: enhanced starter layer using book-confirmed methods.
  - [x] Varga/Divisional: active starter layer.
  - [x] Yogini: deterministic calculation active, interpretation rules started.
  - [x] Transits: active wrapper over existing priority logic.

- [~] Career/business rules
  - [x] Starter rules exist.
  - [x] Stronger deterministic starter conditions added.
  - [x] Add first source-referenced D10/Dashamsha rules from divisional book OCR.
  - [x] Continue extracting D10 rule set from remaining Dashamsha paragraphs.
  - [x] Add source-referenced starter rules for D2, D3, D4, D7, D9, D12, D16, D20, D24, D27, D30, D40, D45, and D60.
  - [~] Add page-referenced Yogini rules after OCR/review.
  - [x] Continue expanding Jaimini rules from the readable book.
  - [x] Add second-pass D10 house-meaning rules and D9 strength/marriage rules.
  - [x] Add second-pass Jaimini Rajayoga, Moon aspect, AK-AmK struggle, and Sagittarius caution rules.
  - [x] Add deeper D24 education, D4 property, D7 children, D12 family, D27 strength, and D30 risk rules.
  - [x] Add Jaimini Chara Dasha running-sign-as-lagna rules.
  - [x] Add Jaimini Karakamsha and Pada/Arudha starter rules.
  - [x] Add first Parashari D1/Vimshottari career-business source rule batch.
  - [x] Add Parashari Rajayoga/Dhanayoga/dusthana/dasha-activation helper facts.
  - [x] Add deeper divisional extraction for D2, D3, D16, D20, D40, D45, and D60.
  - [x] Add deeper Jaimini category rules for Darakaraka, Putrakaraka, Upapada, Arudha gains, Karakamsha spirituality, and Chara Dasha timing.
  - [x] Add deeper Parashari category rules for marriage, children, education, property, family, health, and wealth.
  - [ ] Continue deeper chart-by-chart divisional extraction beyond current D2/D3/D4/D7/D12/D16/D20/D24/D27/D30/D40/D45/D60 batch.
  - [ ] Continue deeper Jaimini extraction beyond current category-karaka batch.
  - [ ] Continue deeper Parashari extraction beyond current multi-category batch.

## Still Left

- [x] Add RAG query builder from triggered rules and calculated facts.
- [x] Add strict prompt builder under `astrology/synthesis/`.
- [x] Add generic-answer validation layer.
- [x] Add evidence checker.
- [x] Add completeness checker.
- [x] Add contradiction checker.
- [x] Add answer repair instruction structure.
- [x] OCR/read `Yogini Dasha.pdf`.
- [~] Convert Yogini book rules into deterministic YAML with source references.
- [x] OCR/read `Comprehensive Prediction.docx`.
- [~] Convert book rules into deterministic YAML with source references.
- [ ] Add a chart regeneration/migration path so older saved charts receive newly calculated D3/D12/D16/D27/D40/D45/D60 data.
- [x] Add initial unit tests for Varga helpers.
- [x] Add initial tests for Dasha fact extraction.
- [x] Add initial tests for enhanced Jaimini helpers.
- [x] Add initial tests for Yogini calculation.
- [x] Add initial tests for rule loading, triggering, and scoring.
- [x] Add initial tests for RAG query builder.
- [x] Add tests for prompt builder and validation.

## Recommended Next Batch

1. Integrate the new prompt payload into the live chat/LLM call.
2. Run validator on LLM responses before returning answers.
3. Add repair/regeneration flow when validation fails.
4. Run `refresh_chart_data` without `--dry-run` when ready to update existing saved charts.
5. Continue divisional book extraction chart by chart.
6. Deepen Parashari source rules with a readable classical source or your existing RAG book text.
7. Add targeted tests for property, education, children, family, and health question categories.
8. Add live chat integration for the new evidence ledger and validation/repair loop.
