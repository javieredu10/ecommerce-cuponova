from typing import Optional
from .base import DomainEvent


class DeliveryAssigned(DomainEvent):
    event_type: str = "delivery.assigned"
    delivery_id: str
    order_id: str
    motorizado_id: str
    customer_id: str
    address: str


class DeliveryCompleted(DomainEvent):
    event_type: str = "delivery.completed"
    delivery_id: str
    order_id: str
    qr_code: str
    delivered_at: str


class DeliveryFailed(DomainEvent):
    event_type: str = "delivery.failed"
    delivery_id: str
    order_id: str
    reason: str
