import hashlib
import json
import logging

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI, OpenAIError

from astrology.services.prediction_service import build_prediction_evidence
from astrology.synthesis.answer_schema import REQUIRED_SECTIONS
from astrology.validation.validator import validate_answer
from charts.remedies import remedies_for_dasha


ANSWER_CACHE_VERSION = "v20-period-match-verdict-relocation"
logger = logging.getLogger(__name__)


def model_for_depth(depth_level):
    return settings.OPENAI_MODEL or "gpt-4o-mini"


def _target_length(depth_level):
    if depth_level == 1:
        return "150-220 words"
    if depth_level == 2:
        return "400-600 words"
    return "800-1200 words"


def _system_instructions(depth_level, answer_style="", answer_language="English"):
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    style_note = ""
    if answer_style.strip():
        style_note = f"\nUser answer-style instruction: {answer_style.strip()}"
    return (
        "You are AstroGPT, a careful Vedic astrology synthesis assistant.\n"
        "Use the provided hybrid evidence payload as the authority. The software calculates, "
        "the deterministic rules judge, RAG supports, and you only explain.\n"
        "Never calculate or invent planetary positions, divisional chart placements, dashas, "
        "transits, Sarvashtakavarga points, houses, signs, nakshatras, yogas, or timing windows.\n"
        "Use only: evidence_payload, evidence_ledger, summary_scores, triggered_rules, "
        "contradictions, and retrieved RAG/file-search context.\n\n"

        "═══ FOUR REQUIRED SECTIONS — in this exact order ═══\n"
        "### Jyotish Analysis\n"
        "### Why We Advise That\n"
        "### Remedy\n"
        "### Practical Guidance\n"
        "Do not add any other ### headings. Do not create sub-headings inside sections.\n\n"

        "═══ QUESTION TYPE DETECTION ═══\n"
        "Check evidence_payload.question.time_scope.is_fixed.\n\n"

        "IF is_fixed = false  (timing scan — user asked 'when', 'best period', 'which year', 'any chance'):\n"
        "  ### Jyotish Analysis — write EXACTLY this structure:\n"
        "    Paragraph 1 (2-3 sentences): Direct verdict on the overall chart readiness for this topic.\n"
        "    **Option 1 — [Bold date range]**: One sentence on why this is the top window (its core strength).\n"
        "    **Option 2 — [Bold date range]**: One sentence on the character of this alternative period.\n"
        "    If no strong window exists, say so plainly and name the least difficult period anyway.\n"
        "  ### Why We Advise That — explain the evidence behind BOTH options, one paragraph per system.\n"
        "  ⚠ CRITICAL PERIOD MATCH RULE: For each option you recommend (e.g., Oct 2028–Aug 2029),\n"
        "    ALL lords and periods cited in 'Why We Advise That' for that option MUST come from that\n"
        "    option's own entry in evidence_payload.transits.future_timing.windows[].\n"
        "    Use the window's: mahadasha_lord, antardasha_lord, jaimini_active_sign,\n"
        "    jaimini_active_sub_sign, yogini_name, sub_yogini_name, jaimini_confirmation,\n"
        "    yogini_alignment, and transit_segments.\n"
        "    DO NOT use evidence_payload.parashari_vimshottari.current_mahadasha or\n"
        "    current_antardasha for future-window explanations — those reflect TODAY's running dasha,\n"
        "    not the dasha active in the recommended window.\n"
        "    Para 1 — Vimshottari/Parashari: 'During Option 1 (Oct 2028–Aug 2029), the active dasha is\n"
        "      [window.mahadasha_lord] Mahadasha / [window.antardasha_lord] Antardasha...'\n"
        "    Para 2 — Jaimini/Chara: 'In Option 1, the Chara Dasha is [window.jaimini_active_sign] sign...'\n"
        "    Para 3 — Yogini: 'In Option 1, the Yogini is [window.yogini_name] / [window.sub_yogini_name]...'\n"
        "    Para 4 — Divisional Charts: What the relevant D-chart (D4/D9/D10 per topic) shows for\n"
        "      the antardasha lords of each option.\n"
        "    Para 5 — Transit & Ashtakavarga: SAV-based transit quality for each option.\n"
        "    End with one sentence explaining why Option 1 is ranked above Option 2.\n\n"

        "IF is_fixed = true  (specific period — user named a date, month, year, or said 'now'/'currently'):\n"
        "  ### Jyotish Analysis — write EXACTLY this structure:\n"
        "    Line 1 (bold): A human-language verdict phrase — NOT a label like 'Verdict: Yes'. Instead:\n"
        "      • If chart clearly supports: **Clearly supported — [one-line reason]**\n"
        "      • If mixed but leaning yes: **Possible, though conditions must align — [one-line reason]**\n"
        "      • If not confirmed: **Possible, but not cleanly confirmed — [one-line reason]**\n"
        "      • If unlikely: **Unlikely in the near term — [one-line reason]**\n"
        "      Choose the phrase that fits — do not default to 'Verdict: Partially'.\n"
        "    Then 3-5 sentences of plain-language explanation covering the overall picture.\n"
        "    Do NOT give timing options. The user asked about a fixed period; answer that period only.\n"
        "  ### Why We Advise That — explain the verdict system by system:\n"
        "    Para 1 — Vimshottari: Name Mahadasha and Antardasha lord active in this period and their stance.\n"
        "    Para 2 — Jaimini/Chara: Active Chara sign, which house from lagna, whether it supports the topic.\n"
        "    Para 3 — Yogini: Active Yogini and sub-Yogini names, whether auspicious/challenging for this topic.\n"
        "    Para 4 — Divisional & Transit: D-chart confirmation (or denial) and transit quality in this period.\n"
        "    Close with one sentence on overall confidence level.\n\n"

        "═══ MANDATORY SPECIFICITY ═══\n"
        "Naming a system without its active lords is a validation failure:\n"
        "• Vimshottari: NEVER 'current Mahadasha'. ALWAYS 'Sun Mahadasha / Rahu Antardasha (Jan 2024 – Oct 2026)'.\n"
        "• Jaimini: NEVER 'Jaimini indicates'. ALWAYS 'In Capricorn Chara Dasha, Mercury as Amatyakaraka...'.\n"
        "• Yogini: NEVER 'Yogini shows mixed'. ALWAYS 'Pingala Yogini major / Bhramari sub-period shows...'.\n"
        "• D-charts: NEVER 'D10 is weak'. ALWAYS 'In D10, Mercury as 10th lord is in the 8th house, weakening...'.\n\n"

        "═══ GENERAL RULES ═══\n"
        "Treat Parashari/Vimshottari, Jaimini, Yogini, Varga/Divisional charts, and Transits as first-class systems.\n"
        "Vimshottari is part of Parashari timing — do not write 'Parashari, Vimshottari, and Jaimini' as three separate systems.\n"
        "Chara is a Jaimini dasha. Do not call it a separate system.\n"
        "Every timing window you recommend must be bold in Markdown: '**October 2028 to August 2029**'.\n"
        "For transits, mention Sarvashtakavarga points only as one supporting layer. Never call a transit unfavorable "
        "unless the payload shows the planet, house, SAV points, and a weak/challenging score.\n"
        "Do not expose internal score phrases ('composite score is low'). Translate to user language ('preparation "
        "is supported more than immediate results').\n"
        "Do not write checklist labels: 'Timing:', 'Parashari:', 'Confidence:', 'Transits:'.\n"
        "If muhurta data is missing, say: 'Exact muhurta requires tithi, nakshatra, yoga, karana, weekday, and lagna "
        "calculation — this is a preliminary timing recommendation only.'\n"
        "If judgment is cautious or negative, describe windows as pressure/watch periods, not opportunities.\n\n"

        "═══ TOPIC-SPECIFIC RULES ═══\n"
        "RELOCATION / RETURN TO HOMELAND questions (category = foreign_travel, keywords: return, forever, go back, "
        "native place, homeland, settle back, come back):\n"
        "  • The primary houses are 4th (homeland/roots), 12th (foreign land/settlement abroad), 9th (long-distance "
        "travel), 7th (change of residence/place). Do NOT default to 2nd/6th/10th/11th career houses.\n"
        "  • D4 (Chaturthamsha) is the key divisional chart for land, residence, and property — always mention it.\n"
        "  • If the question uses 'forever', 'permanently', 'for good', 'never come back', 'settle permanently', "
        "or 'permanent return': MANDATORY — explicitly distinguish:\n"
        "    (a) Temporary return/visit vs (b) Permanent resettlement/change of base.\n"
        "    Temporary return: 4th/9th house transits active but 12th house still strong (Rahu in 12th or 12th lord "
        "strong in a foreign sign).\n"
        "    Permanent resettlement: 4th lord strong in D1 + D4, 12th house weakening, Ketu supporting separation "
        "from foreign land, 4th Chara sign active in Jaimini.\n"
        "  • Rahu naturally pulls toward the foreign/unfamiliar; Ketu toward roots/homeland. When relevant, "
        "state which is currently dominant.\n"
        "  • If chart shows return is possible but NOT permanent settlement, say that plainly:\n"
        "    'Your chart shows windows for a temporary return, but permanent resettlement is less clearly supported "
        "in the near term.'\n"
        "  • Never use career/authority/financial indicators (10th lord, D10) as the primary evidence for "
        "a relocation question — these are only secondary context.\n\n"

        "═══ SECTION RULES ═══\n"
        "### Remedy — bullet points only, from remedy_context in payload. "
        "Name the Mahadasha/Antardasha lord. Include Beej Mantra, deity mantra, and practical observance from the payload. "
        "If no remedy data: 'No deterministic remedy was calculated.'\n"
        "### Why We Advise That — this section is collapsed in the UI (user taps 'View' to open). "
        "It must be substantive — do not repeat Jyotish Analysis prose. Write the technical evidence basis only.\n"
        "### Practical Guidance — ordinary practical guidance only, not a repeated astrology summary.\n\n"

        "Write in a calm, precise traditional Jyotish tone. Avoid generic motivation, absolute guarantees, "
        "fear, medical certainty, legal advice, or financial promises.\n"
        f"Answer language: {answer_language}. "
        "Keep Mahadasha, Antardasha, Lagna, Dasha, Nakshatra, Ashtakavarga transliterated.\n"
        "Astrology is interpretive guidance, not professional, medical, legal, or financial advice.\n"
        f"Target answer length: {_target_length(depth_level)}."
        f"{style_note}"
    )


