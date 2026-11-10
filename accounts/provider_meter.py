"""One bounded boundary for paid Responses calls. No prompt/body is persisted."""
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import UsageRequest, ProviderUsage, CreditAccount
from .usage_policy import BudgetExceeded, policy_for, tariff_for, cost_for
from .token_budget import input_token_bound

CURRENT = ContextVar('astrogpt_provider_budget', default=None)


class Budget:
    def __init__(self, policy=None, request_pk=None):
        self.policy = policy or policy_for('free')
        self.request_pk = request_pk
        self.rounds = self.tokens = self.searches = 0
        self.reserved = Decimal(0)
        self.last_usage = (0, 0)
        self.failed = False

    def before(self, kwargs):
        if self.failed: raise BudgetExceeded('previous_provider_failure')
        model = kwargs.get('model')
        tariff = tariff_for(model)
        output = kwargs.get('max_output_tokens', self.policy['output'])
        if type(output) is not int or not 0 < output <= self.policy['output']:
            raise BudgetExceeded('output_limit')
        size = input_token_bound(kwargs, model)
        if size + output > tariff['context']: raise BudgetExceeded('input_limit')
        searches = int(any(t.get('type') == 'file_search' for t in kwargs.get('tools', [])))
        if any(t.get('type') not in ('file_search', 'function') for t in kwargs.get('tools', [])):
            raise BudgetExceeded('unpriced_tool')
        input_bound = tariff['context'] if searches else size
        reserved = cost_for(tariff, input_bound, output, file_searches=searches)
        if self.rounds + 1 > self.policy['rounds'] or self.tokens + input_bound + output > self.policy['tokens']:
            raise BudgetExceeded('token_or_round_limit')
        if self.searches + searches > self.policy['file_searches'] or self.reserved + reserved > Decimal(self.policy['cost']):
            raise BudgetExceeded('cost_or_search_limit')
        event = None
        if self.request_pk:
            with transaction.atomic():
                row = UsageRequest.objects.select_for_update().get(pk=self.request_pk)
                if row.status not in ('reserved', 'running'): raise BudgetExceeded('request_cancelled')
                # Serialize per-user daily reservations across separate conversations/workers.
                CreditAccount.objects.select_for_update().get(user_id=row.user_id)
                daily_cap = Decimal(str(getattr(settings, 'ASTROGPT_DAILY_PROVIDER_CAP_USD', '1.00')))
                if not daily_cap.is_finite() or not 0 < daily_cap <= 100:
                    raise BudgetExceeded('invalid_daily_cap')
                daily = ProviderUsage.objects.filter(request__user_id=row.user_id,
                    created_at__gte=timezone.now() - timedelta(days=1)).aggregate(total=Sum('reserved_cost'))['total'] or Decimal(0)
                if daily + reserved > daily_cap: raise BudgetExceeded('daily_cost_limit')
                # Persist the attempt before external spending. No retries/replay of this event.
                event = ProviderUsage.objects.create(request=row, sequence=self.rounds + 1, model=model,
                    tariff=tariff, estimated_input=input_bound, estimated_output=output,
                    file_searches=searches, reserved_cost=reserved)
                UsageRequest.objects.filter(pk=row.pk).update(status='running', estimated_cost=F('estimated_cost') + reserved, updated_at=timezone.now())
        self.rounds += 1
        self.tokens += input_bound + output
        self.searches += searches
        self.reserved += reserved
        self.last_usage = (input_bound, output)
        kwargs.update(max_output_tokens=output, max_tool_calls=1, store=False)
        return event, tariff, input_bound, output, searches, reserved

    def after(self, reservation, reply=None, error=False):
        event, tariff, upper_input, upper_output, searches, reserved = reservation
        usage = getattr(reply, 'usage', None) if reply is not None else None
        incoming, outgoing = getattr(usage, 'input_tokens', None), getattr(usage, 'output_tokens', None)
        known = all(type(v) is int and v >= 0 for v in (incoming, outgoing))
        detail = getattr(usage, 'input_tokens_details', None)
        cached = getattr(detail, 'cached_tokens', None)
        cached_known = type(cached) is int and known and 0 <= cached <= incoming
        if not cached_known: cached = 0
        output = getattr(reply, 'output', None) if reply is not None else None
        reported_searches = sum(getattr(item, 'type', None) == 'file_search_call' for item in output) if type(output) is list else None
        rated = cost_for(tariff, incoming, outgoing, cached, searches if reported_searches is None else reported_searches) if known else reserved
        self.last_usage = (incoming, outgoing) if known else (upper_input, upper_output)
        breached = (known and (incoming > upper_input or outgoing > upper_output)) or (reported_searches is not None and reported_searches > searches)
        self.failed = self.failed or error or breached
        if event:
            ProviderUsage.objects.filter(pk=event.pk).update(status='error' if error else 'overrun' if breached else 'reported' if known else 'estimated',
                input_tokens=incoming if known else None, output_tokens=outgoing if known else None,
                cached_tokens=cached if cached_known else None, rated_cost=rated, reported_file_searches=reported_searches,
                cached_discount=(Decimal(cached) * (Decimal(tariff['input']) - Decimal(tariff['cached'])) / 1000000) if cached_known else Decimal(0),
                error_code='provider_failure' if error else 'provider_usage_overrun' if breached else '')
            total = sum((x.rated_cost if x.rated_cost is not None else x.reserved_cost)
                        for x in ProviderUsage.objects.filter(request_id=self.request_pk))
            UsageRequest.objects.filter(pk=self.request_pk).update(estimated_cost=total, updated_at=timezone.now())
        if breached: raise BudgetExceeded('provider_usage_overrun')


@contextmanager
def request_budget(row):
    budget = Budget(row.policy, row.pk)
    token = CURRENT.set(budget)
    try:
        yield budget
    finally:
        CURRENT.reset(token)


def responses_create(client, **kwargs):
    from .pilot_ops import progress
    progress('sources' if kwargs.get('tool_choice') == {'type': 'file_search'} else 'answer')
    budget = CURRENT.get() or Budget()  # Direct internal callers still receive a conservative per-call cap.
    try:
        reservation = budget.before(kwargs)
    except BudgetExceeded as exc:
        budget.failed = True
        if budget.request_pk:
            UsageRequest.objects.filter(pk=budget.request_pk).update(stop_reason=str(exc)[:48], updated_at=timezone.now())
        raise
    try:
        response = client.responses.create(**kwargs)
    except Exception:
        budget.after(reservation, error=True)
        raise
    budget.after(reservation, response)
    return response


def usage_counts(reply):
    usage = getattr(reply, 'usage', None)
    values = (getattr(usage, 'input_tokens', None), getattr(usage, 'output_tokens', None))
    if all(type(x) is int and x >= 0 for x in values): return values
    budget = CURRENT.get()
    return budget.last_usage if budget else (0, 0)
