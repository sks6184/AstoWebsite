"""Short CAS transactions around generation; no database lock held across API calls."""
from dataclasses import dataclass
import re
from uuid import UUID

from django.db import transaction, OperationalError, IntegrityError
from django.db.models import F, Max
from django.http import Http404
from django.utils import timezone
from charts.models import SavedChart

from .memory import build_context, update_summary
from .models import Conversation, ConsultationTurn, Message, ErasedAnswerUsage
from accounts.usage import reserve, settle
from accounts.usage_policy import BudgetExceeded
from accounts.provider_meter import request_budget
from accounts.models import UsageRequest
from .evidence_manifest import manifest


@dataclass(frozen=True)
class TurnOutcome:
    http_status: int
    state: str
    conversation_id: int
    result: dict | None = None


def owned_conversation(user, conversation_id, *, require_chart=True):
    if not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False):
        raise Http404
    conversation = Conversation.objects.select_related('chart').filter(pk=conversation_id, user_id=user.pk).first()
    if conversation is None:
        raise Http404
    if require_chart and (conversation.chart is None or conversation.chart.user_id != user.pk):
        raise Http404
    return conversation


def _append_turn(user, conversation_id, question, *, request_id, expected_revision,
                kind='question', supersedes_message_id=None, reference_message_id=None, generator=None):
    conversation = owned_conversation(user, conversation_id)
    if type(question) is not str or not question.strip() or len(question.encode('utf-8')) > 4096 or type(expected_revision) is not int or expected_revision < 0:
        return TurnOutcome(400, 'invalid_request', conversation_id)
    try:
        request_id = UUID(str(request_id))
    except (TypeError, ValueError, AttributeError):
        return TurnOutcome(400, 'invalid_request', conversation_id)
    previous = ConsultationTurn.objects.filter(conversation=conversation, request_id=request_id).first()
    if previous:
        return TurnOutcome(200 if previous.state == 'complete' else 409, previous.state, conversation_id)
    if kind not in ('question', 'user_fact', 'correction'):
        return TurnOutcome(400, 'invalid_request', conversation_id)
    if re.match(r'\s*(actually\b|correction\b|i meant\b|no[, :])', question, re.I):
        kind = 'correction'
    if kind == 'correction' and supersedes_message_id is None:
        supersedes_message_id = conversation.messages.filter(role=Message.USER, pk__gt=conversation.memory_floor).order_by('-id').values_list('pk', flat=True).first()
    if supersedes_message_id is not None and not conversation.messages.filter(pk=supersedes_message_id, role=Message.USER, pk__gt=conversation.memory_floor).exists():
        return TurnOutcome(400, 'invalid_correction_reference', conversation_id)
    with transaction.atomic():
        if not SavedChart.objects.select_for_update().filter(pk=conversation.chart_id, user=user).exists():
            raise Http404
        previous = ConsultationTurn.objects.filter(conversation=conversation, request_id=request_id).first()
        if previous:
            return TurnOutcome(200 if previous.state == 'complete' else 409, previous.state, conversation_id)
        changed = Conversation.objects.filter(pk=conversation_id, user=user, chart_id=conversation.chart_id,
            revision=expected_revision, active_request__isnull=True).update(
                revision=F('revision') + 1, active_request=request_id, active_since=timezone.now(), updated_at=timezone.now())
        if not changed:
            return TurnOutcome(409, 'conversation_conflict', conversation_id)
        conversation.refresh_from_db()
        usage, created = reserve(user, conversation.chart, conversation, request_id, question.strip())
        if not created:
            raise BudgetExceeded('duplicate_request')
        user_message = Message.objects.create(conversation=conversation, role=Message.USER, content=question.strip(), kind=kind,
            provenance={'source': 'user', 'trust': 'user_assertion_not_verified',
                        'supersedes_message_id': supersedes_message_id if kind == 'correction' else None,
                        'memory_epoch': conversation.memory_epoch})
        turn = ConsultationTurn.objects.create(conversation=conversation, request_id=request_id,
            sequence=conversation.revision, epoch=conversation.memory_epoch, user_message=user_message)
    try:
        context = build_context(conversation, before_message_id=user_message.pk, reference_message_id=reference_message_id, current_message=user_message)
        if not Conversation.objects.filter(pk=conversation_id, user=user, chart_id=conversation.chart_id,
            chart__user=user, revision=turn.sequence, memory_epoch=turn.epoch, active_request=request_id).exists():
            settle(usage.pk, reason='cancelled')
            return TurnOutcome(409, 'conversation_changed_result_discarded', conversation_id)
        if generator is None:
            from .agent_service import generate_question_answer
            generator = generate_question_answer
        kwargs = {'answer_language': conversation.answer_language}
        if context is not None:
            kwargs['consultation_context'] = context
        with request_budget(usage):
            result = generator(user, conversation.chart, question.strip(), conversation.depth_level, **kwargs)
        if type(result) is not dict or type(result.get('answer')) is not str or type(result.get('model')) is not str or len(result['answer'].encode('utf-8')) > 1048576:
            raise ValueError('Invalid generation result.')
        if any(type(result.get(k, 0)) is not int or result.get(k, 0) < 0 for k in ('prompt_tokens', 'completion_tokens')):
            raise ValueError('Invalid generation usage.')
        for field in ('validation', 'validation_result'):
            if field in result and (type(result[field]) is not dict or result[field].get('passed') is not True):
                result = {**result, 'status': 'error', 'answer': 'The final reading could not be verified; no unvalidated answer was published.'}
    except BudgetExceeded:
        result = {'status': 'error', 'answer': 'The request reached its spending limit or was cancelled. No question credit was consumed.', 'model': 'deterministic'}
    except ValueError:
        result = {'status': 'error', 'answer': 'The requested conversation context is unavailable or invalid. Please review your references and try again.', 'model': 'deterministic'}
    except Exception:
        result = {'status': 'error', 'answer': 'The reading could not be completed. Please retry with a new submission.', 'model': 'deterministic'}
    with transaction.atomic():
        if not UsageRequest.objects.select_for_update().filter(pk=usage.pk, status__in=['reserved', 'running']).first():
            Conversation.objects.filter(pk=conversation_id, active_request=request_id).update(active_request=None, active_since=None)
            return TurnOutcome(409, 'conversation_changed_result_discarded', conversation_id)
        if not SavedChart.objects.select_for_update().filter(pk=conversation.chart_id, user=user).exists():
            settle(usage.pk, reason='cancelled')
            return TurnOutcome(409, 'conversation_changed_result_discarded', conversation_id)
        current = Conversation.objects.filter(pk=conversation_id, user=user, chart_id=conversation.chart_id,
            memory_epoch=turn.epoch, revision=turn.sequence, active_request=request_id)
        if not current.update(active_request=None, active_since=None, updated_at=timezone.now()):
            settle(usage.pk, reason='cancelled')
            return TurnOutcome(409, 'conversation_changed_result_discarded', conversation_id)
        conversation.refresh_from_db()
        assistant = None
        if result.get('status') != 'error':
            assistant = Message.objects.create(conversation=conversation, role=Message.ASSISTANT,
                content=result['answer'], kind='interpretation', model_name=result['model'][:80],
                prompt_tokens=result.get('prompt_tokens', 0), completion_tokens=result.get('completion_tokens', 0),
                provenance={'source': 'agent_or_legacy', 'trust': 'preliminary_interpretation_not_fact',
                            'evidence': manifest(result, usage.provider_calls.values_list('model', flat=True)),
                            'memory_epoch': turn.epoch, 'status': result.get('status', 'legacy_unvalidated')})
        if conversation.memory_enabled:
            Conversation.objects.filter(pk=conversation.pk).update(memory_summary=update_summary(conversation, user_message, assistant, result))
        ConsultationTurn.objects.filter(pk=turn.pk).update(state='complete' if assistant else 'failed', assistant_message=assistant)
        checked = result.get('validation', result.get('validation_result', {}))
        delivered = bool(assistant and result.get('status') == 'ok' and checked.get('passed') is True
                         and result.get('stop_reason', 'complete') == 'complete')
        settle(usage.pk, delivered=delivered, reason='partial_free' if assistant else 'failed')
    return TurnOutcome(200, 'complete' if assistant else 'failed', conversation_id, result)