def _compact_transits(transits: dict) -> dict:
    """Strip large repeated fields from the transit object before sending to the LLM."""
    future = transits.get("future_timing", {})
    return {
        "score": transits.get("score"),
        "horizon": transits.get("horizon"),
        "target_date": transits.get("target_date"),
        "dasha_lord_transits": transits.get("dasha_lord_transits", [])[:4],
        "future_timing": {
            "scan_months": future.get("scan_months"),
            "scan_years": future.get("scan_years"),
            "start": future.get("start"),
            "end": future.get("end"),
            "windows": future.get("windows", []),
        },
    }


def _compact_live_evidence(evidence, answer_language="English"):
    synthesis_payload = evidence.get("synthesis", {}).get("prompt_payload", {})
    system_evidence = synthesis_payload.get("system_evidence", {})
    vimshottari = system_evidence.get("parashari_vimshottari", evidence.get("parashari_vimshottari", {}))
    mahadasha_lord = (vimshottari.get("current_mahadasha") or {}).get("lord")
    antardasha_lord = (vimshottari.get("current_antardasha") or {}).get("lord")
    return {
        "question": evidence.get("question", {}),
        "summary_scores": evidence.get("summary_scores", {}),
        "evidence_ledger": evidence.get("evidence_ledger", []),
        "contradictions": evidence.get("contradictions", {}),
        "triggered_rules": synthesis_payload.get("triggered_rules", evidence.get("triggered_rules", [])[:24]),
        "parashari": system_evidence.get("parashari", evidence.get("parashari", {})),
        "parashari_vimshottari": system_evidence.get(
            "parashari_vimshottari",
            evidence.get("parashari_vimshottari", {}),
        ),
        "jaimini": system_evidence.get("jaimini", evidence.get("jaimini", {})),
        "yogini": system_evidence.get("yogini", evidence.get("yogini", {})),
        "varga": system_evidence.get("varga", evidence.get("varga", {})),
        "transits": _compact_transits(system_evidence.get("transits", evidence.get("transits", {}))),
        "remedy_context": remedies_for_dasha(mahadasha_lord, antardasha_lord, answer_language),
        "rag_context_request": evidence.get("rag", {}),
        "rule_engine": evidence.get("rule_engine", {}),
        "required_output_sections": REQUIRED_SECTIONS,
        "format_contract": {
            "sections": REQUIRED_SECTIONS,
            "open_sections": ["Jyotish Analysis"],
            "collapsed_sections": ["Why We Advise That", "Remedy", "Practical Guidance"],
            "no_extra_system_headings": True,
            "section_style": "traditional_jyotish_prose_with_remedy_bullets",
            "temporal_intent": (
                (evidence.get("question") or {}).get("time_scope") or {}
            ).get("temporal_intent", "general"),
            "temporal_framing_rule": (
                "If temporal_intent is 'future': write in forward-looking language — "
                "'your chart shows...', 'the coming period...', 'you are likely to...'. "
                "If temporal_intent is 'past': write in retrospective language — "
                "'in that period your chart showed...', 'the dasha active then was...'. "
                "If temporal_intent is 'general': use neutral language."
            ),
            "specificity_required": [
                "Vimshottari Mahadasha/Antardasha names and dates when present",
                "Jaimini Chara Dasha sign and relevant karakas when present",
                "Yogini major/sub-period and lords when present",
                "D-chart names and concrete findings when present",
                "Transit timing windows and Sarvashtakavarga as timing support only",
                "Bold Markdown for all timing windows",
            ],
        },
        "validation_gate": {
            "must_mention_available_jaimini": evidence.get("jaimini", {}).get("calculation_status") == "active",
            "must_mention_available_yogini": evidence.get("yogini", {}).get("calculation_status") == "active",
            "must_mention_available_parashari": evidence.get("parashari", {}).get("calculation_status") == "active",
            "must_mention_divisional_when_available": evidence.get("varga", {}).get("status") not in {None, "missing"},
            "must_explain_contradictions": bool(evidence.get("contradictions", {}).get("issues")),
            "must_not_present_pressure_windows_as_opportunities": True,
        },
    }


