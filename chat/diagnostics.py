"""Private diagnostics for a consultation that produced no reading.

One small record per failed request, kept on the user's message (``provenance['failure']``) and never
rendered to the user: the stage and code of the failure, the validation outcome, the status of each
provider call, what happened to the question credit, the cost, and the application version. It holds no
question text, no answer text and no chart data. One line goes to the operations log as well.
"""
import logging
import os
import subprocess
import traceback
from decimal import Decimal
from pathlib import Path

from django.conf import settings

log = logging.getLogger('astrogpt.operations')


def _version():
    """The commit the running code was started from (read once, when the server process loads this module)."""
    stated = os.getenv('ASTROGPT_VERSION', '').strip()
    if stated:
        return stated[:40]
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=str(Path(settings.BASE_DIR)), capture_output=True,
                             text=True, timeout=3).stdout.strip()
        return out[:40] or 'unknown'
    except Exception:
        return 'unknown'


APP_VERSION = _version()


def from_exception(exc, stage='generation'):
    """Type and code location only: an exception message can carry user or chart text."""
    frames = traceback.extract_tb(exc.__traceback__)
    where = [f"{Path(f.filename).name}:{f.lineno} {f.name}" for f in frames[-3:]]
    return {'stage': stage, 'code': 'exception', 'exception': type(exc).__name__, 'where': where}


def from_result(result, code):
    """A result that was produced but not published."""
    checked = result.get('validation') if type(result.get('validation')) is dict else {}
    draft = result.get('draft_validation') if type(result.get('draft_validation')) is dict else {}
    events = [e for e in result.get('trace', []) if type(e) is dict]
    stages = [str(e.get('stage'))[:16] for e in events if e.get('event') == 'round']
    return {'stage': 'validation' if stages else 'generation', 'code': str(code)[:48],
            'stop_reason': str(result.get('stop_reason', ''))[:48],
            'validation': {'passed': checked.get('passed'), 'issues': [str(i)[:120] for i in (draft.get('issues') or checked.get('issues') or [])[:12]],
                           'missing_sections': [str(m)[:60] for m in (draft.get('missing_sections') or checked.get('missing_sections') or [])[:12]],
                           'essential_missing': [str(m)[:60] for m in (draft.get('essential_missing') or [])[:12]]},
            'model_stages': stages[:8],
            'calculations': _count(result, lambda tool: tool != SEARCH),
            'retrieval': {**_count(result, lambda tool: tool == SEARCH),
                          'kept': next((len(e.get('kept', [])) for e in events if e.get('event') == 'rerank'), 0)}}


SEARCH = 'search_astrology_knowledge'


def _count(result, wanted):
    rows = [e for e in (result.get('evidence') or {}).values() if type(e) is dict and wanted(e.get('tool'))]
    ok = sum(1 for e in rows if (e.get('result') or {}).get('status') == 'ok')
    return {'ok': ok, 'failed': len(rows) - ok}


def record_failure(user_message, usage_id, failure, request_id=None):
    """Save the record on the user's message and write one operations log line. Never raises."""
    try:
        from accounts.models import UsageRequest
        row = UsageRequest.objects.filter(pk=usage_id).first()
        calls = list(row.provider_calls.order_by('sequence').values('sequence', 'model', 'status', 'error_code', 'rated_cost', 'reserved_cost')) if row else []
        cost = sum((c['rated_cost'] if c['rated_cost'] is not None else c['reserved_cost'] or Decimal(0)) for c in calls) if calls else Decimal(0)
        record = {**(failure or {'stage': 'unknown', 'code': 'unknown'}), 'schema_version': 1, 'app_version': APP_VERSION,
                  'request_id': str(request_id or (row.request_id if row else '')), 'usage_request_id': usage_id,
                  'message_id': user_message.pk if user_message else None,
                  'provider_calls': [{'sequence': c['sequence'], 'model': str(c['model'])[:60], 'status': c['status'],
                                      'error_code': c['error_code']} for c in calls[:16]],
                  'credit': ({'status': row.status, 'reserved': row.credits_reserved, 'consumed': row.credits_consumed,
                              'released': row.credits_released} if row else None),
                  'api_cost_usd': str(cost)}
        if user_message is not None:
            provenance = dict(user_message.provenance or {})
            provenance['failure'] = record
            type(user_message).objects.filter(pk=user_message.pk).update(provenance=provenance)
        if row and not row.stop_reason:
            UsageRequest.objects.filter(pk=row.pk).update(stop_reason=str(record.get('stop_reason') or record.get('code'))[:48])
        log.warning('consultation_failed', extra={'safe_event': 'consultation_failed', 'safe_code': record.get('code'),
                                                  'safe_stage': record.get('stage'), 'safe_usage': usage_id, 'safe_version': APP_VERSION})
        return record
    except Exception:
        log.warning('consultation_failure_record_unavailable', extra={'safe_event': 'consultation_failure_record_unavailable'})
        return None
