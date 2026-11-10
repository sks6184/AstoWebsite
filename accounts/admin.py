from django.contrib import admin

from .models import Plan, UserProfile
from .models import UsageRequest, ProviderUsage
from .private_admin import PrivateDataAdmin


class FinanceOnly(admin.ModelAdmin):
    def has_module_permission(self, request): return request.user.is_active and request.user.is_superuser
    def has_view_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_change_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(UsageRequest)
class UsageRequestAdmin(FinanceOnly):
    list_display = ('id', 'plan', 'status', 'credits_consumed', 'estimated_cost', 'actual_cost', 'created_at')
    list_filter = ('plan', 'status')
    exclude = ('user', 'chart', 'conversation', 'fingerprint')
    readonly_fields = ('request_id', 'plan', 'policy', 'status', 'stop_reason', 'credits_reserved', 'credits_consumed', 'credits_released', 'estimated_cost', 'created_at', 'updated_at')
    actions = ['refund_credits']

    @admin.action(description='Release/refund selected customer question credits (does not refund provider charges)')
    def refund_credits(self, request, queryset):
        if not self.has_change_permission(request): return
        from .usage import refund
        for row in queryset:
            refund(row.user, row.request_id)
            self.log_change(request, row, 'Customer question credit refunded; provider cost retained.')


@admin.register(ProviderUsage)
class ProviderUsageAdmin(FinanceOnly):
    list_display = ('id', 'request_id', 'sequence', 'model', 'status', 'input_tokens', 'output_tokens', 'rated_cost')
    readonly_fields = tuple(field.name for field in ProviderUsage._meta.fields)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price_usd", "chart_limit", "monthly_question_limit", "max_depth_level", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserProfile)
class UserProfileAdmin(PrivateDataAdmin):
    list_display = ("user", "plan", "bonus_question_credits", "country", "created_at")
    search_fields = ("user__username", "user__email", "birth_name")
