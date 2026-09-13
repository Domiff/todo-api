from django.urls import path

from todo.views import (
    TodoCreateView,
    TodoDeleteView,
    TodoDetailView,
    TodoListView,
    TodoUpdateView,
)

app_name = "todolist"

urlpatterns = [
    path("list/", TodoListView.as_view(), name="list"),
    path("list/<int:pk>", TodoDetailView.as_view(), name="detail"),
    path("create/", TodoCreateView.as_view(), name="create"),
    path("update/<int:pk>", TodoUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", TodoDeleteView.as_view(), name="delete"),
]
