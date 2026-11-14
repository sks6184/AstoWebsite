"""No raw path, query, body, IP, user identity or exception in operational output."""
import json
import logging
import time
from django.conf import settings
from django.http import HttpResponse

ROUTES = {'ask_question', 'conversation_followup', 'conversation_memory_action', 'chart_create',
    'account_login', 'account_signup', 'login', 'admin:login', 'password_reset', 'account_reset_password',
    'account_delete', 'answer_feedback', 'request_status'}


class SafeJsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'event': getattr(record, 'safe_event', 'application_event'),
            'level': record.levelname, 'component': record.name,
            'status': getattr(record, 'status_code', None),
            'route': getattr(record, 'safe_route', None) if getattr(record, 'safe_route', None) in ROUTES else None,
            'elapsed_ms': getattr(record, 'elapsed_ms', None),
            # Failed-consultation diagnostics: codes and identifiers only, never question, answer or chart text.
            **{k: str(getattr(record, 'safe_' + k))[:48] for k in ('code', 'stage', 'usage', 'version') if getattr(record, 'safe_' + k, None) is not None}},
            separators=(',', ':'))


class PilotMiddleware:
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        from accounts.pilot_ops import metric
        request.get_host()  # Validate Host even for routes that never construct an absolute URL.
        start = time.monotonic()
        response = self.get_response(request)
        route = getattr(getattr(request, 'resolver_match', None), 'view_name', '')
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, private'
            response['Referrer-Policy'] = 'same-origin'
        if route in ROUTES and route != 'request_status':
            elapsed = int((time.monotonic() - start) * 1000)
            outcome = 'error' if response.status_code >= 500 else 'denied' if response.status_code >= 400 else 'ok'
            metric('request', outcome, elapsed)
            logging.getLogger('astrogpt.operations').info('request', extra={
                'safe_event': 'request_finished', 'safe_route': route, 'status_code': response.status_code, 'elapsed_ms': elapsed})
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        from accounts.pilot_ops import allow_rate, metric
        if settings.ACCOUNT_EMAIL_VERIFICATION == 'mandatory' and request.user.is_authenticated and not request.user.is_superuser and request.path.startswith(('/charts/', '/chat/', '/accounts/')) and request.resolver_match.view_name != 'account_delete':
            from allauth.account.models import EmailAddress
            if not EmailAddress.objects.filter(user=request.user, verified=True).exists():
                from django.shortcuts import redirect
                return redirect('account_email_verification_sent')
        if not getattr(settings, 'ASTROGPT_RATE_LIMITS_ENABLED', True): return None
        route = request.resolver_match.view_name
        if route not in ROUTES or (request.method != 'POST' and route != 'request_status'): return None
        if route in {'account_login', 'account_signup', 'login', 'admin:login', 'password_reset', 'account_reset_password'}:
            principal, limit = request.META.get('REMOTE_ADDR', 'unknown'), 10
        elif request.user.is_authenticated:
            principal = request.user.pk
            limit = 180 if route == 'request_status' else 10
        else: return None
        if not allow_rate(route, principal, limit):
            metric('rate_limited', 'denied')
            response = HttpResponse('Too many requests. Wait a minute before trying again; no reading was started.', status=429)
            response['Retry-After'] = '60'
            return response
