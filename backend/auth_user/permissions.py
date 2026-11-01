import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


def is_bot_request(request) -> bool:
    key = settings.BOT_API_KEY
    return bool(key) and hmac.compare_digest(
        request.headers.get("X-Bot-Key", "").encode(), key.encode()
    )


class IsBot(BasePermission):
    def has_permission(self, request, view):
        return is_bot_request(request)
