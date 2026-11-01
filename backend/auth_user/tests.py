from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from auth_user.models import Profile

REGISTER_URL = "/auth/register/"
TG_LINK_URL = "/auth/tg/link/"
TOKEN_URL = "/auth/token/"
REFRESH_URL = "/auth/token/refresh/"
BLACKLIST_URL = "/auth/token/blacklist/"
TASKS_URL = "/api/tasks/"


BOT_KEY = "test-bot-key"


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
    BOT_API_KEY=BOT_KEY,
)
class AuthAPITestCase(APITestCase):
    def assert_tokens(self, data):
        self.assertEqual(set(data), {"id", "tokens"})
        self.assertEqual(set(data["tokens"]), {"access", "refresh"})


class RegisterTests(AuthAPITestCase):
    payload = {
        "username": "new_user",
        "email": "user@example.com",
        "password": "strong-Passw0rd",
    }

    def test_creates_user_and_profile(self):
        response = self.client.post(REGISTER_URL, self.payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assert_tokens(response.data)
        user = User.objects.get(pk=response.data["id"])
        self.assertEqual(user.username, "new_user")
        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.check_password("strong-Passw0rd"))
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.email, "user@example.com")
        self.assertIsNone(profile.tg_id)

    def test_email_is_optional(self):
        payload = {"username": "new_user", "password": "strong-Passw0rd"}

        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(Profile.objects.get().email)

    def test_registered_user_can_log_in(self):
        self.client.post(REGISTER_URL, self.payload)

        response = self.client.post(
            TOKEN_URL, {"username": "new_user", "password": "strong-Passw0rd"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_taken_username_returns_no_tokens(self):
        self.client.post(REGISTER_URL, self.payload)

        response = self.client.post(
            REGISTER_URL,
            {"username": "new_user", "password": "another-Passw0rd"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertNotIn("tokens", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_username_of_user_without_profile_is_taken(self):
        User.objects.create_user(username="new_user", password="password")

        response = self.client.post(REGISTER_URL, self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_taken_email_is_rejected(self):
        self.client.post(REGISTER_URL, self.payload)

        response = self.client.post(
            REGISTER_URL, {**self.payload, "username": "other_user"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(REGISTER_URL, {**self.payload, "password": "123"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.exists())

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            REGISTER_URL, {**self.payload, "email": "not-an-email"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertFalse(User.objects.exists())

    def test_required_fields(self):
        response = self.client.post(REGISTER_URL, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"username", "password"})

    def test_password_is_not_returned(self):
        response = self.client.post(REGISTER_URL, self.payload)

        self.assertNotIn("password", response.data)


class TelegramRegisterTests(AuthAPITestCase):
    payload = {"username": "tg_user", "password": "strong-Passw0rd", "tg_id": 123456}

    def test_bot_registers_user_with_tg_id(self):
        response = self.client.post(REGISTER_URL, self.payload, HTTP_X_BOT_KEY=BOT_KEY)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Profile.objects.get().tg_id, 123456)

    def test_tg_id_without_key_is_forbidden(self):
        response = self.client.post(REGISTER_URL, self.payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.exists())

    def test_tg_id_with_wrong_key_is_forbidden(self):
        response = self.client.post(REGISTER_URL, self.payload, HTTP_X_BOT_KEY="wrong")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(BOT_API_KEY="")
    def test_empty_key_forbids_tg_id(self):
        response = self.client.post(REGISTER_URL, self.payload, HTTP_X_BOT_KEY="")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_registered_tg_id_is_rejected(self):
        self.client.post(REGISTER_URL, self.payload, HTTP_X_BOT_KEY=BOT_KEY)

        response = self.client.post(
            REGISTER_URL,
            {**self.payload, "username": "other_user"},
            HTTP_X_BOT_KEY=BOT_KEY,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tg_id", response.data)
        self.assertEqual(User.objects.count(), 1)


class LinkTelegramTests(AuthAPITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="user", password="password")

    def setUp(self):
        self.client.force_authenticate(self.user)

    def link(self, tg_id=123456, key=BOT_KEY):
        return self.client.post(TG_LINK_URL, {"tg_id": tg_id}, HTTP_X_BOT_KEY=key)

    def test_links_tg_id_and_creates_profile(self):
        response = self.link()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Profile.objects.get(user=self.user).tg_id, 123456)

    def test_repeated_link_is_allowed(self):
        self.link()

        self.assertEqual(self.link().status_code, status.HTTP_200_OK)

    def test_key_is_required(self):
        response = self.link(key="wrong")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Profile.objects.exists())

    def test_authentication_is_required(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.link().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tg_id_of_another_user_is_rejected(self):
        other = User.objects.create_user(username="other", password="password")
        Profile.objects.create(user=other, tg_id=123456)

        response = self.link()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Profile.objects.filter(user=self.user).exclude(tg_id=None))

    def test_second_tg_id_is_rejected(self):
        self.link()

        response = self.link(tg_id=654321)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Profile.objects.get(user=self.user).tg_id, 123456)


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

    def test_refresh_of_deleted_user_is_rejected(self):
        tokens = self.obtain_tokens()
        self.user.delete()

        response = self.client.post(REFRESH_URL, {"refresh": tokens["refresh"]})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