def build_prompt_payload(question, chart_data, depth_level, answer_style="", answer_language="English"):
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    evidence = build_prediction_evidence(question, chart_data or {})
    return {
        "user_question": question,
        "depth_level": depth_level,
        "answer_language": answer_language,
        "answer_style": answer_style.strip(),
        "cost_control": {
            "send_compact_context_only": True,
            "do_not_send_full_chart_unless_needed": True,
            "cacheable": True,
        },
        "evidence_payload": _compact_live_evidence(evidence, answer_language),
    }


def _cache_key(payload, model, vector_store_id):
    raw = json.dumps(
        {
            "cache_version": ANSWER_CACHE_VERSION,
            "payload": payload,
            "model": model,
            "vector_store_id": vector_store_id,
        },
        sort_keys=True,
        default=str,
    )
    return "astro-rag-answer:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _usage_counts(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return 0, 0
    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
    completion_tokens = getattr(usage, "output_tokens", 0) or 0
    return prompt_tokens, completion_tokens


def _fallback_answer(question, payload, model, reason):
    evidence = payload.get("evidence_payload", {})
    systems = evidence.get("system_evidence", {})
    future_timing = systems.get("transits", {}).get("future_timing", {})
    windows = future_timing.get("windows", [])

    def _window_line(w):
        vim = w.get("label", "?")
        jai = w.get("jaimini_active_sign") or "?"
        jai_sub = w.get("jaimini_active_sub_sign") or "?"
        yog = w.get("yogini_name") or "?"
        yog_sub = w.get("sub_yogini_name") or "?"
        score = w.get("composite_score") or w.get("score", "n/a")
        return (
            f"- {w.get('start_display') or w.get('start')} to {w.get('end_display') or w.get('end')} "
            f"| Vim: {vim} | Jaimini: {jai}/{jai_sub} | Yogini: {yog}/{yog_sub} | score {score}"
        )

    window_lines = "\n".join(_window_line(w) for w in windows[:5])
    if not window_lines:
        window_lines = "- No candidate windows were calculated for this question category."
    ledger_lines = "\n".join(
        f"- {item.get('system')}: {item.get('claim')} ({item.get('direction')}, {item.get('strength')})"
        for item in evidence.get("evidence_ledger", [])[:8]
    )
    if not ledger_lines:
        ledger_lines = "- Evidence ledger was not populated."
    return {
        "model": model,
        "prompt": json.dumps(payload, indent=2, default=str),
        "answer": (
            "The local astrology computation pipeline is ready, but the OpenAI RAG call did not run.\n\n"
            f"Reason: {reason}\n\n"
            "### Jyotish Analysis\n"
            "The deterministic evidence payload is ready, but the OpenAI RAG interpretation did not run. "
            "The prepared evidence includes Parashari dasha timing, Jaimini, Yogini, divisional charts, transit checks, "
            f"and the following timing windows: {window_lines}. Evidence ledger: {ledger_lines}\n\n"
            "### Remedy\n"
            "No deterministic remedy was generated because the OpenAI RAG call did not run.\n\n"
            "### Practical Guidance\n"
            "Re-run after OpenAI configuration is available to receive the final interpretive answer.\n\n"
            f"Question: {question}"
        ),
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


def _repair_answer(client, model, depth_level, answer_style, answer_language, payload, draft_answer, validation_result):
    repair_payload = {
        "original_payload": payload,
        "draft_answer": draft_answer,
        "validation_result": validation_result,
        "task": "Repair the answer so it satisfies the validation result using only the provided evidence payload.",
    }
    response = client.responses.create(
        model=model,
        instructions=_system_instructions(depth_level, answer_style, answer_language),
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(repair_payload, ensure_ascii=False, default=str),
                    }
                ],
            }
        ],
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID],
                "max_num_results": 8,
            }
        ],
    )
    return response


