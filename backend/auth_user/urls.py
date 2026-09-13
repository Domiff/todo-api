from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from auth_user.views import TgRegisterAPIView, WebRegisterAPIView

app_name = "auth_user"

urlpatterns = [
    path("tg/register/", TgRegisterAPIView.as_view(), name="tg_register"),
    path("web/register/", WebRegisterAPIView.as_view(), name="web_register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
]
