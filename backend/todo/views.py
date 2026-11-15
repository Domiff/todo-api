from adrf.views import APIView
from adrf.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from todo.events import ChangedVia
from todo.models import Category, Task
from todo.serializers import CategorySerializer, SearchSerializer, TaskSerializer
from todo.services import task_service


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

    def changed_via(self) -> ChangedVia:
        if self.request.headers.get("X-Client") == "Telegram":
            return ChangedVia.TELEGRAM
        return ChangedVia.WEB

    async def perform_acreate(self, serializer: TaskSerializer):
        serializer.instance = await task_service.create(
            self.request.user, serializer.validated_data, self.changed_via()
        )

    async def perform_aupdate(self, serializer: TaskSerializer):
        serializer.instance = await task_service.update(
            serializer.instance, serializer.validated_data, self.changed_via()
        )

    async def perform_adestroy(self, instance: Task):
        await task_service.delete(instance, self.changed_via())

    @action(detail=True, methods=["post"])
    async def complete(self, request, pk=None):
        task = await task_service.set_completed(
            await self.aget_object(), True, self.changed_via()
        )
        return Response(await self.get_serializer(task).adata)

    @action(detail=True, methods=["post"], url_path="in-progress")
    async def in_progress(self, request, pk=None):
        task = await task_service.set_completed(
            await self.aget_object(), False, self.changed_via()
        )
        return Response(await self.get_serializer(task).adata)


class SearchView(APIView):
    async def get(self, request: Request):
        serializer = SearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        search_query = SearchQuery(
            serializer.validated_data["query"],
            config="russian",
            search_type="websearch",
        )
        tasks = (
            Task.objects.filter(creator__user=request.user, search_vector=search_query)
            .annotate(rank=SearchRank(F("search_vector"), search_query))
            .order_by("-rank")
            .select_related("category")
        )
        data = await TaskSerializer(tasks, many=True).adata
        return Response(data, status=status.HTTP_200_OK)
