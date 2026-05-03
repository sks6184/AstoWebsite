from django.conf import settings
from django.db import models


class PaymentEvent(models.Model):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"

    GATEWAY_CHOICES = [
        (STRIPE, "Stripe"),
        (RAZORPAY, "Razorpay"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    gateway = models.CharField(max_length=24, choices=GATEWAY_CHOICES)
    external_id = models.CharField(max_length=160, blank=True)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.gateway} {self.event_type}"
