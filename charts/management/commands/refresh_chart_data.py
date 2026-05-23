from django.core.management.base import BaseCommand, CommandError

from charts.astro_engine import build_vedic_chart
from charts.models import SavedChart


class Command(BaseCommand):
    help = "Refresh saved chart JSON with the current deterministic chart engine."

    def add_arguments(self, parser):
        parser.add_argument("--chart-id", type=int, help="Refresh one SavedChart by ID.")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be refreshed without saving.")
        parser.add_argument("--limit", type=int, help="Maximum number of charts to refresh.")

    def handle(self, *args, **options):
        queryset = SavedChart.objects.all().order_by("id")
        if options.get("chart_id"):
            queryset = queryset.filter(id=options["chart_id"])
            if not queryset.exists():
                raise CommandError(f"SavedChart {options['chart_id']} does not exist.")
        if options.get("limit"):
            queryset = queryset[: options["limit"]]

        refreshed = 0
        skipped = 0
        dry_run = options["dry_run"]

        for chart in queryset:
            if chart.latitude is None or chart.longitude is None:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipped {chart.id}: missing coordinates"))
                continue

            chart_data = build_vedic_chart(
                chart.name,
                chart.birth_date,
                chart.birth_time,
                chart.birth_place,
                chart.latitude,
                chart.longitude,
                chart.timezone,
            )
            vargas = [key for key in ["d3", "d12", "d16", "d27", "d40", "d45", "d60"] if key in chart_data]
            if dry_run:
                self.stdout.write(f"Would refresh {chart.id} {chart.name}: added/verified {', '.join(vargas)}")
            else:
                chart.chart_data = chart_data
                chart.save(update_fields=["chart_data", "updated_at"])
                self.stdout.write(self.style.SUCCESS(f"Refreshed {chart.id} {chart.name}: {', '.join(vargas)}"))
            refreshed += 1

        self.stdout.write(f"Done. Refreshed={refreshed} skipped={skipped} dry_run={dry_run}")

