from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from charts.models import SavedChart


class Conversation(models.Model):
    QUICK = 1
    DEEP = 2
    FULL = 3

    DEPTH_CHOICES = [
        (QUICK, "Quick Insight"),
        (DEEP, "Deep Reading"),
        (FULL, "Full Analysis"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chart = models.ForeignKey(SavedChart, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=160, blank=True)
    depth_level = models.PositiveSmallIntegerField(choices=DEPTH_CHOICES, default=FULL)
    answer_language = models.CharField(max_length=40, default="English")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    memory_enabled = models.BooleanField(default=False)
    memory_consent_at = models.DateTimeField(null=True, blank=True)
    memory_summary = models.JSONField(default=dict, blank=True)
    memory_epoch = models.PositiveIntegerField(default=0)
    memory_floor = models.PositiveBigIntegerField(default=0)
    revision = models.PositiveIntegerField(default=0)
    active_request = models.UUIDField(null=True, blank=True)
    active_since = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation {self.pk}"

    def clean(self):
        super().clean()
        if self.chart_id and self.user_id and self.chart.user_id != self.user_id:
            raise ValidationError('The chart must belong to the conversation owner.')
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values('user_id', 'chart_id').first()
            if previous and (previous['user_id'] != self.user_id or previous['chart_id'] != self.chart_id) and self.messages.exists():
                raise ValidationError('Start a new conversation to change the owner or chart after messages exist.')

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class Message(models.Model):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    ROLE_CHOICES = [
        (USER, "User"),
        (ASSISTANT, "Assistant"),
        (SYSTEM, "System"),
    ]

    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    model_name = models.CharField(max_length=80, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=24, default="question", choices=[
        ("question", "Question"), ("user_fact", "User-supplied fact"),
        ("correction", "User correction"), ("interpretation", "Preliminary interpretation"),
    ])
    provenance = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role} message {self.pk}"


class ConsultationTurn(models.Model):
    """Payload-free request identity plus message references; no duplicate question text."""
    conversation = models.ForeignKey(Conversation, related_name="turns", on_delete=models.CASCADE)
    request_id = models.UUIDField()
    sequence = models.PositiveIntegerField()
    epoch = models.PositiveIntegerField()
    state = models.CharField(max_length=16, default="pending", choices=[
        ("pending", "Pending"), ("complete", "Complete"), ("failed", "Failed"), ("cancelled", "Cancelled"),
    ])
    user_message = models.OneToOneField(Message, null=True, blank=True, related_name="user_turn", on_delete=models.SET_NULL)
    assistant_message = models.OneToOneField(Message, null=True, blank=True, related_name="assistant_turn", on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(fields=["conversation", "request_id"], name="chat_turn_request_unique"),
            models.UniqueConstraint(fields=["conversation", "sequence"], name="chat_turn_sequence_unique"),
        ]


class ErasedAnswerUsage(models.Model):
    """Aggregate only: privacy deletion must not reset existing question allowances."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    count = models.PositiveIntegerField(default=0)
