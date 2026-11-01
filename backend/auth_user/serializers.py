from adrf.serializers import Serializer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from auth_user.models import Profile


class RegisterSerializer(Serializer):
    username = serializers.CharField(
        max_length=150,
        validators=[User.username_validator],
    )
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False)
    tg_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        user = User(username=attrs["username"], email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    async def acreate(self, validated_data):
        return await sync_to_async(self._create)(validated_data)

    def _create(self, validated_data):
        username = validated_data["username"]
        email = validated_data.get("email")
        tg_id = validated_data.get("tg_id")

        errors = {}
        if User.objects.filter(username=username).exists():
            errors["username"] = ["This username is already taken."]
        if email and Profile.objects.filter(email=email).exists():
            errors["email"] = ["This email is already taken."]
        if tg_id and Profile.objects.filter(tg_id=tg_id).exists():
            errors["tg_id"] = ["This Telegram account is already registered."]
        if errors:
            raise serializers.ValidationError(errors)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=validated_data["password"],
                    email=email or "",
                )
                Profile.objects.create(user=user, email=email, tg_id=tg_id)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"username": ["This account already exists."]}
            ) from error
        return user

    async def ato_representation(self, user):
        tokens = await sync_to_async(RefreshToken.for_user)(user)
        return {
            "id": user.id,
            "tokens": {
                "refresh": str(tokens),
                "access": str(tokens.access_token),
            },
        }


class LinkTelegramSerializer(Serializer):
    tg_id = serializers.IntegerField(min_value=1)
