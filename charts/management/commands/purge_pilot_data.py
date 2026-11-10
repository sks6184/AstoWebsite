from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import PilotMetric, PilotRateBucket
from chat.models import Conversation
from chat.consultation_service import change_memory


class Command(BaseCommand):
    help = 'Dry-run pilot retention cleanup; --apply deletes expired transcripts/aggregates and rate buckets.'

    def add_arguments(self, parser): parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        now = timezone.now()
        conversations = Conversation.objects.filter(updated_at__lt=now - timedelta(days=settings.ASTROGPT_TRANSCRIPT_RETENTION_DAYS), active_request__isnull=True)
        metrics = PilotMetric.objects.filter(day__lt=(now - timedelta(days=settings.ASTROGPT_METRIC_RETENTION_DAYS)).date())
        buckets = PilotRateBucket.objects.filter(expires_at__lt=now)
        counts = (conversations.count(), metrics.count(), buckets.count())
        if options['apply']:
            for conversation in list(conversations.select_related('user')):
                change_memory(conversation.user, conversation.pk, 'delete', expected_revision=conversation.revision)
            metrics.delete()
            buckets.delete()
        self.stdout.write(f'Eligible conversations={counts[0]}, aggregate rows={counts[1]}, expired rate buckets={counts[2]}; applied={options["apply"]}.')
