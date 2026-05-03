from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.credits import question_credit_status
from accounts.models import Plan
from charts.models import SavedChart
from chat.models import Conversation


def _fallback_plans():
    return [
        SimpleNamespace(slug=Plan.FREE, name="Free starter plan", price_usd=0),
        SimpleNamespace(slug=Plan.BASIC, name="$5 Deep Reading", price_usd=5),
        SimpleNamespace(slug=Plan.PREMIUM, name="$10 Full Analysis", price_usd=10),
    ]


@login_required
def dashboard(request):
    charts = SavedChart.objects.filter(user=request.user)[:5]
    conversations = Conversation.objects.filter(user=request.user)[:5]
    credit_status = question_credit_status(request.user)
    profile = credit_status["profile"]
    active_plans = list(Plan.objects.filter(is_active=True).order_by("price_usd", "id"))
    if not active_plans:
        active_plans = _fallback_plans()
    current_plan = profile.current_plan if profile and profile.current_plan else None
    if not current_plan:
        current_plan = next((plan for plan in active_plans if plan.slug == Plan.FREE), None)
    current_index = next(
        (index for index, plan in enumerate(active_plans) if plan.slug == current_plan.slug),
        -1,
    ) if current_plan else -1
    next_plan = active_plans[current_index + 1] if current_index + 1 < len(active_plans) else None
    return render(
        request,
        "accounts/dashboard.html",
        {
            "charts": charts,
            "conversations": conversations,
            "profile": profile,
            "current_plan": current_plan,
            "next_plan": next_plan,
            "credit_status": credit_status,
        },
    )
