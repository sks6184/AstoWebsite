# M3 design: structured consultations, follow-ups, remedies, domain checks, writer comparison

Status: proposal for owner approval, 2026-11-14. Nothing in this document is implemented.
Baseline: branch `claude/m3-planned-consultation` at `eb20110`.

The pipeline stays as it is: intent -> plan from the event matrix -> engine calculations -> retrieval from
the results -> brief -> one writer call -> fact check -> one targeted repair -> render. No model-chosen
tools and no multi-round loop are reintroduced. Every addition below is a new field, a new server step or
a new renderer on that same line.

## 1. Structured response schema

The writer already returns ten checked fields. The server will assemble the five sections from them; the
writer gains three fields and loses none.

| Section | Built from | Rule |
|---|---|---|
| 1. Direct Answer | `direct_answer` (80-120 words; server accepts 60-140) | With two or more events in the plan, each event must be named in it, or the answer goes to repair |
| 2. Key Reasoning | new `key_reasoning`: `supporting[]` and `opposing[]`, 2-4 items each, plain language | Every item passes the same fact check; an empty `opposing` is allowed only when the brief has no opposing factor |
| 3. Detailed Analysis | existing fields, regrouped by the server (see below) | A subsection is shown only if its evidence exists and at least one checked sentence survives |
| 4. Hindu Remedies | new `remedies[]`, each item tied to a remedy passage ID | Empty until the remedy knowledge base exists (section 4) |
| 5. Further Analysis | new `follow_ups[]`, 3-4 questions | Server-validated (section 3) |

Detailed Analysis subsections and their sources:

- Vimshottari Dasha: `periods`, Vimshottari sentences
- Jaimini / Chara Dasha: `jaimini_view` plus the Chara sentences
- Yogini Dasha: the Yogini sentences
- D1 and divisional charts: `natal_promise`, `divisional_confirmation`
- Transits and Ashtakavarga: `transits`
- Classical sources: `classical_support`, with each cited passage's title and what it was retrieved for
- Conflicting signals and event comparison: `conflicts`, `event_assessment`

To split the period text by system reliably, the writer schema changes `periods` into three fields
(`vimshottari`, `chara`, `yogini`). A subsection whose calculation was not run or failed shows one fixed
server line ("Not calculated in this reading: ...") taken from the plan's `unsupported` list. The writer
cannot fill it.

Saved shape (in the message's private record, next to today's provenance):

```json
{"schema": "consultation.v2",
 "direct_answer": "...",
 "key_reasoning": {"supporting": ["..."], "opposing": ["..."]},
 "analysis": [{"id": "vimshottari", "title": "Vimshottari Dasha", "text": "...",
               "evidence_ids": ["E7"], "status": "ok|not_calculated"}],
 "remedies": {"status": "not_available|ok", "items": []},
 "follow_ups": [{"id": "f1", "text": "...", "domain": "career"}],
 "confidence": "moderate", "notes": ["..."], "validation": {}}
```

`Message.content` keeps a plain-text rendering of the same sections, so history, export and the older
template keep working. The twelve-part answer structure in AGENTS.md maps onto these sections; the
validator's required-section list is unchanged.

## 2. Front-end rendering

- `templates/chat/ask.html` renders from the saved structure when `schema` is `consultation.v2`, and falls
  back to `Message.content` for older answers.
- Direct Answer and Key Reasoning are always open. Supporting and opposing points are two short lists.
- Detailed Analysis uses native `<details>` elements, closed by default, one per subsection. No JavaScript
  is needed to read an answer.
- Remedies is a closed `<details>` block, absent when `status` is `not_available`.
- Further Analysis: each suggested question is a button; below them one text field with the placeholder
  "Ask anything about your reading...". Both submit the same form to the same endpoint; a button only
  pre-fills the question and adds the suggestion ID.
- Validation notes ("statements removed", "preliminary timing") move to a small footer line.

## 3. Follow-up conversations

A follow-up is an ordinary planned consultation with one extra server-built input, the consultation state.

State saved with every answer (`consultation_state`, in the private record): chart ID, method profile and
chart fingerprint; question; direct answer; intent label and events; window; plan summary; evidence index
(evidence ID -> tool, arguments, request fingerprint); verified findings (the checked sentences with their
evidence IDs, at most about 20); kept passage IDs.

