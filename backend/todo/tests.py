from datetime import timedelta

from django.contrib.auth.models import User
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from todo.models import Category, Task

TASKS_URL = "/api/tasks/"


def task_url(pk):
    return f"{TASKS_URL}{pk}/"


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
)
class TaskAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="owner", password="pass")
        cls.other_user = User.objects.create_user(username="stranger", password="pass")
        cls.high = Category.objects.create(urgency="high")
        cls.low = Category.objects.create(urgency="low")

    def setUp(self):
        self.client.force_authenticate(self.user)

    def make_task(self, creator=None, **kwargs):
        fields = {
            "creator": creator or self.user,
            "title": "Task",
            "body": "Body",
            "deadline": timezone.now() + timedelta(days=1),
            "category": self.high,
        }
        fields.update(kwargs)
        return Task.objects.create(**fields)

    def task_payload(self, **kwargs):
        payload = {
            "title": "New task",
            "body": "Body",
            "deadline": (timezone.now() + timedelta(days=1)).isoformat(),
            "category": "high",
        }
        payload.update(kwargs)
        return payload


class AuthenticationTests(TaskAPITestCase):
    def test_anonymous_request_is_rejected(self):
        self.client.force_authenticate(None)
        task = self.make_task()

        requests = [
            ("get", TASKS_URL),
            ("post", TASKS_URL),
            ("get", task_url(task.pk)),
            ("patch", task_url(task.pk)),
            ("put", task_url(task.pk)),
            ("delete", task_url(task.pk)),
        ]
        for method, url in requests:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ListTaskTests(TaskAPITestCase):
    def test_returns_only_own_tasks(self):
        own = self.make_task(title="Mine")
        self.make_task(creator=self.other_user, title="Not mine")

        response = self.client.get(TASKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([task["pk"] for task in response.data], [own.pk])

    def test_returns_empty_list_without_tasks(self):
        self.make_task(creator=self.other_user)

        response = self.client.get(TASKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_task_representation(self):
        task = self.make_task()

        response = self.client.get(TASKS_URL)

        self.assertEqual(
            set(response.data[0]),
            {
                "pk",
                "title",
                "body",
                "deadline",
                "category",
                "completed",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(response.data[0]["pk"], task.pk)
        self.assertEqual(response.data[0]["category"], "high")

    def test_ordered_by_last_update(self):
        first = self.make_task(title="First")
        second = self.make_task(title="Second")
        first.title = "First, updated"
        first.save()

        response = self.client.get(TASKS_URL)

        self.assertEqual([task["pk"] for task in response.data], [first.pk, second.pk])

    def test_category_is_loaded_in_single_query(self):
        for category in (self.high, self.low, self.high):
            self.make_task(category=category)

        with self.assertNumQueries(1):
            response = self.client.get(TASKS_URL)

        self.assertEqual(len(response.data), 3)


class CreateTaskTests(TaskAPITestCase):
    def test_creates_task_for_current_user(self):
        response = self.client.post(TASKS_URL, self.task_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["pk"])
        self.assertEqual(task.creator, self.user)
        self.assertEqual(task.title, "New task")
        self.assertEqual(task.category, self.high)
        self.assertFalse(task.completed)

    def test_creator_from_payload_is_ignored(self):
        response = self.client.post(
            TASKS_URL, self.task_payload(creator=self.other_user.pk)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.get(pk=response.data["pk"]).creator, self.user)

    def test_read_only_fields_from_payload_are_ignored(self):
        created_at = timezone.now() - timedelta(days=30)

        response = self.client.post(
            TASKS_URL, self.task_payload(pk=999, created_at=created_at.isoformat())
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["pk"])
        self.assertNotEqual(task.pk, 999)
        self.assertGreater(task.created_at, created_at)

    def test_unknown_category_is_rejected(self):
        response = self.client.post(TASKS_URL, self.task_payload(category="unknown"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)
        self.assertFalse(Task.objects.exists())

    def test_required_fields(self):
        response = self.client.post(TASKS_URL, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"title", "body", "deadline", "category"})

    def test_invalid_deadline_is_rejected(self):
        response = self.client.post(TASKS_URL, self.task_payload(deadline="not-a-date"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", response.data)


class RetrieveTaskTests(TaskAPITestCase):
    def test_returns_own_task(self):
        task = self.make_task(title="Mine")

        response = self.client.get(task_url(task.pk))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pk"], task.pk)
        self.assertEqual(response.data["title"], "Mine")

    def test_foreign_task_is_not_found(self):
        task = self.make_task(creator=self.other_user)

        response = self.client.get(task_url(task.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_task_is_not_found(self):
        response = self.client.get(task_url(999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trailing_slash_is_optional(self):
        task = self.make_task()

        for url in (f"{TASKS_URL}{task.pk}", f"{TASKS_URL}{task.pk}/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)


class UpdateTaskTests(TaskAPITestCase):
    def test_partial_update(self):
        task = self.make_task(title="Old")

        response = self.client.patch(task_url(task.pk), {"completed": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertTrue(task.completed)
        self.assertEqual(task.title, "Old")

    def test_partial_update_changes_category_by_slug(self):
        task = self.make_task(category=self.high)

        response = self.client.patch(task_url(task.pk), {"category": "low"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category"], "low")
        task.refresh_from_db()
        self.assertEqual(task.category, self.low)

    def test_full_update(self):
        task = self.make_task()
        payload = self.task_payload(title="Replaced", category="low", completed=True)

        response = self.client.put(task_url(task.pk), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Replaced")
        self.assertEqual(task.category, self.low)
        self.assertTrue(task.completed)

    def test_full_update_requires_all_fields(self):
        task = self.make_task()

        response = self.client.put(task_url(task.pk), {"title": "Only title"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creator_cannot_be_changed(self):
        task = self.make_task()

        response = self.client.patch(task_url(task.pk), {"creator": self.other_user.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.creator, self.user)

    def test_foreign_task_is_not_updated(self):
        task = self.make_task(creator=self.other_user, title="Not mine")

        for method in ("patch", "put"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    task_url(task.pk), self.task_payload(title="Hacked")
                )
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        task.refresh_from_db()
        self.assertEqual(task.title, "Not mine")


class DeleteTaskTests(TaskAPITestCase):
    def test_deletes_own_task(self):
        task = self.make_task()

        response = self.client.delete(task_url(task.pk))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_foreign_task_is_not_deleted(self):
        task = self.make_task(creator=self.other_user)

        response = self.client.delete(task_url(task.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
