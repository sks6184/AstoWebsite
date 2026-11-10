"""Legacy final-output safety. Structural validation is not tool-claim certification."""
from copy import deepcopy
from django.core.cache import cache
from astrology.validation.validator import validate_answer

PUBLICATION_VERSION = 'p6-final-postprocess-v1'


def final_legacy_result(answer, payload, base):
    checked = validate_answer(answer, payload.get('evidence_payload', {}))
    return {**base, 'answer': answer if checked['passed'] else 'The final reading could not be verified. No unvalidated prediction was published.',
            'status': 'ok' if checked['passed'] else 'error', 'validation_result': checked,
            'publication_version': PUBLICATION_VERSION,
            'validation_kind': 'legacy_structural_not_tool_claim_validation'}


def validated_legacy_cache(key, payload):
    cached = cache.get(key)
    if not cached:
        return None
    if (type(cached) is dict and cached.get('publication_version') == PUBLICATION_VERSION
        and (cached.get('validation_result') or {}).get('passed') is True
        and type(cached.get('answer')) is str
        and validate_answer(cached['answer'], payload.get('evidence_payload', {}))['passed']):
        return {**deepcopy(cached), 'cache_hit': True}
    cache.delete(key)
    return None


def cache_legacy_result(key, result, timeout):
    if result.get('status') == 'ok' and result.get('publication_version') == PUBLICATION_VERSION and result.get('validation_result', {}).get('passed') is True:
        cache.set(key, {k: v for k, v in result.items() if k != 'prompt'}, timeout)
