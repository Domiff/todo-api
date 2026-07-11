"""
CORS settings (django-cors-headers).
https://github.com/adamchainz/django-cors-headers
"""

from .env import env

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
