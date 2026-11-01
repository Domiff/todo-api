from adrf.serializers import ModelSerializer
from rest_framework.relations import SlugRelatedField

from todo.models import Category, Task


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ("urgency",)


class TaskSerializer(ModelSerializer):
    category = SlugRelatedField(
        slug_field="urgency",
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Task
        fields = (
            "pk",
            "title",
            "body",
            "deadline",
            "category",
            "completed",
            "created_at",
            "updated_at",
        )
