from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError


class PilotAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser: raise ValidationError('Operator access is required.', code='invalid_login')


class PilotAdminSite(AdminSite):
    login_form = PilotAdminAuthenticationForm
    def has_permission(self, request):
        return request.user.is_active and request.user.is_staff and request.user.is_superuser
