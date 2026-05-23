from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


RULES_DIR = Path(__file__).resolve().parent
RULE_FILES = [
    "parashari_rules.yaml",
    "jaimini_rules.yaml",
    "divisional_rules.yaml",
    "yogini_rules.yaml",
    "transit_rules.yaml",
]
REQUIRED_FIELDS = {
    "rule_id",
    "system",
    "category",
    "condition",
    "interpretation",
    "outcomes",
    "weight",
    "polarity",
    "confidence",
}


@dataclass(frozen=True)
class RuleLoadResult:
    rules: list[dict[str, Any]]
    errors: list[str]


def _load_yaml_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or []
    if isinstance(payload, dict):
        payload = payload.get("rules", [])
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a list of rules or a 'rules' list.")
    return payload


def _validate_rule(rule: dict[str, Any], source_file: str) -> list[str]:
    errors = []
    missing = sorted(REQUIRED_FIELDS - set(rule))
    if missing:
        errors.append(f"{source_file}:{rule.get('rule_id', '<missing rule_id>')} missing {missing}")
    if "outcomes" in rule and not isinstance(rule["outcomes"], dict):
        errors.append(f"{source_file}:{rule.get('rule_id', '<missing rule_id>')} outcomes must be a mapping")
    if "condition" in rule and not isinstance(rule["condition"], dict):
        errors.append(f"{source_file}:{rule.get('rule_id', '<missing rule_id>')} condition must be a mapping")
    return errors


def load_rules(rules_dir: Path | None = None, rule_files: list[str] | None = None) -> RuleLoadResult:
    rules_dir = rules_dir or RULES_DIR
    rule_files = rule_files or RULE_FILES
    rules: list[dict[str, Any]] = []
    errors: list[str] = []

    for file_name in rule_files:
        path = rules_dir / file_name
        try:
            loaded = _load_yaml_file(path)
        except Exception as exc:
            errors.append(f"{file_name}: failed to load: {exc}")
            continue

        for rule in loaded:
            if not isinstance(rule, dict):
                errors.append(f"{file_name}: rule entry must be a mapping")
                continue
            normalized = {**rule, "source_file": file_name}
            errors.extend(_validate_rule(normalized, file_name))
            rules.append(normalized)

    return RuleLoadResult(rules=rules, errors=errors)

