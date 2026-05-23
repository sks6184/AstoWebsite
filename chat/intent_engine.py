"""
Hybrid intent classifier: rules first, LLM fallback for ambiguous cases.

Returns:
    {
        'intent':     'periodic' | 'specific' | 'general',
        'horizon':    'weekly' | 'monthly' | 'annual' | None,
        'confidence': 'high' | 'low',
        'method':     'rules' | 'llm' | 'llm-cached' | 'llm-failed' | 'llm-skipped',
    }

intent = 'periodic'  → user wants a general horoscope/reading for a time period
intent = 'specific'  → user asks about a specific life event (job, marriage, money…)
intent = 'general'   → chart reading, explanation, or genuinely unclear
"""
import hashlib
import json
import logging
import re

from django.core.cache import cache

logger = logging.getLogger(__name__)


# ── Horizon vocabulary ────────────────────────────────────────────────────────

_MONTH_NAMES = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
}

_WEEKLY_WORDS  = {"week", "weekly", "hafte", "saptahik", "saptah", "7 din", "saat din"}
_MONTHLY_WORDS = {"month", "monthly", "mahina", "masik", "masic", "maasik"} | _MONTH_NAMES
_ANNUAL_WORDS  = {"year", "yearly", "annual", "saal", "varshik", "varsh"}

_MONTHS_RE = "|".join(sorted(_MONTH_NAMES, key=len, reverse=True))


# ── Periodic patterns ─────────────────────────────────────────────────────────
# Match questions that ask for a *general* horoscope/forecast for a period.

_PERIODIC_PATTERNS = [
    # "how will [this/next/that/month-name/year] be"
    rf"how will (this|next|that|the)?\s*({_MONTHS_RE}|week|month|year)\b.*\bbe\b",
    # "how [this/that/month] will be"
    rf"how (this|next|that|the)?\s*({_MONTHS_RE}|week|month|year)\b.*will be",
    # "how is [month/year] going to be"
    rf"how (is|are) (this|next|that|the)?\s*({_MONTHS_RE}|week|month|year)\b.*going to be",
    # "how will it be" / "how will that be" when a year is also present
    r"how will (it|that|this|things|everything|life)\b.{0,20}be",
    # "my future for [period]"
    r"my future for\b",
    # "tell me/my/us about/for [period or year]"
    rf"tell (me|my|us) (about |for )?(this|next|that|the|my)?\s*({_MONTHS_RE}|week|month|year|20\d{{2}})\b",
    # "what will [period] bring / look like"
    rf"what will (this|next|that|the)?\s*({_MONTHS_RE}|week|month|year)\b.*(bring|look like|be like)",
    # "what to expect / can I expect in [period]"
    rf"what (to expect|can i expect|should i expect).{{0,30}}\b({_MONTHS_RE}|week|month|year)\b",
    # "[period] overview / summary / forecast / reading / prediction"
    rf"\b({_MONTHS_RE}|week|month|year)\b.{{0,20}}\b(overview|summary|forecast|reading|prediction)\b",
    # "overview/summary/forecast of [period]"
    rf"\b(overview|summary|forecast|reading)\s+of\s+(this|next|the|that)?\s*({_MONTHS_RE}|week|month|year)\b",
    # "predict [my/the] [period]"
    r"predict (my|the)?\s*(week|month|year)\b",
    # "[period] kaisa/hoga (Hindi)"
    r"\b(hafte|mahine|saal|mahina)\b.{0,20}(kaisa|kaisi|kaise|hoga|hogi|rahega|rahegi)",
    # Explicit rashifal / horoscope trigger words
    r"\b(rashifal|raashifal|horoscope|bhavishya|bhavishyafal|saptahik|masik|maasik|varshik)\b",
    # "mera [period] kaisa hoga"
    r"\bmera\b.{0,20}\b(hafte|mahine|saal|week|month|year)\b",
    # Year by itself as the subject: "can you tell my 2027", "2026 kaisa rahega"
    r"\b(tell|show|give|explain|describe|batao|bata).{0,20}\b20\d{2}\b",
    r"\b20\d{2}\b.{0,30}\b(kaisa|kaisi|kaise|hoga|hogi|rahega|rahegi|how|like|be|going)\b",
]

# ── Specific-question patterns ────────────────────────────────────────────────
# Split into STRONG (first-person event questions → high confidence)
# and WEAK (ambiguous phrasing → low confidence, needs LLM).

_STRONG_SPECIFIC_PATTERNS = [
    r"\bwill i\b",
    r"\bwhen will i\b",
    r"\bwhen will my\b",
    r"\bshould i\b",
    r"\bcan i\b",
    r"\bam i going to\b",
    r"\bwhen (can|should|would) i\b",
    r"\bcould i\b",
    r"\bwould i\b",
    r"\bwill i ever\b",
    r"\bwill i get\b",
    r"\bwill i be\b",
]

_WEAK_SPECIFIC_PATTERNS = [
    r"\bis there (a chance|any chance|hope|possibility)\b",
    r"\bany chance\b",
    r"\bchances of\b",
    r"\bdo (you|u) see\b",
    r"\bdo (you|u) think\b",
    r"\bany possibility\b",
    r"\bwill (my|it|there|he|she)\b",
    r"\bis it possible\b",
    r"\bany scope\b",
]

