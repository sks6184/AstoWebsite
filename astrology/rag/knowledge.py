"""Authorized request-local retrieval, bounded excerpts and non-invented citations."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
from django.core.cache import cache as shared_cache
from accounts.usage_policy import BudgetExceeded

from charts.models import SavedChart
from astrology.tools.contracts import ToolFailure, json_bytes, parse_request
from .knowledge_contracts import (
    SearchRequest, RetrievalBatch, MAX_RESULTS, SNIPPET_BYTES, TOTAL_SNIPPET_BYTES,
    MAX_OUTPUT_BYTES, HOSTED_OUTPUT_TOKENS, HOSTED_CONTEXT_RESERVE,
)

TOOL = 'search_astrology_knowledge'
CITATION_FIELDS = ('file_id', 'filename', 'document', 'book', 'chapter', 'page', 'tradition')


def prepare(arguments):
    request = parse_request(SearchRequest, arguments)
    if not 1 <= request.result_count <= MAX_RESULTS or not 1 <= len(request.concepts) <= 6:
        raise ToolFailure('invalid_arguments', 'Request 1–5 results and 1–6 specific concepts.')
    for value, limit in [(request.topic, 80), *((c, 80) for c in request.concepts),
                         (request.tradition, 80), (request.source, 120)]:
        if value is not None and (not value.strip() or len(value.encode('utf-8')) > limit or any(ord(c) < 32 for c in value)):
            raise ToolFailure('invalid_arguments', 'Knowledge terms must be short, nonempty text without control characters.')
    # Stable canonicalization makes equivalent repeated requests reusable within this session.
    request = SearchRequest(request.chart_id, request.topic.strip().casefold(),
        tuple(sorted(set(c.strip().casefold() for c in request.concepts))),
        request.tradition.strip().casefold() if request.tradition else None,
        request.source.strip().casefold() if request.source else None, request.result_count)
    query = json.dumps({'topic': request.topic, 'concepts': request.concepts,
                        'tradition': request.tradition, 'source': request.source}, ensure_ascii=False)
    return request, query


def _metadata(value):
    if type(value) in (int, float) and math.isfinite(value):
        return str(value)
    if type(value) is str and value.strip() and len(value.encode('utf-8')) <= 256 and not any(ord(c) < 32 for c in value):
        return value.strip()
    return None


def validate_knowledge(payload):
    required = {'schema_version', 'status', 'data', 'warnings', 'method', 'provenance', 'error'}
    if type(payload) is not dict or set(payload) != required or payload['schema_version'] != '1.0' or payload['status'] not in ('ok', 'partial', 'error'):
        raise ValueError('Invalid knowledge envelope')
    if type(payload['warnings']) is not list or any(type(w) is not str for w in payload['warnings']) or type(payload['method']) is not dict or type(payload['provenance']) is not dict:
        raise ValueError('Invalid knowledge metadata')
    if payload['status'] == 'error':
        if payload['data'] is not None or type(payload['error']) is not dict or set(payload['error']) != {'code', 'message'} or any(type(v) is not str for v in payload['error'].values()):
            raise ValueError('Invalid knowledge error')
    else:
        data = payload['data']
        if type(data) is not dict or set(data) != {'passages', 'support_status', 'query', 'usage', 'viewpoint_policy'} or payload['error'] is not None:
            raise ValueError('Invalid knowledge data')
        if data['support_status'] not in ('retrieved', 'insufficient') or type(data['query']) is not str or type(data['passages']) is not list or len(data['passages']) > MAX_RESULTS:
            raise ValueError('Invalid knowledge support')
        if type(data['viewpoint_policy']) is not str or (data['support_status'] == 'retrieved') != bool(data['passages']):
            raise ValueError('Invalid viewpoint/support statement')
        usage = data['usage']
        if type(usage) is not dict or set(usage) != {'input_tokens', 'output_tokens', 'provider_rounds'} or any(type(v) is not int or v < 0 for v in usage.values()):
            raise ValueError('Invalid retrieval usage')
        total = 0
        for passage in data['passages']:
            if type(passage) is not dict or set(passage) != {'evidence_id', 'snippet', 'citation', 'citation_available', 'truncated', 'score', 'trust'}:
                raise ValueError('Invalid passage')
            if type(passage['evidence_id']) is not str or not passage['evidence_id'].startswith('K') or type(passage['snippet']) is not str or not passage['snippet']:
                raise ValueError('Invalid passage text')
            if type(passage['truncated']) is not bool or type(passage['citation_available']) is not bool or passage['trust'] != 'untrusted_source_text':
                raise ValueError('Invalid passage trust')
            citation = passage['citation']
            if type(citation) is not dict or set(citation) != set(CITATION_FIELDS) or any(v is not None and (type(v) is not str or _metadata(v) != v) for v in citation.values()):
                raise ValueError('Invalid citation')
            expected_id = 'K' + hashlib.sha256(json_bytes([citation, passage['snippet']])).hexdigest()[:20]
            if passage['evidence_id'] != expected_id or passage['citation_available'] != any(citation[f] for f in ('file_id', 'filename', 'document', 'book')):
                raise ValueError('Citation/evidence reference mismatch')
            if passage['score'] is not None and (type(passage['score']) not in (int, float) or not math.isfinite(passage['score']) or not 0 <= passage['score'] <= 1):
                raise ValueError('Invalid search relevance')
            size = len(passage['snippet'].encode('utf-8'))
            total += size
            if size > SNIPPET_BYTES:
                raise ValueError('Snippet limit')
        if total > TOTAL_SNIPPET_BYTES:
            raise ValueError('Passage budget')
    if len(json_bytes(payload)) > MAX_OUTPUT_BYTES:
        raise ValueError('Knowledge envelope limit')
    return payload


class KnowledgeSession:
    """One consultation only. Construct with trusted server principal/chart context."""
    def __init__(self, user, chart_id, adapter=None):
        if adapter is None:
            from .hosted import HostedFileSearch
            adapter = HostedFileSearch()
        self.user, self.chart_id, self.adapter = user, chart_id, adapter
        self.cache = {}
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0, 'provider_rounds': 0}

    def authorized(self):
        return bool(getattr(self.user, 'is_authenticated', False) and getattr(self.user, 'is_active', False)
                    and type(self.chart_id) is int and SavedChart.objects.filter(pk=self.chart_id, user_id=self.user.pk).exists())

    def reservation(self, arguments):
        _, query = prepare(arguments)
        return HOSTED_CONTEXT_RESERVE + len(query.encode('utf-8')) + HOSTED_OUTPUT_TOKENS + 1024

    def cache_key(self, request):
        from astrology.tools.fingerprints import chart_fingerprint, engine_fingerprint
        chart = SavedChart.objects.filter(pk=self.chart_id, user_id=self.user.pk).first()
        return hashlib.sha256(json_bytes({'owner': self.user.pk, 'request': asdict(request),
            'chart': chart_fingerprint(chart) if chart else None, 'engine': engine_fingerprint(),
            'scope': self.shared_scope(), 'adapter': self.adapter.fingerprint})).hexdigest()

    def shared_scope(self):
        from accounts.provider_meter import CURRENT
        from accounts.models import UsageRequest
        budget = CURRENT.get()
        if not budget or not budget.request_pk: return None
        row = UsageRequest.objects.select_related('conversation').filter(pk=budget.request_pk,
            user_id=self.user.pk, chart_id=self.chart_id, status__in=['reserved', 'running']).first()
        conversation = row.conversation if row else None
        if conversation and conversation.memory_enabled:
            return [conversation.pk, conversation.memory_epoch]
        return None

    def hydrate(self, request):
        key = self.cache_key(request)
        if key not in self.cache and self.shared_scope() is not None:
            try:
                value = shared_cache.get('astro-knowledge-p7:' + key)
                if value is not None and value['status'] in ('ok', 'partial'):
                    self.cache[key] = validate_knowledge(value)
            except Exception:
                pass  # Optional cache never bypasses ownership or prevents retrieval.
        return key

    def requires_provider(self, arguments):
        request, _ = prepare(arguments)
        return self.adapter.configured and self.hydrate(request) not in self.cache

    def search(self, arguments, *, token_budget=40000, timeout=15):
        self.last_usage = {'input_tokens': 0, 'output_tokens': 0, 'provider_rounds': 0}
        method = {'tool': TOOL, 'version': '1.0', 'adapter': self.adapter.name,
                  'role': 'traditional explanation only; not a deterministic calculation or rule',
                  'snippet_limit_bytes': SNIPPET_BYTES, 'corpus_coverage': 'unverified'}
        provenance = {}
        def envelope(status, data=None, warnings=(), error=None):
            return validate_knowledge({'schema_version': '1.0', 'status': status, 'data': data,
                'warnings': list(warnings), 'method': method, 'provenance': provenance, 'error': error})
        try:
            if not self.authorized():
                raise ToolFailure('chart_not_found', 'Chart is unavailable.')
            request, query = prepare(arguments)
            if request.chart_id != self.chart_id:
                raise ToolFailure('chart_not_found', 'Chart is unavailable.')
            if not self.adapter.configured:
                raise ToolFailure('knowledge_not_configured', 'Astrology retrieval requires a configured vector store and API key; no retrieved support is available.')
            key = self.hydrate(request)
            if key in self.cache:
                value = deepcopy(self.cache[key])
                value['provenance']['cache_hit'] = True
                value['data']['usage'] = dict(self.last_usage)
                return validate_knowledge(value)
            reserve = self.reservation(arguments)
            if type(token_budget) is not int or token_budget < reserve:
                raise ToolFailure('knowledge_token_limit', 'Insufficient token budget for a bounded hosted retrieval.')
            if type(timeout) not in (int, float) or not 0 < timeout <= 60:
                raise ToolFailure('invalid_arguments', 'Retrieval timeout must be positive and at most 60 seconds.')
            self.last_usage['provider_rounds'] = 1
            batch = self.adapter.retrieve(query, request, timeout=timeout)
            if not isinstance(batch, RetrievalBatch) or type(batch.results) is not list or type(batch.queries) is not list or type(batch.complete) is not bool:
                raise ToolFailure('invalid_retrieval', 'Provider returned malformed retrieval data.')
            for field in ('input_tokens', 'output_tokens'):
                value = getattr(batch, field)
                if type(value) is not int or value < 0:
                    raise ToolFailure('invalid_retrieval', 'Provider returned invalid retrieval usage.')
                self.last_usage[field] = value
            if not self.authorized():
                raise ToolFailure('chart_not_found', 'Chart is unavailable.')
            if batch.input_tokens + batch.output_tokens > token_budget or batch.output_tokens > HOSTED_OUTPUT_TOKENS:
                raise ToolFailure('knowledge_token_limit', 'Provider retrieval usage exceeded the reserved token budget.')
            passages, warnings, ids = [], [], set()
            for row in batch.results[:request.result_count]:
                if type(row) is not dict or type(row.get('text')) is not str or not row['text'].strip():
                    warnings.append('A malformed or empty search result was omitted.')
                    continue
                attrs = row.get('attributes') if type(row.get('attributes')) is dict else {}
                citation = {'file_id': _metadata(row.get('file_id')), 'filename': _metadata(row.get('filename')),
                            'document': _metadata(attrs.get('document') or attrs.get('document_title') or attrs.get('title')),
                            **{field: _metadata(attrs.get(field)) for field in ('book', 'chapter', 'page', 'tradition')}}
                if request.source and not any(request.source in (citation[f] or '').casefold() for f in ('file_id', 'filename', 'document', 'book')):
                    warnings.append('A requested source filter could not be verified against returned metadata.')
                    continue
                if request.tradition and request.tradition != (citation['tradition'] or '').casefold():
                    warnings.append('A requested tradition filter could not be verified against returned metadata.')
                    continue
                raw = row['text'].strip().encode('utf-8')
                snippet = raw[:SNIPPET_BYTES].decode('utf-8', errors='ignore')
                eid = 'K' + hashlib.sha256(json_bytes([citation, snippet])).hexdigest()[:20]
                if eid in ids:
                    continue
                ids.add(eid)
                score = row.get('score')
                if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                    score = None
                passages.append({'evidence_id': eid, 'snippet': snippet, 'citation': citation,
                                 'citation_available': any(citation[f] for f in ('file_id', 'filename', 'document', 'book')),
                                 'truncated': len(raw) > SNIPPET_BYTES, 'score': score, 'trust': 'untrusted_source_text'})
            if not passages:
                warnings.append('Insufficient retrieved support for these concepts and available source metadata.')
            if any(not p['citation_available'] for p in passages):
                warnings.append('Citation unavailable for one or more retrieved excerpts; no book or page was inferred.')
            if any(any(p['citation'][f] is None for f in ('book', 'chapter', 'page', 'tradition')) for p in passages):
                warnings.append('Some book/chapter/page/tradition metadata is unavailable; no missing attribution was inferred.')
            if len(batch.results) > request.result_count or any(p['truncated'] for p in passages):
                warnings.append('Retrieved material was truncated to the requested result/snippet budgets.')
            if not batch.complete:
                warnings.append('Hosted search did not complete; retained support is partial.')
            provenance.update({'chart_id': self.chart_id, 'adapter_fingerprint': self.adapter.fingerprint,
                               'cache_hit': False, 'passage_ids': [p['evidence_id'] for p in passages],
                               'queries': [q[:512] for q in batch.queries[:6] if type(q) is str]})
            result = envelope('partial' if warnings else 'ok',
                {'passages': passages, 'support_status': 'retrieved' if passages else 'insufficient',
                 'query': query, 'usage': dict(self.last_usage),
                 'viewpoint_policy': 'Sources are separate viewpoints; agreement and predictive validity are not inferred.'},
                tuple(dict.fromkeys(warnings)))
            self.cache[key] = deepcopy(result)
            if self.shared_scope() is not None:
                try: shared_cache.set('astro-knowledge-p7:' + key, result, 120)
                except Exception: pass
            return result
        except ToolFailure as exc:
            return envelope('error', error={'code': exc.code, 'message': exc.message})
        except BudgetExceeded:
            return envelope('error', error={'code': 'spending_limit', 'message': 'Retrieval reached the request spending limit; no further paid search was made.'})
        except TimeoutError:
            return envelope('error', error={'code': 'knowledge_timeout', 'message': 'Knowledge retrieval timed out; no retrieved support is established.'})
        except Exception:
            return envelope('error', error={'code': 'knowledge_unavailable', 'message': 'Knowledge retrieval is unavailable; no retrieved support is established.'})
