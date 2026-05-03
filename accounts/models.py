from django.conf import settings
from django.db import models


class Plan(models.Model):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"

    SLUG_CHOICES = [
        (FREE, "Free"),
        (BASIC, "$5 Deep Reading"),
        (PREMIUM, "$10 Full Analysis"),
    ]

    slug = models.SlugField(max_length=32, choices=SLUG_CHOICES, unique=True)
    name = models.CharField(max_length=80)
    price_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    chart_limit = models.PositiveIntegerField(default=1)
    monthly_question_limit = models.PositiveIntegerField(default=2)
    max_depth_level = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_usd", "id"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True)
    bonus_question_credits = models.PositiveIntegerField(default=0)
    birth_name = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} profile"

    @property
    def current_plan(self):
        return self.plan
