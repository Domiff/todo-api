from adrf.serializers import ModelSerializer
from rest_framework.fields import HiddenField, CurrentUserDefault
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
    creator = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Task
        fields = (
            "pk",
            "creator",
            "title",
            "body",
            "deadline",
            "category",
            "completed",
            "created_at",
            "updated_at",
        )
