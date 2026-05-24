import json
from collections import defaultdict
from typing import Any

from .answer_schema import ANSWER_SCHEMA, REQUIRED_SECTIONS
from chat.prediction_context import CATEGORY_RULES
from astrology.calculations.varga import VARGA_PURPOSES


SYSTEM_INSTRUCTIONS = """You are an astrology synthesis engine.

You must not invent chart facts.
You must not calculate planetary placements.
You must not calculate dashas.
You must not apply rules that are not provided.
You must use only:
1. calculated chart facts
2. calculated dasha facts
3. triggered deterministic rules
4. summary scores
5. evidence ledger and contradiction summary
6. retrieved RAG/classical context

If evidence is weak, say evidence is weak.
If systems disagree, clearly explain the disagreement.
For timing/business/startup questions, use only these visible sections: Jyotish Analysis, Remedy, and Practical Guidance.
Do not create subheadings for Direct Answer, Recommended Timing, Launch Strategy, Chart Basis, Dasha Basis,
Divisional Chart Basis, Jaimini Basis, Parashari Basis, Muhurta Basis, RAG / Classical Support,
Conflicting Signals, or Confidence Level. Weave those concepts into Jyotish Analysis as prose.
Do not claim Parashari/Jaimini/D10/Yogini support unless that evidence is present in input JSON.
Vimshottari is a Parashari dasha, not a separate system. Chara is a Jaimini dasha, not a separate system.
Do not call a transit unfavorable unless you name the actual planet, sign, house, Sarvashtakavarga points,
and the payload shows weak support.
If exact muhurta facts are missing, say the recommendation is preliminary.
For startup/business website questions require D10, D9, 2nd/7th/10th/11th house logic, Mercury,
Rahu for online/technology scaling, Jupiter for advisory/astrology wisdom, and Yogini/Vimshottari timing where available.
If the user asks "when should I start", provide a specific better date, better date window,
or a clear statement that exact date selection cannot be completed until muhurta calculations are available.
For timing answers, clearly separate these concepts inside Jyotish Analysis:
- Best Available Option in Checked Window
- Overall Auspiciousness
- Recommended Action
- Soft Launch vs Public Launch distinction
If the best checked date is still not truly auspicious, say so plainly. Use wording like:
"Best Available Option in Checked Window: May 15, 2026. Overall Recommendation: Postpone public launch beyond May 2026. Suggested Use: Soft launch / testing only."
For business money questions, directly answer:
- Can start: yes / no / soft start only
- Money potential now: strong / medium / weak
- Timing: now / later / delay likely
- Risk level
- Best practical action
Do not expose raw internal score language in the customer-facing answer.
Do not use vague phrases like "critical time" unless you explain what it is critical for.
Do not give generic spiritual or motivational advice.
Do not make absolute guarantees.
Give a practical conclusion.
Astrology is interpretive guidance, not professional, medical, legal, or financial advice.
You MUST discuss every chart listed in required_divisional_charts using the triggered rules provided for that chart.
"""


def _format_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule.get("rule_id"),
        "system": rule.get("system"),
        "chart": rule.get("chart"),
        "dasha": rule.get("dasha"),
        "reason": rule.get("reason"),
        "interpretation": rule.get("interpretation"),
        "outcomes": rule.get("outcomes"),
        "polarity": rule.get("polarity"),
        "confidence": rule.get("confidence"),
        "source_book": rule.get("source_book"),
        "source_chapter": rule.get("source_chapter"),
        "source_page": rule.get("source_page"),
    }


