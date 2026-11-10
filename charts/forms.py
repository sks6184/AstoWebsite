from django import forms
from django.utils import timezone as django_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
        value = (self.cleaned_data.get('timezone') or 'UTC').strip()
        try: ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError): raise forms.ValidationError('Choose a valid IANA time zone, such as Asia/Kolkata.')
        return value

    def clean_birth_date(self):
        value = self.cleaned_data['birth_date']
        if value.year < 1800 or value > django_timezone.now().date():
            raise forms.ValidationError('Birth date must be between 1800 and today.')
        return value

    def clean(self):
        values = super().clean()
        latitude, longitude = values.get('latitude'), values.get('longitude')
        if latitude is None or longitude is None:
            self.add_error('birth_place', 'Select a birthplace with valid latitude and longitude before calculating a chart.')
        if latitude is not None and not -90 <= latitude <= 90: self.add_error('latitude', 'Latitude must be between -90 and 90 degrees.')
        if longitude is not None and not -180 <= longitude <= 180: self.add_error('longitude', 'Longitude must be between -180 and 180 degrees.')
        return values
