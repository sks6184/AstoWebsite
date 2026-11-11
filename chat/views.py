from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import never_cache
from uuid import uuid4

from accounts.credits import question_credit_status
from astro_site.localization import remedy_devotion_note
from charts.models import SavedChart

from .forms import AskQuestionForm, FollowUpForm
from .agent_service import agent_route, generate_question_answer
from .models import Conversation, ConsultationTurn
from .consultation_service import append_turn, change_memory, owned_conversation
from .memory import trusted_summary
from accounts.models import UsageRequest


@login_required
@require_GET
@never_cache
def request_status(request, request_id):
    from django.shortcuts import get_object_or_404
    from accounts.pilot_ops import request_summary
    row = get_object_or_404(UsageRequest, user=request.user, request_id=request_id)
    if row.chart_id and row.chart.user_id != request.user.pk: return HttpResponse('Request unavailable.', status=404)
    return JsonResponse(request_summary(row))


def owned_message(request, message_id):
    from django.shortcuts import get_object_or_404
    from .models import Message
    message = get_object_or_404(Message.objects.select_related('conversation__chart'), pk=message_id,
        role=Message.ASSISTANT, conversation__user=request.user)
    if message.conversation.chart_id and message.conversation.chart.user_id != request.user.pk:
        from django.http import Http404
        raise Http404
    return message


@login_required
@require_GET
@never_cache
def answer_provenance(request, message_id):
    message = owned_message(request, message_id)
    return JsonResponse(message.provenance.get('evidence') or {'schema_version': 1, 'pipeline': 'historical',
        'validated': None, 'limitation': 'Detailed tool/source provenance was not retained for this historical answer.'})


@login_required
@require_POST
def answer_feedback(request, message_id):
    from accounts.models import AnswerFeedback
    from accounts.pilot_ops import metric
    message = owned_message(request, message_id)
    vote = request.POST.get('vote')
    if vote not in ('helpful', 'unhelpful', 'unsure'): return HttpResponse('Choose one of the available feedback options.', status=400)
    row, created = AnswerFeedback.objects.get_or_create(message=message, defaults={'vote': vote})
    if created: metric('feedback', vote)
    return redirect('conversation_detail', conversation_id=message.conversation_id)


@login_required
@never_cache
def ask_question(request):
    charts = SavedChart.objects.filter(user=request.user)
    selected_chart_id = request.GET.get("chart_id", "")
    conversation = None
    credit_status = question_credit_status(request.user)
    if request.method == "POST":
        selected_chart_id = request.POST.get("chart_id", "")
        form = AskQuestionForm(request.POST)
        if form.is_valid():
            request_id = form.cleaned_data.get('request_id')
            if request_id is None:
                # Compatibility for older clients: stable per-session form token, not a new ID per POST.
                request_id = request.session.get('ask_request_id') or str(uuid4())
                request.session['ask_request_id'] = str(request_id)
            previous = UsageRequest.objects.filter(user=request.user, request_id=request_id).first()
            if previous:
                from accounts.usage import request_fingerprint
                submitted_chart = charts.filter(pk=form.cleaned_data.get('chart_id')).first()
                if submitted_chart is None or previous.fingerprint != request_fingerprint(submitted_chart,
                    form.cleaned_data['question'].strip(), form.cleaned_data['answer_language'], Conversation.FULL):
                    return HttpResponse('This submission ID belongs to a different request. Open a fresh form.', status=409)
                if previous.conversation_id:
                    return redirect('conversation_detail', conversation_id=previous.conversation_id)
                return HttpResponse('This submission was already processed. Open a fresh form.', status=409)
            credit_status = question_credit_status(request.user)
            if not credit_status["has_credits"]:
                messages.warning(
                    request,
                    "You have used all your question credits. Please buy more credits or upgrade your plan.",
                )
                return redirect(f"{reverse('home')}#pricing")
            chart_id = form.cleaned_data.get("chart_id")
            if not chart_id:
                if charts.exists():
                    messages.error(request, "Please select a chart before asking a question.")
                else:
                    messages.error(
                        request,
                        "You don't have any charts yet. Please create a chart first.",
                    )
                return render(request, "chat/ask.html", {
                    "form": form,
                    "charts": charts,
                    "conversation": None,
                    "credit_status": credit_status,
                    "remedy_note": remedy_devotion_note("English"),
                })
            chart = charts.filter(id=chart_id).first()
            if chart is None:
                messages.error(request, "Chart is unavailable. Please select one of your charts.")
                return redirect("ask_question")
            depth_level = Conversation.FULL
            answer_language = form.cleaned_data["answer_language"]
            question = form.cleaned_data["question"]
            conversation = Conversation.objects.create(
                user=request.user,
                chart=chart,
                depth_level=depth_level,
                answer_language=answer_language,
                title=question[:120],
                memory_enabled=form.cleaned_data['memory_enabled'],
                memory_consent_at=timezone.now() if form.cleaned_data['memory_enabled'] else None,
            )
            outcome = append_turn(request.user, conversation.pk, question, request_id=request_id,
                                  expected_revision=0, generator=generate_question_answer)
            if outcome.http_status in (403, 409):
                # S-9: a rejected first turn (for example, no credits) rolls back its reservation;
                # remove the conversation created above if nothing was recorded in it.
                Conversation.objects.filter(pk=conversation.pk, user=request.user,
                                            messages__isnull=True, turns__isnull=True).delete()
            result = outcome.result or {}
            if result.get("status") == "error":
                messages.error(request, strip_tags(result["answer"])[:2000])
            if outcome.http_status == 403:
                return HttpResponse('Question credits are unavailable. No provider request was made.', status=403)
            if outcome.http_status == 409:
                return HttpResponse("This conversation changed during processing. Reload before retrying.", status=409)
            return redirect("conversation_detail", conversation_id=conversation.id)
    else:
        request.session['ask_request_id'] = str(uuid4())
        form = AskQuestionForm(initial={'request_id': request.session['ask_request_id']})
    return render(
        request,
        "chat/ask.html",
        {
            "form": form,
            "charts": charts,
            "conversation": conversation,
            "selected_chart_id": int(selected_chart_id) if selected_chart_id.isdigit() else None,
            "credit_status": credit_status,
            "remedy_note": remedy_devotion_note("English"),
            "agent_enabled": agent_route(request.user) != "legacy",
        },
    )


