"""Configurable USD standard tariffs, conservative budgets, no pricing guessed by models."""
from decimal import Decimal, InvalidOperation
from django.conf import settings

TARIFFS = {'gpt-4o-mini': {'input': '0.15', 'cached': '0.075', 'output': '0.60',
    'file_search': '0.0025', 'context': 128000, 'version': 'published-standard-2026-11-07',
    'source': 'https://openai.com/index/api-prompt-caching/'}}
POLICIES = {
    'free': {'rounds': 2, 'tokens': 160000, 'output': 1200, 'file_searches': 1, 'cost': '0.05'},
    'basic': {'rounds': 3, 'tokens': 320000, 'output': 1800, 'file_searches': 2, 'cost': '0.10'},
    'premium': {'rounds': 4, 'tokens': 500000, 'output': 2400, 'file_searches': 3, 'cost': '0.20'},
}


class BudgetExceeded(Exception):
    pass


def policy_for(slug):
    policy = dict(getattr(settings, 'ASTROGPT_USAGE_POLICIES', POLICIES).get(slug, POLICIES['free']))
    if set(policy) != {'rounds', 'tokens', 'output', 'file_searches', 'cost'}:
        raise BudgetExceeded('invalid_policy')
    if any(type(policy[k]) is not int or not 0 < policy[k] <= maximum for k, maximum in
           [('rounds', 10), ('tokens', 1000000), ('output', 16000), ('file_searches', 10)]):
        raise BudgetExceeded('invalid_policy')
    try: cost = Decimal(str(policy['cost']))
    except (InvalidOperation, ValueError, TypeError): raise BudgetExceeded('invalid_policy') from None
    if not cost.is_finite() or not 0 < cost <= 10: raise BudgetExceeded('invalid_policy')
    policy['cost'] = str(cost)
    return policy


def tariff_for(model):
    tariff = dict(getattr(settings, 'ASTROGPT_API_TARIFFS', TARIFFS).get(model, {}))
    if not tariff: raise BudgetExceeded('unpriced_model')
    try:
        if any(not Decimal(str(tariff[k])).is_finite() or Decimal(str(tariff[k])) < 0 for k in ('input', 'cached', 'output', 'file_search')):
            raise ValueError
        if Decimal(tariff['cached']) > Decimal(tariff['input']) or type(tariff['context']) is not int or not 1 <= tariff['context'] <= 1000000:
            raise ValueError
    except (KeyError, ValueError, TypeError, InvalidOperation): raise BudgetExceeded('invalid_tariff') from None
    return tariff


def cost_for(tariff, input_tokens, output_tokens, cached_tokens=0, file_searches=0):
    if any(type(x) is not int or x < 0 for x in (input_tokens, output_tokens, cached_tokens, file_searches)) or cached_tokens > input_tokens:
        raise ValueError('Invalid token counts')
    return (((input_tokens - cached_tokens) * Decimal(tariff['input']) + cached_tokens * Decimal(tariff['cached'])
             + output_tokens * Decimal(tariff['output'])) / 1000000
            + file_searches * Decimal(tariff['file_search'])).quantize(Decimal('0.00000001'))
