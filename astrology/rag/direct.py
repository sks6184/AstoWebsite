"""Direct vector-store search: returns stored chunks with no model generation round (M2 adapter b)."""
import hashlib
import json

from django.conf import settings

from accounts.provider_meter import vector_store_search
from accounts.provider_transport import IPv4HttpClient
from .knowledge_contracts import RetrievalBatch


def plain_query(query):
    """The knowledge tool sends a JSON query; direct search needs plain words."""
    try:
        value = json.loads(query)
    except (TypeError, ValueError):
        return str(query)[:512]
    if type(value) is not dict:
        return str(query)[:512]
    parts = [value.get('topic')] + list(value.get('concepts') or []) + [value.get('tradition'), value.get('source')]
    return ' '.join(p for p in parts if type(p) is str and p.strip())[:512]


def result_row(item):
    """Normalise one SDK search result to the row shape KnowledgeSession accepts."""
    data = item.model_dump() if hasattr(item, 'model_dump') else dict(item)
    text = '\n'.join(part.get('text', '') for part in data.get('content') or []
                     if type(part) is dict and part.get('type') == 'text' and type(part.get('text')) is str)
    return {'file_id': data.get('file_id'), 'filename': data.get('filename'), 'score': data.get('score'),
            'attributes': data.get('attributes') if type(data.get('attributes')) is dict else {}, 'text': text}


class DirectVectorStoreSearch:
    name = 'openai-vector-store-search'

    def __init__(self):
        self.store = getattr(settings, 'OPENAI_VECTOR_STORE_ID', '').strip()
        self.key = getattr(settings, 'OPENAI_API_KEY', '').strip()
        self.configured = bool(self.store and self.key)
        self.fingerprint = hashlib.sha256(json.dumps([self.store,
            getattr(settings, 'ASTROGPT_KNOWLEDGE_VERSION', 'unverified-v1'), 'direct-v1']).encode()).hexdigest()

    def retrieve(self, query, request, *, timeout):
        from openai import OpenAI
        text = plain_query(query)
        client = OpenAI(api_key=self.key, max_retries=0, timeout=timeout, http_client=IPv4HttpClient())
        try:
            page = vector_store_search(client, self.store, query=text, max_num_results=request.result_count)
            rows = [result_row(item) for item in list(getattr(page, 'data', None) or [])[:request.result_count]]
            # No model round: no tokens are generated or consumed.
            return RetrievalBatch(rows, [text], 0, 0, True)
        finally:
            client.close()


class StaticRetrieval:
    """Offline adapter for tests and swap checks: returns fixed rows, never contacts a provider."""
    name = 'offline-static-retrieval'

    def __init__(self, rows=None, configured=True):
        self.rows = list(rows or [])
        self.configured = configured
        self.fingerprint = hashlib.sha256(json.dumps(self.rows, sort_keys=True, default=str).encode()).hexdigest()
        self.calls = []

    def retrieve(self, query, request, *, timeout):
        self.calls.append(query)
        return RetrievalBatch([dict(r) for r in self.rows[:request.result_count]], [plain_query(query)], 0, 0, True)


ADAPTERS = {'hosted': 'astrology.rag.hosted.HostedFileSearch', 'direct': 'astrology.rag.direct.DirectVectorStoreSearch'}


def configured_adapter():
    """The adapter named by ASTROGPT_RETRIEVAL_ADAPTER ('hosted' by default; rollback = 'hosted')."""
    from django.utils.module_loading import import_string
    name = getattr(settings, 'ASTROGPT_RETRIEVAL_ADAPTER', 'hosted')
    if name not in ADAPTERS:
        raise ValueError(f'Unknown ASTROGPT_RETRIEVAL_ADAPTER: {name!r}')
    return import_string(ADAPTERS[name])()
