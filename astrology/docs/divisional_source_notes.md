# Divisional Chart Source Notes

Source file:

```text
C:\Users\Vincere\Documents\Sunny\Astrology GPT\Comprehensive Prediction.docx
```

Book:

```text
Comprehensive Prediction by Divisional Charts
V. P. Goel
```

Current extraction status:

- DOCX text is readable enough for deterministic rule extraction.
- Extracted approximately 23,073 paragraphs and 596,000 characters.
- OCR noise exists in cover/table/chart areas.
- English explanatory sections are usable, especially D10/Dashamsha.
- Original PDF page numbers are not reliably preserved in DOCX extraction.

## Book Divisional Chart Map

The book explicitly lists and discusses these Parashari divisions:

- D1 Rashi: basic chart.
- D2 Hora: wealth, family, speech.
- D3 Drekkana: coborns, ability, courage, power.
- D4 Chaturthamsha: destiny, immovable property, home.
- D7 Saptamsha: children and grandchildren.
- D9 Navamsha: supplementary chart, spouse, married life, partners.
- D10 Dashamsha: career, honour, success, promotion/demotion, status.
- D12 Dwadashamsha: parents, lineage, prenatal matters.
- D16 Shodashamsha: movable assets and general happiness.
- D20 Vimshamsha: spiritual pursuits and worship.
- D24 Chaturvimshamsha: learning and academic achievements.
- D27 Saptavimshamsha/Bhamsha: physical strength and weakness.
- D30 Trimshamsha: miseries, evil, arishta.
- D40 Khavedamsha: general auspicious effects.
- D45 Akshavedamsha: character and conduct.
- D60 Shashtiamsha: all effects, benefic/malefic karma.

## Calculation Coverage

The chart engine now calculates:

- D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60.

Book-confirmed calculation notes implemented:

- D3: three 10-degree divisions; first same sign, second fifth from sign, third ninth from sign.
- D12: twelve 2.5-degree divisions starting from the sign itself.
- D16: movable signs start Aries, fixed signs start Leo, dual signs start Sagittarius.
- D27: fiery signs start Aries, earthy signs start Cancer, airy signs start Libra, watery signs start Capricorn.
- D40: odd signs start Aries, even signs start Libra.
- D45: movable signs start Aries, fixed signs start Leo, dual signs start Sagittarius.
- D60: first division starts from the sign itself, then proceeds in direct order.

## First Rule Extraction Target

The first reliable extraction target is the D10/Dashamsha career section around OCR paragraph indexes 7771-7793.

Rule-like statements from this section include:

- D10 Lagna and Lagna lord strength are important for professional stability.
- D10 10th house and 10th lord are the most important career factors.
- Relation of D10 10th house/lord with 6th, 8th, or 12th gives problems and sudden changes in profession.
- Strong Sun in angles in D10 supports high status, government work, administrative power, and career rise.
- Weak Sun in 6th, 8th, or 12th in D10 gives problems from government or indecisiveness.
- Strong Saturn in D10 supports subordinates/workers and can support political or Saturnine fields.
- Badly placed Saturn creates problems from subordinates.
- Planets related to the 10th house and 10th lord give promotion in their dasha periods.
- Dasha relationship with 6th, 8th, and 12th indicates change or transfer.
- Rajyoga in D10 gives high positions.
- Planets in angles are powerful to deliver career results; order of strength is 10th, 7th, 4th, 1st.
- Planets in upachaya houses generally give good results with hard work.

## Rules Added So Far

- D10/Dashamsha starter rules from OCR paragraphs 7771-7793.
- D10 10th-lord placement rules from OCR paragraphs 7795-7812.
- Second-pass D10 house-meaning rules from OCR paragraphs 7561-7575.
- D10 ninth-tenth exchange / professional Rajyoga rule from OCR paragraphs 7872-7873.
- Second-pass D9/Navamsha strength and marriage-support rules from OCR paragraphs 6784-6798, 6841-6848, and 7131-7154.
- Deeper D24/Siddhamsha education rules for Lagna lord, fifth lord, ninth lord, and dusthana pressure.
- Deeper D4/Chaturthamsha property rules for Lagna lord, fourth lord, fourth-lord pressure, and Mars support.
- Deeper D7/Saptamsha children rules for Lagna lord, fifth lord, Jupiter, and fifth-lord pressure.
- Deeper D12/Dwadashamsha family rules for Lagna lord, fourth lord, ninth lord, and parental/family pressure.
- Deeper D27/Bhamsha and D30/Trimshamsha strength/risk rules.
- Deeper D2/Hora wealth rules for second lord, eleventh lord, and dusthana pressure.
- Deeper D3/Drekkana effort rules for Lagna lord and Mars.
- Deeper D16/Shodashamsha comfort rules for fourth lord and Venus.
- Deeper D20/Vimshamsha spiritual rules for ninth lord and Jupiter.
- Deeper D40, D45, and D60 low-confidence support/pressure rules.
- Starter source-referenced rules for D2, D3, D4, D7, D9, D12, D16, D20, D24, D27, D30, D40, D45, and D60.

The non-D10 rules are currently broad framework rules using the book's chart-purpose and initial examination sections. They should be deepened chart by chart with more precise chapter rules.

## Rule Extraction Policy

- Store short paraphrases and source section references only.
- Do not copy long book text into YAML.
- Use `source_book`, `source_chapter`, and `source_page`/`source_section` metadata.
- If a statement depends on a calculation we do not yet have, add the calculation helper first or mark the rule as pending.
