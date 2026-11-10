"""Deterministic, consent-bound memory. No model-generated factual summaries."""
from copy import deepcopy
import json

from .models import Message

SUMMARY_VERSION = 1
SUMMARY_BYTES = 4096
CONTEXT_BYTES = 12288
RECENT_MESSAGES = 6
TEXT_BYTES = 640


def compact(text, limit=TEXT_BYTES):
    return str(text).encode('utf-8')[:limit].decode('utf-8', errors='ignore')


def size(value):
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))


def empty_summary(conversation):
    return {'schema_version': SUMMARY_VERSION, 'chart_id': conversation.chart_id,
            'epoch': conversation.memory_epoch, 'topic': None, 'windows': [],
            'user_assertions': [], 'corrections': [], 'deterministic_references': [],
            'interpretations': []}


def trusted_summary(conversation):
    value = conversation.memory_summary
    expected = empty_summary(conversation)
    if type(value) is not dict or set(value) != set(expected) or value.get('schema_version') != SUMMARY_VERSION or value.get('chart_id') != conversation.chart_id or value.get('epoch') != conversation.memory_epoch:
        return expected
    if value['topic'] not in (None, 'job', 'business', 'general') or any(type(value[k]) is not list for k in ('windows', 'user_assertions', 'corrections', 'deterministic_references', 'interpretations')):
        return expected
    try:
        if size(value) > SUMMARY_BYTES:
            return expected
    except (TypeError, ValueError):
        return expected
    return deepcopy(value)


def message_record(message):
    # Deliberately avoid copying tool payloads, book text or birth inputs into memory.
    return {'message_id': message.pk, 'role': message.role,
            'kind': 'interpretation' if message.role == Message.ASSISTANT else message.kind,
            'content': compact(message.content),
            'trust': 'unverified_interpretation' if message.role == Message.ASSISTANT else 'user_assertion_not_verified',
            'supersedes_message_id': message.provenance.get('supersedes_message_id') if type(message.provenance) is dict else None}


def build_context(conversation, *, before_message_id, reference_message_id=None, current_message=None):
    if not conversation.memory_enabled:
        if reference_message_id is not None:
            raise ValueError('Enable memory before sending older context.')
        return None
    eligible = conversation.messages.filter(pk__gt=conversation.memory_floor, pk__lt=before_message_id)
    recent_turns = list(conversation.turns.filter(user_message_id__gt=conversation.memory_floor,
        user_message_id__lt=before_message_id).order_by('-sequence').values_list('user_message_id', 'assistant_message_id')[:3])
    message_ids = [mid for pair in recent_turns for mid in pair if mid is not None]
    rows = list(eligible.filter(pk__in=message_ids).order_by('-id')[:RECENT_MESSAGES])
    context = {'schema_version': SUMMARY_VERSION, 'conversation_id': conversation.pk,
               'chart_id': conversation.chart_id, 'epoch': conversation.memory_epoch,
               'summary': trusted_summary(conversation),
               'recent_messages': [message_record(m) for m in reversed(rows)],
               'older_reference': None,
               'current_user': message_record(current_message) if current_message else None}
    if reference_message_id is not None:
        older = eligible.filter(pk=reference_message_id).first()
        if older is None:
            raise ValueError('Referenced message is unavailable in this conversation memory epoch.')
        context['older_reference'] = message_record(older)
    while size(context) > CONTEXT_BYTES and context['recent_messages']:
        context['recent_messages'].pop(0)
    if size(context) > CONTEXT_BYTES:
        raise ValueError('Consultation context exceeds its byte limit.')
    return context


def update_summary(conversation, user_message, assistant_message, result):
    summary = trusted_summary(conversation)
    for event in result.get('trace', []):
        if event.get('event') == 'plan':
            summary['topic'] = event.get('topic')
            summary['windows'] = [list(w) for w in event.get('windows', [])[:2]]
    if user_message.kind == 'user_fact':
        summary['user_assertions'].append({'message_id': user_message.pk, 'text': compact(user_message.content, 320),
                                           'status': 'user_assertion_not_verified'})
    elif user_message.kind == 'correction':
        target = user_message.provenance.get('supersedes_message_id')
        summary['corrections'].append({'message_id': user_message.pk, 'supersedes_message_id': target,
                                      'text': compact(user_message.content, 320), 'status': 'user_correction_not_verified'})
        for assertion in summary['user_assertions']:
            if assertion.get('message_id') == target:
                assertion['status'] = 'superseded'
    if assistant_message is not None:
        summary['interpretations'].append({'message_id': assistant_message.pk,
                                           'status': 'preliminary_not_a_fact', 'result_status': result.get('status', 'legacy_unvalidated')})
        for item in list(result.get('evidence', {}).values())[:8]:
            if item['tool'] == 'search_astrology_knowledge' or item['result'].get('status') not in ('ok', 'partial'):
                continue
            summary['deterministic_references'].append({'message_id': assistant_message.pk,
                'tool': item['tool'], 'chart_fingerprint': item['result'].get('provenance', {}).get('chart_fingerprint'),
                'status': 'reference_only_recalculate_before_use'})
    for key, limit in (('user_assertions', 6), ('corrections', 6), ('deterministic_references', 8), ('interpretations', 3)):
        summary[key] = summary[key][-limit:]
    # Preserve scope and newest correction first; older entries age out rather than become truths.
    for key in ('deterministic_references', 'interpretations', 'user_assertions', 'corrections'):
        while size(summary) > SUMMARY_BYTES and len(summary[key]) > (1 if key == 'corrections' else 0):
            summary[key].pop(0)
    if size(summary) > SUMMARY_BYTES:
        return empty_summary(conversation)
    return summary
