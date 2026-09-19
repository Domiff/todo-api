from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from auth_user.models import TgProfile, WebProfile

TG_REGISTER_URL = "/auth/tg/register/"
WEB_REGISTER_URL = "/auth/web/register/"
TOKEN_URL = "/auth/token/"
REFRESH_URL = "/auth/token/refresh/"
BLACKLIST_URL = "/auth/token/blacklist/"
TASKS_URL = "/api/tasks/"


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
)
class AuthAPITestCase(APITestCase):
    def assert_tokens(self, data):
        self.assertEqual(set(data), {"id", "tokens"})
        self.assertEqual(set(data["tokens"]), {"access", "refresh"})


class TgRegisterTests(AuthAPITestCase):
    payload = {
        "username": "tg_user",
        "first_name": "First",
        "last_name": "Last",
        "tg_id": 123456,
    }

    def test_creates_user_and_profile(self):
        response = self.client.post(TG_REGISTER_URL, self.payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assert_tokens(response.data)
        user = User.objects.get(pk=response.data["id"])
        self.assertEqual(user.username, "tg-123456")
        profile = TgProfile.objects.get(user=user)
        self.assertEqual(profile.tg_id, 123456)
        self.assertEqual(profile.username, "tg_user")

    def test_repeated_registration_returns_same_user(self):
        first = self.client.post(TG_REGISTER_URL, self.payload)
        second = self.client.post(TG_REGISTER_URL, self.payload)

        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(TgProfile.objects.count(), 1)

    def test_required_fields(self):
        response = self.client.post(TG_REGISTER_URL, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            set(response.data), {"username", "first_name", "last_name", "tg_id"}
        )
        self.assertFalse(User.objects.exists())


class WebRegisterTests(AuthAPITestCase):
    payload = {
        "username": "web_user",
        "first_name": "First",
        "last_name": "Last",
        "email": "web@example.com",
        "password": "strong-password",
    }

    def test_creates_user_and_profile(self):
        response = self.client.post(WEB_REGISTER_URL, self.payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assert_tokens(response.data)
        user = User.objects.get(pk=response.data["id"])
        self.assertEqual(user.username, "web_user")
        self.assertEqual(user.email, "web@example.com")
        self.assertTrue(user.check_password("strong-password"))
        self.assertTrue(WebProfile.objects.filter(user=user).exists())

    def test_password_is_not_stored_in_profile(self):
        self.client.post(WEB_REGISTER_URL, self.payload)

        self.assertFalse(hasattr(WebProfile.objects.get(), "password"))

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            WEB_REGISTER_URL, {**self.payload, "email": "not-an-email"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertFalse(User.objects.exists())

    def test_required_fields(self):
        response = self.client.post(WEB_REGISTER_URL, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            set(response.data),
            {"username", "first_name", "last_name", "email", "password"},
        )


class TokenTests(AuthAPITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="user", password="password")

    def obtain_tokens(self):
        response = self.client.post(
            TOKEN_URL, {"username": "user", "password": "password"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_obtain_with_valid_credentials(self):
        tokens = self.obtain_tokens()

        self.assertEqual(set(tokens), {"access", "refresh"})

    def test_obtain_with_wrong_password(self):
        response = self.client.post(
            TOKEN_URL, {"username": "user", "password": "wrong"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_authorizes_api(self):
        tokens = self.obtain_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.get(TASKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_access_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid")

        response = self.client.get(TASKS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotates_token(self):
        tokens = self.obtain_tokens()

        response = self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {"access", "refresh"})
        self.assertNotEqual(response.data["refresh"], tokens["refresh"])

    def test_rotated_refresh_token_cannot_be_reused(self):
        tokens = self.obtain_tokens()
        self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]})

        response = self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklisted_refresh_token_cannot_be_used(self):
        tokens = self.obtain_tokens()

        blacklist = self.client.post(BLACKLIST_URL, {"refresh": tokens["refresh"]})
        refresh = self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]})

        self.assertEqual(blacklist.status_code, status.HTTP_200_OK)
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)
