from datetime import timedelta
from unittest.mock import AsyncMock, patch

from django.contrib.auth.models import User
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from auth_user.models import Profile
from todo.events import TadkEventType
from todo.models import Category, Task
from todo.producers import TaskRoutingKey

TASKS_URL = "/api/tasks/"
CATEGORIES_URL = "/api/categories/"


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
        cls.profile = Profile.objects.create(user=cls.user)
        cls.other_profile = Profile.objects.create(user=cls.other_user)
        cls.work = Category.objects.get(slug="work")
        cls.home = Category.objects.get(slug="home")

    def setUp(self):
        self.client.force_authenticate(self.user)
        patcher = patch("todo.views.publish", new_callable=AsyncMock)
        self.publish = patcher.start()
        self.addCleanup(patcher.stop)

    def make_task(self, creator=None, **kwargs):
        fields = {
            "creator": creator or self.profile,
            "title": "Task",
            "body": "Body",
            "deadline": timezone.now() + timedelta(days=1),
            "category": self.work,
        }
        fields.update(kwargs)
        return Task.objects.create(**fields)

    def task_payload(self, **kwargs):
        payload = {
            "title": "New task",
            "body": "Body",
            "deadline": (timezone.now() + timedelta(days=1)).isoformat(),
            "category": "work",
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
        self.make_task(creator=self.other_profile, title="Not mine")

        response = self.client.get(TASKS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([task["pk"] for task in response.data], [own.pk])

    def test_returns_empty_list_without_tasks(self):
        self.make_task(creator=self.other_profile)

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
                "priority",
                "category",
                "completed",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(response.data[0]["pk"], task.pk)
        self.assertEqual(response.data[0]["category"], "work")

    def test_ordered_by_last_update(self):
        first = self.make_task(title="First")
        second = self.make_task(title="Second")
        first.title = "First, updated"
        first.save()

        response = self.client.get(TASKS_URL)

        self.assertEqual([task["pk"] for task in response.data], [first.pk, second.pk])

    def test_category_is_loaded_in_single_query(self):
        for category in (self.work, self.home, self.work):
            self.make_task(category=category)

        with self.assertNumQueries(1):
            response = self.client.get(TASKS_URL)

        self.assertEqual(len(response.data), 3)


class CreateTaskTests(TaskAPITestCase):
    def test_creates_task_for_current_user(self):
        response = self.client.post(TASKS_URL, self.task_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["pk"])
        self.assertEqual(task.creator, self.profile)
        self.assertEqual(task.title, "New task")
        self.assertEqual(task.category, self.work)
        self.assertFalse(task.completed)

    def test_creates_profile_for_user_without_one(self):
        user = User.objects.create_user(username="no_profile", password="pass")
        self.client.force_authenticate(user)

        response = self.client.post(TASKS_URL, self.task_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["pk"])
        self.assertEqual(task.creator, Profile.objects.get(user=user))

    def test_creator_from_payload_is_ignored(self):
        response = self.client.post(
            TASKS_URL, self.task_payload(creator=self.other_user.pk)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.get(pk=response.data["pk"]).creator, self.profile)

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
        self.assertEqual(set(response.data), {"title", "body", "deadline"})

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
        task = self.make_task(creator=self.other_profile)

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
        task = self.make_task(category=self.work)

        response = self.client.patch(task_url(task.pk), {"category": "home"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category"], "home")
        task.refresh_from_db()
        self.assertEqual(task.category, self.home)

    def test_full_update(self):
        task = self.make_task()
        payload = self.task_payload(title="Replaced", category="home", completed=True)

        response = self.client.put(task_url(task.pk), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Replaced")
        self.assertEqual(task.category, self.home)
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
        self.assertEqual(task.creator, self.profile)

    def test_foreign_task_is_not_updated(self):
        task = self.make_task(creator=self.other_profile, title="Not mine")

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
        task = self.make_task(creator=self.other_profile)

        response = self.client.delete(task_url(task.pk))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())


class PriorityTests(TaskAPITestCase):
    def test_default_priority_is_middle(self):
        response = self.client.post(TASKS_URL, self.task_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["priority"], Task.Priority.MIDDLE)

    def test_priority_can_be_set(self):
        response = self.client.post(
            TASKS_URL, self.task_payload(priority=Task.Priority.HIGH)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.get().priority, Task.Priority.HIGH)

    def test_unknown_priority_is_rejected(self):
        response = self.client.post(TASKS_URL, self.task_payload(priority=99))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("priority", response.data)


class CategoryTests(TaskAPITestCase):
    def test_task_can_be_created_without_category(self):
        payload = self.task_payload()
        del payload["category"]

        response = self.client.post(TASKS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["category"])

    def test_category_can_be_removed_from_task(self):
        task = self.make_task()

        response = self.client.patch(
            task_url(task.pk), {"category": None}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertIsNone(task.category)

    def test_list_returns_predefined_categories(self):
        response = self.client.get(CATEGORIES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [category["slug"] for category in response.data],
            [
                "work",
                "study",
                "personal",
                "home",
                "shopping",
                "health",
                "finance",
                "other",
            ],
        )
        self.assertEqual(set(response.data[0]), {"slug", "name"})

    def test_retrieve_by_slug(self):
        response = self.client.get(f"{CATEGORIES_URL}work/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Work")

    def test_categories_are_read_only(self):
        response = self.client.post(CATEGORIES_URL, {"slug": "new", "name": "New"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_anonymous_request_is_rejected(self):
        self.client.force_authenticate(None)

        response = self.client.get(CATEGORIES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TaskEventTests(TaskAPITestCase):
    def setUp(self):
        super().setUp()
        self.profile.tg_id = 777
        self.profile.save()

    def published(self):
        self.publish.assert_awaited_once()
        kwargs = self.publish.await_args.kwargs
        return kwargs["event"], kwargs["routing_key"]

    def test_create_publishes_event(self):
        response = self.client.post(TASKS_URL, self.task_payload())

        event, routing_key = self.published()
        pk = response.data["pk"]
        self.assertEqual(routing_key, TaskRoutingKey.CREATED)
        self.assertEqual(event.type, TadkEventType.CREATED_EVENT)
        self.assertEqual(event.subject, f"tasks/{pk}")
        self.assertEqual(event.data.task_id, pk)
        self.assertEqual(event.data.tg_id, 777)

    def test_update_publishes_event(self):
        task = self.make_task(priority=Task.Priority.LOW)

        self.client.patch(task_url(task.pk), {"completed": True})

        event, routing_key = self.published()
        self.assertEqual(routing_key, TaskRoutingKey.UPDATED)
        self.assertEqual(event.type, TadkEventType.UPDATED_EVENT)
        self.assertEqual(event.data.task_id, task.pk)
        self.assertTrue(event.data.completed)
        self.assertEqual(event.data.priority, Task.Priority.LOW)
        self.assertEqual(event.data.category, "work")

    def test_update_of_task_without_category_publishes_empty_category(self):
        task = self.make_task(category=None)

        self.client.patch(task_url(task.pk), {"completed": True})

        event, _ = self.published()
        self.assertEqual(event.data.category, "")

    def test_delete_publishes_event_with_task_id(self):
        task = self.make_task(title="Removed")
        pk = task.pk

        self.client.delete(task_url(pk))

        event, routing_key = self.published()
        self.assertEqual(routing_key, TaskRoutingKey.DELETED)
        self.assertEqual(event.type, TadkEventType.DELETED_EVENT)
        self.assertEqual(event.subject, f"tasks/{pk}")
        self.assertEqual(event.data.task_id, pk)
        self.assertEqual(event.data.title, "Removed")

    def test_events_are_serializable(self):
        self.client.post(TASKS_URL, self.task_payload())

        event, _ = self.published()
        self.assertIsInstance(event.to_bytes(), bytes)

    def test_nothing_is_published_without_tg_id(self):
        self.profile.tg_id = None
        self.profile.save()

        pk = self.client.post(TASKS_URL, self.task_payload()).data["pk"]
        self.client.patch(task_url(pk), {"completed": True})
        self.client.delete(task_url(pk))

        self.publish.assert_not_awaited()

    def test_invalid_request_publishes_nothing(self):
        self.client.post(TASKS_URL, {})

        self.publish.assert_not_awaited()
