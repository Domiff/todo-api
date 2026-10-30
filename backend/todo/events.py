from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TadkEventType(StrEnum):
    CREATED_EVENT = "todo.task.created.v1"
    UPDATED_EVENT = "todo.task.updated.v1"
    DELETED_EVENT = "todo.task.deleted.v1"


@dataclass(frozen=True, kw_only=True)
class TaskCreatedData:
    task_id: int
    tg_id: int
    title: str
    deadline: datetime


@dataclass(frozen=True, kw_only=True)
class TaskUpdatedData:
    task_id: int
    tg_id: int
    title: str
    body: str
    completed: bool
    deadline: datetime
    category: str


@dataclass(frozen=True, kw_only=True)
class TaskDeletedData:
    task_id: int
    tg_id: int
    title: str
