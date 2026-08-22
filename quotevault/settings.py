import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-secure-memora-vault-key-prod-dev-fallback-2026-a1b2c3d4e5f6g7h8i9j0"
)
DEBUG = os.environ.get("DEBUG", "False") == "True"
INTERNAL_IPS = ["127.0.0.1", "::1"]

# Production Security & Reverse Proxy Settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    f"https://{h}" for h in ALLOWED_HOSTS if h and h != "*" and h not in ("127.0.0.1", "localhost")
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
CSRF_TRUSTED_ORIGINS.append("https://*.onrender.com")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "quotes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "quotevault.urls"

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

WSGI_APPLICATION = "quotevault.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=os.environ.get("DATABASE_URL", "").startswith("postgres"),
    )
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

import sys

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if (DEBUG or "test" in sys.argv)
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# VAPID Web Push Keys Configuration
import json
VAPID_KEY_FILE = BASE_DIR / ".vapid_keys.json"

if os.environ.get("VAPID_PUBLIC_KEY") and os.environ.get("VAPID_PRIVATE_KEY"):
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
elif VAPID_KEY_FILE.exists():
    try:
        with open(VAPID_KEY_FILE, "r") as f:
            _vapid_data = json.load(f)
            VAPID_PUBLIC_KEY = _vapid_data.get("public_key", "")
            VAPID_PRIVATE_KEY = _vapid_data.get("private_key", "")
    except Exception:
        VAPID_PUBLIC_KEY = ""
        VAPID_PRIVATE_KEY = ""
else:
    try:
        from py_vapid import Vapid
        from cryptography.hazmat.primitives import serialization
        import base64
        _vapid = Vapid()
        _vapid.generate_keys()
        _raw_pub = _vapid.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )
        VAPID_PUBLIC_KEY = base64.urlsafe_b64encode(_raw_pub).rstrip(b'=').decode('utf-8')
        VAPID_PRIVATE_KEY = _vapid.private_pem().decode('utf-8')
        with open(VAPID_KEY_FILE, "w") as f:
            json.dump({"public_key": VAPID_PUBLIC_KEY, "private_key": VAPID_PRIVATE_KEY}, f)
    except Exception:
        VAPID_PUBLIC_KEY = ""
        VAPID_PRIVATE_KEY = ""

VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "admin@memora.vault")

