from django import forms

from .models import SavedChart


class SavedChartForm(forms.ModelForm):
    birth_date = forms.DateField(
        input_formats=["%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"],
        widget=forms.DateInput(
            format="%d-%b-%Y",
            attrs={
                "type": "text",
                "placeholder": "DD-Mon-YYYY",
                "pattern": r"\d{2}-[A-Za-z]{3}-\d{4}",
                "title": "Use DD-Mon-YYYY, for example 06-Jun-1983.",
            },
        ),
        error_messages={
            "invalid": "Enter birth date as DD-Mon-YYYY, for example 06-Jun-1983.",
        },
    )
    timezone = forms.CharField(required=False)

    class Meta:
        model = SavedChart
        fields = [
            "name",
            "birth_date",
            "birth_time",
            "birth_place",
            "gender",
            "marital_status",
            "latitude",
            "longitude",
            "timezone",
        ]
        widgets = {
            "birth_time": forms.TimeInput(attrs={"type": "time"}),
            "birth_place": forms.TextInput(
                attrs={
                    "autocomplete": "off",
                    "data-place-autocomplete": "true",
                    "placeholder": "Start typing a city or town",
                }
            ),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "timezone": forms.TextInput(
                attrs={
                    "autocomplete": "off",
                    "placeholder": "e.g. Asia/Kolkata",
                }
            ),
        }

    def clean_timezone(self):
        return (self.cleaned_data.get("timezone") or "UTC").strip()
