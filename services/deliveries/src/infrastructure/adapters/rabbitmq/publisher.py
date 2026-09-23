import os
import json
import logging
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secret@localhost:5672/")
logger = logging.getLogger(__name__)


class DeliveryPublisher:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._exchange = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "deliveries.topic", ExchangeType.TOPIC, durable=True
        )

    async def _publish(self, routing_key: str, payload: dict):
        if not self._exchange:
            await self.connect()
        msg = Message(
            body=json.dumps(payload, default=str).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self._exchange.publish(msg, routing_key=routing_key)

    async def publish_assigned(self, delivery):
        await self._publish("delivery.assigned", {
            "event_type": "delivery.assigned",
            "delivery_id": delivery.id,
            "order_id": delivery.order_id,
            "tenant_id": delivery.tenant_id,
            "customer_id": delivery.customer_id,
            "motorizado_id": delivery.motorizado_id,
            "address": delivery.delivery_address,
        })

    async def publish_completed(self, delivery):
        await self._publish("delivery.completed", {
            "event_type": "delivery.completed",
            "delivery_id": delivery.id,
            "order_id": delivery.order_id,
            "tenant_id": delivery.tenant_id,
            "customer_id": delivery.customer_id,
            "qr_code": delivery.qr_code,
            "delivered_at": str(delivery.delivered_at),
        })


_publisher = DeliveryPublisher()

async def get_publisher() -> DeliveryPublisher:
    if not _publisher._connection:
        await _publisher.connect()
    return _publisher
