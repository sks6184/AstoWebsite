from django.urls import path

from . import views


urlpatterns = [
    path("webhook/", views.webhook_placeholder, name="payment_webhook"),
]
