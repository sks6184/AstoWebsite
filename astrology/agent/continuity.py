"""Resolve bounded elliptical follow-ups without trusting historical predictions."""
from dataclasses import replace
from datetime import date
import json
import re

from .policy import Plan, ScopeError, make_plan

MAX_CONTEXT_BYTES = 12288


def validate_context(context, chart_id):
    if context is None:
        return None
    if type(context) is not dict or context.get('schema_version') != 1 or context.get('chart_id') != chart_id:
        raise ScopeError('Conversation memory does not match the selected chart.')
    if len(json.dumps(context, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_CONTEXT_BYTES:
        raise ScopeError('Conversation context exceeds its byte budget.')
    summary = context.get('summary')
    if type(summary) is not dict or summary.get('chart_id') != chart_id or summary.get('epoch') != context.get('epoch') or summary.get('schema_version') != 1:
        raise ScopeError('Conversation summary is invalid for this memory epoch.')
    if type(context.get('recent_messages')) is not list or len(context['recent_messages']) > 6:
        raise ScopeError('Conversation history exceeds its turn budget.')
    return context


def _windows(summary, max_days):
    windows = summary.get('windows', [])
    try:
        if type(windows) is not list or len(windows) > 2:
            raise ValueError
        pairs = tuple((date.fromisoformat(a), date.fromisoformat(b)) for a, b in windows)
        if any(a > b for a, b in pairs) or (pairs and (max(b for a, b in pairs) - min(a for a, b in pairs)).days + 1 > max_days):
            raise ValueError
        return tuple((a.isoformat(), b.isoformat()) for a, b in pairs)
    except (TypeError, ValueError):
        raise ScopeError('Prior calendar context is invalid; specify the requested dates.') from None


def reject_chart_change(question):
    """A follow-up never changes the chart or birth inputs (shared by the P3 slice and the M3 agent)."""
    q = question.casefold()
    if re.search(r'\b(birth|born|latitude|longitude)\b', q) and re.match(r'\s*(actually\b|correction\b|i meant\b|no[, :])', q):
        raise ScopeError('Birth inputs come from the selected saved chart. Edit and recalculate that chart, then start a new conversation; this correction does not change calculated facts.')
    if re.search(r'\b(my wife|my husband|my son|my daughter|another person|different person|another chart|new chart)\b', q):
        raise ScopeError('Start a new conversation and select that person’s chart before continuing.')


def plan_with_context(question, today, max_days, context):
    if context is None:
        return make_plan(question, today, max_days)
    q = question.casefold()
    reject_chart_change(question)
    summary = context['summary']
    topic = summary.get('topic')
    prior = _windows(summary, max_days)
    if re.fullmatch(r'\s*(?:what about|show|check|and)\s+(?:my\s+)?d10[?.!\s]*', q):
        if topic not in ('job', 'business') or not prior:
            raise ScopeError('Please specify the career/business question and dates for D10.')
        return Plan('chart_focus', topic, prior, 'Focused D10 follow-up for the same chart and prior career/business period: ' + str(prior))
    # A named topic or new dates override inherited scope; interpretations never supply dates.
    text = question
    late = re.search(r'\blate\s+((?:18|19|20|21|22)\d{2})\b', q)
    if late:
        year = late.group(1)
        text = text[:late.start()] + f'{year}-10-01 to {year}-12-31' + text[late.end():]
    if topic in ('job', 'business') and not any(w in q for w in ('career', 'job', 'promot', 'business', 'startup')):
        text += ' career' if topic == 'job' else ' business'
    plan = make_plan(text, today, max_days)
    explicit_dates = bool(re.search(r'\b(?:18|19|20|21|22)\d{2}\b|\b(now|current|next|today|tomorrow|yesterday)\b', q))
    if prior and not explicit_dates and plan.kind != 'current_dasha' and plan.kind != 'house_lord':
        plan = replace(plan, windows=prior, reason=plan.reason + ' Reuses this conversation’s prior period and chart.')
    if 'compare' in q and prior and explicit_dates:
        combined = tuple(dict.fromkeys((*prior, *plan.windows)))
        if len(combined) > 2:
            raise ScopeError('Select one previous and one new period for comparison.')
        _windows({'windows': [list(w) for w in combined]}, max_days)
        plan = replace(plan, kind='timing', windows=combined, reason=plan.reason + ' Compares both the previous and newly requested period.')
    if late:
        plan = replace(plan, reason=plan.reason + ' Interprets “late year” as October through December; specify dates to narrow it.')
    return plan
