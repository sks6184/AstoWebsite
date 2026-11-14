# AstroGPT developer handover

Written 2026-11-14 for the next coding agent (Codex or another). It reflects the repository at commit
`b691ef5` and the diagnostic audit of the same day. Statements are marked **confirmed** (seen in code,
saved records or an offline reproduction), **inferred** (best explanation, not directly observed) or
**open** (not investigated). Nothing here is a plan that has been implemented unless it says so.

Read `AGENTS.md` first. Its rule is the whole architecture: software calculates, rules judge, RAG
supports, the LLM explains, the validator controls quality.

## 1. Project and status

AstroGPT is a Django application that answers Vedic astrology questions about a saved birth chart. The
owner wants evidence-grounded consultations, not generic LLM text.

| Milestone | State |
|---|---|
| M1, M1b calculation integrity and settings (Lahiri, true node, whole-sign houses, true solar years) | Done; owner confirmed against Jagannatha Hora |
| M2 retrieval over the owner's book library (OpenAI vector store, direct adapter) | Closed; quality is weak (section 6) |
| M3 multi-round agent loop | Abandoned after repeated live failures; archived, still selectable |
| M3 planned consultation (current pipeline) | Live for allow-listed accounts; career is the reference domain |
| Structured five-section answers, follow-ups, remedies | Designed and approved, **not implemented** (`M3_STRUCTURED_CONSULTATION_DESIGN.md`) |
| Writer-model comparison (gpt-4o-mini vs gpt-4.1) | Planned, **not run** (section 12) |

Why the multi-round agent loop was replaced (confirmed in live runs, 2026-11-11 to 2026-11-13): the
model chose which tools to call, round by round. With gpt-4o-mini it chose badly, repeated requests it
had already been answered, sent draft answers together with new requests so the requests never ran, and
often ended with no answer at all. Two rounds of fixes (commits `3f48aec`, `ed6c926`) did not make it
reliable. The owner then asked for the present order: the model only classifies the question and writes;
the server decides and runs every calculation, searches the library from the results, and checks the
answer. Do not bring model-chosen tools back.

Other documents in this folder: `M1_REPORT.md`, `M1B_REPORT.md`, `M2_REPORT.md`, `M3_REPORT.md` (describes
the abandoned loop; out of date for the planned pipeline), `M3_DOMAIN_PROFILE_CHANGES.md` (not updated for
profile revision 4), `M3_EVENT_MATRIX_COMPARISON.md`, `M3_STRUCTURED_CONSULTATION_DESIGN.md`.

## 2. Architecture and execution flow

```text
question
 -> intent call (model): question type, domains, events, window        astrology/planned/provider.py
 -> plan (server): houses, planets, vargas, dashas, rules, tool calls   astrology/planned/plan.py
 -> engine tools, each once (server)                                    astrology/tools/
 -> one deterministic supplementary step (rules at later sub-periods)   plan.supplementary_calls
 -> retrieval built from the results, pooled re-rank                    astrology/planned/retrieval.py
 -> astrologer's brief (server text)                                    astrology/planned/brief.py
 -> one writer call (model): ten structured fields, no tags             provider.py
 -> fact check against the engine tables                                astrology/planned/checker.py
 -> one targeted repair call if needed, then wrong sentences removed    consultation.py, checker.prune
 -> publish: complete | preliminary | incomplete | failed               consultation.py, chat/consultation_service.py
```

The model never chooses tools and never calculates. Three model calls at most per question (intent,
writer, repair) plus up to four library searches.

Routing (`chat/agent_service.py`, `astro_site/settings.py`): `ASTROGPT_AGENT_ENABLED`,
`ASTROGPT_AGENT_USERS` (allow-list), `ASTROGPT_AGENT_PIPELINE` (`planned` default, `loop` for the old
agent), `ASTROGPT_WRITER_MODEL` (empty: the default `OPENAI_MODEL`, gpt-4o-mini). Accounts not on the
allow-list get the legacy placeholder path.

## 3. Codebase map

