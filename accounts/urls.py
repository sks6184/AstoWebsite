from django.urls import path

from . import views


urlpatterns = [
    path('pilot/analytics/', views.pilot_analytics, name='pilot_analytics'),
    path('privacy/delete/', views.account_delete, name='account_delete'),
    path('contribution/', views.contribution_dashboard, name='contribution_dashboard'),
    path("start/", views.post_login_redirect, name="post_login_redirect"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
