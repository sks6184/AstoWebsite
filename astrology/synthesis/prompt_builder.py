import json
from typing import Any

from .answer_schema import ANSWER_SCHEMA, REQUIRED_SECTIONS


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
"""


def _compact_rules(triggered_rules: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return [
        {
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
        for rule in triggered_rules[:limit]
    ]


def build_prompt_payload(evidence: dict[str, Any], rag_context: dict[str, Any] | None = None) -> dict[str, Any]:
    rag_context = rag_context or evidence.get("rag", {})
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
        "summary_scores": evidence.get("summary_scores", {}),
        "evidence_ledger": evidence.get("evidence_ledger", []),
        "contradictions": evidence.get("contradictions", {}),
        "triggered_rules": _compact_rules(evidence.get("triggered_rules", [])),
        "system_evidence": {
            "parashari": evidence.get("parashari", {}),
            "parashari_vimshottari": evidence.get("parashari_vimshottari", {}),
            "jaimini": evidence.get("jaimini", {}),
            "varga": {
                "status": evidence.get("varga", {}).get("status"),
                "score": evidence.get("varga", {}).get("score"),
                "d9_findings": evidence.get("varga", {}).get("d9_findings", []),
                "d10_findings": evidence.get("varga", {}).get("d10_findings", []),
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
