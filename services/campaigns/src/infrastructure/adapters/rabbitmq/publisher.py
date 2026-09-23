import os
import json
import logging
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode
from src.domain.entities.campaign import Campaign

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:secret@localhost:5672/")
logger = logging.getLogger(__name__)


class CampaignPublisher:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._exchange = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "campaigns.topic", ExchangeType.TOPIC, durable=True
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
        logger.info("Published %s", routing_key)

    async def publish_campaign_created(self, campaign: Campaign):
        await self._publish("campaign.created", {
            "event_type": "campaign.created",
            "campaign_id": campaign.id,
            "tenant_id": campaign.tenant_id,
            "name": campaign.name,
            "product_ids": campaign.product_ids,
            "service_ids": campaign.service_ids,
        })

    async def publish_campaign_activated(self, campaign: Campaign):
        await self._publish("campaign.activated", {
            "event_type": "campaign.activated",
            "campaign_id": campaign.id,
            "tenant_id": campaign.tenant_id,
        })


# Singleton
_publisher = CampaignPublisher()

async def get_publisher() -> CampaignPublisher:
    if not _publisher._connection:
        await _publisher.connect()
    return _publisher
