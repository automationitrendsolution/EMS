"""
Django settings for iTrendTASKS.

Architecture notes
------------------
* Domain data lives in MongoDB via MongoEngine (see ``config.mongo``).
* Django's relational ORM is intentionally NOT used for domain models. A tiny
  SQLite database is configured only so that Django's machinery never crashes;
  no app migrations create domain tables.
* Authentication is custom: JWT for the REST API and signed-cookie sessions for
  the server-rendered frontend. See ``accounts.auth``.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, default)).lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    raw = env(key, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", "dev-insecure-secret-key")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0") or ["*"]
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
)

INSTALLED_APPS = [
    "daphne",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    # third party
    "rest_framework",
    "corsheaders",
    "drf_yasg",
    "channels",
    "django_celery_beat",
    # local
    "accounts",
    "projects",
    "tasks",
    "notifications",
    "reports",
    "ai_assistant",
    "dashboard",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.CurrentUserMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.current_user",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# A throwaway SQLite DB: Django needs *a* database configured, but no domain
# models use it. Sessions use signed cookies, so nothing is written here.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "django_internal.sqlite3",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Sessions (no DB) + messages
# ---------------------------------------------------------------------------
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

# ---------------------------------------------------------------------------
# MongoDB (MongoEngine)
# ---------------------------------------------------------------------------
MONGO = {
    "db": env("MONGO_DB", "itrendtasks"),
    "host": env("MONGO_HOST", "localhost"),
    "port": int(env("MONGO_PORT", "27017")),
    "username": env("MONGO_USERNAME") or None,
    "password": env("MONGO_PASSWORD") or None,
    "authentication_source": env("MONGO_AUTH_SOURCE", "admin"),
}

# ---------------------------------------------------------------------------
# Redis / Channels
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.auth.JWTAuthentication",
        "accounts.auth.SessionUserAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "10/min",
        "ai": "20/min",
        "default": "1000/hour",
    },
    "UNAUTHENTICATED_USER": None,
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
    "USE_SESSION_AUTH": False,
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
JWT_SECRET = env("JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_MINUTES = int(env("JWT_ACCESS_MINUTES", "60"))
JWT_REFRESH_DAYS = int(env("JWT_REFRESH_DAYS", "7"))

# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

ALLOWED_UPLOAD_EXTENSIONS = ["pdf", "docx", "xlsx", "zip", "png", "jpg", "jpeg"]
MAX_UPLOAD_SIZE_MB = int(env("MAX_UPLOAD_SIZE_MB", "25"))

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Security (tightened automatically when DEBUG is off)
# ---------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:8000")
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = DEBUG

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "SAMEORIGIN"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGIN_URL = "/login/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
