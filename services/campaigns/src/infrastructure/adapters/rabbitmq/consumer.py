import os
import json
import logging
import asyncio
import aio_pika
from aio_pika import ExchangeType

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secret@localhost:5672/")
logger = logging.getLogger(__name__)


async def handle_order_paid(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        logger.info("Campaign service received order.paid: %s", body)
        # Here: increment coupon usage counters, update campaign analytics
        order_id = body.get("order_id")
        campaign_id = body.get("campaign_id")
        logger.info("Incrementing uses for campaign %s from order %s", campaign_id, order_id)


async def start_consumer():
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        orders_exchange = await channel.declare_exchange("orders.topic", ExchangeType.TOPIC, durable=True)

        # Listen for order.paid to update campaign stats
        queue = await channel.declare_queue("campaigns.order.paid", durable=True)
        await queue.bind(orders_exchange, routing_key="order.paid")
        await queue.consume(handle_order_paid)

        logger.info("Campaign consumer started")
        await asyncio.Future()
    except Exception as e:
        logger.error("Campaign consumer error: %s", e)
        raise
