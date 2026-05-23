from .completeness_checker import check_completeness
from .contradiction_checker import check_contradictions
from .evidence_checker import check_evidence
from .genericity_checker import check_genericity
from .specificity_checker import check_specificity
from .answer_validator import validate_astrology_answer


def validate_answer(answer: str, evidence: dict) -> dict:
    result = validate_astrology_answer(answer, evidence)
    issues = list(result.get("issues", []))
    issues.extend(check_genericity(answer))
    issues.extend(check_evidence(answer, evidence))
    issues.extend(check_completeness(answer, evidence))
    issues.extend(check_contradictions(answer, evidence))
    issues.extend(check_specificity(answer, evidence))
    deduped = list(dict.fromkeys(issues))
    if deduped:
        result["issues"] = deduped
        result["passed"] = False
        if not result.get("repair_instruction"):
            result["repair_instruction"] = "Regenerate the answer using calculated evidence and repair these issues: " + "; ".join(deduped)
    return result
