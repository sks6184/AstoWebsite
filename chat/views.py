from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.credits import question_credit_status
from charts.models import SavedChart

from .forms import AskQuestionForm
from .llm_engine import generate_placeholder_answer
from .models import Conversation, Message


@login_required
def ask_question(request):
    charts = SavedChart.objects.filter(user=request.user)
    selected_chart_id = request.GET.get("chart_id", "")
    conversation = None
    credit_status = question_credit_status(request.user)
    if request.method == "POST":
        form = AskQuestionForm(request.POST)
        if form.is_valid():
            credit_status = question_credit_status(request.user)
            if not credit_status["has_credits"]:
                messages.warning(
                    request,
                    "You have used all your question credits. Please buy more credits or upgrade your plan.",
                )
                return redirect(f"{reverse('home')}#pricing")
            chart = charts.filter(id=form.cleaned_data.get("chart_id")).first()
            depth_level = int(form.cleaned_data["depth_level"])
            answer_language = form.cleaned_data["answer_language"]
            question = form.cleaned_data["question"]
            conversation = Conversation.objects.create(
                user=request.user,
                chart=chart,
                depth_level=depth_level,
                title=question[:120],
            )
            Message.objects.create(conversation=conversation, role=Message.USER, content=question)
            result = generate_placeholder_answer(
                question,
                chart.chart_data if chart else {},
                depth_level,
                answer_language=answer_language,
            )
            Message.objects.create(
                conversation=conversation,
                role=Message.ASSISTANT,
                content=result["answer"],
                model_name=result["model"],
                prompt_tokens=result.get("prompt_tokens", 0),
                completion_tokens=result.get("completion_tokens", 0),
            )
    else:
        form = AskQuestionForm()
    return render(
        request,
        "chat/ask.html",
        {
            "form": form,
            "charts": charts,
            "conversation": conversation,
            "selected_chart_id": int(selected_chart_id) if selected_chart_id.isdigit() else None,
            "credit_status": credit_status,
        },
    )


@login_required
def conversation_detail(request, conversation_id):
    charts = SavedChart.objects.filter(user=request.user)
    conversations = Conversation.objects.filter(user=request.user).select_related("chart")[:12]
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related("messages").select_related("chart"),
        id=conversation_id,
        user=request.user,
    )
    return render(
        request,
        "chat/ask.html",
        {
            "form": AskQuestionForm(),
            "charts": charts,
            "conversation": conversation,
            "conversations": conversations,
            "credit_status": question_credit_status(request.user),
        },
    )


@login_required
def question_history(request):
    conversations = (
        Conversation.objects.filter(user=request.user)
        .select_related("chart")
        .prefetch_related("messages")
    )
    return render(request, "chat/history.html", {"conversations": conversations})
