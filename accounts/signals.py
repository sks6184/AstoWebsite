from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from allauth.account.signals import user_signed_up
from .pilot_ops import metric


@receiver(user_logged_in)
def remember_recent_login(sender, request, **kwargs):
    if request is not None: request.session['privacy_authenticated_at'] = int(timezone.now().timestamp())


@receiver(user_signed_up)
def signup_metric(sender, **kwargs):
    metric('signup')