def _select_rules(
    triggered_rules: list[dict[str, Any]],
    category_charts: list[str],
    per_chart_min: int = 4,
    total_limit: int = 40,
) -> list[dict[str, Any]]:
    """Guarantee representation for every divisional chart in the category, then fill by weight."""
    by_chart: dict[str, list] = defaultdict(list)
    for rule in triggered_rules:
        chart_key = (rule.get("chart") or "other").upper()
        by_chart[chart_key].append(rule)

    for chart_key in by_chart:
        by_chart[chart_key].sort(key=lambda r: r.get("weight", 0), reverse=True)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    # Guaranteed slots for each divisional chart in the category (skip d1 — always implied)
    priority_charts = [c for c in category_charts if c != "d1"]
    for chart in priority_charts:
        for rule in by_chart.get(chart.upper(), [])[:per_chart_min]:
            rid = rule.get("rule_id", "")
            if rid not in selected_ids:
                selected.append(rule)
                selected_ids.add(rid)

    # Fill remaining slots with the highest-weight rules from any system
    remaining = sorted(
        [r for r in triggered_rules if r.get("rule_id", "") not in selected_ids],
        key=lambda r: r.get("weight", 0),
        reverse=True,
    )
    for rule in remaining:
        if len(selected) >= total_limit:
            break
        rid = rule.get("rule_id", "")
        if rid not in selected_ids:
            selected.append(rule)
            selected_ids.add(rid)

    return [_format_rule(r) for r in selected]


def _required_divisional_charts(category: str) -> list[dict[str, str]]:
    """Return the non-D1 divisional charts required for this category, with their purpose."""
    charts = CATEGORY_RULES.get(category, {}).get("divisional_charts", [])
    return [
        {"chart": c.upper(), "purpose": VARGA_PURPOSES.get(c, "")}
        for c in charts
        if c != "d1"
    ]


def build_prompt_payload(evidence: dict[str, Any], rag_context: dict[str, Any] | None = None) -> dict[str, Any]:
    rag_context = rag_context or evidence.get("rag", {})
    category = (evidence.get("question") or {}).get("category", "")
    category_charts = CATEGORY_RULES.get(category, {}).get("divisional_charts", ["d1"])

    return {
        "role": "astrology_synthesis_payload",
        "answer_schema": ANSWER_SCHEMA,
        "strict_rules": {
            "no_invented_facts": True,
            "no_llm_calculation": True,
            "only_use_triggered_rules": True,
            "must_explain_conflicts": True,
            "must_state_confidence_reason": True,
        },
        "question": evidence.get("question", {}),
        "required_divisional_charts": _required_divisional_charts(category),
        "summary_scores": evidence.get("summary_scores", {}),
        "evidence_ledger": evidence.get("evidence_ledger", []),
        "contradictions": evidence.get("contradictions", {}),
        "triggered_rules": _select_rules(evidence.get("triggered_rules", []), category_charts),
        "system_evidence": {
            "parashari": evidence.get("parashari", {}),
            "parashari_vimshottari": evidence.get("parashari_vimshottari", {}),
            "jaimini": evidence.get("jaimini", {}),
            "varga": {
                "status": evidence.get("varga", {}).get("status"),
                "score": evidence.get("varga", {}).get("score"),
                "primary_chart": evidence.get("varga", {}).get("primary_chart"),
                "secondary_chart": evidence.get("varga", {}).get("secondary_chart"),
                "primary_findings": evidence.get("varga", {}).get("primary_findings", []),
                "secondary_findings": evidence.get("varga", {}).get("secondary_findings", []),
                "cross_chart_confirmations": evidence.get("varga", {}).get("cross_chart_confirmations", []),
            },
            "yogini": evidence.get("yogini", {}),
            "transits": evidence.get("transits", {}),
        },
        "chart_facts": {
            "ascendant": evidence.get("chart_facts", {}).get("ascendant", {}),
            "varga": evidence.get("chart_facts", {}).get("varga", {}),
        },
        "rag_context": rag_context,
        "required_output_sections": REQUIRED_SECTIONS,
    }


def build_prompt_messages(evidence: dict[str, Any], rag_context: dict[str, Any] | None = None) -> dict[str, str]:
    payload = build_prompt_payload(evidence, rag_context)
    return {
        "system": SYSTEM_INSTRUCTIONS,
        "user": json.dumps(payload, ensure_ascii=False, indent=2, default=str),
    }
