"""Aggregate unit economics; incomplete allocations never imply profitability."""
from decimal import Decimal
from math import ceil
from .models import UsageRequest, ProviderUsage


def contribution_report():
    groups = {}
    estimates, actuals = [], []
    for row in UsageRequest.objects.all().iterator():
        group = groups.setdefault(row.plan, {'requests': 0, 'consumed_credits': 0,
            'revenue': Decimal(0), 'provider_estimate': Decimal(0), 'invoice_actual': Decimal(0),
            'payment_fees': Decimal(0), 'infrastructure': Decimal(0), 'unknown_allocations': 0,
            'unknown_invoices': 0, 'provider_cost_basis': Decimal(0), 'contribution_margin_estimate': None})
        group['requests'] += 1
        estimates.append(row.estimated_cost)
        if row.actual_cost is not None: actuals.append(row.actual_cost)
        group['consumed_credits'] += row.credits_consumed
        group['provider_estimate'] += row.estimated_cost
        group['provider_cost_basis'] += row.actual_cost if row.actual_cost is not None else row.estimated_cost
        if row.actual_cost is None: group['unknown_invoices'] += 1
        else: group['invoice_actual'] += row.actual_cost
        fields = [('revenue_usd', 'revenue'), ('payment_fee_usd', 'payment_fees'), ('infrastructure_usd', 'infrastructure')]
        if any(getattr(row, field) is None for field, _ in fields): group['unknown_allocations'] += 1
        for field, key in fields:
            if getattr(row, field) is not None: group[key] += getattr(row, field)
    for group in groups.values():
        if not group['unknown_allocations']:
            group['contribution_margin_estimate'] = group['revenue'] - group['provider_cost_basis'] - group['payment_fees'] - group['infrastructure']
    def distribution(values):
        ordered = sorted(values)
        return {'count': len(values), 'average': sum(values) / len(values) if values else None,
                'p95': ordered[ceil(.95 * len(ordered)) - 1] if ordered else None}
    return {'currency': 'USD', 'plans': groups, 'estimated_request_costs': distribution(estimates),
            'known_invoice_request_costs': distribution(actuals),
            'basis': 'Before marketing and tax; provider costs estimated unless invoice actual is supplied.',
            'unknown_usage_calls': ProviderUsage.objects.filter(input_tokens__isnull=True).count()}
