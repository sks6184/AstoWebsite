GENERIC_PHRASES = [
    "work hard",
    "stay positive",
    "believe in yourself",
    "everything happens for a reason",
    "good things will happen",
    "trust the process",
    "challenging planetary movements",
    "be cautious",
    "use this time for preparation",
    "future planetary movements",
    "favorable business launch",
    "market viability",
    "positive visibility",
    "auspiciousness",
    "prudent approach",
]


def detect_generic_phrases(answer: str) -> list[str]:
    lowered = answer.lower()
    return [phrase for phrase in GENERIC_PHRASES if phrase in lowered]


def check_genericity(answer: str) -> list[str]:
    issues = []
    hits = detect_generic_phrases(answer)
    if hits:
        issues.append(f"Answer contains generic advice phrases: {', '.join(hits)}.")
    if len(answer.split()) < 80:
        issues.append("Answer is too short to provide evidence-based astrology synthesis.")
    return issues
