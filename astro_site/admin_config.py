from django.contrib.admin.apps import AdminConfig


class PilotAdminConfig(AdminConfig):
    default_site = 'astro_site.admin_site.PilotAdminSite'
