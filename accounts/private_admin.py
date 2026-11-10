from django.contrib import admin


class PrivateDataAdmin(admin.ModelAdmin):
    """Pilot staff permissions never implicitly grant access to birth/chat data."""
    def has_module_permission(self, request): return request.user.is_active and request.user.is_superuser
    def has_view_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_change_permission(self, request, obj=None): return self.has_module_permission(request)
    def has_add_permission(self, request): return self.has_module_permission(request)
    def has_delete_permission(self, request, obj=None): return self.has_module_permission(request)
