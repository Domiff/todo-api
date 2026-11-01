from adrf.viewsets import ModelViewSet, ReadOnlyModelViewSet

from auth_user.models import Profile
from core.messaging.events import Event
from todo.events import TadkEventType, TaskCreatedData, TaskDeletedData, TaskUpdatedData
from todo.models import Category, Task
from todo.producers import TaskRoutingKey, publish
from todo.serializers import CategorySerializer, TaskSerializer


class CategoryViewSet(ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    lookup_field = "slug"


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()

    async def afilter_queryset(self, queryset):
        queryset = await super().afilter_queryset(queryset)
        return queryset.filter(creator__user=self.request.user).select_related(
            "category", "creator"
        )

    def should_notify(self, tg_id: int | None) -> bool:
        return tg_id is not None and self.request.headers.get("X-Client") != "Telegram"

    async def perform_acreate(self, serializer: TaskSerializer):
        profile, _ = await Profile.objects.aget_or_create(user=self.request.user)
        task: Task = await serializer.asave(creator=profile)

        if not self.should_notify(profile.tg_id):
            return

        event = Event(
            type=TadkEventType.CREATED_EVENT,
            subject=f"tasks/{task.pk}",
            data=TaskCreatedData(
                task_id=task.pk,
                tg_id=profile.tg_id,
                title=task.title,
                deadline=task.deadline,
            ),
        )
        await publish(event=event, routing_key=TaskRoutingKey.CREATED)

    async def perform_aupdate(self, serializer):
        await super().perform_aupdate(serializer)
        task: Task = serializer.instance
        tg_id = task.creator.tg_id
        if not self.should_notify(tg_id):
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
                priority=task.priority,
                category=task.category.slug if task.category else "",
                deadline=task.deadline,
            ),
        )
        await publish(event=event, routing_key=TaskRoutingKey.UPDATED)

    async def perform_adestroy(self, instance):
        task_id = instance.pk
        title = instance.title
        tg_id = instance.creator.tg_id
        await super().perform_adestroy(instance)
        if not self.should_notify(tg_id):
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
