from adrf.viewsets import ModelViewSet

from todo.models import Task
from todo.serializers import TaskSerializer


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()

    async def afilter_queryset(self, queryset):
        queryset = await super().afilter_queryset(queryset)
        return queryset.filter(creator=self.request.user).select_related("category")