| Path | Responsibility |
|---|---|
| `charts/` | Chart calculation and storage. `charts/views._refresh_chart_calculation` recalculates a stale chart. Do not rewrite. |
| `astrology/calculations/` | Vargas, dasha facts, Yogini, Jaimini (`jaimini.py`, `_pada_from_house` holds the Arudha exception) |
| `astrology/rules/` | Deterministic rule engine and YAML rule files; `scoring.aggregate_scores` |
| `astrology/tools/` | Tool registry (`registry.py`, cached by chart fingerprint), adapters (`adapters.py`), contracts |
| `astrology/methodology/domains.v0.yaml`, `profile.py` | Domain profile, revision 4: domains, event guides, conventions, declared-unavailable calculations |
| `astrology/methodology/source_guidance.v0.yaml` | Event-matrix book guidance for retrieval |
| `astrology/planned/plan.py` | `Plan`, `stated_window`, `clamp_window`, `build_plan`, `supplementary_calls` |
| `astrology/planned/tables.py` | `Tables`: indexes tool results for the brief and the checker |
| `astrology/planned/brief.py` | `build_brief`, `_in_window`, `_event_evidence` |
| `astrology/planned/retrieval.py` | `build_queries`, `rerank`, `worked_example`, `guided_books` |
| `astrology/planned/provider.py` | `PlannedProvider`; `INTENT`, `WRITER`, `REPAIR` instructions; schemas |
| `astrology/planned/checker.py` | `SentenceCheck`, `check_answer`, `_report`, `essential_sections`, `prune`, `clean_text` |
| `astrology/planned/consultation.py` | `PlannedConsultation` (`investigate`, `check`, `render`, `fallback`, `extra`), `run_planned_consultation` |
| `astrology/agent/general.py` | Base class `GeneralConsultation` (`run`, limits, disclosures) and the archived loop |
| `chat/consultation_service.py` | `_append_turn`: reservation, generation, save, credit settlement |
| `chat/evidence_manifest.py` | Private saved record of each answer (16 KB cap) |
| `chat/diagnostics.py` | Private failure record, `APP_VERSION` |
| `chat/memory.py` | Conversation memory (opt-in summary and recent turns) |
| `accounts/usage.py`, `provider_meter.py`, `usage_policy.py` | Credits, budget, tariffs (only gpt-4o-mini is priced) |
| `templates/chat/ask.html` | The only answer UI |

## 4. Calculation methodology (verified conventions)

- Lahiri ayanamsha, true node, whole-sign houses, true sidereal solar years. Method profile
  `lahiri.geometric.truenode.wholesign.v2`. A chart stored under another profile is recalculated before a
  reading; if that fails, timing questions stop.
- Charts: D1, D9, D10 are used by plans; further vargas exist in `charts/`. Yogas are detections.
- Dashas: Vimshottari (Mahadasha and sub-period), Jaimini Chara, Yogini. Period end dates are exclusive.
  Pratyantar and lower levels are not calculated.
- Transits: Saturn, Jupiter, Rahu and Ketu only, as daily noon samples (sign-change dates approximate).
  Houses from the Lagna; the count from the Moon is reported separately and is never an aspect.
  Parashari transit aspects are calculated.
- Ashtakavarga: SAV per sign and each planet's BAV.
- Jaimini: seven Chara karakas, Karakamsha, house padas with the classical exception (pada falling in
  the house itself or its 7th moves ten signs on). The owner confirmed Arudha Lagna = Scorpio for their
  chart against Jagannatha Hora. The exception is applied to all twelve padas; A3, A4 and A6 on the
  owner's chart have **not** been confirmed by the owner.
- Declared unavailable (never estimated): muhurta and panchanga, kundli matching, shadbala, prashna,
  longevity, planetary padas, KP, combustion and similar strength conditions.
- Rule-engine scores saturate at 100 and are not comparable across categories. They are not given to the
  writer. The scoring code is unchanged by owner decision.

Never change a formula to make a test or a reading pass. Report defects as findings.

## 5. Event matrix

`domains.v0.yaml` holds twelve domains (career, business, marriage, relationships, children,
conception_childbirth, education, wealth, health, foreign_settlement, property, spirituality). Each has
houses, significators, vargas, Jaimini points and event guides. `build_plan` merges the labelled domains
and events into one plan.

