from adrf.generics import CreateAPIView
from adrf.views import APIView
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView

from auth_user.models import Profile
from auth_user.permissions import IsBot, is_bot_request
from auth_user.serializers import LinkTelegramSerializer, RegisterSerializer


class RegisterAPIView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    async def acreate(self, request, *args, **kwargs):
        if "tg_id" in request.data and not is_bot_request(request):
            raise PermissionDenied("tg_id is accepted only from the bot.")
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = await serializer.asave()
        data = await serializer.ato_representation(user)
        return Response(data, status=status.HTTP_201_CREATED)


class LinkTelegramAPIView(APIView):
    permission_classes = (IsAuthenticated, IsBot)

    async def post(self, request):
        serializer = LinkTelegramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tg_id = serializer.validated_data["tg_id"]

        profile, _ = await Profile.objects.aget_or_create(user=request.user)
        if profile.tg_id == tg_id:
            return Response({"tg_id": tg_id})
        if profile.tg_id is not None:
            raise ValidationError(
                {"tg_id": ["This account is linked to another Telegram account."]}
            )

        taken = {"tg_id": ["This Telegram account is linked to another user."]}
        if await Profile.objects.filter(tg_id=tg_id).aexists():
            raise ValidationError(taken)
        profile.tg_id = tg_id
        try:
            await profile.asave(update_fields=["tg_id"])
        except IntegrityError as error:
            raise ValidationError(taken) from error
        return Response({"tg_id": tg_id})


class RefreshAPIView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except User.DoesNotExist as error:
            raise InvalidToken("User no longer exists.") from error
