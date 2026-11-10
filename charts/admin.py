from django.contrib import admin

from .models import SavedChart
from accounts.private_admin import PrivateDataAdmin


@admin.register(SavedChart)
class SavedChartAdmin(PrivateDataAdmin):
    list_display = ("name", "user", "birth_date", "birth_place", "created_at")
    search_fields = ("name", "user__username", "user__email", "birth_place")
    list_filter = ("created_at",)