Known gaps (confirmed):

- Only career has detailed event guides with `derived_houses`, `opposing` and `rule_outcomes`
  (promotion, voluntary employer change, involuntary disruptive change).
- A question labelled `general` with no event gets a thin plan: 1st house only, no significators, D1 and
  D9, and `get_timing_candidates` returns "unsupported" (section 11, weekly predictions).
- The live intent call labelled "When will I get a new job?" as `career:unemployment_and_reemployment`
  on every run, not as a voluntary change. The classifier is unchanged by owner instruction.
- The other domains have never been exercised end to end. Offline smoke tests for them are designed
  (design document, section 5) and not written.

## 6. RAG

One search per principle, built from calculated results (`build_queries`), at most four searches. Results
are pooled and re-ranked (`rerank`): semantic score, overlap bonus, guided-book bonus, a penalty for
worked examples of other charts; six passages are kept, two per purpose. Kept passages go into the brief
with a marker (P1...), and the saved record keeps source, purpose, score and an excerpt of up to 700
characters.

Confirmed problems from the saved records of messages 486 and 488:

- Of six kept passages, typically one or two state a usable principle. The rest are chart-diagram text
  extracted from the PDF ("Jup Example 1 13 May 1955 ... Mars Rah"), a table of contents, a "pause and
  think" filler paragraph, and Yogini-book case studies returned for a Saturn-transit query.
  `worked_example` does not recognise diagram or contents text.
- The same search results appear across unrelated questions (the same Comprehensive Prediction passages
  for a 10th-lord query and a 1st-lord query).
- Library files carry only file names: no book, chapter or page metadata, so `source_guidance.v0.yaml`
  rarely matches.
- The citation check (`passage_supports`) is a wording test: it shows a citation is on topic, not that
  the passage supports the claim. In message 486 a passage about promotion in D10 was cited for a claim
  about Venus in the 12th house.
- Each of the four searches in message 488 was recorded with status `partial`. Open: not investigated.

## 7. Writer, validation, repair, publication, credits

The writer returns the fields in `checker.FIELDS`. `check_answer` checks every sentence against `Tables`
(placement, lordship, natal and transit aspects, dignity, periods and dates, period start/end swaps,
SAV/BAV numbers, karakas, padas, yogas, uncalculated terms, citations, policy guards) and lists missing
sections. One repair call receives only the findings with the calculated values. Sentences still wrong
are removed (`prune`), with a sentence that depends on them.

Outcomes (implemented in `b691ef5`, tested offline):

| Outcome | When | Shown | Credit |
|---|---|---|---|
| Complete | nothing wrong remains, no section missing | the reading | 1 |
| Preliminary | nothing wrong remains, only supplementary sections missing | reading opening with "Preliminary reading." and what is missing | 0 |
| Incomplete | an essential section missing after repair and removal | "This reading is incomplete: ..." plus the calculated evidence | 0 |
| Failed | exception or a result that did not pass | generic message; private record on the user message | 0 |

`essential_sections(plan)`: always direct answer, calculated basis, natal basis, primary-house logic;
for timing questions also `timing` and `period_basis`; for two or more events also `event_comparison`.
Everything else is supplementary.

Failure records: `Message.provenance['failure']` on the user's message (`chat/diagnostics.py`), plus one
operations log line. Saved readings carry `app_version` and a `reading` block.

Budget (`agent_pilot` policy): six rounds, 200,000 tokens, 1,800 output tokens, four searches, US$0.05
per question. A typical question costs about US$0.014.

## 8. Conversation state

Implemented: conversations tied to one chart, opt-in memory (`Conversation.memory_enabled`, summary and
up to three recent turns, `chat/memory.py`), passed to the intent call as untrusted context. The tool
registry caches results by chart fingerprint and arguments.