def _remedy_lines(remedy_context):
    remedies = remedy_context.get("remedies", [])
    if not remedies:
        return []
    lines = []
    for remedy in remedies:
        role = remedy.get("role", "Dasha lord")
        planet = remedy.get("planet") or remedy.get("lord")
        lines.append(f"- For the current {role} {planet}, recite the provided mantra with steadiness and devotion.")
        beej = remedy.get("beej", {})
        deity = remedy.get("deity_specific", {})
        if beej.get("mantra"):
            text = f"  - Beej Mantra: {beej['mantra']}"
            if beej.get("transliteration") and beej["transliteration"] != beej["mantra"]:
                text += f" ({beej['transliteration']})"
            lines.append(text)
            if beej.get("meaning"):
                lines.append(f"  - Beej Meaning: {beej['meaning']}")
        if deity.get("mantra"):
            text = f"  - Deity Mantra: {deity['mantra']}"
            if deity.get("transliteration"):
                text += f" ({deity['transliteration']})"
            lines.append(text)
            if deity.get("meaning"):
                lines.append(f"  - Deity Meaning: {deity['meaning']}")
        for item in remedy.get("extra_guidance", []):
            lines.append(f"  - {item}")
    note = remedy_context.get("devotion_note")
    if note:
        lines.append(f"- {note}")
    return lines


