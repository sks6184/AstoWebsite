"""Transactional reservations. Caller settles in the same transaction as answer publication."""
from uuid import UUID
from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils.crypto import salted_hmac
from django.utils import timezone
from .models import CreditAccount, UsageRequest
from .credits import get_or_create_profile, plan_credit_limit, successful_answer_count
from .usage_policy import policy_for, BudgetExceeded


def request_fingerprint(chart, question, language, depth):
    from astrology.tools.fingerprints import chart_fingerprint
    return salted_hmac('p7-request', str([chart.pk, chart_fingerprint(chart), question, language, depth])).hexdigest()


def reserve(user, chart, conversation, request_id, question):
    from charts.models import SavedChart
    if not getattr(user, 'is_authenticated', False) or not user.is_active or conversation.user_id != user.pk or conversation.chart_id != chart.pk or not SavedChart.objects.filter(pk=chart.pk, user=user).exists():
        raise BudgetExceeded('chart_unavailable')
    chart = SavedChart.objects.get(pk=chart.pk, user=user)
    request_id = UUID(str(request_id))
    fingerprint = request_fingerprint(chart, question, conversation.answer_language, conversation.depth_level)
    with transaction.atomic():
        previous = UsageRequest.objects.filter(user=user, request_id=request_id).first()
        if previous:
            if previous.fingerprint != fingerprint: raise BudgetExceeded('idempotency_conflict')
            return previous, False
        profile = get_or_create_profile(user)
        slug = profile.current_plan.slug if profile.current_plan else 'free'
        policy = policy_for(slug)
        account, _ = CreditAccount.objects.get_or_create(user=user, defaults={'consumed': successful_answer_count(user)})
        available = plan_credit_limit(profile.current_plan) + profile.bonus_question_credits
        selected = CreditAccount.objects.filter(pk=account.pk, reserved__lt=2)
        if settings.ENFORCE_QUESTION_LIMITS:
            selected = selected.filter(consumed__lt=available - F('reserved'))
        if not selected.update(reserved=F('reserved') + 1):
            account.refresh_from_db()
            raise BudgetExceeded('concurrent_request_limit' if account.reserved >= 2 else 'insufficient_credits')
        row = UsageRequest.objects.create(user=user, chart=chart, conversation=conversation, request_id=request_id,
            plan=slug, policy=policy, fingerprint=fingerprint)
        return row, True


def settle(row_id, *, delivered=False, reason='failed'):
    """Idempotent; financial rows survive conversation deletion. Nested atomic is intentional."""
    with transaction.atomic():
        row = UsageRequest.objects.select_for_update().get(pk=row_id)
        if row.status not in ('reserved', 'running'): return row
        # Conditional state transition also protects backends where select_for_update is unavailable.
        if not UsageRequest.objects.filter(pk=row.pk, status__in=['reserved', 'running']).update(
            status='succeeded' if delivered else reason, credits_consumed=1 if delivered else 0,
            credits_released=0 if delivered else 1, credits_reserved=0, updated_at=timezone.now()): return row
        changed = CreditAccount.objects.filter(user_id=row.user_id, reserved__gte=1).update(
            reserved=F('reserved') - 1, consumed=F('consumed') + (1 if delivered else 0))
        if changed != 1: raise RuntimeError('Credit reservation invariant failed.')
        if not row.provider_calls.exists():
            UsageRequest.objects.filter(pk=row.pk).update(estimated_cost=0, actual_cost=0)
        row.refresh_from_db()
        return row


def refund(user, request_id):
    with transaction.atomic():
        row = UsageRequest.objects.select_for_update().get(user=user, request_id=request_id)
        if row.status in ('reserved', 'running'): return settle(row.pk, reason='cancelled')
        if UsageRequest.objects.filter(pk=row.pk, status='succeeded', credits_consumed=1).update(
            status='refunded', credits_consumed=0, credits_released=1, updated_at=timezone.now()):
            CreditAccount.objects.filter(user=user, consumed__gte=1).update(consumed=F('consumed') - 1)
        row.refresh_from_db()
        return row
