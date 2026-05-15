import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from openai import OpenAI, OpenAIError

from chat.prediction_context import CATEGORY_RULES

from .jaimini_confirmation import build_jaimini_confirmation
from .models import MonthlyPrediction
from .remedies import remedies_for_dasha
from .transit_priority import build_transit_priority_context
from .vedic_utils import (
    PLANET_NAMES,
    get_owned_houses,
    get_planet,
    house_from_sign,
    transit_context_for_lord,
    transit_longitude,
    SIGN_NAMES,
)


PREDICTION_VERSION = "v14-jaimini-confirmation"
SLOW_TRIGGER_PLANETS = ["Ju", "Sa", "Ra", "Ke"]
REPORT_TRANSIT_PLANETS = ["Su", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
SECONDARY_TRIGGER_CAP = 24


def month_start(value):
    return date(value.year, value.month, 1)


def add_months(value, months):
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def month_range(start_month, months=13):
    return [add_months(start_month, offset) for offset in range(months)]


def _parse_date(value):
    return datetime.fromisoformat(value).date()


def _period_for_month(periods, target_month):
    if not periods:
        return {}
    month_end = add_months(target_month, 1)
    for period in periods:
        start = _parse_date(period["start"])
        end = _parse_date(period["end"])
        if start < month_end and end >= target_month:
            return period
    return {}


def _age_on(chart, target_month):
    years = target_month.year - chart.birth_date.year
    if (target_month.month, target_month.day) < (chart.birth_date.month, chart.birth_date.day):
        years -= 1
    return years


def yearly_topics_for_chart(chart, start_month):
    topics = ["health"]
    topics.append("education" if _age_on(chart, start_month) < 24 else "career")
    topics.append("marriage")
    return topics


def _topic_label(topic):
    return {
        "career": "Job and Career",
        "education": "Study and Education",
        "health": "Health",
        "marriage": "Marriage and Relationships",
    }.get(topic, topic.replace("_", " ").title())


def _bullet_prefix(topic):
    return {
        "health": "Health",
        "career": "Career",
        "education": "Education",
        "marriage": "Marriage",
    }.get(topic, topic.replace("_", " ").title())


def _with_topic_prefix(topic, bullet):
    prefix = _bullet_prefix(topic)
    bullet = str(bullet).strip()
    if not bullet:
        return ""
    for label in [_topic_label(topic), _bullet_prefix(topic)]:
        marker = f"{label}:"
        if bullet.lower().startswith(marker.lower()) and label != prefix:
            bullet = bullet[len(marker):].strip()
    if bullet.lower().startswith(f"{prefix.lower()}:"):
        rest = bullet[len(prefix) + 1 :].strip()
        topic_label_marker = f"{_topic_label(topic)}:"
        if rest.lower().startswith(topic_label_marker.lower()):
            rest = rest[len(topic_label_marker):].strip()
        return f"{prefix}: {rest}" if rest else f"{prefix}:"
    return f"{prefix}: {bullet}"


def _score_lord(chart_data, lord, topic, month):
    if not lord:
        return 0, [], {}

    houses = CATEGORY_RULES.get(topic, {}).get("houses", [])
    planet = get_planet(chart_data, lord)
    transit = transit_context_for_lord(
        chart_data,
        lord,
        datetime(month.year, month.month, 15, tzinfo=ZoneInfo("UTC")),
    )
    owned = get_owned_houses(chart_data, lord)
    score = 0
    reasons = []

    owned_matches = [house for house in owned if house in houses]
    if owned_matches:
        score += 18
        reasons.append(f"{PLANET_NAMES.get(lord, lord)} owns relevant house(s) {owned_matches}.")

    if planet.get("house") in houses:
        score += 14
        reasons.append(f"{PLANET_NAMES.get(lord, lord)} is placed in relevant house {planet.get('house')}.")

    if transit.get("transit_house_from_lagna") in houses:
        if lord == "Mo":
            reasons.append(
                "Moon is the active dasha lord; monthly interpretation uses natal Moon placement rather than Moon's fast transit."
            )
        else:
            score += 20
            reasons.append(
                f"{PLANET_NAMES.get(lord, lord)} transits relevant house {transit.get('transit_house_from_lagna')}."
            )

    sav = transit.get("sarvashtakavarga_points", 0)
    if lord != "Mo":
        if sav > 28:
            score += 16
            reasons.append(f"Transit house has strong Sarvashtakavarga support ({sav}).")
        elif sav >= 25:
            score += 8
            reasons.append(f"Transit house has moderate Sarvashtakavarga support ({sav}).")

    return score, reasons, transit


def _dasha_lord_detail(chart_data, lord, role, topic, month):
    planet = get_planet(chart_data, lord)
    transit = transit_context_for_lord(
        chart_data,
        lord,
        datetime(month.year, month.month, 15, tzinfo=ZoneInfo("UTC")),
    )
    topic_houses = CATEGORY_RULES.get(topic, {}).get("houses", [])
    return {
        "role": role,
        "lord": lord,
        "lord_name": PLANET_NAMES.get(lord, lord),
        "natal": {
            "house": planet.get("house"),
            "sign": planet.get("sign"),
            "sign_number": planet.get("sign_number"),
            "degree": planet.get("degree"),
            "nakshatra": planet.get("nakshatra"),
            "owned_houses": get_owned_houses(chart_data, lord),
        },
        "transit": {
            "house": transit.get("transit_house_from_lagna"),
            "sign": transit.get("transit_sign"),
            "sign_number": transit.get("transit_sign_number"),
            "sarvashtakavarga_points": transit.get("sarvashtakavarga_points"),
            "is_topic_house": transit.get("transit_house_from_lagna") in topic_houses,
            "used_for_monthly_scoring": lord != "Mo",
        },
        "note": (
            "Moon moves quickly, so this report uses natal Moon placement for Moon dasha interpretation."
            if lord == "Mo"
            else ""
        ),
    }


def _planet_transit_summary(chart_data, planet_code, month):
    start_dt = datetime(month.year, month.month, 1, tzinfo=ZoneInfo("UTC"))
    end_month = add_months(month, 1)
    end_dt = datetime.combine(end_month - timedelta(days=1), datetime.min.time(), tzinfo=ZoneInfo("UTC"))
    start_sign_number = int(transit_longitude(planet_code, start_dt) // 30) + 1
    end_sign_number = int(transit_longitude(planet_code, end_dt) // 30) + 1
    start_house = house_from_sign(chart_data, start_sign_number)
    end_house = house_from_sign(chart_data, end_sign_number)
    return {
        "planet": planet_code,
        "planet_name": PLANET_NAMES.get(planet_code, planet_code),
        "start_sign": SIGN_NAMES.get(start_sign_number),
        "start_house": start_house,
        "end_sign": SIGN_NAMES.get(end_sign_number),
        "end_house": end_house,
        "changed_sign": start_sign_number != end_sign_number,
    }


def _monthly_transit_summary(chart_data, month):
    return [
        _planet_transit_summary(chart_data, planet_code, month)
        for planet_code in REPORT_TRANSIT_PLANETS
    ]


def _secondary_transit_triggers(chart_data, dasha_lords, month):
    triggers = []
    target_lords = [
        (lord, get_planet(chart_data, lord))
        for lord in dict.fromkeys(dasha_lords)
        if lord and get_planet(chart_data, lord)
    ]

    for transit_planet in REPORT_TRANSIT_PLANETS:
        transit = transit_context_for_lord(
            chart_data,
            transit_planet,
            datetime(month.year, month.month, 15, tzinfo=ZoneInfo("UTC")),
        )
        transit_house = transit.get("transit_house_from_lagna")
        transit_sign_number = transit.get("transit_sign_number")

        for target_lord, natal_planet in target_lords:
            target_name = PLANET_NAMES.get(target_lord, target_lord)
            transit_name = PLANET_NAMES.get(transit_planet, transit_planet)
            owned_houses = get_owned_houses(chart_data, target_lord)

            if (
                transit_planet in SLOW_TRIGGER_PLANETS
                and transit_sign_number
                and transit_sign_number == natal_planet.get("sign_number")
            ):
                triggers.append(
                    {
                        "transit_planet": transit_planet,
                        "transit_planet_name": transit_name,
                        "target_lord": target_lord,
                        "target_lord_name": target_name,
                        "trigger": "crossing_dasha_lord_sign",
                        "weight": 8,
                        "transit_house": transit_house,
                        "transit_sign": transit.get("transit_sign"),
                        "reason": f"{transit_name} transits over natal {target_name}'s sign.",
                    }
                )

            if (
                transit_planet in SLOW_TRIGGER_PLANETS
                and transit_house
                and transit_house == natal_planet.get("house")
            ):
                triggers.append(
                    {
                        "transit_planet": transit_planet,
                        "transit_planet_name": transit_name,
                        "target_lord": target_lord,
                        "target_lord_name": target_name,
                        "trigger": "crossing_dasha_lord_house",
                        "weight": 7,
                        "transit_house": transit_house,
                        "transit_sign": transit.get("transit_sign"),
                        "reason": f"{transit_name} transits through natal {target_name}'s house.",
                    }
                )

            if transit_house in owned_houses:
                triggers.append(
                    {
                        "transit_planet": transit_planet,
                        "transit_planet_name": transit_name,
                        "target_lord": target_lord,
                        "target_lord_name": target_name,
                        "trigger": "crossing_dasha_lord_owned_house",
                        "weight": 5 if transit_planet not in SLOW_TRIGGER_PLANETS else 6,
                        "transit_house": transit_house,
                        "transit_sign": transit.get("transit_sign"),
                        "reason": f"{transit_name} transits a house owned by natal {target_name}.",
                    }
                )

    return triggers


def _tone(topic, score):
    if topic == "health":
        if score >= 70:
            return "needs attention"
        if score >= 45:
            return "is active"
        if score >= 25:
            return "is mixed"
        return "looks steady"

    if score >= 70:
        return "looks strong"
    if score >= 45:
        return "looks supportive"
    if score >= 25:
        return "looks mixed"
    return "looks steady"


def _monthly_context(chart, topic, month, answer_language="English"):
    chart_data = chart.chart_data or {}
    vimshottari = chart_data.get("dashas", {}).get("vimshottari", {})
    mahadasha = _period_for_month(vimshottari.get("periods", []), month)
    antardasha = _period_for_month(mahadasha.get("antardashas", []), month)
    lords = [lord for lord in [mahadasha.get("lord"), antardasha.get("lord")] if lord]
    total_score = 10
    reasons = []
    transit_checks = []
    dasha_lord_details = []

    for role, lord in [("Mahadasha lord", mahadasha.get("lord")), ("Antardasha lord", antardasha.get("lord"))]:
        if lord:
            dasha_lord_details.append(_dasha_lord_detail(chart_data, lord, role, topic, month))

    for lord in dict.fromkeys(lords):
        score, lord_reasons, transit = _score_lord(chart_data, lord, topic, month)
        total_score += score
        reasons.extend(lord_reasons)
        transit_checks.append(
            {
                "lord": lord,
                "lord_name": PLANET_NAMES.get(lord, lord),
                "transit_house_from_lagna": transit.get("transit_house_from_lagna"),
                "transit_sign": transit.get("transit_sign"),
                "sarvashtakavarga_points": transit.get("sarvashtakavarga_points"),
                "owned_houses": transit.get("owned_houses", []),
                "natal_placed_house": transit.get("natal_placed_house"),
            }
        )

    secondary_triggers = _secondary_transit_triggers(chart_data, lords, month)
    transit_priority = build_transit_priority_context(
        chart_data,
        CATEGORY_RULES.get(topic, {}).get("houses", []),
        month,
        mahadasha_lord=mahadasha.get("lord"),
        antardasha_lord=antardasha.get("lord"),
        horizon="monthly",
        cap=10,
    )
    jaimini_confirmation = build_jaimini_confirmation(
        chart_data,
        topic,
        CATEGORY_RULES.get(topic, {}).get("houses", []),
        month,
    )
    secondary_score = min(
        sum(trigger["weight"] for trigger in secondary_triggers)
        + sum(max(event["score"], 0) for event in transit_priority["events"][:4]) // 4,
        SECONDARY_TRIGGER_CAP,
    )
    if secondary_score:
        total_score += secondary_score
        reasons.extend(trigger["reason"] for trigger in secondary_triggers[:3])

    score = min(total_score, 100)
    return {
        "topic": topic,
        "topic_label": _topic_label(topic),
        "month": month.isoformat(),
        "score": score,
        "tone": _tone(topic, score),
        "age": _age_on(chart, month),
        "marital_status": chart.marital_status,
        "gender": chart.gender,
        "active_dasha": {
            "mahadasha": mahadasha.get("lord"),
            "antardasha": antardasha.get("lord"),
            "label": "/".join(lords),
        },
        "remedies": remedies_for_dasha(mahadasha.get("lord"), antardasha.get("lord"), answer_language),
        "transit_checks": transit_checks,
        "dasha_lord_details": dasha_lord_details,
        "monthly_transits": _monthly_transit_summary(chart_data, month),
        "transit_priority": transit_priority,
        "jaimini_confirmation": jaimini_confirmation,
        "secondary_transit_triggers": secondary_triggers[:8],
        "secondary_transit_score": secondary_score,
        "reasons": reasons[:6],
        "prediction_bullets": _prediction_bullets(topic, score, reasons, chart.marital_status),
    }


def _prediction_bullets(topic, score, reasons, marital_status):
    bullets = []

    if topic == "health":
        if score >= 70:
            bullets.append("Health houses are strongly activated, so this month needs extra care rather than overconfidence.")
        elif score >= 45:
            bullets.append("Health matters are active this month; steady routines and timely attention are important.")
        elif score >= 25:
            bullets.append("Health indications are mixed; avoid neglect and keep routines consistent.")
        else:
            bullets.append("Health looks comparatively steady; keep basic routines stable.")
    elif topic == "career":
        if score >= 70:
            bullets.append("Career is strongly supported for visible progress, execution, and practical outcomes.")
        elif score >= 45:
            bullets.append("Career is supportive, but results may come through steady effort rather than sudden change.")
        elif score >= 25:
            bullets.append("Career is mixed; use the helpful openings carefully and avoid forcing outcomes.")
        else:
            bullets.append("Career looks steady; use this month for planning, preparation, and disciplined follow-through.")
    elif topic == "education":
        if score >= 70:
            bullets.append("Study and education are strongly supported for focus, preparation, and progress.")
        elif score >= 45:
            bullets.append("Study and education are supportive, especially with consistent effort.")
        elif score >= 25:
            bullets.append("Study indications are mixed; avoid distraction and keep a disciplined schedule.")
        else:
            bullets.append("Study looks steady; use the month for revision and foundation-building.")
    elif topic == "marriage":
        if score >= 70:
            bullets.append("Relationship matters are strongly activated, so important developments or decisions may come into focus.")
        elif score >= 45:
            bullets.append("Relationship matters are supportive, but they still need patience and clear communication.")
        elif score >= 25:
            bullets.append("Relationship indications are mixed; avoid assumptions and handle sensitive topics carefully.")
        else:
            bullets.append("Relationship matters look steady; small consistent efforts matter more than dramatic moves.")
    else:
        if score >= 70:
            bullets.append("This area is strongly activated and can show visible progress.")
        elif score >= 45:
            bullets.append("This area is supportive, but results may come through steady effort.")
        elif score >= 25:
            bullets.append("This area is mixed; use the supportive factors carefully.")
        else:
            bullets.append("This area looks steady and is better for maintenance and planning.")

    if topic == "marriage" and marital_status == "married":
        bullets.append("For married life, prioritize patience, communication, and shared decisions.")
    elif topic == "marriage":
        bullets.append("For relationships, watch gradual developments and avoid treating one month as a final promise.")
    elif topic == "health":
        bullets.append("For health, keep routines stable and respond early to stress, sleep, digestion, or recurring symptoms.")
    elif topic == "education":
        bullets.append("For study, this month supports disciplined preparation, revision, and skill-building.")
    else:
        bullets.append("For career, use the month for execution, networking, applications, client work, or practical planning.")
    return [_with_topic_prefix(topic, bullet) for bullet in bullets]


def _prediction_text(context):
    month_name = datetime.fromisoformat(context["month"]).strftime("%B %Y")
    dasha = context["active_dasha"]["label"] or "available chart periods"
    topic_label = context["topic_label"]
    tone = context["tone"]

    return (
        f"{month_name}: {topic_label} {tone}. "
        f"Active dasha reference: {dasha}."
    )


def _deterministic_prediction_payload(month, contexts):
    return {
        "month": month.strftime("%B %Y"),
        "instruction": (
            "Write concise, non-repetitive Vedic astrology predictions from the supplied facts only. "
            "Do not invent placements, dates, dashas, houses, signs, or transits. "
            "Do not copy template-like wording. Vary phrasing by month and topic. "
            "For health, strong 6th/8th/12th activation means caution or attention, not good health. "
            "Return JSON only. Each topic value must be an object with a bullets array of 2-4 practical strings. "
            "Each bullet must start with the visible topic label, like 'Health: ', 'Career: ', 'Marriage: ', or 'Education: '."
        ),
        "topics": {
            context["topic"]: {
                "topic_label": context["topic_label"],
                "tone": context["tone"],
                "score": context["score"],
                "active_dasha": context["active_dasha"],
                "dasha_lord_details": context["dasha_lord_details"],
                "secondary_transit_triggers": context["secondary_transit_triggers"],
                "monthly_transits": context["monthly_transits"],
                "topic_relevant_facts": context["reasons"],
                "remedies": context["remedies"],
            }
            for context in contexts
        },
    }


def _extract_json_object(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object returned.")
    return json.loads(text[start : end + 1])


def _llm_month_predictions(month, contexts, answer_language="English"):
    if not settings.OPENAI_API_KEY:
        return {}

    payload = _deterministic_prediction_payload(month, contexts)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = json.dumps(payload, ensure_ascii=False, default=str)
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL or "gpt-4o-mini",
            instructions=(
                "You are AstroGPT, a careful Vedic astrologer writing premium report bullets. "
                "Keep the tone like a traditional Vedic astrologer: calm, precise, respectful, practical, "
                "and rooted in dasha, bhava, transit, and Ashtakavarga reasoning. "
                "Use terms such as Mahadasha, Antardasha, Lagna, bhava, transit, and Sarvashtakavarga naturally, "
                "but keep the wording understandable for a normal user. "
                "Use only the JSON facts supplied by the app. "
                "Do not calculate or invent planetary positions, dashas, houses, signs, dates, aspects, yogas, or transits. "
                "Do not sound generic, overly modern, or motivational. "
                "For health, be cautious and practical; do not create fear and do not give medical advice. "
                "For career, speak in terms of effort, responsibility, opportunity, and timing. "
                "For relationships, speak with maturity and avoid absolute promises. "
                "Do not include mantras, remedies, lamp rituals, or Hanuman Chalisa in these prediction bullets; "
                "the app renders remedies separately under a Remedies section. "
                f"Answer language: {answer_language}. "
                "Return strict JSON shaped as {\"topic\": {\"bullets\": [\"Topic: bullet\", \"Topic: bullet\"]}}."
            ),
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        )
        parsed = _extract_json_object(response.output_text)
    except (OpenAIError, ValueError, json.JSONDecodeError):
        return {}

    cleaned = {}
    for context in contexts:
        topic = context["topic"]
        topic_payload = parsed.get(topic, {})
        bullets = topic_payload.get("bullets", []) if isinstance(topic_payload, dict) else topic_payload
        if isinstance(bullets, str):
            bullets = [bullets]
        if isinstance(bullets, list):
            cleaned[topic] = [
                _with_topic_prefix(topic, bullet)
                for bullet in bullets
                if str(bullet).strip()
            ][:4]
    return cleaned


def build_monthly_prediction(chart, topic, month, answer_language="English"):
    context = _monthly_context(chart, topic, month, answer_language)
    return MonthlyPrediction(
        chart=chart,
        topic=topic,
        month=month,
        prediction_version=PREDICTION_VERSION,
        answer_language=answer_language,
        computed_context=context,
        prediction_text=_prediction_text(context),
        model_name="deterministic-v7-fallback",
    )


def _build_monthly_predictions(chart, topics, month, answer_language="English"):
    contexts = [_monthly_context(chart, topic, month, answer_language) for topic in topics]
    llm_bullets = _llm_month_predictions(month, contexts, answer_language)
    predictions = []

    for context in contexts:
        topic = context["topic"]
        bullets = llm_bullets.get(topic)
        model_name = settings.OPENAI_MODEL or "gpt-4o-mini"
        if bullets:
            context["prediction_bullets"] = bullets
            prediction_text = f"{month.strftime('%B %Y')}: {context['topic_label']} {context['tone']}."
        else:
            prediction_text = _prediction_text(context)
            model_name = "deterministic-v7-fallback"

        predictions.append(
            MonthlyPrediction(
                chart=chart,
                topic=topic,
                month=month,
                prediction_version=PREDICTION_VERSION,
                answer_language=answer_language,
                computed_context=context,
                prediction_text=prediction_text,
                model_name=model_name,
            )
        )
    return predictions


def get_or_create_yearly_predictions(chart, start_date=None, answer_language="English"):
    start_month = month_start(start_date or timezone.localdate())
    months = month_range(start_month, 13)
    topics = yearly_topics_for_chart(chart, start_month)
    existing = MonthlyPrediction.objects.filter(
        chart=chart,
        prediction_version=PREDICTION_VERSION,
        answer_language=answer_language,
        month__in=months,
        topic__in=topics,
    )
    existing_by_key = {(prediction.month, prediction.topic): prediction for prediction in existing}
    created = []

    for month in months:
        missing_topics = [topic for topic in topics if (month, topic) not in existing_by_key]
        if missing_topics:
            for prediction in _build_monthly_predictions(chart, missing_topics, month, answer_language):
                prediction.save()
                existing_by_key[(month, prediction.topic)] = prediction
                created.append(prediction)

    predictions = [existing_by_key[(month, topic)] for month in months for topic in topics]
    return {
        "start_month": start_month,
        "end_month": months[-1],
        "topics": topics,
        "predictions": predictions,
        "created_count": len(created),
        "reused_count": len(predictions) - len(created),
        "version": PREDICTION_VERSION,
    }
