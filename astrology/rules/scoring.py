from typing import Any

from astrology.structures import business_score_template, career_score_template


def _base_scores(category: str) -> dict[str, int]:
    return business_score_template() if category == "business" else career_score_template()


def aggregate_scores(triggered_rules: list[dict[str, Any]], category: str) -> dict[str, int]:
    scores = _base_scores(category)
    for rule in triggered_rules:
        weight = int(rule.get("weight", 0) or 0)
        if weight <= 0:
            continue
        for outcome, value in rule.get("outcomes", {}).items():
            if outcome not in scores:
                scores[outcome] = 0
            scores[outcome] += int(value or 0) * weight
    return {key: max(0, min(100, value)) for key, value in scores.items()}
