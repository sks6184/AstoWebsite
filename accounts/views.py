from types import SimpleNamespace

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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
def post_login_redirect(request):
    if SavedChart.objects.filter(user=request.user).exists():
        return redirect("ask_question")
    return redirect("chart_list")


@login_required
def dashboard(request):
    return post_login_redirect(request)


@login_required
def pilot_analytics(request):
    from django.http import HttpResponseForbidden
    from .models import PilotMetric
    if not request.user.is_active or not request.user.is_superuser: return HttpResponseForbidden('Pilot analytics are restricted.')
    return render(request, 'accounts/pilot_analytics.html', {'metrics': PilotMetric.objects.order_by('-day', 'event', 'outcome')[:500]})


@login_required
def account_delete(request):
    from django.contrib.auth import logout
    from django.db import transaction
    from django.http import HttpResponse
    from django.utils import timezone
    from payments.models import PaymentEvent
    from .pilot_ops import metric
    if request.method == 'POST':
        fresh = 0 <= timezone.now().timestamp() - request.session.get('privacy_authenticated_at', 0) <= 900
        verified = request.user.check_password(request.POST.get('password', '')) if request.user.has_usable_password() else fresh
        if request.POST.get('confirmation') != 'DELETE' or not verified:
            return HttpResponse('Deletion requires DELETE and your current password, or a recent social sign-in.', status=400)
        with transaction.atomic():
            from django.contrib.admin.models import LogEntry
            from django.contrib.contenttypes.models import ContentType
            from django.contrib.auth import get_user_model
            from .models import UserProfile
            from chat.models import Message
            owned = [(SavedChart, SavedChart.objects.filter(user=request.user).values_list('pk', flat=True)),
                (Conversation, Conversation.objects.filter(user=request.user).values_list('pk', flat=True)),
                (Message, Message.objects.filter(conversation__user=request.user).values_list('pk', flat=True)),
                (UserProfile, UserProfile.objects.filter(user=request.user).values_list('pk', flat=True)),
                (get_user_model(), [request.user.pk])]
            for model, identifiers in owned:
                LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(model),
                    object_id__in=[str(pk) for pk in identifiers]).delete()
            PaymentEvent.objects.filter(user=request.user).delete()
            request.user.delete()
        logout(request)
        metric('account_deleted')
        return redirect('home')
    return render(request, 'accounts/delete.html')


@login_required
def contribution_dashboard(request):
    from django.http import HttpResponseForbidden
    from .reporting import contribution_report
    if not request.user.is_active or not request.user.is_superuser:
        return HttpResponseForbidden('Financial reporting is restricted.')
    response = render(request, 'accounts/contribution.html', {'report': contribution_report()})
    response['Cache-Control'] = 'no-store, private'
    return response


@login_required
def legacy_dashboard(request):
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
