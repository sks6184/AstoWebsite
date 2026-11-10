from django import forms

from astro_site.localization import SUPPORTED_LANGUAGES


def question_byte_limit(value):
    if len(value.encode('utf-8')) > 4096:
        raise forms.ValidationError('Questions must be at most 4096 UTF-8 bytes.')

class AskQuestionForm(forms.Form):
    request_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    chart_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    answer_language = forms.ChoiceField(
        choices=SUPPORTED_LANGUAGES,
        initial="English",
        label="Answer language",
    )
    question = forms.CharField(max_length=4096, validators=[question_byte_limit], widget=forms.Textarea(attrs={"rows": 4}))
    memory_enabled = forms.BooleanField(required=False, label="Use this conversation’s earlier messages for follow-ups")


class FollowUpForm(forms.Form):
    question = forms.CharField(max_length=4096, validators=[question_byte_limit], widget=forms.Textarea(attrs={"rows": 3}))
    request_id = forms.UUIDField(widget=forms.HiddenInput)
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    kind = forms.ChoiceField(choices=[("question", "Question"), ("user_fact", "User-supplied fact or constraint"), ("correction", "Correction to an earlier statement")])
    supersedes_message_id = forms.IntegerField(required=False, min_value=1, label="Corrected message number (optional)")
    reference_message_id = forms.IntegerField(required=False, min_value=1, label="Older message to include (optional)")
