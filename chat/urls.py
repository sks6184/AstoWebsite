from django.urls import path

from . import views


urlpatterns = [
    path('requests/<uuid:request_id>/status/', views.request_status, name='request_status'),
    path('answers/<int:message_id>/evidence/', views.answer_provenance, name='answer_provenance'),
    path('answers/<int:message_id>/feedback/', views.answer_feedback, name='answer_feedback'),
    path("ask/", views.ask_question, name="ask_question"),
    path("history/", views.question_history, name="question_history"),
    path("ask/history/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path("conversations/<int:conversation_id>/followup/", views.conversation_followup, name="conversation_followup"),
    path("conversations/<int:conversation_id>/memory/", views.conversation_memory, name="conversation_memory"),
    path("conversations/<int:conversation_id>/memory/action/", views.conversation_memory_action, name="conversation_memory_action"),
]
