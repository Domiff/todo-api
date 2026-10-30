from adrf.viewsets import ModelViewSet

from auth_user.models import TgProfile
from core.messaging.events import Event
from todo.events import TadkEventType, TaskCreatedData, TaskDeletedData, TaskUpdatedData
from todo.models import Task
from todo.producers import TaskRoutingKey, publish
from todo.serializers import TaskSerializer


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()

    async def afilter_queryset(self, queryset):
        queryset = await super().afilter_queryset(queryset)
        return queryset.filter(creator=self.request.user).select_related("category")

    async def perform_acreate(self, serializer: TaskSerializer):
        await super().perform_acreate(serializer)
        task: Task = serializer.instance

        tg_id = (
            await TgProfile.objects.filter(user=self.request.user)
            .values_list("tg_id", flat=True)
            .afirst()
        )
        if tg_id is None:
            return

        event = Event(
            type=TadkEventType.CREATED_EVENT,
            subject=f"tasks/{task.pk}",
            data=TaskCreatedData(
                task_id=task.pk,
                tg_id=tg_id,
                title=task.title,
                deadline=task.deadline,
            ),
        )
        await publish(event=event, routing_key=TaskRoutingKey.CREATED)

    async def perform_aupdate(self, serializer):
        await super().perform_aupdate(serializer)
        task: Task = serializer.instance
        tg_id = (
            await TgProfile.objects.filter(user=self.request.user)
            .values_list("tg_id", flat=True)
            .afirst()
        )
        if tg_id is None:
            return

        event = Event(
            type=TadkEventType.UPDATED_EVENT,
            subject=f"tasks/{task.pk}",
            data=TaskUpdatedData(
                task_id=task.pk,
                tg_id=tg_id,
                title=task.title,
                body=task.body,
                completed=task.completed,
                category=task.category.urgency,
                deadline=task.deadline,
            ),
        )
        await publish(event=event, routing_key=TaskRoutingKey.UPDATED)

    async def perform_adestroy(self, instance):
        task_id = instance.pk
        title = instance.title
        await super().perform_adestroy(instance)
        tg_id = (
            await TgProfile.objects.filter(user=self.request.user)
            .values_list("tg_id", flat=True)
            .afirst()
        )
        if tg_id is None:
            return

        event = Event(
            type=TadkEventType.DELETED_EVENT,
            subject=f"tasks/{task_id}",
            data=TaskDeletedData(
                task_id=task_id,
                tg_id=tg_id,
                title=title,
            ),
        )
        await publish(event=event, routing_key=TaskRoutingKey.DELETED)
