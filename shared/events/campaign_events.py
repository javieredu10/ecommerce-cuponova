from typing import List, Optional
from .base import DomainEvent


class CampaignCreated(DomainEvent):
    event_type: str = "campaign.created"
    campaign_id: str
    name: str
    discount_type: str
    discount_value: float
    product_ids: List[str]
    service_ids: List[str]
    start_date: str
    end_date: str


class CampaignActivated(DomainEvent):
    event_type: str = "campaign.activated"
    campaign_id: str


class CampaignExpired(DomainEvent):
    event_type: str = "campaign.expired"
    campaign_id: str
