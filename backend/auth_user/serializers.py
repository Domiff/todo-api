from adrf.serializers import Serializer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from auth_user.models import TgProfile, WebProfile


class BaseProfileSerializer(Serializer):
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    async def ato_representation(self, user):
        tokens = await sync_to_async(RefreshToken.for_user)(user)
        return {
            "id": user.id,
            "tokens": {
                "refresh": str(tokens),
                "access": str(tokens.access_token),
            },
        }


class TgProfileSerializer(BaseProfileSerializer):
    tg_id = serializers.IntegerField()

    async def acreate(self, validated_data):
        tg_id = validated_data["tg_id"]
        tg_profile = (
            await TgProfile.objects.filter(tg_id=tg_id).select_related("user").afirst()
        )

        if tg_profile:
            user = tg_profile.user
        else:
            user = await User.objects.acreate_user(username=f"tg-{tg_id}")
            await TgProfile.objects.acreate(user=user, **validated_data)
        return user


class WebProfileSerializer(BaseProfileSerializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    async def acreate(self, validated_data):
        username = validated_data["username"]
        password = validated_data.pop("password")
        email = validated_data["email"]
        web_profile = (
            await WebProfile.objects.filter(username=username)
            .select_related("user")
            .afirst()
        )

        if web_profile:
            user = web_profile.user
        else:
            user = await User.objects.acreate_user(
                username=username, password=password, email=email,
            )
            await WebProfile.objects.acreate(user=user, **validated_data)
        return user