_PERIODIC_RE       = [re.compile(p, re.IGNORECASE) for p in _PERIODIC_PATTERNS]
_STRONG_SPECIFIC_RE = [re.compile(p, re.IGNORECASE) for p in _STRONG_SPECIFIC_PATTERNS]
_WEAK_SPECIFIC_RE   = [re.compile(p, re.IGNORECASE) for p in _WEAK_SPECIFIC_PATTERNS]


# ── Horizon detection ─────────────────────────────────────────────────────────

_RASHIFAL_ALONE = re.compile(
    r"\b(rashifal|raashifal|horoscope|bhavishya|bhavishyafal|varshik|saalik)\b",
    re.IGNORECASE,
)


def _detect_horizon(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in _WEEKLY_WORDS):
        return "weekly"
    if any(w in lowered for w in _MONTHLY_WORDS):
        return "monthly"
    if any(w in lowered for w in _ANNUAL_WORDS):
        return "annual"
    # 4-digit year present → annual
    if re.search(r"\b20\d{2}\b", lowered):
        return "annual"
    # Bare rashifal / horoscope / varshik trigger → annual (Indian convention)
    if _RASHIFAL_ALONE.search(lowered):
        return "annual"
    return "monthly"  # safe default for periodic


# ── Rule classifier ───────────────────────────────────────────────────────────

def _rule_classify(question: str) -> dict:
    is_periodic      = any(p.search(question) for p in _PERIODIC_RE)
    is_strong_specific = any(p.search(question) for p in _STRONG_SPECIFIC_RE)
    is_weak_specific   = any(p.search(question) for p in _WEAK_SPECIFIC_RE)

    # Strong first-person event question + no periodic signal → high confidence specific
    if is_strong_specific and not is_periodic:
        return {"intent": "specific", "horizon": None, "confidence": "high", "method": "rules"}

    # Strong specific overrides periodic (e.g. "will I get a job this month?")
    if is_strong_specific and is_periodic:
        return {"intent": "specific", "horizon": None, "confidence": "high", "method": "rules"}

    # Clear periodic, no conflicting signals → high confidence
    if is_periodic and not is_strong_specific and not is_weak_specific:
        return {
            "intent": "periodic",
            "horizon": _detect_horizon(question),
            "confidence": "high",
            "method": "rules",
        }

    # Periodic wins over weak specific (e.g. "how will it be?" with a year present)
    if is_periodic and is_weak_specific:
        return {
            "intent": "periodic",
            "horizon": _detect_horizon(question),
            "confidence": "high",
            "method": "rules",
        }

    # Only weak specific, nothing else → genuinely ambiguous → LLM fallback
    if is_weak_specific:
        return {"intent": "general", "horizon": None, "confidence": "low", "method": "rules"}

    # Nothing matched
    return {"intent": "general", "horizon": None, "confidence": "low", "method": "rules"}


# ── LLM fallback classifier ───────────────────────────────────────────────────

_LLM_SYSTEM = (
    "You are an intent classifier for a Vedic astrology app. "
    "Classify the user's question into ONE of:\n"
    '- "periodic": user wants a general horoscope/forecast for a time period '
    '(e.g. "how will July be?", "tell me about 2026", "rashifal", "mera mahina kaisa hoga")\n'
    '- "specific": user asks about a specific life event or outcome '
    '(e.g. "will I get a job?", "when will I marry?", "should I invest?")\n'
    '- "general": chart reading request, explanation, or completely unclear\n\n'
    "If periodic, also identify horizon: \"weekly\", \"monthly\", or \"annual\".\n"
    'Respond with JSON only: {"intent": "...", "horizon": "..."|null}'
)


def _llm_classify(question: str) -> dict:
    from django.conf import settings
    from openai import OpenAI, OpenAIError

    cache_key = "intent-v1:" + hashlib.sha256(question.lower().strip().encode()).hexdigest()[:24]
    cached = cache.get(cache_key)
    if cached:
        return {**cached, "method": "llm-cached"}

    if not getattr(settings, "OPENAI_API_KEY", None):
        logger.debug("Intent LLM skipped — no OPENAI_API_KEY")
        return {"intent": "specific", "horizon": None, "confidence": "low", "method": "llm-skipped"}

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": question},
            ],
            max_tokens=40,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        intent = data.get("intent", "specific")
        horizon = data.get("horizon") or None
        result = {"intent": intent, "horizon": horizon, "confidence": "high", "method": "llm"}
        # Cache for 24 h — same question always has the same intent
        cache.set(cache_key, {"intent": intent, "horizon": horizon, "confidence": "high"}, 60 * 60 * 24)
        logger.info("Intent LLM: %r → intent=%s horizon=%s", question[:60], intent, horizon)
        return result
    except (OpenAIError, json.JSONDecodeError, Exception) as exc:
        logger.warning("Intent LLM classify failed: %s", exc)
        return {"intent": "specific", "horizon": None, "confidence": "low", "method": "llm-failed"}


# ── Public entry point ────────────────────────────────────────────────────────

def classify_intent(question: str) -> dict:
    """
    Classify the user's question intent.
    Rules first (fast, free). LLM fallback only when rules return low confidence.
    """
    result = _rule_classify(question)
    if result["confidence"] == "high":
        return result
    return _llm_classify(question)