Steps:

1. Resolve. The intent call receives the new text plus the previous question, direct answer, label and
   window, and returns a standalone question, the label, the window and a `relation`: `refines` (same
   event), `same_domain_new_event`, `new_domain`, `different_person` or `unrelated`. Stated periods are
   still read by the server, not the model. This adds input to the intent call; its instructions for
   classifying a first question do not change.
2. Guard. If the conversation's chart, the method profile or the chart fingerprint differs from the
   state's, the state is discarded and a fresh plan is built. `different_person` never inherits evidence:
   the app asks the user to choose that person's chart. Two-chart analysis stays declared unavailable.
3. Plan. `build_plan` runs as today. Each planned call is compared with the evidence index: same tool,
   arguments and chart fingerprint means the existing tool cache answers it at no cost; anything else is
   calculated. A changed window recalculates only the date-dependent tools (periods, transits,
   candidates). `new_domain` gets a new event-specific plan; only chart-level facts are reused.
4. Retrieve. New searches run only for principles not covered by the kept passages. Kept passages are
   reloaded by ID, at most six in total; passages kept for a different domain are dropped.
5. Write and check. The brief is rebuilt from the engine tables, never from the earlier prose. It adds a
   short "EARLIER IN THIS CONSULTATION" block: previous question, direct answer and verified findings,
   marked as context. The fact check runs against the tables as usual.
6. Consistency. New server check: a sentence that contradicts a verified earlier finding resting on the
   same evidence becomes a repair finding. If the evidence changed (new window, recalculated chart), the
   answer must say so. The calculation always wins over the earlier answer.

Memory control:

- Memory enabled: the existing summary and recent turns are used as today, plus the state above.
- Memory disabled: nothing from earlier turns is reused silently. Clicking a suggested question, or ticking
  "about this reading" beside the text field, authorises exactly one thing: the state of that one answer.
  No summary and no other turns. The form says so in one line.
- Erasing a message or resetting memory deletes its state; a follow-up then runs as a new question.

Credits (recommendation, needs your decision): one question credit for every follow-up, suggested or
typed, because both run the same workflow and cost about the same. Before submission the form shows "This
uses 1 question credit. You have N left." beside the buttons and the text field, and submission is
disabled at zero. Generating the suggestions costs nothing extra: they come from the same writer call.

Suggested questions are validated by the server: 3-4 items, each a question, each mapped to a domain in
the profile, none asking for a declared-unavailable calculation or a declined topic, none repeating the
question just answered.

## 4. Hindu remedies: knowledge requirements

No remedy text will be generated until a remedy source collection exists. Today a remedy sentence without
a retrieved source already fails the fact check; that stays.

Needed from you:

- Source texts you are entitled to use, in a collection separate from the predictive books, with book,
  chapter and verse or page in the metadata.
- For each remedy entry: the indication it answers (planet, house, period, affliction), the practice
  (mantra, stotra, deity worship, daana, seva, vrata), the tradition, and a source class: `scriptural`
  (a named Purana, Agama, Smriti or stotra text), `classical_jyotisha` (a named chapter of a Jyotisha
  text) or `customary` (later practice without a textual source).
- Mantras and stotras are stored and shown only as verified text from the source. The model never
  produces or completes them.

Flow: after the fact check, the server selects indications that are calculated and verified (for example
a debilitated period lord), searches the remedy collection for those indications only, and gives the
writer the matching entries. The writer may select and explain; it cannot add a practice. The checker
then requires a remedy passage ID per item, the source class shown to the user, and no promise of an
outcome. With no match the section says that nothing was found in the sources; it is never filled from
general knowledge and never replaced by secular advice.

## 5. Additional-domain smoke tests (offline, synthetic chart)

One test module, `astrology/test_planned_domains.py`, with no model and no library. For each case a
scripted intent reply is fed in, and the test asserts that the label is accepted, the plan's houses,
planets, vargas and events come from that domain's guide, the calls run, and unsupported items are listed.

