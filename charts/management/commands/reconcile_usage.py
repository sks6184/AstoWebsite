"""Release abandoned customer reservations; never retry a paid provider call."""
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from accounts.models import UsageRequest
from accounts.usage import settle
from chat.models import Conversation, ConsultationTurn


class Command(BaseCommand):
    help = 'Dry-run stale usage reconciliation by default; --apply releases credits and blocks late publication.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than-seconds', type=int, default=900)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        age = options['older_than_seconds']
        if not 600 <= age <= 30 * 86400: raise CommandError('Use an age between 600 seconds and 30 days.')
        cutoff = timezone.now() - timedelta(seconds=age)
        ids = list(UsageRequest.objects.filter(status__in=['reserved', 'running'], created_at__lt=cutoff).values_list('pk', flat=True))
        changed = 0
        if options['apply']:
            for pk in ids:
                with transaction.atomic():
                    row = UsageRequest.objects.select_for_update().get(pk=pk)
                    if row.status not in ('reserved', 'running'): continue
                    settle(pk, reason='abandoned_unknown')
                    Conversation.objects.filter(pk=row.conversation_id, active_request=row.request_id).update(active_request=None, active_since=None)
                    ConsultationTurn.objects.filter(conversation_id=row.conversation_id, request_id=row.request_id, state='pending').update(state='failed')
                    changed += 1
        self.stdout.write(f"Stale requests={len(ids)}; reconciled={changed}; provider attempts were not retried.")
