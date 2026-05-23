from typing import Any

from .loader import load_rules


def _values_at_path(payload: Any, path: str) -> list[Any]:
    values = [payload]
    for part in path.split("."):
        next_values = []
        for value in values:
            if isinstance(value, dict):
                if part in value:
                    next_values.append(value[part])
            elif isinstance(value, list):
                if part.isdigit():
                    index = int(part)
                    if 0 <= index < len(value):
                        next_values.append(value[index])
                else:
                    for item in value:
                        if isinstance(item, dict) and part in item:
                            next_values.append(item[part])
        values = next_values
        if not values:
            break
    return values


def _flatten(values: list[Any]) -> list[Any]:
    flattened = []
    for value in values:
        if isinstance(value, list):
            flattened.extend(value)
        else:
            flattened.append(value)
    return flattened


def _compare(value: Any, operator: str, expected: Any) -> bool:
    if operator == "exists":
        return value not in (None, "", [], {})
    if operator == "equals":
        return value == expected
    if operator == "not_equals":
        return value != expected
    if operator == "in":
        return value in expected
    if operator == "contains":
        return isinstance(value, list | tuple | set | str) and expected in value
    if operator == "contains_any":
        return isinstance(value, list | tuple | set) and any(item in value for item in expected)
    if operator == "gt":
        return value > expected
    if operator == "gte":
        return value >= expected
    if operator == "lt":
        return value < expected
    if operator == "lte":
        return value <= expected
    raise ValueError(f"Unsupported rule operator: {operator}")


def evaluate_condition(condition: dict[str, Any], evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    if "all" in condition:
        reasons = []
        for child in condition["all"]:
            passed, child_reasons = evaluate_condition(child, evidence)
            reasons.extend(child_reasons)
            if not passed:
                return False, reasons
        return True, reasons

    if "any" in condition:
        reasons = []
        for child in condition["any"]:
            passed, child_reasons = evaluate_condition(child, evidence)
            reasons.extend(child_reasons)
            if passed:
                return True, child_reasons
        return False, reasons

    path = condition.get("path")
    operator = condition.get("operator", "equals")
    expected = condition.get("value")
    values = _flatten(_values_at_path(evidence, path)) if path else []
    passed = any(_compare(value, operator, expected) for value in values)
    reason = f"{path} {operator} {expected}; observed={values[:6]}"
    return passed, [reason]


def _category_matches(rule: dict[str, Any], category: str) -> bool:
    rule_category = rule.get("category", "general")
    if isinstance(rule_category, list):
        return category in rule_category or "general" in rule_category
    return rule_category in {category, "general"}


def _triggered_rule(rule: dict[str, Any], match_reasons: list[str]) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "system": rule.get("system"),
        "chart": rule.get("chart", ""),
        "dasha": rule.get("dasha", ""),
        "category": rule.get("category"),
        "reason": rule.get("reason", match_reasons[0] if match_reasons else ""),
        "match_reasons": match_reasons,
        "interpretation": rule.get("interpretation", ""),
        "outcomes": rule.get("outcomes", {}),
        "weight": rule.get("weight", 0),
        "polarity": rule.get("polarity", "mixed"),
        "confidence": rule.get("confidence", "medium"),
        "source_book": rule.get("source_book", ""),
        "source_chapter": rule.get("source_chapter", ""),
        "source_page": rule.get("source_page", ""),
        "source_file": rule.get("source_file", ""),
    }


def run_rule_engine(
    evidence: dict[str, Any],
    category: str,
    include_skipped: bool = False,
) -> dict[str, Any]:
    load_result = load_rules()
    triggered = []
    skipped = []

    for rule in load_result.rules:
        if not _category_matches(rule, category):
            continue
        passed, reasons = evaluate_condition(rule.get("condition", {}), evidence)
        if passed:
            triggered.append(_triggered_rule(rule, reasons))
        elif include_skipped:
            skipped.append(
                {
                    "rule_id": rule.get("rule_id"),
                    "system": rule.get("system"),
                    "reasons": reasons,
                }
            )

    return {
        "triggered_rules": triggered,
        "skipped_rules": skipped,
        "load_errors": load_result.errors,
        "rule_count": len(load_result.rules),
        "triggered_count": len(triggered),
    }

