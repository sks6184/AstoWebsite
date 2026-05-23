from typing import Any


MAX_TERMS = 100


def _append_unique(terms: list[str], value: Any) -> None:
    if value in (None, "", [], {}):
        return
    text = str(value).strip()
    if text and text not in terms:
        terms.append(text)


def _trigger_terms(triggered_rules: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for rule in triggered_rules[:12]:
        _append_unique(terms, rule.get("rule_id"))
        _append_unique(terms, rule.get("system"))
        _append_unique(terms, rule.get("chart"))
        _append_unique(terms, rule.get("dasha"))
        for outcome in rule.get("outcomes", {}):
            _append_unique(terms, outcome.replace("_", " "))
    return terms


def _fact_terms(evidence: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    category = evidence.get("question", {}).get("category")
    _append_unique(terms, category)

    for item in evidence.get("evidence_ledger", []):
        _append_unique(terms, item.get("system"))
        _append_unique(terms, item.get("direction"))
        _append_unique(terms, item.get("strength"))
        for rule_id in item.get("supporting_rule_ids", [])[:3]:
            _append_unique(terms, rule_id)

    for issue in evidence.get("contradictions", {}).get("issues", [])[:3]:
        _append_unique(terms, issue.get("issue"))

    vimshottari = evidence.get("parashari_vimshottari", {})
    for field in ["current_mahadasha", "current_antardasha"]:
        period = vimshottari.get(field, {})
        _append_unique(terms, period.get("lord_name") or period.get("lord"))
        _append_unique(terms, field.replace("_", " "))

    yogini = evidence.get("yogini", {})
    _append_unique(terms, yogini.get("current_yogini_dasha", {}).get("yogini"))
    _append_unique(terms, yogini.get("current_yogini_subperiod", {}).get("yogini"))

    jaimini = evidence.get("jaimini", {})
    _append_unique(terms, "Atmakaraka")
    _append_unique(terms, jaimini.get("karakas", {}).get("atmakaraka", {}).get("name"))
    _append_unique(terms, "Amatyakaraka")
    _append_unique(terms, jaimini.get("karakas", {}).get("amatyakaraka", {}).get("name"))
    _append_unique(terms, "Arudha Lagna")
    _append_unique(terms, jaimini.get("padas", {}).get("arudha_lagna", {}).get("pada_sign"))
    _append_unique(terms, "Karakamsha")
    _append_unique(terms, jaimini.get("karakamsha", {}).get("sign"))

    for chart_key in ["d9", "d10", "d24", "d30"]:
        chart = evidence.get("chart_facts", {}).get("varga", {}).get("charts", {}).get(chart_key, {})
        if chart:
            _append_unique(terms, chart_key.upper())
            _append_unique(terms, chart.get("purpose"))

    future = evidence.get("transits", {}).get("future_timing", {})
    if future:
        _append_unique(terms, f"{future.get('scan_years')} year transit scan")
        start_year = str(future.get("start", ""))[:4]
        end_year = str(future.get("end", ""))[:4]
        _append_unique(terms, start_year)
        _append_unique(terms, end_year)
        _append_unique(terms, "future timing windows")
        _append_unique(terms, "dasha lord transit")
        _append_unique(terms, "Sarvashtakavarga support pressure")
        for window in future.get("windows", [])[:5]:
            _append_unique(terms, window.get("label"))
            _append_unique(terms, window.get("start", "")[:4])
            _append_unique(terms, window.get("end", "")[:4])
            active = window.get("active_dasha", {})
            _append_unique(terms, active.get("label"))
            for check in window.get("dasha_lord_transit_checks", [])[:2]:
                _append_unique(terms, check.get("lord_name"))
                _append_unique(terms, f"transit house {check.get('transit_house_from_lagna')}")
                _append_unique(terms, f"SAV {check.get('sarvashtakavarga_points')}")
    return terms


def build_rag_query(evidence: dict[str, Any]) -> str:
    terms: list[str] = []
    for term in _trigger_terms(evidence.get("triggered_rules", [])) + _fact_terms(evidence):
        _append_unique(terms, term)
        if len(terms) >= MAX_TERMS:
            break
    return " ".join(terms)


def build_rag_context_request(evidence: dict[str, Any]) -> dict[str, Any]:
    query = build_rag_query(evidence)
    return {
        "query": query,
        "status": "query_built" if query else "insufficient_evidence",
        "retrieved_sources": [],
        "query_policy": {
            "built_from": [
                "question category",
                "triggered rule IDs",
                "deterministic chart facts",
                "dasha facts",
                "Jaimini facts",
                "Yogini facts",
                "evidence ledger",
                "contradiction resolver",
                "future transit timing windows",
            ],
            "not_allowed": "generic raw-question-only retrieval",
        },
    }
