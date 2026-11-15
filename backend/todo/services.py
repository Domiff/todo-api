from datetime import datetime
from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone

from auth_user.models import Profile
from core.messaging.events import Event
from todo.events import ChangedVia, TadkEventType, TaskData
from todo.models import Task
from todo.producers import TaskRoutingKey, publish


def resolve_completed_at(task: Task, completed: bool) -> datetime | None:
    if completed == task.completed:
        return task.completed_at
    return timezone.now() if completed else None


class TaskService:
    @staticmethod
    def _task_data(task: Task, changed_via: ChangedVia) -> TaskData:
        return TaskData(
            task_id=task.pk,
            user_id=task.creator.user_id,
            tg_id=task.creator.tg_id,
            changed_via=changed_via,
            title=task.title,
            body=task.body,
            completed=task.completed,
            priority=task.priority,
            category=task.category.slug if task.category else "",
            deadline=task.deadline,
        )

    @staticmethod
    async def _publish(
        event_type: TadkEventType, routing_key: TaskRoutingKey, data: TaskData
    ) -> None:
        event = Event(type=event_type, subject=f"tasks/{data.task_id}", data=data)
        await publish(event=event, routing_key=routing_key)

    async def create(
        self, user: User, data: dict[str, Any], changed_via: ChangedVia
    ) -> Task:
        profile, _ = await Profile.objects.aget_or_create(user=user)
        task = await Task.objects.acreate(creator=profile, **data)

        await self._publish(
            TadkEventType.CREATED_EVENT,
            TaskRoutingKey.CREATED,
            self._task_data(task, changed_via),
        )
        return task

    async def update(
        self, task: Task, data: dict[str, Any], changed_via: ChangedVia
    ) -> Task:
        completed_at = resolve_completed_at(task, data.get("completed", task.completed))
        for field, value in data.items():
            setattr(task, field, value)
        task.completed_at = completed_at
        await task.asave()

        await self._publish(
            TadkEventType.UPDATED_EVENT,
            TaskRoutingKey.UPDATED,
            self._task_data(task, changed_via),
        )
        return task

    async def set_completed(
        self, task: Task, completed: bool, changed_via: ChangedVia
    ) -> Task:
        if task.completed == completed:
            return task

        task.completed_at = resolve_completed_at(task, completed)
        task.completed = completed
        await task.asave(update_fields=["completed", "completed_at", "updated_at"])

        await self._publish(
            TadkEventType.UPDATED_EVENT,
            TaskRoutingKey.UPDATED,
            self._task_data(task, changed_via),
        )
        return task

    async def delete(self, task: Task, changed_via: ChangedVia) -> None:
        data = self._task_data(task, changed_via)
        await task.adelete()

        await self._publish(TadkEventType.DELETED_EVENT, TaskRoutingKey.DELETED, data)


task_service = TaskService()
