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

## Chapter 3 Extraction

Implemented from Chapter 3, "The Basic Principles" (printed pages 22-29 /
PDF pages 30-37):

- Removed fixed auspicious/challenging labels for individual Yoginis.
- Judge the active Yogini major and subperiod planetary lords contextually.
- Score available Chapter 3 factors: D1 dignity, relevant house lordship and
  placement, difficult-house lordship, directional strength or weakness,
  Vargottama status, primary divisional-chart placement and dignity, and
  natural-benefic or natural-malefic association/aspect.
- Keep unimplemented factors explicit: moolatrikona, friend/enemy signs,
  combustion, Aarohi/Avarohi, Rashi-Sandhi/Gandanta, and full Shadabala.

## Chapter 4 Extraction

Implemented from Chapter 4, "Interpretation of a Horoscope" (printed pages
30-45 / PDF pages 38-53):

- Treat a Yogini period as activation of the natal promise carried by its lord,
  not as a fixed good or bad outcome.
- Add the active lord's dispositor condition and topic-house relevance.
- Add active-lord aspects to topic houses and dusthana placement pressure.
- Add category-karaka relevance.
- Add active-lord Raja Yoga and Dhana Yoga activation through calculated
  house-lord relationships.
- Keep broad natal personality analysis and Dharma/Artha/Kama/Moksha
  distribution outside the timing evaluator for a later normalized-facts pass.

## Chapter 5 Extraction

Implemented from Chapter 5, "Interpretation of Divisional Charts" (printed
pages 46-49 / PDF pages 54-57):

- Confirm timing through the category's primary varga.
- Check varga Lagna lord, relevant house lords, category karakas, and active
  dasha lords in the varga.
- Keep vargas as a promise-confirmation layer, while dashas remain the timing
  layer.

## Chapter 6 Extraction

Implemented from Chapter 6, "Interpretation of Vimshottari Dasha" (printed
pages 50-59 / PDF pages 58-67):

- Apply shared planetary-dasha pair rules to both Vimshottari and Yogini.
- Treat the major-period lord as a temporary Lagna and judge the subperiod lord
  from it.
- Support kendra/trikona relationships.
- Mark 6/8 and 2/12 relationships as pressure.
- Surface category-house activation by the subperiod lord.

## Chapter 7 Extraction

Implemented from Chapter 7, "The Meaning in Psychology of Yoginis" (printed
pages 60-70 / PDF pages 68-78):

- Add paraphrased baseline themes for each Yogini major period.
- Add a reviewed major/subperiod baseline matrix.
- Keep both baseline layers deliberately low weight. They modify the result but
  never override calculated lord condition or cross-system verification.

## Chapter 8 Extraction

Implemented from Chapter 8, "Quick Use of Yogini Dasha" (printed pages 71-81 /
PDF pages 79-89):

- Expose a traceable snapshot checklist for active Yogini names, lordship,
  placement, aspects, conjunction context, and dispositor context.
- Mark the checklist as explanatory only. It must not bypass Vimshottari,
  Jaimini, divisional-chart, or transit verification in normal predictions.

## Chapter 9 Extraction

Implemented from Chapter 9, "Confirmation of an Event" (printed pages 82-97 /
PDF pages 90-105):

- Add a cross-system event-confirmation object for Vimshottari, Jaimini, and
  Yogini.
- Rank intersections of three systems first, intersections of two systems
  second, then single-system windows using divisional support and composite
  score.
- Surface contradicting or unconfirmed systems instead of hiding them.

## Chapter 10 Extraction

Implemented from Chapter 10, "Successful Predictive Techniques" (printed
pages 98-129 / PDF pages 106-137):

- Expose calculated topic houses from D1 Lagna, Moon as Lagna, relevant natural
  karakas as temporary Lagnas, and the category's primary divisional-chart
  Lagna.
- Keep these as normalized facts so the LLM never derives houses itself.
- Keep individual case-study narratives out of the deterministic engine.

## Chapter 11 Extraction

Implemented conservatively from Chapter 11, "Composite Approach of Vedic
Astrology" (printed pages 130-182 / PDF pages 138-190):

- Confirm timing through Jupiter and Saturn slow-transit triggers.
- Treat Mars as an execution trigger and Sun/Moon as narrower timing refiners.
- Expose transit houses from both natal Lagna and Moon.
- Keep pre-ingress effects, body-part health predictions, dasha-start transit
  snapshots, Moon-Lagna Vedha ranking, and Jupiter trines to natal or Navamsha
  lords as explicit deferred, unscored rules pending separate verification.

## Chapter 12 Extraction

Implemented from Chapter 12, "Yogini Dasha and the Annual Chart" (printed
pages 183-191 / PDF pages 191-199):

- Add an isolated annual-chart Yogini period generator.
- Determine the first annual Yogini from `(birth nakshatra number + completed
  years + 3) mod 8`.
- Use annual durations of 10, 20, 30, 40, 50, 60, 70, and 80 days.
- Calculate the first-period balance from the untraversed portion of the natal
  Moon nakshatra and calculate proportional subperiods.
- Keep annual Yogini output outside prediction scoring until a deterministic
  solar-return / Varshaphala chart calculator supplies the annual-chart start.
- Record the printed example's inconsistent sentence: its formula and table
  identify the 16-day balance as Pingala, which the implementation follows.

## Chapter 13 Extraction

Implemented conservatively from Chapter 13, "Derived Meanings of the Yoginis"
(printed pages 192-203 / PDF pages 200-211):

- Store concise paraphrased derived themes as experimental metadata only.
- Keep these themes unscored and optional for explanation after calculated
  evidence.
- Exclude medical claims, danger claims, fatality claims, and highly
  speculative symbolic meanings from automated output.

## Chapter 14 Extraction

Recorded from Chapter 14, "Conclusion" (printed pages 204-205 / PDF pages
212-213):

- Retain contextual Yogini-lord evaluation and cross-check Yogini with
  Vimshottari, divisional charts, and transits.
- Do not treat Sankata or Ulka as automatically negative. Their lords may
  support modern technical, industrial, educational, or authority-related
  outcomes when the calculated chart context supports that result.
