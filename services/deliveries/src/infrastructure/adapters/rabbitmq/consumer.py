import os
import json
import logging
import asyncio
import aio_pika
from aio_pika import ExchangeType

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secret@localhost:5672/")
logger = logging.getLogger(__name__)

_create_delivery_callback = None


def register_create_delivery(callback):
    """Register callback so consumer can invoke use case."""
    global _create_delivery_callback
    _create_delivery_callback = callback


async def handle_order_paid(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        logger.info("Deliveries received order.paid: %s", body)
        if _create_delivery_callback:
            await _create_delivery_callback(body)


async def start_consumer():
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        exchange = await channel.declare_exchange("orders.topic", ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue("deliveries.order.paid", durable=True)
        await queue.bind(exchange, routing_key="order.paid")
        await queue.consume(handle_order_paid)

        logger.info("Deliveries consumer started")
        await asyncio.Future()
    except Exception as e:
        logger.error("Deliveries consumer error: %s", e)
        raise
