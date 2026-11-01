from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
)

from auth_user.views import LinkTelegramAPIView, RefreshAPIView, RegisterAPIView

app_name = "auth_user"

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("tg/link/", LinkTelegramAPIView.as_view(), name="tg_link"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", RefreshAPIView.as_view(), name="token_refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
]
