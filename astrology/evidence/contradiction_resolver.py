from typing import Any


SUPPORT_DIRECTIONS = {"positive"}
PRESSURE_DIRECTIONS = {"mixed", "negative"}


def _by_system(ledger: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item.get("system"): item for item in ledger if item.get("system")}


def _direction(system_map: dict[str, dict[str, Any]], system: str) -> str:
    return system_map.get(system, {}).get("direction", "unavailable")


def _add_issue(issues: list[dict[str, Any]], systems: list[str], issue: str, instruction: str, severity: str = "medium") -> None:
    issues.append(
        {
            "systems": systems,
            "issue": issue,
            "instruction": instruction,
            "severity": severity,
        }
    )


def resolve_contradictions(evidence: dict[str, Any]) -> dict[str, Any]:
    ledger = evidence.get("evidence_ledger", [])
    systems = _by_system(ledger)
    issues: list[dict[str, Any]] = []

    parashari_direction = _direction(systems, "Parashari")
    vimshottari_direction = _direction(systems, "Vimshottari")
    jaimini_direction = _direction(systems, "Jaimini")
    yogini_direction = _direction(systems, "Yogini")
    varga_direction = _direction(systems, "Divisional")
    transit_direction = _direction(systems, "Transit")

    if vimshottari_direction in SUPPORT_DIRECTIONS and yogini_direction in PRESSURE_DIRECTIONS:
        _add_issue(
            issues,
            ["Vimshottari", "Yogini"],
            "Vimshottari timing is supportive while Yogini timing is mixed or pressured.",
            "Mention mixed timing and describe Yogini as a period-quality overlay, not a full denial.",
        )
    if jaimini_direction in SUPPORT_DIRECTIONS and parashari_direction in PRESSURE_DIRECTIONS:
        _add_issue(
            issues,
            ["Jaimini", "Parashari"],
            "Jaimini supports visibility or role potential while Parashari/D1 is mixed.",
            "State that Jaimini support is partial and needs D1/dasha confirmation.",
        )
    if parashari_direction in SUPPORT_DIRECTIONS and varga_direction in PRESSURE_DIRECTIONS:
        _add_issue(
            issues,
            ["Parashari", "Divisional"],
            "D1/Parashari support is stronger than divisional confirmation.",
            "Reduce confidence and explain that the divisional chart does not fully confirm the D1 promise.",
        )
    if vimshottari_direction in SUPPORT_DIRECTIONS and transit_direction in PRESSURE_DIRECTIONS:
        _add_issue(
            issues,
            ["Vimshottari", "Transit"],
            "Dasha timing is supportive but transit/timing windows are mixed.",
            "Describe the result as possible but delayed, pressured, or window-dependent.",
        )

    negative_rules = [
        rule
        for rule in evidence.get("triggered_rules", [])
        if rule.get("polarity") in {"negative", "mixed"}
    ]
    if negative_rules and not issues:
        _add_issue(
            issues,
            ["Rule Engine"],
            "Some triggered rules are mixed or negative.",
            "Mention pressure, caveats, and confidence limits even if the overall answer is positive.",
            "low",
        )

    return {
        "has_contradictions": bool(issues),
        "issues": issues,
        "summary": "No major cross-system contradictions found." if not issues else "Cross-system mixed signals require explicit explanation.",
    }
