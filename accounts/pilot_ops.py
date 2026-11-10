"""Coarse progress, anonymous aggregates and expiring hashed rate buckets."""
from datetime import timedelta
import logging
import time
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import PilotMetric, PilotRateBucket, UsageRequest

EVENTS = {'signup', 'chart_created', 'question', 'followup', 'feedback', 'request', 'rate_limited', 'account_deleted'}
OUTCOMES = {'ok', 'partial', 'error', 'denied', 'helpful', 'unhelpful', 'unsure'}
PROGRESS = {'queued': 'Request accepted', 'charts': 'Checking chart evidence', 'periods': 'Checking requested periods',
    'transits': 'Checking scoped transits', 'rules': 'Checking deterministic rules', 'sources': 'Looking for source support',
    'answer': 'Preparing the answer', 'validation': 'Verifying the final answer'}


def request_summary(row):
    active = row.status in ('reserved', 'running')
    label = PROGRESS.get(row.progress, 'Working on your request') if active else {
        'succeeded': 'Reading complete', 'partial_free': 'Preliminary answer available; no question credit consumed',
        'failed': 'Reading could not be completed; no question credit consumed', 'cancelled': 'Request cancelled',
        'refunded': 'Question credit refunded', 'abandoned_unknown': 'Request stopped; no question credit consumed'}.get(row.status, 'Request stopped')
    return {'status': row.status, 'label': label, 'active': active, 'credits_consumed': row.credits_consumed}


def metric(event, outcome='ok', elapsed_ms=0):
    if event not in EVENTS or outcome not in OUTCOMES: return
    elapsed_ms = max(0, min(int(elapsed_ms), 3600000))
    try:
        row, _ = PilotMetric.objects.get_or_create(day=timezone.now().date(), event=event, outcome=outcome)
        PilotMetric.objects.filter(pk=row.pk).update(count=F('count') + 1,
            elapsed_total_ms=F('elapsed_total_ms') + elapsed_ms, elapsed_max_ms=Greatest(F('elapsed_max_ms'), elapsed_ms))
    except Exception:
        # Monitoring must not change customer settlement or leak payloads through error logs.
        pass


def progress(stage):
    if stage not in PROGRESS: return
    from .provider_meter import CURRENT
    budget = CURRENT.get()
    if budget and budget.request_pk:
        UsageRequest.objects.filter(pk=budget.request_pk, status__in=['reserved', 'running']).update(progress=stage)


def allow_rate(scope, principal, limit, *, now=None):
    now = now or timezone.now()
    slot = int(now.timestamp()) // 60
    key = salted_hmac('p8-rate', str([scope, principal, slot])).hexdigest()
    try:
        with transaction.atomic():
            row, _ = PilotRateBucket.objects.get_or_create(key=key, defaults={'expires_at': now + timedelta(minutes=2)})
            return bool(PilotRateBucket.objects.filter(pk=row.pk, hits__lt=limit).update(hits=F('hits') + 1))
    except Exception:
        return False  # Fail closed if the shared limiter is unavailable.
