import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI, OpenAIError

from .prediction_context import build_prediction_context


ANSWER_CACHE_VERSION = "v13-time-scope-window-jaimini"


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
        "You are AstroGPT, a careful Vedic astrology interpretation assistant.\n"
        "Write in the tone of a traditional Vedic astrologer: calm, precise, respectful, practical, "
        "and rooted in dasha, bhava, transit, and Ashtakavarga reasoning. "
        "Use terms such as Mahadasha, Antardasha, Lagna, bhava, transit, Nakshatra, and Sarvashtakavarga naturally, "
        "but keep the wording understandable for a normal user. "
        "Do not sound generic, overly modern, or motivational. "
        "For health, be cautious and practical; do not create fear and do not give medical advice. "
        "For career, speak in terms of effort, responsibility, opportunity, and timing. "
        "For relationships, speak with maturity and avoid absolute promises.\n"
        "You are answering a user's question, not merely writing a report. "
        "Before explaining, convert the computed factors into a clear judgment, but make it sound human and astrological, not like an AI template.\n"
        "Follow computed_context.answer_contract strictly. "
        "For yes/no, stay/move, job, marriage, visa, settlement, or similar decision questions, "
        "internally decide one of: Likely yes, Likely no, Mixed leaning yes, or Mixed leaning no. "
        "Do not print these as labels unless the sentence needs them naturally. "
        "Start with one direct sentence that borrows the user's subject and states the probability in natural language. "
        "Example: if the user asks about staying in a foreign country, begin like "
        "'Your stay in the foreign country looks likely to continue for a longer period, though there may be pressure during Saturn-related periods.' "
        "Example: if the answer is weaker, begin like "
        "'Your stay in the foreign country may continue for now, but the chart shows a stronger chance of change after the next dasha shift.' "
        "Do not start with Current Mahadasha, Current Antardasha, confidence labels, or a list of facts. "
        "Do not use AI-looking headings named Short Answer, Confidence, Prediction, Reason, or Astrological Reason. "
        "Do not write a standalone confidence heading. If needed, include confidence naturally in the opening paragraph, "
        "such as 'The confidence is moderate because the dasha supports staying but the transit shows pressure.' "
        "For non-binary questions, still begin with a plain-language outcome such as strong, moderate, challenging, or improving.\n"
        "After the natural opening paragraph, use only helpful human headings such as ### Timing, ### Why this is indicated, "
        "### Remedy, and ### Practical guidance. Keep headings short and not mechanical.\n"
        "Use the OpenAI file-search/RAG knowledge and the provided computed JSON only.\n"
        "Do not calculate or invent planetary positions, divisional charts, dashas, transits, "
        "ashtakavarga bindus, houses, signs, nakshatras, or timing windows.\n"
        "For timing questions, lead with the provided candidate_timing_windows. "
        "Do not create dates outside those windows unless you explicitly say the app did not calculate them. "
        "Obey computed_context.temporal_policy.time_scope strictly. "
        "If the user says this year/current year, mention only windows inside that year. "
        "If no explicit time phrase is found, the app scans the next 5 years.\n"
        "Important: computed_context.dasha is the dasha active on current_date only. "
        "For any future candidate_timing_windows, use that window's active_dasha, mahadasha_lord, "
        "and antardasha_lord fields. Do not carry the current Antardasha into future windows after it ends.\n"
        "For every timing window you mention, explicitly name the window's Mahadasha and Antardasha. "
        "Then explain the transit of the Mahadasha lord and the transit of the Antardasha lord using "
        "that window's dasha_lord_transit_checks, including Sarvashtakavarga points. "
        "Use each window's required_explanation as the factual basis for the Reason section. "
        "If a window includes transit_segments, explain the segment changes instead of treating the whole period "
        "as one fixed transit. Mention any date where the Mahadasha or Antardasha lord changes sign/house.\n"
        "Do not mention another transit planet as the main reason unless it is the Mahadasha lord or Antardasha lord "
        "for that exact window.\n"
        "Use computed_context.transit_priority as the deterministic transit formula. "
        "For weekly questions, Moon transit may be considered along with fast planets and slow background planets. "
        "For monthly questions, Moon is excluded; use Dasha/Antardasha lords first, then other planets by priority. "
        "When explaining events, connect the Mahadasha/Antardasha lord's natal placed house, owned houses, "
        "and transit house to likely life areas. Use RAG knowledge for house significations, but do not invent placements. "
        "If transit_priority marks low Sarvashtakavarga, describe it as pressure, delay, or care needed rather than support.\n"
        "Always use computed_context.jaimini_confirmation as a confirmation layer. "
        "For selected future timing windows, prefer each candidate window's jaimini_confirmation over the current-date Jaimini check. "
        "Do not let Jaimini override Vimshottari by itself; use it to raise or lower confidence. "
        "If Jaimini status is supports, say naturally that Jaimini also confirms the same direction and mention the Chara Dasha, "
        "Antardasha, relevant Karakas, and activated houses from the provided JSON. "
        "If status is mixed, weak, or not_confirmed, say the confirmation is limited and keep confidence moderate or cautious. "
        "Use OpenAI file-search/RAG only to explain Jaimini principles and house meanings; do not invent Jaimini placements.\n"
        "When you give predicted timing, include a ### Remedy section before ### Practical Guidance. "
        "Use the provided remedies/remedial mantra data for that exact window's Mahadasha and Antardasha lords. "
        "Include both planetary Beej mantra and deity mantra when present, in the provided answer language when available. "
        "Format both mantras consistently as separate bullets: "
        "'Beej Mantra: <mantra> (<transliteration>)' and "
        "'Deity Mantra: <mantra> (<transliteration>)'. "
        "After Beej Mantra, add 'Beej Meaning: <meaning>' when provided. "
        "After Deity Mantra, add 'Deity Meaning: <meaning>' when provided. "
        "Clearly say the mantra should be recited, not the meaning. "
        "For Mars or Saturn remedies, include the provided extra guidance such as Hanuman Chalisa; "
        "for Saturn include the mustard-oil lamp guidance when provided. "
        "Mention mustard-oil lamp only when Saturn is the Mahadasha lord or Antardasha lord for that exact timing window, "
        "and only if the provided remedy data includes it. "
        "Do not invent mantras, deity days, remedy days, counts, rituals, or remedies. "
        "Do not write the devotion note yourself; the app renders that note deterministically after the answer.\n"
        "Keep remedies out of ### Practical Guidance. Practical Guidance should contain ordinary behavioral guidance only, "
        "such as planning, patience, health routines, communication, study discipline, or career follow-through.\n"
        "Use computed_context.temporal_policy.current_date as today's date. "
        "Never describe any date before current_date as upcoming, future, or pending. "
        "If past periods are relevant, label them explicitly as past context. "
        "For prediction questions, separate past context, current indications, and future windows when applicable.\n"
        "When candidate windows span months or a year, explain the Mahadasha lord and Antardasha lord transit checks "
        "and their Sarvashtakavarga support from the computed JSON.\n"
        "If a required calculation is absent from the JSON, say the app must calculate it first.\n"
        "Format the answer as Markdown using H3 headings and bullet points. "
        "Do not use headings named ### Short Answer, ### Confidence, ### Prediction, ### Reason, or ### Astrological Reason. "
        "Prefer this flow: opening judgment paragraph, ### Timing, ### Why this is indicated, ### Remedy, ### Practical guidance. "
        "If a section truly does not apply, omit it rather than filling it mechanically.\n"
        f"Answer language: {answer_language}. "
        "Keep terms like Mahadasha, Antardasha, Lagna, Dasha, Nakshatra, and Ashtakavarga transliterated.\n"
        "Explain the locally calculated factors in plain language and cite uncertainty responsibly.\n"
        "Astrology is interpretive and not a substitute for professional, medical, legal, or financial advice.\n"
        f"Target answer length: {_target_length(depth_level)}."
        f"{style_note}"
    )


