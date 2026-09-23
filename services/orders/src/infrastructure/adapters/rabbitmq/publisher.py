import os
import json
import logging
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secret@localhost:5672/")
logger = logging.getLogger(__name__)


class OrderPublisher:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._exchange = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "orders.topic", ExchangeType.TOPIC, durable=True
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
        logger.info("Published order event: %s", routing_key)

    async def publish_order_created(self, order):
        await self._publish("order.created", {
            "event_type": "order.created",
            "order_id": order.id,
            "tenant_id": order.tenant_id,
            "customer_id": order.customer_id,
            "total": order.total,
            "coupon_code": order.coupon_code,
            "campaign_id": order.campaign_id,
        })

    async def publish_order_paid(self, order):
        await self._publish("order.paid", {
            "event_type": "order.paid",
            "order_id": order.id,
            "tenant_id": order.tenant_id,
            "customer_id": order.customer_id,
            "amount": order.total,
            "payment_method": order.payment_method.value if order.payment_method else None,
            "campaign_id": order.campaign_id,
        })

    async def publish_order_cancelled(self, order, reason: str):
        await self._publish("order.cancelled", {
            "event_type": "order.cancelled",
            "order_id": order.id,
            "tenant_id": order.tenant_id,
            "customer_id": order.customer_id,
            "reason": reason,
        })


_publisher = OrderPublisher()

async def get_publisher() -> OrderPublisher:
    if not _publisher._connection:
        await _publisher.connect()
    return _publisher
