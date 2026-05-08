import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI, OpenAIError

from .prediction_context import build_prediction_context


ANSWER_CACHE_VERSION = "v6-segment-first-explanation"


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
        "Use the OpenAI file-search/RAG knowledge and the provided computed JSON only.\n"
        "Do not calculate or invent planetary positions, divisional charts, dashas, transits, "
        "ashtakavarga bindus, houses, signs, nakshatras, or timing windows.\n"
        "For timing questions, lead with the provided candidate_timing_windows. "
        "Do not create dates outside those windows unless you explicitly say the app did not calculate them.\n"
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
        "Use computed_context.temporal_policy.current_date as today's date. "
        "Never describe any date before current_date as upcoming, future, or pending. "
        "If past periods are relevant, label them explicitly as past context. "
        "For prediction questions, separate past context, current indications, and future windows when applicable.\n"
        "When candidate windows span months or a year, explain the Mahadasha lord and Antardasha lord transit checks "
        "and their Sarvashtakavarga support from the computed JSON.\n"
        "If a required calculation is absent from the JSON, say the app must calculate it first.\n"
        "Format the answer as Markdown using H3 headings and bullet points. "
        "Prefer headings named: ### Prediction, ### Reason, and ### Practical Guidance.\n"
        f"Answer language: {answer_language}. "
        "Keep terms like Mahadasha, Antardasha, Lagna, Dasha, Nakshatra, and Ashtakavarga transliterated.\n"
        "Explain the locally calculated factors in plain language and cite uncertainty responsibly.\n"
        "Astrology is interpretive and not a substitute for professional, medical, legal, or financial advice.\n"
        f"Target answer length: {_target_length(depth_level)}."
        f"{style_note}"
    )


def build_prompt_payload(question, chart_data, depth_level, answer_style="", answer_language="English"):
    answer_style = answer_style or settings.ASTROGPT_ANSWER_STYLE
    prediction_context = build_prediction_context(question, chart_data)
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
            "Computed context prepared for GPT interpretation:\n"
            f"Category: {payload['computed_context']['category']}\n"
            f"Mahadasha lord: {payload['computed_context']['dasha'].get('mahadasha', {}).get('lord', 'n/a')}\n"
            f"Antardasha lord: {payload['computed_context']['dasha'].get('antardasha', {}).get('lord', 'n/a')}\n"
            f"Transit checks: {len(payload['computed_context']['transit_lords'])}\n\n"
            f"Current date for future/past separation: "
            f"{payload['computed_context'].get('temporal_policy', {}).get('current_date', 'n/a')}\n\n"
            f"Candidate timing windows:\n{window_lines}\n\n"
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
