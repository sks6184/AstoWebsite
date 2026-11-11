from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
if os.getenv('DJANGO_SETTINGS_MODULE') != 'astro_site.production':
    load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
# S-5: never run with DEBUG off on the development secret (or a weak one).
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("dev-", "django-insecure-"))):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("DJANGO_DEBUG is false but DJANGO_SECRET_KEY is missing or a development value.")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID", "").strip()
ASTROGPT_ANSWER_STYLE = os.getenv("ASTROGPT_ANSWER_STYLE", "").strip()
ENFORCE_QUESTION_LIMITS = os.getenv("ENFORCE_QUESTION_LIMITS", "True").lower() == "true"
FREE_QUESTION_CREDITS = int(os.getenv("FREE_QUESTION_CREDITS", "2"))
BASIC_QUESTION_CREDITS = int(os.getenv("BASIC_QUESTION_CREDITS", "5"))
PREMIUM_QUESTION_CREDITS = int(os.getenv("PREMIUM_QUESTION_CREDITS", "10"))
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if os.getenv('ASTROGPT_TRUST_PROXY') == 'true' else None
USE_X_FORWARDED_HOST = False

INSTALLED_APPS = [
    "astro_site.admin_config.PilotAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "accounts",
    "charts",
    "chat",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "astro_site.pilot_middleware.PilotMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "astro_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "astro_site.context_processors.auth_flags",
                "astro_site.context_processors.ui_language",
            ],
        },
    },
]

WSGI_APPLICATION = "astro_site.wsgi.application"

database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    DATABASES = {
        "default": dj_database_url.parse(database_url, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "post_login_redirect"
LOGOUT_REDIRECT_URL = "home"
ACCOUNT_LOGIN_REDIRECT_URL = "post_login_redirect"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.AutoUsernameSocialAccountAdapter"
SOCIALACCOUNT_LOGIN_ON_GET = True
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APPS": [
            {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "key": "",
            }
        ],
    }
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# P3 is opt-in; disabling this flag preserves the existing one-shot pipeline.
ASTROGPT_AGENT_ENABLED = os.getenv("ASTROGPT_AGENT_ENABLED", "false").lower() in {"1", "true", "yes"}
# M3 (A7): only these usernames or e-mail addresses reach the general agent; empty by default, so every
# existing and new user stays on legacy until explicitly added. Rollback: remove the account.
ASTROGPT_AGENT_USERS = tuple(u.strip().casefold() for u in os.getenv("ASTROGPT_AGENT_USERS", "").split(",") if u.strip())
# M3: the earlier P3 career slice is reachable only through this explicit compatibility setting (off by default).
ASTROGPT_AGENT_P3_COMPAT = os.getenv("ASTROGPT_AGENT_P3_COMPAT", "false").lower() in {"1", "true", "yes"}
# M2: retrieval adapter for the agent knowledge tool ("hosted" file_search or "direct" vector-store search).
# M2-AC5 (owner, provisional, 2026-11-11): direct vector-store search. Rollback: set ASTROGPT_RETRIEVAL_ADAPTER=hosted.
ASTROGPT_RETRIEVAL_ADAPTER = os.getenv("ASTROGPT_RETRIEVAL_ADAPTER", "direct").strip() or "direct"
ASTROGPT_RATE_LIMITS_ENABLED = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536
ASTROGPT_TRANSCRIPT_RETENTION_DAYS = 30
ASTROGPT_METRIC_RETENTION_DAYS = 90
LOGGING = {'version': 1, 'disable_existing_loggers': False,
    'formatters': {'safe': {'()': 'astro_site.pilot_middleware.SafeJsonFormatter'}},
    'handlers': {'safe_console': {'class': 'logging.StreamHandler', 'formatter': 'safe'}},
    'loggers': {'astrogpt.operations': {'handlers': ['safe_console'], 'level': 'INFO', 'propagate': False}}}
