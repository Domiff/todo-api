from adrf.serializers import ModelSerializer
from rest_framework.relations import SlugRelatedField

from todo.models import Category, Task


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ("slug", "name")


class TaskSerializer(ModelSerializer):
    category = SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = (
            "pk",
            "title",
            "body",
            "deadline",
            "priority",
            "category",
            "completed",
            "created_at",
            "updated_at",
        )