def append_turn(user, conversation_id, question, **kwargs):
    import time
    from accounts.pilot_ops import metric
    started = time.monotonic()
    try:
        outcome = _append_turn(user, conversation_id, question, **kwargs)
        if outcome.result is not None:
            status = outcome.result.get('status', 'error')
            metric('question' if kwargs.get('expected_revision') == 0 else 'followup',
                status if status in ('ok', 'partial') else 'error', (time.monotonic() - started) * 1000)
        return outcome
    except IntegrityError:
        return TurnOutcome(409, 'conversation_conflict', conversation_id)
    except BudgetExceeded as exc:
        return TurnOutcome(403 if str(exc) == 'insufficient_credits' else 409, str(exc), conversation_id)
    except OperationalError as exc:
        if any(term in str(exc).lower() for term in ('locked', 'deadlock', 'serialization')):
            return TurnOutcome(409, 'conversation_busy', conversation_id)
        raise


def _change_memory(user, conversation_id, action, *, expected_revision):
    conversation = owned_conversation(user, conversation_id, require_chart=False)
    if action == 'enable':
        owned_conversation(user, conversation_id)
    if action not in ('enable', 'disable', 'reset', 'clear_history', 'delete') or type(expected_revision) is not int:
        return False
    with transaction.atomic():
        selected = Conversation.objects.filter(pk=conversation_id, user=user, revision=expected_revision)
        if not selected.update(revision=F('revision') + 1, memory_epoch=F('memory_epoch') + 1,
                               active_request=None, active_since=None, memory_summary={}, updated_at=timezone.now()):
            return False
        from accounts.models import UsageRequest
        for usage_id in UsageRequest.objects.filter(conversation_id=conversation_id, status__in=['reserved', 'running']).values_list('pk', flat=True):
            settle(usage_id, reason='cancelled')
        ConsultationTurn.objects.filter(conversation_id=conversation_id, state='pending').update(state='cancelled')
        if action in ('delete', 'clear_history'):
            count = conversation.messages.filter(role=Message.ASSISTANT).count()
            if count:
                usage, _ = ErasedAnswerUsage.objects.get_or_create(user=user)
                ErasedAnswerUsage.objects.filter(pk=usage.pk).update(count=F('count') + count)
        if action == 'delete':
            Conversation.objects.filter(pk=conversation_id, user=user).delete()
            return True
        floor = conversation.messages.aggregate(value=Max('pk'))['value'] or 0
        values = {'memory_floor': floor}
        if action == 'enable':
            values.update(memory_enabled=True, memory_consent_at=timezone.now())
        elif action == 'disable':
            values.update(memory_enabled=False, memory_consent_at=None)
        elif action == 'clear_history':
            conversation.messages.all().delete()
            ConsultationTurn.objects.filter(conversation_id=conversation_id).update(state='cancelled')
            values['memory_floor'] = 0
        Conversation.objects.filter(pk=conversation_id, user=user).update(**values)
    return True


def change_memory(user, conversation_id, action, *, expected_revision):
    try:
        return _change_memory(user, conversation_id, action, expected_revision=expected_revision)
    except IntegrityError:
        return False
    except OperationalError as exc:
        if any(term in str(exc).lower() for term in ('locked', 'deadlock', 'serialization')):
            return False
        raise
