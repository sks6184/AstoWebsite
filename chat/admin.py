from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "depth_level", "answer_language", "chart", "updated_at")
    list_filter = ("depth_level", "answer_language", "created_at")
    search_fields = ("title", "user__username", "user__email")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "model_name", "created_at")
    list_filter = ("role", "model_name", "created_at")
    search_fields = ("content",)
