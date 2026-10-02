# -*- coding: utf-8 -*-
"""پیکربندی Django برای بازی وب «جنگ جهانی».

نسخه وب همان منطق نسخه تلگرام (پوشه ww3) را سمت سرور اجرا می‌کند؛
تمام قوانین بازی در این backend قرار دارد و فرانت فقط رابط کاربری است.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


def env(key, default=""):
    return os.environ.get(key, default)


def env_bool(key, default="0"):
    return env(key, default).lower() in ("1", "true", "yes", "on")

SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,web,nginx").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in env("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if o]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
    "drf_spectacular",
    "django_filters",
    "django_celery_beat",
    # project
    "accounts",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------- Database ----------
if env_bool("USE_SQLITE", "0") or not env("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "ww3"),
            "USER": env("POSTGRES_USER", "ww3"),
            "PASSWORD": env("POSTGRES_PASSWORD", "ww3"),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

# ---------- Cache / Channels / Celery ----------
REDIS_URL = env("REDIS_URL", "redis://redis:6379/0")

if env_bool("USE_SQLITE", "0") or not env("POSTGRES_HOST"):
    # توسعه بدون Redis: کش محلی و channel layer in-memory
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", "0")
CELERY_BEAT_SCHEDULE = {
    # سود شبانه ساعت ۲۲:۰۰ — مطابق نسخه تلگرام
    "daily-profit-22": {"task": "core.services.tick.task_daily_profit", "schedule": 3600.0},
    # آسیب و کاهش مدت ویروس‌ها — یک بار در هر روز بازی
    "virus-damage-hourly": {"task": "core.services.tick.task_virus_damage", "schedule": 3600.0},
    # انتشار تصادفی ویروس هر ۶ ساعت (شانس ۱۵٪) — مطابق نسخه تلگرام
    "virus-spread-6h": {"task": "core.services.tick.task_spread_virus", "schedule": 21600.0},
    # آتش‌سوزی بمب آتش‌زا — روزانه
    "fire-burn-hourly": {"task": "core.services.tick.task_fire_burn", "schedule": 3600.0},
    # جنگ زمان‌بندی‌شده: هر ۵ دقیقه چک می‌شود
    "war-schedule-check": {"task": "core.services.tick.task_check_war_schedule", "schedule": 300.0},
}

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "core.api.throttling.GameRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth": "30/min",
        "game": "300/min",
        "admin": "600/min",
    },
}

SPECTACULAR_SETTINGS = {"TITLE": "WW3 Web Game API", "VERSION": "1.0.0"}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = [o for o in env(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:4173,http://localhost:8080",
).split(",") if o]
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = env("TIME_ZONE", "Asia/Tehran")
USE_I18N = True
# TZ فعال — tick.py از timezone.localtime() برای سود ۲۲:۰۰ استفاده می‌کند
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- تنظیمات بازی (معادل ww3/config.py) ----------
GAME = {
    "TELEGRAM_BOT_TOKEN": env("BOT_TOKEN", ""),
    "TELEGRAM_BOT_USERNAME": env("BOT_USERNAME", "WWar3_bot"),
    "MAIN_ADMIN_TELEGRAM_ID": env("MAIN_ADMIN_ID", "6254295276"),
    # محدودیت‌ها — دقیقاً مطابق نسخه تلگرام
    "ATTACK_LIMIT": 4,
    "ATTACK_WINDOW": 86400,
    "STATEMENT_LIMIT": 4,
    "STATEMENT_WINDOW": 86400,
    "UNION_DONATION_LIMITS": {1: 20000, 2: 50000, 3: 70000, 4: 90000, 5: 110000},
    "MAX_ITEM_DONATION": 100,
    "MAX_ECONOMIC_ITEMS": 100,
    "DONATION_COOLDOWN": 172800,  # 48 ساعت
    "BASE_PRICE": 20000,
    "BASE_BUILD_SECONDS": 1800,
    "BASE_PERMISSION_TIMEOUT": 300,
    "PAYMENT_REQUEST_TIMEOUT": 3600,
    "INDUSTRIAL_COMPANY_PROFIT": 70000,
    "START_CREDIT": 10000,
    "START_DEFENSE": 5000,
    "START_POPULATION": 10000,
    "VIRUS_START_DAY": 5,
    "VIRUS_DURATION_DAYS": 5,
    "VIRUS_SPREAD_CHANCE": 0.15,
}

# تلگرام لاگین: توکن ربات جهت verifyLoginWidget (HMAC)
TELEGRAM_LOGIN_BOT_TOKEN = env("TELEGRAM_LOGIN_BOT_TOKEN", env("BOT_TOKEN", ""))

# Security (production)
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", "0")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
