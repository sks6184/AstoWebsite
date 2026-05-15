from django.conf import settings
from django.db import models


class SavedChart(models.Model):
    GENDER_CHOICES = [
        ("", "Prefer not to say"),
        ("female", "Female"),
        ("male", "Male"),
        ("non_binary", "Non-binary"),
        ("other", "Other"),
    ]
    MARITAL_STATUS_CHOICES = [
        ("", "Prefer not to say"),
        ("unmarried", "Unmarried"),
        ("married", "Married"),
        ("separated", "Separated"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    birth_date = models.DateField()
    birth_time = models.TimeField()
    birth_place = models.CharField(max_length=160)
    gender = models.CharField(max_length=24, choices=GENDER_CHOICES, blank=True)
    marital_status = models.CharField(max_length=24, choices=MARITAL_STATUS_CHOICES, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    chart_data = models.JSONField(default=dict, blank=True)
    svg_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.birth_date}"


class MonthlyPrediction(models.Model):
    chart = models.ForeignKey(SavedChart, on_delete=models.CASCADE, related_name="monthly_predictions")
    topic = models.CharField(max_length=40)
    month = models.DateField()
    prediction_version = models.CharField(max_length=24, default="v1")
    answer_language = models.CharField(max_length=40, default="English")
    computed_context = models.JSONField(default=dict, blank=True)
    prediction_text = models.TextField()
    model_name = models.CharField(max_length=80, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["month", "topic"]
        constraints = [
            models.UniqueConstraint(
                fields=["chart", "topic", "month", "prediction_version", "answer_language"],
                name="unique_monthly_prediction_cache",
            )
        ]

    def __str__(self):
        return f"{self.chart} - {self.topic} - {self.month:%b %Y}"
