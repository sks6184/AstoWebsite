from django import forms

from astro_site.localization import SUPPORTED_LANGUAGES

from .models import Conversation


class AskQuestionForm(forms.Form):
    chart_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    depth_level = forms.ChoiceField(choices=Conversation.DEPTH_CHOICES)
    answer_language = forms.ChoiceField(
        choices=SUPPORTED_LANGUAGES,
        initial="English",
        label="Answer language",
    )
    question = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
