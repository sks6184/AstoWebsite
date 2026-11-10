import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import F, Sum
from accounts.models import CreditAccount, UsageRequest
from chat.models import Conversation


class Command(BaseCommand):
    help = 'Read-only migration, privacy and wallet readiness checks; prints no personal data or secrets.'

    def add_arguments(self, parser): parser.add_argument('--development', action='store_true')

    def handle(self, *args, **options):
        executor = MigrationExecutor(connection)
        pending = bool(executor.migration_plan(executor.loader.graph.leaf_nodes()))
        checks = {'migrations_current': not pending}
        if not pending:
            consistent = True
            for wallet in CreditAccount.objects.all():
                reserved = UsageRequest.objects.filter(user_id=wallet.user_id, status__in=['reserved', 'running']).aggregate(n=Sum('credits_reserved'))['n'] or 0
                consumed = UsageRequest.objects.filter(user_id=wallet.user_id).aggregate(n=Sum('credits_consumed'))['n'] or 0
                consistent = consistent and wallet.reserved == reserved and wallet.consumed >= consumed
            checks['wallets_consistent'] = consistent
            checks['chart_conversation_ownership'] = not Conversation.objects.filter(chart__isnull=False).exclude(chart__user_id=F('user_id')).exists()
        if not options['development']:
            checks.update(debug_disabled=not settings.DEBUG, secure_session=settings.SESSION_COOKIE_SECURE,
                secure_csrf=settings.CSRF_COOKIE_SECURE, https_redirect=settings.SECURE_SSL_REDIRECT,
                postgres=connection.vendor == 'postgresql', pilot_invites=bool(getattr(settings, 'ASTROGPT_PILOT_EMAILS', ())),
                email_verified=settings.ACCOUNT_EMAIL_VERIFICATION == 'mandatory', credits_enforced=settings.ENFORCE_QUESTION_LIMITS,
                rate_controls=settings.ASTROGPT_RATE_LIMITS_ENABLED,
                shared_cache='locmem' not in settings.CACHES['default']['BACKEND'].lower())
        self.stdout.write(json.dumps({'checks': checks, 'passed': all(checks.values()), 'agent_enabled': settings.ASTROGPT_AGENT_ENABLED}))
        if not all(checks.values()): raise CommandError('Pilot readiness failed; resolve named checks before rollout.')
