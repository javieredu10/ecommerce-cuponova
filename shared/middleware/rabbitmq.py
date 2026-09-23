from __future__ import annotations
import json
import logging
import asyncio
from typing import Any, Dict
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode

logger = logging.getLogger(__name__)

# Exchange topology
EXCHANGES = {
    "campaigns": "campaigns.topic",
    "orders": "orders.topic",
    "deliveries": "deliveries.topic",
    "notifications": "notifications.topic",
}

QUEUES = {
    "campaign.created": ("campaigns.topic", "campaign.created"),
    "campaign.activated": ("campaigns.topic", "campaign.activated"),
    "order.created": ("orders.topic", "order.created"),
    "order.paid": ("orders.topic", "order.paid"),
    "order.cancelled": ("orders.topic", "order.cancelled"),
    "order.shipped": ("orders.topic", "order.shipped"),
    "delivery.assigned": ("deliveries.topic", "delivery.assigned"),
    "delivery.completed": ("deliveries.topic", "delivery.completed"),
    "notification.email": ("notifications.topic", "notification.email"),
    "notification.qr": ("notifications.topic", "notification.qr"),
}


class RabbitMQPublisher:
    def __init__(self, url: str):
        self._url = url
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchanges: dict[str, aio_pika.abc.AbstractExchange] = {}

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        for name, exchange_name in EXCHANGES.items():
            self._exchanges[name] = await self._channel.declare_exchange(
                exchange_name, ExchangeType.TOPIC, durable=True
            )
        logger.info("RabbitMQ publisher connected")

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type not in QUEUES:
            raise ValueError(f"Unknown event type: {event_type}")
        exchange_key, routing_key = QUEUES[event_type]
        # Get exchange group key (first word before '.')
        group = routing_key.split(".")[0]
        exchange = self._exchanges.get(group)
        if not exchange:
            raise RuntimeError(f"Exchange for group '{group}' not found")
        message = Message(
            body=json.dumps(payload).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await exchange.publish(message, routing_key=routing_key)
        logger.debug("Published %s to %s", event_type, routing_key)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()


class RabbitMQConsumer:
    def __init__(self, url: str, queue_name: str, exchange_name: str, routing_key: str):
        self._url = url
        self._queue_name = queue_name
        self._exchange_name = exchange_name
        self._routing_key = routing_key

    async def consume(self, callback) -> None:
        connection = await aio_pika.connect_robust(self._url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)
        exchange = await channel.declare_exchange(self._exchange_name, ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(self._queue_name, durable=True)
        await queue.bind(exchange, routing_key=self._routing_key)
        await queue.consume(callback)
        logger.info("Consuming from %s [%s]", self._queue_name, self._routing_key)
        await asyncio.Future()  # run forever
