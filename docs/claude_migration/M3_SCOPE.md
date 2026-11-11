# M3 scope record: offline implementation

- **Branch:** `claude/m3-general-agent`, created from `claude/m3-agent-spec` at `bf5016c`.
- **Specification:** `CLAUDE_M1_M4_ACCEPTANCE_CRITERIA.md` §5 (revision 3), the domain profile `astrology/methodology/domains.v0.yaml` (revision 3, this milestone), and `docs/claude_migration/M3_EVENT_MATRIX_COMPARISON.md`.
- **Authorization (owner, 2026-11-11):**
  - Proceed with the **offline** M3 implementation.
  - The approved refinements are M3-1, M3-4 to M3-8 and M3-10, plus the tools OD-31, OD-32 and OD-33.
  - **No paid OpenAI calls and no live testing.** The US$0.15 initial live budget is **not** authorized for spending yet.

## In scope

1. **Domain profile revision 3.** Apply the approved refinements. The matrix alternatives for voluntary and lateral career change are kept only in a `research_annex` that is excluded from the model's guidance, for comparison in M4.
2. **A loader and validator for the profile** (`astrology/methodology/profile.py`):
   - schema checks;
   - vocabulary bounds;
   - no tool sequences;
   - it returns guidance only for the domains and events the model labels.
3. **New read-only tools**, all going through the existing registry and its chart-ownership check:
   - `get_jaimini_facts`: wraps the existing `astrology/calculations/jaimini.py`.
   - `get_counted_sign` (OD-31): the n-th sign (1–12) from AL, UL or Karakamsha. It is a new additive module, `astrology/calculations/counted_signs.py`, that reuses the existing helpers and conventions.
   - `get_natal_aspects` (OD-32): wraps the existing Parashari aspects in `charts/vedic_utils.py`. It is kept separate from Jaimini rasi drishti.
   - `get_chart_facts` gains an opt-in `include_yogas` that exposes the stored `chart_data['yogas']`.
   - Transit samples gain `transit_house_from_moon` (OD-33), alongside the existing Lagna count.
4. **Fact catalog:** an opt-in mode that publishes all 12 house lords, plus the new fact kinds (Jaimini, counted sign, aspect, yoga, Moon-based transit house).
5. **The general agent** (`astrology/agent/general.py`):
   - **Single model, batched rounds:** the model labels the question type, the domains (1–3) and the events in its first round; it then batches evidence requests (the meter permits one tool call per round); then it writes the final answer.
   - **Hard limits:** at most 6 model rounds (including one repair), at most 4 searches, and the largest round at most 25k input tokens by `tiktoken`.
   - **Shortcut:** factual questions keep the deterministic shortcut with zero LLM calls.
   - **Free tool choice:** the model may call any authorized tool. The profile is guidance only.
6. **Retrieval:**
   - the model writes the search text (a new optional `query` on `search_astrology_knowledge`);
   - a score below 0.70 raises an advisory flag only;
   - three distinct non-answer states: `retrieval_failed`, `no_source_support` and `calculation_unavailable`.
7. **Prose validation** (`astrology/validation/prose_validator.py`):
   - a claim scanner (G-1) over natural prose with inline fact tags;
   - a citation checker (G-2) and a verbatim-copy check (OD-11);
   - probability and sensitive-domain guards (G-3 to G-5, A8);
   - content elements rather than headings (A6, R10);
   - core-factor coverage (A1).
   One repair round; after that, a deterministic fallback marked partial and unbilled.
8. **Routing (A7):** `ASTROGPT_AGENT_USERS`, an allowlist that is empty by default.
   - Only allow-listed users reach the general agent.
   - Everyone else stays on legacy.
   - The old P3 slice stays reachable only through an explicit compatibility setting used by the existing tests.
9. **A pilot usage policy** for allow-listed users: 6 rounds, 4 searches, US$0.05 per consultation.
10. **Offline tests and traces:**
    - a scripted provider, with no network;
    - all 12 primary domains, the mixed-domain questions and the distinction pairs;
    - the three non-answer states, the safeguards and wrapper parity on the R1–R5 synthetic charts;
    - committed synthetic execution traces.

## Out of scope

- Paid calls and live testing.
- Changes to existing calculation modules. The new modules are additive.
- KP.
- New RAG infrastructure, specialist agents or vector-store changes.
- Automatic memory (M5).
- Paid-plan envelopes (M7).
- Importing the 81 matrix events.
- Hard-coded prediction rules.

## Privacy

- Tests and traces use the synthetic R1–R5 charts and synthetic passages only.
- The owner's chart is never used.
- No book text is committed.