Not implemented: follow-up resolution, reuse of an earlier reading's evidence, suggested questions. The
approved design is in `M3_STRUCTURED_CONSULTATION_DESIGN.md`, section 3. Approved rules: one credit per
substantive follow-up, typed or suggested, with the cost shown before submission; reopening a reading is
free; with memory off only one explicitly selected earlier reading may be reused; resolve follow-ups
through the existing intent call unless tests show a separate call is needed.

## 9. Testing

```text
python manage.py test                           # whole suite, about 7 minutes
python manage.py test astrology.test_planned    # planned pipeline, about 4 minutes
```

Latest result at `b691ef5`: 495 tests, all passing, 1 skipped (a pending Jagannatha Hora reference).
`astrology/test_planned.py` holds 71 of them. Tests use synthetic charts and synthetic passages only. The
owner's chart and book text are never used in tests or committed traces. All tests are offline: they
patch the network and the OpenAI client.

Helpers in `astrology/test_planned.py`: `Scripted` (a scripted model), `astrologer` (a truthful writer
built from the engine tables), `PlannedBase.consult`, `PlannedUiTests.post` and `PublicationTests.run_with`
(through the real view and service). Test doubles must include a badly behaved model, not only a
cooperative one.

Known test hazard (confirmed): a fresh checkout or worktree on Windows converts line endings of
`astrology/evaluation/fixtures/p6_cases_v1.json`, which breaks its hash lock and fails 12 tests in
`test_quality` and `test_evaluation`. Restore LF endings in that file locally. A `.gitattributes` rule
would fix it; the owner has not decided.

Shell hazard on the owner's machine: bash heredocs collapse backslashes and break on some quotes. Write
patch scripts with a file tool and assert that no backspace character (`chr(8)`) ends up in a source file.

## 10. Git

- Remote: `origin` = `https://github.com/sks6184/AstoWebsite.git`. It holds `main` (`2312a42`) and
  `claude/m3-publish-partial`.
- Live checkout: `...\Astro_Code_base`, branch `claude/m3-planned-consultation` at `b691ef5`. The owner's
  development server runs from it and reloads on every file change.
- Development worktree: `...\Astro_Code_base_dev`, branch `claude/m3-publish-partial`. It has no `.env`,
  so it cannot make paid calls. This document is committed there. **This is the branch to continue
  from**: it is the live branch plus docs-only commits, and it was pushed to `origin` on 2026-11-14 with
  the owner's approval.
- To move the live checkout onto it later (`git merge --ff-only claude/m3-publish-partial` in the live
  checkout), the untracked copy of `docs/claude_migration/M3_STRUCTURED_CONSULTATION_DESIGN.md` there has
  to be removed first, because the branch now tracks that file. The owner has asked that it not be
  touched without their say.
- Tags: `m3-agent-loop-v1` (old loop; also branch `claude/m3-agent-loop-archive`), `m3-planned-v1`
  (planned pipeline before the audit fixes).
- Commits on the feature line, newest first: `b691ef5` publish preliminary readings and failure records;
  `eb20110` period start/end check and brief wording; `8425556`, `79d55f9`, `75ec57d`, `1f86200` audit
  fixes; `49023e2`, `439ed93` planned pipeline.
- Pushed: `claude/m3-publish-partial` only. Never merge into `main` without explicit approval. The live
  diagnostic test of `b691ef5` (approved budget US$0.05) has not been run.
