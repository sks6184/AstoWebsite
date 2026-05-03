from django.contrib import admin

from .models import SavedChart


@admin.register(SavedChart)
class SavedChartAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "birth_date", "birth_place", "created_at")
    search_fields = ("name", "user__username", "user__email", "birth_place")
    list_filter = ("created_at",)
