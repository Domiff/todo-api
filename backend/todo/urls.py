from adrf.routers import SimpleRouter
from django.urls import path

from todo.views import CategoryViewSet, SearchView, TaskViewSet

app_name = "todolist"

router = SimpleRouter()
router.trailing_slash = "/?"
router.register("tasks", TaskViewSet, basename="task")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    *router.urls,
]
