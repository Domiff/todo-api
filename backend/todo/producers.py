from enum import StrEnum

from aio_pika import DeliveryMode, Message

from core.messaging.connection import get_channel
from core.messaging.events import Event
from core.messaging.topology import TASKS_EXCHANGE


class TaskRoutingKey(StrEnum):
    CREATED = "tasks.created"


async def publish(event: Event, routing_key: TaskRoutingKey) -> None:
    channel = await get_channel()
    exchange = await channel.get_exchange(name=TASKS_EXCHANGE, ensure=False)

    await exchange.publish(
        routing_key=routing_key,
        message=Message(body=event.to_bytes(), delivery_mode=DeliveryMode.PERSISTENT),
    )