def build_prompt_payload(question, chart_data, depth_level, answer_style="", answer_language="English"):
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    prediction_context = build_prediction_context(question, chart_data, answer_language=answer_language)
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
        "computed_context": prediction_context,
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
    windows = payload["computed_context"].get("candidate_timing_windows", [])
    window_lines = "\n".join(
        f"- {window.get('start_display', window['start'])} to {window.get('end_display', window['end'])} "
        f"| score {window['score']} | {window['label']} "
        f"| active dasha {window.get('active_dasha', {}).get('label', 'n/a')} "
        f"| transit checks {window.get('dasha_lord_transit_checks', [])}"
        for window in windows[:5]
    )
    if not window_lines:
        window_lines = "- No candidate windows were calculated for this question category."
    return {
        "model": model,
        "prompt": json.dumps(payload, indent=2, default=str),
        "answer": (
            "The local astrology computation pipeline is ready, but the OpenAI RAG call did not run.\n\n"
            f"Reason: {reason}\n\n"
            "A clear yes-or-no leaning could not be finalized because the RAG/LLM interpretation did not run. "
            "The deterministic astrology context is ready, but the final reading still needs the interpretation step.\n\n"
            "### Timing\n"
            f"- Candidate timing windows:\n{window_lines}\n\n"
            "### Why this is indicated\n"
            "- Computed context prepared for GPT interpretation:\n"
            f"Category: {payload['computed_context']['category']}\n"
            f"Mahadasha lord: {payload['computed_context']['dasha'].get('mahadasha', {}).get('lord', 'n/a')}\n"
            f"Antardasha lord: {payload['computed_context']['dasha'].get('antardasha', {}).get('lord', 'n/a')}\n"
            f"Transit checks: {len(payload['computed_context']['transit_lords'])}\n\n"
            f"Current date for future/past separation: "
            f"{payload['computed_context'].get('temporal_policy', {}).get('current_date', 'n/a')}\n\n"
            "### Practical guidance\n"
            "- Re-run after OpenAI configuration is available to receive the final interpretive answer.\n\n"
            f"Question: {question}"
        ),
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


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
    result = {
        "model": model,
        "prompt": prompt,
        "answer": response.output_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }
    cache.set(cache_key, result, 60 * 60 * 24 * 30)
    return result


def generate_placeholder_answer(question, chart_data, depth_level, answer_style="", answer_language="English"):
    return generate_answer(question, chart_data, depth_level, answer_style, answer_language)
