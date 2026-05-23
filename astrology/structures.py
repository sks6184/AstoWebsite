from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class QuestionContext:
    text: str
    category: str = "general"
    time_scope: dict[str, Any] = field(default_factory=dict)
    primary_divisional_chart: str = "d1"
    all_divisional_charts: list[str] = field(default_factory=lambda: ["d1"])


@dataclass
class SystemAssessment:
    findings: list[dict[str, Any]] = field(default_factory=list)
    score: int = 0
    status: str = "not_evaluated"


@dataclass
class PredictionEvidence:
    question: QuestionContext
    chart_facts: dict[str, Any] = field(default_factory=dict)
    parashari: dict[str, Any] = field(default_factory=dict)
    parashari_vimshottari: dict[str, Any] = field(default_factory=dict)
    jaimini: dict[str, Any] = field(default_factory=dict)
    varga: dict[str, Any] = field(default_factory=dict)
    yogini: dict[str, Any] = field(default_factory=dict)
    transits: dict[str, Any] = field(default_factory=dict)
    triggered_rules: list[dict[str, Any]] = field(default_factory=list)
    summary_scores: dict[str, int] = field(default_factory=dict)
    rag: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def career_score_template() -> dict[str, int]:
    return {
        "promotion_score": 0,
        "job_change_score": 0,
        "business_score": 0,
        "authority_score": 0,
        "income_growth_score": 0,
        "foreign_opportunity_score": 0,
        "risk_score": 0,
        "delay_score": 0,
    }


def business_score_template() -> dict[str, int]:
    return {
        "business_success_score": 0,
        "partnership_score": 0,
        "financial_risk_score": 0,
        "market_visibility_score": 0,
        "execution_pressure_score": 0,
        "long_term_sustainability_score": 0,
    }