- Untracked in the live checkout, the owner's: `.vscode/`, `docs/AstroGPT Implementation
  Recommendations.txt`, `docs/AstroGPT_Event_Matrix.csv`.

## 11. Known defects and open issues, by priority

1. **Weekly and other short-window questions cannot be answered (confirmed).** Message 488, "How will be
   my next week": the plan held nothing that changes within a week. Only one Vimshottari sub-period runs,
   the four slow planets do not change sign, and the Moon, Sun, Mercury, Venus and Mars transits,
   pratyantar periods and panchanga are not calculated. The writer's period and placement sentences were
   wrong (codes `wrong_period`, `wrong_placement`, `wrong_house_lord`), five sentences were removed, no
   verified period sentence was left, and the reading became incomplete. Requiring `period_basis` for a
   seven-day window is also questionable. Fixing this needs new calculations and a planning profile for
   short windows: a methodology decision for the owner.
2. **"Next week" is not read by the server (confirmed).** `stated_window` handles years and "next N
   months" only. The window 2026-11-14 to 2026-11-21 came from the model's intent reply: seven days from
   today, not the next calendar week. Dates should be decided by the server. `TIME_ZONE` is UTC, so
   "today" can differ from the user's local date near midnight.
3. **The incomplete reading is a long evidence dump (confirmed).** `fallback()` prints up to 14 lines of
   each of five brief sections, including two blocks of generic triggered rules, and discards the
   verified sentences (31 were verified in message 488). It should say briefly what could not be verified
   and why, and keep what was verified.
4. **Writer text is not saved (confirmed).** The raw writer and repair answers and the removed sentences
   exist in memory (`attempts`, `removed_statements`) but are not in the saved record, and the record's
   16 KB cap drops the later events. The exact wrong claim in messages 482-484 and 488 cannot be
   recovered. This blocks diagnosis of writer versus checker.
5. **RAG relevance (confirmed).** Section 6.
6. **Evaluative claims pass the check (confirmed).** Message 481 says the 10th lord is "well placed"; it
   is in the 12th house and the rule engine flags that as a caution. The checker verifies facts, not
   judgements. Phrases without a house ("aspects your career") are also unchecked; the owner approved
   controlled mappings for career, employment, promotion and job change, not yet built, and not as an
   automatic "career = aspect to the 10th".
7. **Ashtakavarga is unused (confirmed).** SAV and BAV reach the writer, but none of the three latest
   career readings mentions them.
8. **Cause of failures 482-484 (inferred).** A reading with a missing section was discarded by the
   service. The mechanism was reproduced offline and fixed in `b691ef5`. The same question succeeded as
   message 486 on the older code, so the failures depended on what the writer happened to write.
9. **An absent evidence-strength label makes a reading preliminary (confirmed, by design of `b691ef5`).**
   The owner has said a formatting label must not count like missing evidence. Small fix: treat
   `evidence_strength_label` and `evidence_strength_reason` as notes, not as missing sections.
10. **Writer depth (open).** Every live run needed the repair call. Whether a stronger writer fixes this
    is the purpose of the comparison in section 12.

## 12. Writer-model comparison (planned, not run)

Baseline gpt-4o-mini, challenger gpt-4.1. The intent classifier, engine, planning, retrieval and
validator stay unchanged. Procedure:

1. Freeze: run intent, planning, calculations and retrieval once per question and save the brief text
   (it contains the calculations and the kept passages).
2. Send the identical brief, instructions and schema to both writers from a standalone script outside the
   app's request path, with model name and prices as arguments. `ASTROGPT_WRITER_MODEL` and the tariff
   table are not changed. The script first lists the models available to the key and stops if `gpt-4.1`
   is missing.
3. Save the raw writer answer, the checker report on it, the repair answer, its report, the removed
   sentences and the final outcome, for each model.
4. Compare: wrong statements by type before repair, sentences removed, sections missing, outcome, the
   owner's blind rating of reasoning and usefulness, tokens, latency and cost.

Owner decisions of 2026-11-14: approved in principle with a ceiling of US$0.20 in paid calls; not to be
run until defect 4 (private capture of raw writer answers, repaired answers, removed sentences and
findings) is implemented; pricing and model availability must be verified immediately before the run.
Two career questions are the primary comparison ("When will I get a new job in 2027?" and one more, for
example "Can I get promoted next year or get a new job?"). The weekly question ("How will my next week
be? Give me a weekly prediction.") is a diagnostic for insufficient evidence only: it is expected to end
incomplete for both writers until defect 1 is addressed.

Prices read from OpenAI's pricing page on 2026-11-13, to be re-verified on the day: gpt-4o-mini US$0.15
input and US$0.60 output per million tokens; gpt-4.1 US$2.00 and US$8.00. Estimate: freezing two
questions US$0.02; gpt-4o-mini both questions US$0.01; gpt-4.1 about US$0.06 (career, with repair) plus
US$0.04 (weekly). With a second career question the total is about US$0.20, at the approved ceiling: check the
estimate again before running, and drop the weekly question first if it does not fit. One gpt-4.1 career answer with repair
exceeds the app's US$0.05 per-question cap, which is why the runner is separate.

## 13. Next approved phase (not started)

Five-section answers (Direct Answer, Key Reasoning, expandable Detailed Analysis, Hindu Remedies, Further
Analysis with clickable questions and a free-text field). Remedies need a verified source collection;
gemstones are deferred; mantras are shown only as verified source text. See
`M3_STRUCTURED_CONSULTATION_DESIGN.md`. The owner's order: make the live pipeline reliable first.

## 14. Safeguards

- Edit and test only in the development worktree. Bring a commit to the live checkout by fast-forward
  only after the full suite passes there.
- No paid OpenAI calls, pushes, merges, dependency installs or deployments without the owner's explicit
  approval. A live diagnostic budget of US$0.05 was approved once and has not been used.
- Never print, log or send the `.env` API key. Never use the owner's chart in tests or commit book text.
- Do not reintroduce model-chosen tools or the multi-round loop.
- Do not change calculation formulas or astrological methodology without approval. Do not hard-code dates.
- Do not fabricate Jagannatha Hora reference values.

## Instructions for the Next Coding Agent

**Preserve.** The planned pipeline and its stage order; the fact check and targeted repair; the four
publication outcomes and their credit rules; the private failure record; chart-freshness handling; the
Arudha exception; the 495 passing tests.

**Defective or unverified.** Everything in section 11. In addition, commits `eb20110` and `b691ef5` have
never been exercised by a successful live reading: message 486 ran on older code, and message 488 ran on
`b691ef5` but ended incomplete.

**First task.** Save the writer's raw answer, the repair answer, the per-sentence findings and the
removed sentences in the private record of every reading (defect 4). It is small, changes no behaviour
the user sees, and every other investigation, including the writer comparison, depends on it. Suggested
approach: store them in a separate key of the assistant message's provenance (or on the user's message
for failed readings) so the 16 KB cap on the evidence record does not drop them. They contain chart
statements, so they must stay private: check that `chat.views.answer_provenance` and
`templates/chat/ask.html` do not expose the new key.

The owner has assigned fixes 1 to 5 of the audit to the next agent: defect 4 (capture), defect 3
(concise incomplete reading), defect 9 (strength label), defect 2 (server reads "next week" and "this
week") and the retrieval filter for diagram and contents text in defect 5.

**Second and third.** Defect 3 (a concise incomplete reading that keeps verified sentences) and defect 9
(the strength label). Both are small and inside `consultation.py` and `checker.py`. Then bring defects 1
and 2 to the owner as a methodology proposal before writing code.

**Inspect first.** `astrology/planned/consultation.py` (`investigate`, `check`, `fallback`, `extra`),
`astrology/planned/checker.py` (`check_answer`, `_report`, `essential_sections`),
`chat/evidence_manifest.py` (`manifest`), `chat/consultation_service.py` (`_append_turn`),
`astrology/planned/plan.py` (`stated_window`, `build_plan`).

**Reproduce offline.** For an incomplete reading:
`python manage.py test astrology.test_planned.PublicationTests.test_a_reading_whose_period_section_is_emptied_by_removal_is_incomplete_not_lost`.
For the thin weekly plan, build a `PlannedConsultation` on a synthetic chart with a `Scripted` intent of
`{'question_type': 'predictive_timing', 'domains': ['general'], 'events': []}` and a seven-day window, and
read `result['brief']` and `result['plan']`.

**Tests required before a change is accepted.** The whole suite passes in the development worktree, with
new offline tests for the change, including a badly behaved scripted writer.

**Do not change without approval.** Calculation formulas and conventions (section 4); the domain profile
and event guides; rule-engine scoring; the intent classifier's instructions; the writer model and tariff
table; which sections are essential; credit rules.

**Needs explicit approval every time.** Paid API calls of any size, pushing, merging into `main`,
installing dependencies, and fast-forwarding the live checkout while the owner is using the server.
