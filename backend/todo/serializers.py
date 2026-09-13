from adrf.serializers import ModelSerializer
from rest_framework.fields import HiddenField, CurrentUserDefault
from rest_framework.relations import SlugRelatedField

from todo.models import Category, Task


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "urgency"


class TaskBaseSerializer(ModelSerializer):
    category = SlugRelatedField(
        slug_field="urgency",
        queryset=Category.objects.all(),
    )
    creator = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Task
        fields = (
            "creator",
            "title",
            "deadline",
            "category",
        )


class TaskListSerializer(TaskBaseSerializer):
    class Meta(TaskBaseSerializer.Meta):
        fields = TaskBaseSerializer.Meta.fields + (
            "pk",
            "body",
            "completed",
            "created_at",
        )


class TaskDetailSerializer(TaskBaseSerializer):
    class Meta(TaskBaseSerializer.Meta):
        fields = TaskBaseSerializer.Meta.fields + (
            "pk",
            "body",
            "completed",
            "created_at",
            "updated_at",
        )


class TaskCreateSerializer(TaskBaseSerializer):
    class Meta(TaskBaseSerializer.Meta):
        fields = TaskBaseSerializer.Meta.fields + ("body",)


class TaskUpdateSerializer(TaskBaseSerializer):
    class Meta(TaskBaseSerializer.Meta):
        fields = TaskBaseSerializer.Meta.fields + ("body", "deadline", "completed", "pk")
