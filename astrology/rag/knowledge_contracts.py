"""Bounded read-only knowledge contracts, independent of a retrieval vendor."""
from dataclasses import dataclass
from typing import Protocol

MAX_RESULTS = 5
# Owner (M2 close-out, 2026-11-11): interpretive searches return at least 3 passages.
# Requests for fewer are accepted and raised to this floor.
MIN_RESULTS = 3
SNIPPET_BYTES = 1200
TOTAL_SNIPPET_BYTES = 6000
MAX_OUTPUT_BYTES = 32768
HOSTED_OUTPUT_TOKENS = 512
HOSTED_CONTEXT_RESERVE = 32768


@dataclass(frozen=True)
class SearchRequest:
    chart_id: int
    topic: str
    concepts: tuple[str, ...]
    tradition: str | None = None
    source: str | None = None
    result_count: int = 3


@dataclass(frozen=True)
class RetrievalBatch:
    results: list[dict]
    queries: list[str]
    input_tokens: int
    output_tokens: int
    complete: bool = True


class RetrievalAdapter(Protocol):
    name: str
    configured: bool
    fingerprint: str

    def retrieve(self, query: str, request: SearchRequest, *, timeout: float) -> RetrievalBatch: ...


def tool_definition():
    return {'name': 'search_astrology_knowledge', 'input_schema': {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'chart_id': {'type': 'integer', 'minimum': 1},
            'topic': {'type': 'string', 'maxLength': 80},
            'concepts': {'type': 'array', 'minItems': 1, 'maxItems': 6, 'items': {'type': 'string', 'maxLength': 80}},
            'tradition': {'type': ['string', 'null'], 'maxLength': 80},
            'source': {'type': ['string', 'null'], 'maxLength': 120},
            'result_count': {'type': 'integer', 'minimum': 1, 'maximum': MAX_RESULTS},
        }, 'required': ['chart_id', 'topic', 'concepts']}}