@login_required
@never_cache
def conversation_detail(request, conversation_id):
    from accounts.pilot_ops import request_summary
    charts = SavedChart.objects.filter(user=request.user)
    conversations = Conversation.objects.filter(user=request.user).select_related("chart")[:12]
    conversation = owned_conversation(request.user, conversation_id, require_chart=False)
    latest_usage = UsageRequest.objects.filter(user=request.user, conversation=conversation).order_by('-created_at').first()
    if conversation.chart_id and conversation.chart.user_id != request.user.pk:
        return HttpResponse("Conversation chart is unavailable.", status=404)
    return render(
        request,
        "chat/ask.html",
        {
            "form": AskQuestionForm(),
            "charts": charts,
            "conversation": conversation,
            "latest_request_summary": request_summary(latest_usage) if latest_usage else None,
            "conversations": conversations,
            "credit_status": question_credit_status(request.user),
            "remedy_note": remedy_devotion_note(conversation.answer_language),
            "followup_form": FollowUpForm(initial={"request_id": uuid4(), "expected_revision": conversation.revision, "kind": "question"}),
            "memory_summary": trusted_summary(conversation) if conversation.memory_enabled else None,
            "agent_enabled": agent_route(request.user) != "legacy",
        },
    )


@login_required
@never_cache
def question_history(request):
    conversations = (
        Conversation.objects.filter(user=request.user)
        .select_related("chart")
        .prefetch_related("messages")
    )
    return render(request, "chat/history.html", {"conversations": conversations})


@login_required
@require_POST
def conversation_followup(request, conversation_id):
    conversation = owned_conversation(request.user, conversation_id)
    if 'chart_id' in request.POST and request.POST['chart_id'] != str(conversation.chart_id):
        return HttpResponse("Start a new conversation to use another chart.", status=409)
    form = FollowUpForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'invalid_followup', 'fields': form.errors.get_json_data()}, status=400)
    existing = ConsultationTurn.objects.filter(conversation=conversation, request_id=form.cleaned_data['request_id']).exists()
    if not existing and not question_credit_status(request.user)['has_credits']:
        return HttpResponse("Question credits are unavailable.", status=403)
    data = form.cleaned_data
    outcome = append_turn(request.user, conversation_id, data['question'], request_id=data['request_id'],
        expected_revision=data['expected_revision'], kind=data['kind'],
        supersedes_message_id=data['supersedes_message_id'], reference_message_id=data['reference_message_id'],
        generator=generate_question_answer)
    if outcome.http_status != 200:
        return JsonResponse({'error': outcome.state, 'instruction': 'Reload the conversation before submitting again.'}, status=outcome.http_status)
    if outcome.result and outcome.result.get('status') == 'error':
        messages.error(request, strip_tags(outcome.result['answer'])[:2000])
    return redirect('conversation_detail', conversation_id=conversation_id)


@login_required
@require_GET
def conversation_memory(request, conversation_id):
    conversation = owned_conversation(request.user, conversation_id)
    response = JsonResponse({'memory_enabled': conversation.memory_enabled, 'revision': conversation.revision,
        'summary': trusted_summary(conversation) if conversation.memory_enabled else {}})
    response['Cache-Control'] = 'no-store, private'
    return response


@login_required
@require_POST
def conversation_memory_action(request, conversation_id):
    owned_conversation(request.user, conversation_id, require_chart=False)
    try:
        revision = int(request.POST.get('expected_revision', ''))
    except ValueError:
        return HttpResponse('Invalid revision.', status=400)
    action = request.POST.get('action')
    if action not in ('enable', 'disable', 'reset', 'clear_history', 'delete'):
        return HttpResponse('Invalid memory action.', status=400)
    if not change_memory(request.user, conversation_id, action, expected_revision=revision):
        return HttpResponse('Conversation changed. Reload before retrying.', status=409)
    if action == 'delete':
        return redirect('question_history')
    return redirect('conversation_detail', conversation_id=conversation_id)
