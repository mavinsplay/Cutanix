import os
from pathlib import Path
import sys

from dotenv import load_dotenv

from cutanix.utils import get_bool_env

load_dotenv()

__all__ = []

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-cutanix-dev-key-change-in-production",
)

DEBUG = get_bool_env(
    os.getenv("DJANGO_DEBUG", "true"),
)

ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1",
).split(",")

CSRF_TRUSTED_ORIGINS = os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost,http://127.0.0.1",
).split(",")

SITE_URL = os.getenv(
    "DJANGO_SITE_URL", "http://127.0.0.1:8000",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "users",
    "analysis",
    "payments",
    "api",
    "bot",
    "webapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cutanix.urls"

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django"
            ".DjangoTemplates"
        ),
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                (
                    "django.contrib.auth.context_processors"
                    ".auth"
                ),
                (
                    "django.contrib.messages.context_processors"
                    ".messages"
                ),
            ],
        },
    },
]

WSGI_APPLICATION = "cutanix.wsgi.application"
ASGI_APPLICATION = "cutanix.asgi.application"

DB = os.getenv("DJANGO_SELECTED_DB", "sqlite")

if DB == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": (
                "django.db.backends.postgresql"
            ),
            "NAME": os.getenv(
                "POSTGRES_DB", "cutanix_db",
            ),
            "USER": os.getenv(
                "POSTGRES_USER", "postgres",
            ),
            "PASSWORD": os.getenv(
                "POSTGRES_PASSWORD", "root",
            ),
            "HOST": os.getenv(
                "POSTGRES_HOST", "localhost",
            ),
            "PORT": int(
                os.getenv("POSTGRES_PORT", "5432"),
            ),
        },
    }

if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": (
                "django.db.backends.sqlite3"
            ),
            "NAME": ":memory:",
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".NumericPasswordValidator"
        ),
    },
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [
    BASE_DIR / "static_dev",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.auth.TelegramAuth",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination"
        ".PageNumberPagination"
    ),
    "PAGE_SIZE": 20,
}

CORS_ALLOW_ALL_ORIGINS = DEBUG

IS_REDIS = get_bool_env(
    os.getenv("DJANGO_USE_REDIS", "false"),
)
CELERY_ALWAYS_EAGER = get_bool_env(
    os.getenv("CELERY_ALWAYS_EAGER", "false"),
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

if REDIS_PASSWORD:
    REDIS_URI = (
        f"redis://:{REDIS_PASSWORD}"
        f"@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    )
else:
    REDIS_URI = (
        f"redis://{REDIS_HOST}:{REDIS_PORT}"
        f"/{REDIS_DB}"
    )

if IS_REDIS:
    CACHES = {
        "default": {
            "BACKEND": (
                "django.core.cache.backends"
                ".locmem.LocMemCache"
            ),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": (
                "django_redis.cache.RedisCache"
            ),
            "LOCATION": REDIS_URI,
            "OPTIONS": {
                "CLIENT_CLASS": (
                    "django_redis.client.DefaultClient"
                ),
            },
        },
    }

CELERY_TASK_ALWAYS_EAGER = CELERY_ALWAYS_EAGER
CELERY_BROKER_URL = REDIS_URI
CELERY_RESULT_BACKEND = "rpc://"
CELERY_TASK_IGNORE_RESULT = True
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "",
)
TELEGRAM_CHANNEL_ID = os.getenv(
    "TELEGRAM_CHANNEL_ID", "",
)
ADMIN_TELEGRAM_IDS = [
    int(tid.strip())
    for tid in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if tid.strip().isdigit()
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TOGETHER_API_KEY = os.getenv(
    "TOGETHER_API_KEY", "",
)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "[{levelname}] {asctime} "
                "{name}: {message}"
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "debug.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": [
                "console",
                "file" if DEBUG else "console",
            ],
            "level": "INFO",
            "propagate": True,
        },
        "api": {
            "handlers": ["console"],
            "level": (
                "DEBUG" if DEBUG else "WARNING"
            ),
            "propagate": False,
        },
        "bot": {
            "handlers": ["console"],
            "level": (
                "DEBUG" if DEBUG else "WARNING"
            ),
            "propagate": False,
        },
    },
}

if DEBUG:
    INSTALLED_APPS.insert(0, "debug_toolbar")
    INTERNAL_IPS = ["127.0.0.1"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

    def _show_toolbar(request):
        """Show toolbar only on admin and __debug__ routes."""
        return (
            request.path.startswith("/admin/")
            or request.path.startswith("/__debug__/")
        )

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": _show_toolbar,
    }
