"""Minimal settings for the incremental Django migration."""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-local-development-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "polskiflow.learning",
]

MIDDLEWARE = [
    "polskiflow.auth_cache.AuthFormCacheMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "polskiflow.request_id.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "polskiflow.auth.SupabaseAuthMiddleware",
]
ROOT_URLCONF = "polskiflow.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "polskiflow.pwa_version.pwa_shell_context",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "polskiflow.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if database_url := os.environ.get("DATABASE_URL"):
    parsed_database_url = urlparse(database_url)
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed_database_url.path.lstrip("/")),
        "USER": unquote(parsed_database_url.username or ""),
        "PASSWORD": unquote(parsed_database_url.password or ""),
        "HOST": parsed_database_url.hostname or "",
        "PORT": parsed_database_url.port or 5432,
        "CONN_MAX_AGE": int(os.environ.get("DATABASE_CONN_MAX_AGE", "0")),
        "OPTIONS": {"sslmode": "require", "prepare_threshold": None},
    }

LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский"), ("pl", "Polski"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60
LANGUAGE_COOKIE_HTTPONLY = True
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGE_COOKIE_SECURE = not DEBUG
TIME_ZONE = os.environ.get("APP_TIME_ZONE", "Europe/Warsaw")
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DATABASE_ROUTERS = ["polskiflow.learning.router.SupabaseSchemaRouter"]

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_AUTH_TIMEOUT = float(os.environ.get("SUPABASE_AUTH_TIMEOUT", "5"))
SUPABASE_AUTH_NETWORK_ATTEMPTS = int(
    os.environ.get("SUPABASE_AUTH_NETWORK_ATTEMPTS", "3")
)
SUPABASE_AUTH_RETRY_BACKOFF = float(
    os.environ.get("SUPABASE_AUTH_RETRY_BACKOFF", "0.2")
)
VERCEL = os.environ.get("VERCEL", "") == "1"
REQUEST_SLOW_THRESHOLD_MS = int(os.environ.get("REQUEST_SLOW_THRESHOLD_MS", "1500"))
AUTH_FORM_RATE_LIMITS = {
    "login": (int(os.environ.get("AUTH_LOGIN_ATTEMPTS", "10")), 15 * 60),
    "register": (int(os.environ.get("AUTH_REGISTER_ATTEMPTS", "5")), 60 * 60),
    "forgot": (int(os.environ.get("AUTH_RECOVERY_ATTEMPTS", "5")), 60 * 60),
    "resend": (int(os.environ.get("AUTH_RESEND_ATTEMPTS", "5")), 60 * 60),
    "delete": (int(os.environ.get("AUTH_DELETE_ATTEMPTS", "5")), 60 * 60),
}
API_MUTATION_RATE_LIMITS = {
    "answer": (int(os.environ.get("API_ANSWER_ATTEMPTS", "180")), 60),
    "profile": (int(os.environ.get("API_PROFILE_ATTEMPTS", "30")), 60),
    "sm2": (int(os.environ.get("API_SM2_ATTEMPTS", "180")), 60),
    "dictionary": (int(os.environ.get("API_DICTIONARY_ATTEMPTS", "90")), 60),
    "bookmark": (int(os.environ.get("API_BOOKMARK_ATTEMPTS", "90")), 60),
    "draft": (int(os.environ.get("API_DRAFT_ATTEMPTS", "180")), 60),
    "result": (int(os.environ.get("API_RESULT_ATTEMPTS", "120")), 60),
    "feedback": (int(os.environ.get("API_FEEDBACK_ATTEMPTS", "20")), 60),
    "account": (int(os.environ.get("API_ACCOUNT_ATTEMPTS", "5")), 60 * 60),
}
AUTH_COOKIE_SECURE = os.environ.get("AUTH_COOKIE_SECURE", str(not DEBUG)).lower() == "true"
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE
SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS", "https://*.vercel.app"
    ).split(",")
    if origin
]
SECURE_SSL_REDIRECT = os.environ.get(
    "DJANGO_SECURE_SSL_REDIRECT", str(not DEBUG)
).lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "false"
).lower() == "true"
SECURE_HSTS_PRELOAD = os.environ.get(
    "DJANGO_SECURE_HSTS_PRELOAD", "false"
).lower() == "true"
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "polskiflow.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        }
    },
}
