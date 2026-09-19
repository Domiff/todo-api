from django.contrib.auth.models import User
from django.utils import timezone
from django.test import TestCase

from todo.models import Category, Task


class TestModels(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(username="test")

    async def test_category(self):
        category = await Category.objects.acreate(urgency="test")

        self.assertIsNotNone(category)
        self.assertIsInstance(category, Category)
        self.assertEqual(category.urgency, "test")

    async def test_task(self):
        category = await Category.objects.acreate(urgency="test")

        task = await Task.objects.acreate(
            creator=self.user,
            title="Test",
            body="Test",
            completed=False,
            deadline=timezone.now(),
            category=category,
        )

        self.assertIsNotNone(task)
        self.assertIsInstance(task, Task)
        self.assertEqual(task.title, "Test")
