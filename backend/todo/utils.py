from django.http import Http404

from todo.models import Task


async def get_valid_task_or_404(user, pk):
    task = await Task.objects.filter(creator=user, pk=pk).afirst()
    if not task:
        raise Http404
    return task
