"""Explicit production profile; development .env and tunnel hosts are not deployment defaults."""
from .settings import *
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse

DEBUG = False
if os.getenv('DJANGO_DEBUG', 'false').lower() == 'true':
    raise ImproperlyConfigured('Production requires DJANGO_DEBUG=false.')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith(('dev-', 'django-insecure-')):
    raise ImproperlyConfigured('Set a strong production DJANGO_SECRET_KEY.')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
if not ALLOWED_HOSTS or any('*' in h or h.startswith('.') or '/' in h or ':' in h or 'ngrok' in h or h in ('localhost', '127.0.0.1', '0.0.0.0', 'testserver') for h in ALLOWED_HOSTS):
    raise ImproperlyConfigured('Configure exact production DNS hosts; development/tunnel hosts are not allowed.')
if not os.getenv('DATABASE_URL', '').startswith(('postgres://', 'postgresql://')):
    raise ImproperlyConfigured('Production requires an explicit PostgreSQL DATABASE_URL.')
CSRF_TRUSTED_ORIGINS = ['https://' + h for h in ALLOWED_HOSTS]
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 43200
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
USE_X_FORWARDED_HOST = False
ENFORCE_QUESTION_LIMITS = True
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'pilot_cache', 'TIMEOUT': 120}}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', '')
if not EMAIL_HOST or not DEFAULT_FROM_EMAIL:
    raise ImproperlyConfigured('Configure production verification email delivery.')
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_ADAPTER = 'accounts.pilot_adapter.PilotAccountAdapter'
SOCIALACCOUNT_LOGIN_ON_GET = False
ASTROGPT_PILOT_SIGNUPS_RESTRICTED = True
ASTROGPT_PILOT_EMAILS = tuple(e.strip().casefold() for e in os.getenv('ASTROGPT_PILOT_EMAILS', '').split(',') if e.strip())
if not ASTROGPT_PILOT_EMAILS: raise ImproperlyConfigured('Configure a limited pilot invitation list.')
LOGGING['root'] = {'handlers': ['safe_console'], 'level': 'INFO'}
for component in ('django', 'django.request', 'django.security', 'django.server', 'openai', 'httpx'):
    LOGGING['loggers'][component] = {'handlers': ['safe_console'], 'level': 'WARNING', 'propagate': False}
