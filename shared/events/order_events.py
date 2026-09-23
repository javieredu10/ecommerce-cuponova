from typing import List, Optional
from decimal import Decimal
from .base import DomainEvent


class OrderCreated(DomainEvent):
    event_type: str = "order.created"
    order_id: str
    customer_id: str
    items: List[dict]
    total_amount: float
    coupon_code: Optional[str] = None


class OrderPaid(DomainEvent):
    event_type: str = "order.paid"
    order_id: str
    customer_id: str
    payment_method: str
    amount_paid: float


class OrderCancelled(DomainEvent):
    event_type: str = "order.cancelled"
    order_id: str
    customer_id: str
    reason: str


class OrderShipped(DomainEvent):
    event_type: str = "order.shipped"
    order_id: str
    delivery_id: str
