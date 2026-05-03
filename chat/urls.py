from django.urls import path

from . import views


urlpatterns = [
    path("ask/", views.ask_question, name="ask_question"),
    path("history/", views.question_history, name="question_history"),
    path("ask/history/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
]
