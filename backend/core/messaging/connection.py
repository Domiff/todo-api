import asyncio

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from django.conf import settings

from core.messaging.topology import declare_exchanges

connection: AbstractRobustConnection | None = None
channel: AbstractChannel | None = None
lock = asyncio.Lock()


async def get_channel() -> AbstractChannel:
    global connection, channel

    if channel is not None and not channel.is_closed:
        return channel

    async with lock:
        if channel is not None and not channel.is_closed:
            return channel

        if connection is None or connection.is_closed:
            connection = await connect_robust(url=settings.RABBITMQ_URL)

        channel = await connection.channel()
        await declare_exchanges(channel=channel)

        return channel


async def close() -> None:
    global connection, channel

    if connection is not None and not connection.is_closed:
        await connection.close()
    connection = channel = None
