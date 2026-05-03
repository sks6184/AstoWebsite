from django.conf import settings
from django.db import models

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
    depth_level = models.PositiveSmallIntegerField(choices=DEPTH_CHOICES, default=QUICK)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Conversation {self.pk}"


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

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
