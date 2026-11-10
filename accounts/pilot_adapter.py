from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class PilotAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        if not getattr(settings, 'ASTROGPT_PILOT_SIGNUPS_RESTRICTED', False): return True
        return request.method == 'GET' or request.POST.get('email', '').strip().casefold() in settings.ASTROGPT_PILOT_EMAILS
