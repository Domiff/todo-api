import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from core.messaging.utils import validate_dict


@dataclass(frozen=True, kw_only=True)
class Event:
    specversion: str = "1.0"
    id: UUID = field(default_factory=uuid4)
    source: str = "todo-api"
    type: str
    time: datetime = field(default_factory=lambda: datetime.now(UTC))
    subject: str
    datacontenttype: str = "application/json"
    data: Any

    def to_bytes(self) -> bytes:
        return json.dumps(
            asdict(self), default=validate_dict
        ).encode()
