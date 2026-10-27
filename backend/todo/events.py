from dataclasses import dataclass
from datetime import datetime

TASK_CREATED_EVENT_TYPE = "todo.task.created.v1"


@dataclass(frozen=True, kw_only=True)
class TaskCreatedData:
    task_id: int
    tg_id: int
    title: str
    deadline: datetime
