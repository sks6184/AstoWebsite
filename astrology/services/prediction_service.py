from datetime import date
from typing import Any

from chat.prediction_context import CATEGORY_RULES, build_location_verdict, build_natural_karaka_assessment, classify_question, detect_question_scope

from astrology.calculations.dasha_facts import build_dasha_facts
from astrology.calculations.parashari import build_parashari_facts
from astrology.calculations.transit_facts import build_transit_facts
from astrology.calculations.varga import build_chart_facts, build_varga_assessment
from astrology.calculations.d1_lagna_rules import evaluate_d1_lagna_roles
from astrology.calculations.d2_hora_rules import evaluate_d2_hora_rules
from astrology.calculations.d3_drekkana_rules import evaluate_d3_drekkana_rules
from astrology.calculations.d4_chaturthamsha_rules import evaluate_d4_chaturthamsha_rules
from astrology.calculations.d7_saptamsha_rules import evaluate_d7_saptamsha_rules
from astrology.calculations.d9_navamsha_rules import evaluate_d9_navamsha_rules
from astrology.calculations.varga_generic_rules import evaluate_generic_varga_rules
from astrology.evidence.confidence_scorer import build_confidence_summary
from astrology.evidence.contradiction_resolver import resolve_contradictions
from astrology.evidence.ledger import build_evidence_ledger
from astrology.rag.query_builder import build_rag_context_request
from astrology.rules.engine import run_rule_engine
from astrology.rules.scoring import aggregate_scores
from astrology.synthesis.prompt_builder import build_prompt_payload
from astrology.structures import PredictionEvidence, QuestionContext, business_score_template, career_score_template


BUSINESS_KEYWORDS = {
    "business",
    "startup",
    "venture",
    "client",
    "clients",
    "partnership",
    "partner",
    "contract",
    "entrepreneur",
}


TIMING_KEYWORDS = {
    "when",
    "which year",
    "which month",
    "best period",
    "right period",
    "promoted",
    "promotion",
    "job change",
    "job switch",
    "switch job",
}


def _engine_category(question: str) -> str:
    lowered = question.lower()
    if any(keyword in lowered for keyword in BUSINESS_KEYWORDS):
        return "business"
    return classify_question(question)


def _score_template(category: str) -> dict[str, int]:
    if category == "business":
        return business_score_template()
    return career_score_template()


def build_prediction_evidence(
    user_question: str,
    chart_data: dict[str, Any],
    target_date: date | None = None,
) -> dict[str, Any]:
    category = _engine_category(user_question)
    category_houses = CATEGORY_RULES.get(category, CATEGORY_RULES.get("job", {})).get("houses", [6, 2, 10, 11])
    if category == "business":
        category_houses = [2, 7, 10, 11]

    _div_charts = CATEGORY_RULES.get(category, {}).get("divisional_charts", ["d1"])
    _primary_chart = _div_charts[1] if len(_div_charts) > 1 else _div_charts[0]
    _secondary_chart = _div_charts[2] if len(_div_charts) > 2 else None

    scope = detect_question_scope(user_question, target_date)
    effective_start = scope["start"]
    effective_end = scope["end"]
    effective_months = scope.get("months") or max(
        1, round((effective_end - effective_start).days / 30)
    )

    chart_facts = build_chart_facts(chart_data, category, category_houses, _div_charts)
    dasha_facts = build_dasha_facts(chart_data, category, category_houses, effective_start)
    parashari_facts = build_parashari_facts(chart_data, category, category_houses, dasha_facts["parashari_vimshottari"])
    varga_assessment = build_varga_assessment(chart_facts, category, _primary_chart, _secondary_chart)
    transit_facts = build_transit_facts(
        chart_data,
        category_houses,
        dasha_facts,
        user_question,
        category,
        effective_start,
        future_months=effective_months,
        end_date=effective_end,
    )

    evidence = PredictionEvidence(
        question=QuestionContext(
            text=user_question,
            category=category,
            time_scope={
                "phrase": scope.get("phrase"),
                "start": effective_start.isoformat(),
                "end": effective_end.isoformat(),
                "months": effective_months,
                "is_fixed": scope.get("is_fixed", False),
                "instruction": scope.get("instruction", ""),
                "temporal_intent": scope.get("temporal_intent", "general"),
            },
            primary_divisional_chart=_primary_chart,
            all_divisional_charts=_div_charts,
        ),
        chart_facts=chart_facts,
        parashari=parashari_facts,
        parashari_vimshottari=dasha_facts["parashari_vimshottari"],
        jaimini=dasha_facts["jaimini"],
        varga=varga_assessment,
        yogini=dasha_facts["yogini"],
        transits=transit_facts,
        triggered_rules=[],
        summary_scores=_score_template(category),
        rag={
            "query": "",
            "retrieved_sources": [],
            "status": "pending_rule_engine_and_query_builder",
        },
        validation={
            "passed": False,
            "issues": [],
            "confidence": "pending",
        },
    )
    evidence_json = evidence.to_dict()
    rule_result = run_rule_engine(evidence_json, category)
    generic_varga_rules = evaluate_generic_varga_rules(evidence_json["chart_facts"], category)
    d1_lagna_rules = evaluate_d1_lagna_roles(evidence_json["chart_facts"], evidence_json, category)
    d2_rules = evaluate_d2_hora_rules(evidence_json["chart_facts"], category)
    d3_rules = evaluate_d3_drekkana_rules(evidence_json["chart_facts"], category)
    d4_rules = evaluate_d4_chaturthamsha_rules(evidence_json["chart_facts"], category)
    d7_rules = evaluate_d7_saptamsha_rules(evidence_json["chart_facts"], category)
    d9_rules = evaluate_d9_navamsha_rules(evidence_json["chart_facts"], category)
    all_triggered = rule_result["triggered_rules"] + generic_varga_rules + d1_lagna_rules + d2_rules + d3_rules + d4_rules + d7_rules + d9_rules
    evidence_json["triggered_rules"] = all_triggered
    evidence_json["summary_scores"] = aggregate_scores(all_triggered, category)
    evidence_json["evidence_ledger"] = build_evidence_ledger(evidence_json)
    evidence_json["contradictions"] = resolve_contradictions(evidence_json)
    evidence_json["rag"] = build_rag_context_request(evidence_json)
    evidence_json["synthesis"] = {
        "prompt_payload": build_prompt_payload(evidence_json),
        "status": "prompt_built",
    }
    evidence_json["rule_engine"] = {
        "rule_count": rule_result["rule_count"],
        "triggered_count": rule_result["triggered_count"],
        "load_errors": rule_result["load_errors"],
    }
    if rule_result["load_errors"]:
        evidence_json["validation"]["issues"].extend(rule_result["load_errors"])
    evidence_json["confidence_summary"] = build_confidence_summary(evidence_json)
    evidence_json["natural_karakas_assessment"] = build_natural_karaka_assessment(chart_data, category)
    if category == "property":
        jaimini_active = evidence_json.get("jaimini", {}).get("active_chara_dasha")
        evidence_json["location_verdict"] = build_location_verdict(
            user_question, chart_data, jaimini_data={"active_chara_dasha": jaimini_active} if jaimini_active else None
        )
    return evidence_json
