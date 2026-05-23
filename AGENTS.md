# AGENTS.md - Astrology AI Application Architecture Instructions

## Project Context

This is a Django astrology AI application. The long-term architecture must keep deterministic astrology logic separate from RAG and LLM text generation.

The application should work like this:

```text
User question
-> deterministic chart facts
-> deterministic dasha facts
-> deterministic rule triggering
-> score aggregation
-> RAG support from books
-> strict LLM synthesis
-> validation / repair
-> final answer
```

The guiding rule:

```text
Software calculates.
Rules judge.
RAG supports.
LLM explains.
Validator controls quality.
```

## Mandatory Boundaries

- The LLM must not calculate planetary placements, house positions, dashas, vargas, yogas, or transits.
- The LLM must not decide whether a deterministic astrology rule applies.
- RAG must not be the rule engine.
- RAG is used only for explanation, nuance, source support, and classical references after deterministic facts and triggered rules are known.
- Deterministic rule files should store paraphrased interpretations and source references only. Do not store long copyrighted book text.

## Four-System Verification Goal

Predictions should be checked through four systems where available:

1. Parashari with Vimshottari Dasha
2. Jaimini with Jaimini/Chara Dasha
3. Varga / divisional chart confirmation
4. Yogini Dasha

Transits should be used as timing confirmation and pressure/support context, not as the sole basis for a prediction.

## Target Module Shape

```text
astrology/
    calculations/
        varga.py
        dasha_facts.py
        yogini.py

    rules/
        engine.py
        loader.py
        scoring.py
        parashari_rules.yaml
        jaimini_rules.yaml
        divisional_rules.yaml
        yogini_rules.yaml

    rag/
        query_builder.py

    synthesis/
        prompt_builder.py

    validation/
        genericity_checker.py
        evidence_checker.py
        completeness_checker.py
        contradiction_checker.py

    services/
        prediction_service.py
```

The existing `charts/` app currently owns chart calculation. Do not rewrite it unless necessary. Prefer wrapping its existing output into normalized fact structures first.

## Required JSON Evidence Shape

The prediction pipeline should build a structured payload containing:

- `question`
- `chart_facts`
- `parashari_vimshottari`
- `jaimini`
- `varga`
- `yogini`
- `transits`
- `triggered_rules`
- `summary_scores`
- `rag`
- `validation`

Every final answer should be traceable back to these fields.

## MVP Scope

Start with career/business questions.

Phase 1 should support:

- D1, D9, and D10 fact extraction
- Vimshottari Mahadasha and Antardasha facts
- Jaimini karaka and Chara Dasha facts where already available
- Yogini Dasha skeleton until the scanned Yogini book has been OCR processed
- Rule-engine-ready JSON structures

Do not attempt to implement every astrology rule at once. Build the framework first so book-derived rules can be added gradually.

## Astrology Answer Quality Rules

The astrology app must not return generic LLM-style answers.

Every final astrology answer must be evidence-based and must include specific deterministic facts from the app.

The LLM is not allowed to invent:

- chart facts
- dasha facts
- divisional chart facts
- Jaimini facts
- muhurta facts
- rule conclusions

The LLM may only synthesize:

1. calculated chart facts
2. calculated dasha facts
3. triggered deterministic rules
4. RAG/book context
5. validation feedback

### Mandatory Answer Structure

For any serious prediction, the final answer must include:

1. Direct Answer
2. Best Timing / Recommended Window
3. Chart Basis
4. Dasha Basis
5. Divisional Chart Basis
6. Jaimini Basis
7. Parashari Basis
8. Muhurta Basis, if the question asks "when should I start", "when should I launch", "best time", or "auspicious time"
9. RAG / Classical Support
10. Conflicting Signals
11. Practical Guidance
12. Confidence Level

### Special Rule For Timing Questions

If the user asks a timing question such as:

- When should I start?
- When should I launch?
- What is the best time?
- Which date is good?
- Should I start around this date?

Then the answer must not only say "avoid this date".

It must provide:

- whether the proposed date is good, bad, or mixed
- at least one better date or better date window
- whether the user should do soft launch, beta launch, private testing, payment launch, or public marketing launch
- reason based on dasha, transit, muhurta, and relevant divisional charts
- confidence level

If exact muhurta calculation is not yet implemented, the answer must clearly say:

"Exact muhurta selection requires tithi, nakshatra, yoga, karana, weekday, lagna, Moon strength, and planetary hour calculation. Based on current available evidence, this is only a preliminary timing recommendation."

### Mandatory Evidence By Question Type

For career / business / startup questions, the answer must include evidence from D1, D9, D10, current Vimshottari dasha, Yogini dasha if available, 2nd house, 7th house, 10th house, 11th house, 10th lord, 11th lord, Mercury, Jupiter, Saturn, Rahu if online/business/technology/foreign market is involved, Amatyakaraka if Jaimini is available, and Arudha Lagna if Jaimini is available.

For timing / muhurta questions, the answer must include proposed date assessment, tithi, nakshatra, weekday, yoga, karana, Moon sign, Moon strength, lagna at chosen time, Mercury strength for website/business, Jupiter support for wisdom/advisory business, 10th/11th house support, Rahu/technology relevance if online business, avoid periods if any, and a better alternative window.

If these calculations are not implemented, validation must fail or mark the answer as preliminary.

### Generic Answer Failure Rules

The answer must fail validation if:

- it does not directly answer the user's question
- it says "avoid" but gives no better alternative date/window
- it mentions Parashari without specific Parashari factors
- it mentions Jaimini without specific Jaimini factors
- it mentions divisional charts without naming D9/D10/etc.
- it answers a business question without 2nd, 7th, 10th, or 11th house logic
- it answers a website/business question without Mercury and Rahu/technology consideration
- it answers a timing question without muhurta factors
- it gives generic phrases like "planetary movements are challenging" without naming the actual factors
- it gives advice but no evidence
- it contains spelling or grammar issues
- it makes strong claims with low evidence
- it does not provide a confidence level
- it does not explain contradictions

### Validation Output

The validation layer must return structured JSON:

```json
{
  "passed": true,
  "score": 0,
  "issues": [],
  "missing_sections": [],
  "generic_phrases_detected": [],
  "unsupported_claims": [],
  "repair_instruction": ""
}
```

If validation fails, the app should regenerate or repair the answer using the repair_instruction.
