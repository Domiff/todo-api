"""
Application definition.
https://docs.djangoproject.com/en/6.0/ref/settings/#installed-apps
"""

INSTALLED_APPS = [
    "unfold",
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "adrf",
    "drf_spectacular",
    "corsheaders",
    "todo.apps.TodoConfig",
    "auth_user.apps.AuthUserConfig",
]