| Case | Profile domain | Checks beyond the common ones |
|---|---|---|
| Marriage timing | `marriage` | D9 planned; kundli matching reported unavailable |
| Travel or relocation | `foreign_settlement` | plan built from that guide, not from career |
| Education | `education` | any divisional chart the engine lacks is listed as unsupported |
| Finance or business | `wealth`, `business` | two domains give two sets of events |
| Health | `health` | diagnosis, prognosis and treatment sentences fail the checker; longevity is declined |
| Childbirth | `conception_childbirth` | fertility and medical-outcome sentences fail the checker |

These tests prove the mapping, planning and unsupported-capability handling. They cannot show whether the
live model classifies such questions correctly; that needs six intent calls (well under one cent in
total) whenever you approve it. Career alone gets end-to-end interpretation tests.

## 6. Controlled writer comparison

Not run until approved. The production writer and the tariff table stay untouched.

- Freeze: for each case the brief text (calculations and passages are already inside it) is saved once.
  Both writers receive the identical brief, instructions and schema. Intent and retrieval are not re-run.
- Cases: the three career questions already asked on your chart, plus two synthetic briefs with planted
  traps (a period ending just inside the window; a Moon count next to a Lagna house). Five cases.
- Runner: a standalone script outside the app's request path that takes the model name and prices as
  arguments, so neither `ASTROGPT_WRITER_MODEL` nor the tariff table changes. It first lists the models
  available to your key and stops if `gpt-4.1` is absent.
- Measured by the existing checker, before any repair: wrong statements by type (placement, lordship,
  aspect, period, boundary, transit), statements removed, sections missing, repair needed or not.
- Judged by you, blind (answers labelled A and B): comparative reasoning between events, recognition of
  contradictions, clarity of the direct answer, relevance of technical detail. One sheet, 1-5 each.
- Cost and latency: tokens and seconds per call, from the API responses.

Prices to re-verify on the day (OpenAI pricing page, read 2026-11-13): gpt-4o-mini $0.15 input / $0.60
output per million tokens; gpt-4.1 $2.00 / $8.00. With a brief of about 8,400 tokens and about 1,500
tokens out, one gpt-4.1 answer is about $0.03, or $0.06 with a repair, which is above the current $0.05
per-question cap. gpt-4o-mini is about $0.005. The whole comparison is estimated at under $0.40.

## 7. Phased plan

| Phase | Work | Modules | Paid calls |
|---|---|---|---|
| 0 | Live re-test of the corrected pipeline on the two career questions | none | about $0.03, needs approval |
| 1 | Response schema v2: new writer fields, per-system period fields, server assembly, word-range and per-event checks, saved structure, text fallback | `astrology/planned/provider.py`, `checker.py`, `consultation.py`, `brief.py`; `chat/evidence_manifest.py`; tests | none |
| 2 | Rendering: sections, expandable analysis, footer notes | `templates/chat/ask.html`, `static/css`, `chat/views.py`, `chat/templatetags` | none |
| 3 | Follow-ups: state, resolve step, evidence reuse, consistency check, memory rules, credit disclosure, suggested-question validation | new `astrology/planned/followup.py`; `plan.py`, `consultation.py`, `provider.py`; `chat/memory.py`, `chat/agent_service.py`, `chat/views.py`, `chat/forms.py`; template | none offline; one live check |
| 4 | Domain smoke tests | new `astrology/test_planned_domains.py`; any gap found in a domain guide is reported, not patched silently | none |
| 5 | Writer comparison | new script under `scripts/`; a short report | under $0.40, needs approval |
| 6 | Remedies | new remedy collection and loader; `retrieval.py`, `checker.py`, template | depends on the collection |

Phases 1, 2 and 4 do not depend on the writer decision. Phase 6 waits for the sources.

## Decisions needed

1. Approve the five-section schema, including the split of `periods` into three per-system fields.
2. Credit rule: one credit per follow-up for both suggested and typed questions (recommended), or another
   rule.
3. With memory off, a click or the "about this reading" tick authorises that one answer's state and
   nothing else.
4. Remedy sources: which texts, and whether gemstone recommendations are in or out.
5. The resolve step adds follow-up context to the intent call's input. Confirm this is compatible with
   "keep the intent classifier unchanged", or the resolve step becomes a separate small call.
6. Phase 0 and, later, phase 5 as paid runs.
