from .localization import SUPPORTED_LANGUAGES, remedy_devotion_note


def auth_flags(request):
    from django.conf import settings

    return {
        "google_login_enabled": bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)
    }


def ui_language(request):
    return {
        "ui_languages": SUPPORTED_LANGUAGES,
        "remedy_devotion_note": remedy_devotion_note("English"),
    }
