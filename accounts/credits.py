from django.conf import settings

from chat.models import Message

from .models import Plan, UserProfile


PLAN_CREDIT_SETTINGS = {
    Plan.FREE: "FREE_QUESTION_CREDITS",
    Plan.BASIC: "BASIC_QUESTION_CREDITS",
    Plan.PREMIUM: "PREMIUM_QUESTION_CREDITS",
}


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def plan_credit_limit(plan):
    slug = plan.slug if plan else Plan.FREE
    setting_name = PLAN_CREDIT_SETTINGS.get(slug, "FREE_QUESTION_CREDITS")
    return getattr(settings, setting_name, settings.FREE_QUESTION_CREDITS)


def successful_answer_count(user):
    return Message.objects.filter(conversation__user=user, role=Message.ASSISTANT).count()


def question_credit_status(user):
    profile = get_or_create_profile(user)
    base_limit = plan_credit_limit(profile.current_plan)
    bonus_credits = profile.bonus_question_credits
    used = successful_answer_count(user)
    total = base_limit + bonus_credits
    remaining = max(total - used, 0)
    return {
        "enforced": settings.ENFORCE_QUESTION_LIMITS,
        "profile": profile,
        "plan": profile.current_plan,
        "base_limit": base_limit,
        "bonus_credits": bonus_credits,
        "total": total,
        "used": used,
        "remaining": remaining,
        "has_credits": (not settings.ENFORCE_QUESTION_LIMITS) or remaining > 0,
    }
