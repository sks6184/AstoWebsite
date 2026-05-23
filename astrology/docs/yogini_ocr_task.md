# Yogini Dasha Source Notes

Source file checked:

```text
C:\Users\Vincere\Desktop\Yogini Dasha.pdf
```

Current status:

- The PDF exists.
- It has 217 pages.
- The current file has extractable text.
- Calculation-method pages are readable enough for deterministic implementation.

## Implemented Calculation Method

Implemented from the calculation chapter:

- Yogini sequence: Mangala, Pingala, Dhanya, Bhramari, Bhadrika, Ulka, Siddha, Sankata.
- Lords: Moon, Sun, Jupiter, Mars, Mercury, Saturn, Venus, Rahu.
- Years: 1, 2, 3, 4, 5, 6, 7, 8.
- Total cycle: 36 years.
- Birth Yogini formula: `(Moon nakshatra number + 3) mod 8`.
- Birth balance: remaining Moon nakshatra arc divided by full nakshatra span, multiplied by birth Yogini years.
- Subperiods: natural Yogini order starting from the major Yogini itself, proportionate to Yogini years.
- Cycles repeat after 36 years.

## Still To Extract

Rules must be stored as paraphrased deterministic metadata, not long copied book text.

Next extraction tasks:

- Extract case-study rules for career, marriage, father/mother, children, health, and danger.
- Convert rule-like statements into `yogini_rules.yaml`.
- Store short paraphrases and source references only.
- Use RAG only for explanation after deterministic Yogini rules have triggered.
