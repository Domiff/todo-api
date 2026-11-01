from adrf.serializers import Serializer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from auth_user.models import Profile


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
        profile = (
            await Profile.objects.filter(tg_id=tg_id).select_related("user").afirst()
        )

        if profile:
            user = profile.user
        else:
            user = await User.objects.acreate_user(
                username=f"tg-{tg_id}",
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
            )
            await Profile.objects.acreate(user=user, tg_id=tg_id)
        return user


class WebProfileSerializer(BaseProfileSerializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    async def acreate(self, validated_data):
        username = validated_data["username"]
        email = validated_data["email"]
        profile = (
            await Profile.objects.filter(user__username=username)
            .select_related("user")
            .afirst()
        )

        if profile:
            user = profile.user
        else:
            user = await User.objects.acreate_user(
                username=username,
                password=validated_data["password"],
                email=email,
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
            )
            await Profile.objects.acreate(user=user, email=email)
        return user
