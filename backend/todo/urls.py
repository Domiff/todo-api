from adrf.routers import SimpleRouter

from todo.views import TaskViewSet

app_name = "todolist"

router = SimpleRouter()
router.trailing_slash = "/?"
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
