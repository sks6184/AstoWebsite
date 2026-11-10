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


class CreditAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    consumed = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)


class UsageRequest(models.Model):
    """Financial metadata only. No question, birth inputs, answers or retrieved text."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chart = models.ForeignKey('charts.SavedChart', null=True, on_delete=models.SET_NULL)
    conversation = models.ForeignKey('chat.Conversation', null=True, on_delete=models.SET_NULL)
    request_id = models.UUIDField()
    plan = models.CharField(max_length=32)
    policy = models.JSONField(default=dict)
    fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=24, default='reserved')
    stop_reason = models.CharField(max_length=48, blank=True)
    progress = models.CharField(max_length=24, default='queued')
    credits_reserved = models.PositiveIntegerField(default=1)
    credits_consumed = models.PositiveIntegerField(default=0)
    credits_released = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=16, decimal_places=8, default=0)
    actual_cost = models.DecimalField(max_digits=16, decimal_places=8, null=True, blank=True)
    # Actual invoice cost is not inferred from token counts.
    revenue_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    payment_fee_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    infrastructure_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'request_id'], name='unique_user_usage_request')]

    def __str__(self):
        return f'Usage request {self.pk}'


class ProviderUsage(models.Model):
    request = models.ForeignKey(UsageRequest, related_name='provider_calls', on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    model = models.CharField(max_length=100)
    status = models.CharField(max_length=24, default='started')
    tariff = models.JSONField(default=dict)
    estimated_input = models.PositiveIntegerField()
    estimated_output = models.PositiveIntegerField()
    input_tokens = models.PositiveIntegerField(null=True)
    output_tokens = models.PositiveIntegerField(null=True)
    cached_tokens = models.PositiveIntegerField(null=True)
    file_searches = models.PositiveIntegerField(default=0)
    reported_file_searches = models.PositiveIntegerField(null=True)
    reserved_cost = models.DecimalField(max_digits=16, decimal_places=8)
    rated_cost = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    cached_discount = models.DecimalField(max_digits=16, decimal_places=8, default=0)
    error_code = models.CharField(max_length=48, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['request', 'sequence'], name='unique_provider_sequence')]


class PilotMetric(models.Model):
    day = models.DateField()
    event = models.CharField(max_length=32)
    outcome = models.CharField(max_length=24)
    count = models.PositiveIntegerField(default=0)
    elapsed_total_ms = models.PositiveBigIntegerField(default=0)
    elapsed_max_ms = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['day', 'event', 'outcome'], name='unique_pilot_metric')]


class PilotRateBucket(models.Model):
    key = models.CharField(max_length=64, unique=True)
    hits = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()


class AnswerFeedback(models.Model):
    message = models.OneToOneField('chat.Message', on_delete=models.CASCADE)
    vote = models.CharField(max_length=12, choices=[('helpful', 'Helpful'), ('unhelpful', 'Not helpful'), ('unsure', 'Unsure')])
    created_at = models.DateTimeField(auto_now_add=True)
