from django import forms

from .models import Conversation


ANSWER_LANGUAGE_CHOICES = [
    ("English", "English"),
    ("Hindi", "Hindi"),
    ("Telugu", "Telugu"),
    ("Marathi", "Marathi"),
    ("Kannada", "Kannada"),
    ("Tamil", "Tamil"),
    ("Bengali", "Bengali"),
    ("Vietnamese", "Vietnamese"),
    ("Mandarin", "Mandarin"),
    ("Malay", "Malay"),
]


class AskQuestionForm(forms.Form):
    chart_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    depth_level = forms.ChoiceField(choices=Conversation.DEPTH_CHOICES)
    answer_language = forms.ChoiceField(choices=ANSWER_LANGUAGE_CHOICES, initial="English")
    question = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
