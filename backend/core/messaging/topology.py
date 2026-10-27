from aio_pika.abc import AbstractChannel, ExchangeType

TASKS_EXCHANGE = "todo.tasks"

EXCHANGES = {
    TASKS_EXCHANGE: ExchangeType.DIRECT,
}


async def declare_exchanges(channel: AbstractChannel) -> None:
    for name, exchange_type in EXCHANGES.items():
        await channel.declare_exchange(
            name=name,
            type=exchange_type,
            durable=True
        )
