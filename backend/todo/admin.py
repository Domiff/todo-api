from django.contrib import admin
from unfold.admin import ModelAdmin

from todo.models import Category, Task


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["slug", "name"]


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = [
        "creator",
        "title",
        "completed",
        "created_at",
        "updated_at",
        "deadline",
        "priority",
        "category",
    ]
    list_editable = [
        "title",
        "completed",
    ]
