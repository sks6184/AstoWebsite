from django.contrib import admin

from .models import PaymentEvent


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("gateway", "event_type", "external_id", "user", "received_at")
    list_filter = ("gateway", "event_type", "received_at")
    search_fields = ("external_id", "event_type", "user__email")
