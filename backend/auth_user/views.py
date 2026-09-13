from adrf.generics import CreateAPIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from auth_user.serializers import TgProfileSerializer, WebProfileSerializer


class TgRegisterAPIView(CreateAPIView):
    serializer_class = TgProfileSerializer
    permission_classes = (AllowAny,)

    async def create(self, request, *args, **kwargs):
        serializer = TgProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = await serializer.ato_representation(user)
        return Response(data, status=status.HTTP_201_CREATED)


class WebRegisterAPIView(CreateAPIView):
    serializer_class = WebProfileSerializer
    permission_classes = (AllowAny,)

    async def create(self, request, *args, **kwargs):
        serializer = WebProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = await serializer.ato_representation(user)
        return Response(data, status=status.HTTP_201_CREATED)
