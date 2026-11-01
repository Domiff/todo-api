from adrf.routers import SimpleRouter

from todo.views import CategoryViewSet, TaskViewSet

app_name = "todolist"

router = SimpleRouter()
router.trailing_slash = "/?"
router.register("tasks", TaskViewSet, basename="task")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = router.urls
