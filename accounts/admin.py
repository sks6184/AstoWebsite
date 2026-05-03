from django.contrib import admin

from .models import Plan, UserProfile


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price_usd", "chart_limit", "monthly_question_limit", "max_depth_level", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "bonus_question_credits", "country", "created_at")
    search_fields = ("user__username", "user__email", "birth_name")
