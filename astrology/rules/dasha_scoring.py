"""Helpers for validating and summarizing dasha rule evidence."""

from typing import Any


DASHA_SYSTEM_MARKERS = ("vimshottari", "parashari/vimshottari")
DASHA_NAMES = ("vimshottari", "mahadasha", "antardasha", "dasha")


def is_vimshottari_rule(rule: dict[str, Any]) -> bool:
    system = str(rule.get("system") or "").lower()
    dasha = str(rule.get("dasha") or "").lower()
    rule_id = str(rule.get("rule_id") or "").lower()
    return (
        any(marker in system for marker in DASHA_SYSTEM_MARKERS)
        or "vimshottari" in dasha
        or rule_id.startswith("vimshottari")
    )


def triggered_vimshottari_rules(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        rule
        for rule in evidence.get("triggered_rules", [])
        if is_vimshottari_rule(rule)
    ]


def dasha_polarity_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    rules = triggered_vimshottari_rules(evidence)
    positive = [rule for rule in rules if rule.get("polarity") == "positive" and int(rule.get("weight") or 0) > 0]
    mixed = [rule for rule in rules if rule.get("polarity") == "mixed" and int(rule.get("weight") or 0) > 0]
    negative = [rule for rule in rules if rule.get("polarity") == "negative" and int(rule.get("weight") or 0) > 0]

    return {
        "has_positive": bool(positive),
        "has_pressure": bool(mixed or negative),
        "has_negative": bool(negative),
        "positive_rule_ids": [rule.get("rule_id") for rule in positive],
        "pressure_rule_ids": [rule.get("rule_id") for rule in mixed + negative],
        "negative_rule_ids": [rule.get("rule_id") for rule in negative],
        "rule_count": len(rules),
    }

