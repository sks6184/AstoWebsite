TIMING_SECTION_TERMS = [
    "jyotish analysis",
    "practical guidance",
]

GENERAL_SECTION_TERMS = [
    "jyotish analysis",
    "practical guidance",
]


def is_timing_question(question: str) -> bool:
    lowered = (question or "").lower()
    return any(
        phrase in lowered
        for phrase in [
            "when should",
            "when will",
            "best time",
            "which date",
            "good date",
            "auspicious time",
            "launch",
            "start",
        ]
    )


def is_business_question(question: str) -> bool:
    lowered = (question or "").lower()
    return any(
        phrase in lowered
        for phrase in [
            "business",
            "startup",
            "website",
            "launch",
            "market",
            "client",
            "part-time",
            "part time",
        ]
    )


def missing_sections(answer: str, question: str) -> list[str]:
    lowered = (answer or "").lower()
    required = TIMING_SECTION_TERMS if is_timing_question(question) or is_business_question(question) else GENERAL_SECTION_TERMS
    missing = []
    for section in required:
        alternatives = [section]
        if section == "best timing":
            alternatives.append("recommended timing")
        if section == "recommended window":
            alternatives.append("recommended timing")
        if section == "rag / classical support":
            alternatives.append("classical support")
        if not any(alternative in lowered for alternative in alternatives):
            missing.append(section)
    return missing
