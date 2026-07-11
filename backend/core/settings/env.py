"""
Environment variables (django-environ).
https://django-environ.readthedocs.io/
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),

    CSRF_TRUSTED_ORIGINS=(list, []),
    CSRF_COOKIE_SECURE=(bool, True),
    SESSION_COOKIE_SECURE=(bool, True),
    SECURE_SSL_REDIRECT=(bool, True),
    SECURE_HSTS_SECONDS=(int, 31536000),
    SECURE_HSTS_PRELOAD=(bool, True),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, True),

    POSTGRES_DB=(str, ""),
    POSTGRES_USER=(str, ""),
    POSTGRES_PASSWORD=(str, ""),
    POSTGRES_HOST=(str, ""),
    POSTGRES_PORT=(int, 5432),
)

environ.Env.read_env(BASE_DIR.parent / ".env")
