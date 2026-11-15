from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TadkEventType(StrEnum):
    CREATED_EVENT = "todo.task.created.v1"
    UPDATED_EVENT = "todo.task.updated.v1"
    DELETED_EVENT = "todo.task.deleted.v1"


class ChangedVia(StrEnum):
    WEB = "web"
    TELEGRAM = "telegram"


@dataclass(frozen=True, kw_only=True)
class TaskData:
    task_id: int
    user_id: int
    tg_id: int | None
    changed_via: ChangedVia
    title: str
    body: str
    completed: bool
    deadline: datetime
    priority: int
    category: str