def _replace_section(markdown_text, heading, body):
    marker = f"### {heading}"
    start = markdown_text.find(marker)
    replacement = marker + "\n" + body.strip() + "\n"
    if start == -1:
        return markdown_text.rstrip() + "\n\n" + replacement
    next_start = markdown_text.find("\n### ", start + len(marker))
    if next_start == -1:
        return markdown_text[:start].rstrip() + "\n\n" + replacement
    return markdown_text[:start].rstrip() + "\n\n" + replacement + "\n" + markdown_text[next_start:].lstrip()


def _apply_deterministic_remedy(answer_text, payload):
    remedy_context = payload.get("evidence_payload", {}).get("remedy_context", {})
    lines = _remedy_lines(remedy_context)
    if not lines:
        return answer_text
    return _replace_section(answer_text, "Remedy", "\n".join(lines))


def generate_answer(question, chart_data, depth_level, answer_style="", answer_language="English"):
    model = model_for_depth(depth_level)
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    payload = build_prompt_payload(question, chart_data or {}, depth_level, answer_style, answer_language)

    if not settings.OPENAI_API_KEY:
        return _fallback_answer(question, payload, model, "OPENAI_API_KEY is not set.")

    if not settings.OPENAI_VECTOR_STORE_ID:
        return _fallback_answer(
            question,
            payload,
            model,
            "OPENAI_VECTOR_STORE_ID is not set. Add your uploaded astrology RAG vector store ID.",
        )

    cache_key = _cache_key(payload, model, settings.OPENAI_VECTOR_STORE_ID)
    cached = cache.get(cache_key)
    if cached:
        cached["answer"] = cached["answer"] + "\n\n[Reused cached answer.]"
        return cached

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = json.dumps(payload, ensure_ascii=False, default=str)

    try:
        response = client.responses.create(
            model=model,
            instructions=_system_instructions(depth_level, answer_style, answer_language),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID],
                    "max_num_results": 8,
                }
            ],
        )
    except OpenAIError as exc:
        return _fallback_answer(question, payload, model, f"OpenAI API error: {exc}")

    prompt_tokens, completion_tokens = _usage_counts(response)
    answer_text = response.output_text
    validation_result = validate_answer(answer_text, payload.get("evidence_payload", {}))
    logger.info(
        "Astrology answer validation score=%s passed=%s issues=%s",
        validation_result.get("score"),
        validation_result.get("passed"),
        validation_result.get("issues"),
    )
    if not validation_result["passed"]:
        try:
            repair_response = _repair_answer(
                client,
                model,
                depth_level,
                answer_style,
                answer_language,
                payload,
                answer_text,
                validation_result,
            )
            repair_prompt_tokens, repair_completion_tokens = _usage_counts(repair_response)
            answer_text = repair_response.output_text
            prompt_tokens += repair_prompt_tokens
            completion_tokens += repair_completion_tokens
            validation_result = validate_answer(answer_text, payload.get("evidence_payload", {}))
            logger.info(
                "Astrology repaired answer validation score=%s passed=%s issues=%s",
                validation_result.get("score"),
                validation_result.get("passed"),
                validation_result.get("issues"),
            )
        except OpenAIError:
            answer_text = (
                answer_text
                + "\n\n### Validation Note\n"
                + validation_result["repair_instruction"]
            )
    answer_text = _apply_deterministic_remedy(answer_text, payload)
    result = {
        "model": model,
        "prompt": prompt,
        "answer": answer_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "validation_result": validation_result,
    }
    cache.set(cache_key, result, 60 * 60 * 24 * 30)
    return result


def generate_placeholder_answer(question, chart_data, depth_level, answer_style="", answer_language="English"):
    return generate_answer(question, chart_data, depth_level, answer_style, answer_language)
