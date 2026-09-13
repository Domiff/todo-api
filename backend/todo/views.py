from adrf.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)

from todo.models import Task
from todo.serializers import (
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskUpdateSerializer,
)
from todo.utils import get_valid_task_or_404


class TodoListView(ListAPIView):
    serializer_class = TaskListSerializer
    queryset = Task.objects.all()

    async def afilter_queryset(self, queryset):
        return queryset.filter(creator=self.request.user)


class TodoDetailView(RetrieveAPIView):
    serializer_class = TaskDetailSerializer
    queryset = Task.objects.all()

    async def aget_object(self):
        return await get_valid_task_or_404(user=self.request.user, pk=self.kwargs["pk"])


class TodoCreateView(CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskCreateSerializer


class TodoUpdateView(UpdateAPIView):
    serializer_class = TaskUpdateSerializer
    queryset = Task.objects.all()

    async def aget_object(self):
        return await get_valid_task_or_404(user=self.request.user, pk=self.kwargs["pk"])


class TodoDeleteView(DestroyAPIView):
    queryset = Task.objects.all()

    async def aget_object(self):
        return await get_valid_task_or_404(user=self.request.user, pk=self.kwargs["pk"])
