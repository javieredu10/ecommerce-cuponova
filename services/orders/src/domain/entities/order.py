from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from decimal import Decimal


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CARD = "card"
    TRANSFER = "transfer"
    CASH = "cash"


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    discount_applied: float = 0.0

    @property
    def subtotal(self) -> float:
        return (self.unit_price - self.discount_applied) * self.quantity


@dataclass
class Order:
    """Order aggregate root — fully persisted in Postgres (transactional)."""

    id: str
    tenant_id: str
    customer_id: str
    items: List[OrderItem]
    status: OrderStatus
    coupon_code: Optional[str]
    campaign_id: Optional[str]
    subtotal: float
    discount_total: float
    total: float
    payment_method: Optional[PaymentMethod]
    payment_reference: Optional[str]
    delivery_address: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        tenant_id: str,
        customer_id: str,
        items: List[OrderItem],
        delivery_address: str,
        coupon_code: Optional[str] = None,
        campaign_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> "Order":
        subtotal = sum(i.unit_price * i.quantity for i in items)
        discount_total = sum(i.discount_applied * i.quantity for i in items)
        total = subtotal - discount_total
        now = datetime.utcnow()
        return Order(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            customer_id=customer_id,
            items=items,
            status=OrderStatus.PENDING,
            coupon_code=coupon_code,
            campaign_id=campaign_id,
            subtotal=subtotal,
            discount_total=discount_total,
            total=total,
            payment_method=None,
            payment_reference=None,
            delivery_address=delivery_address,
            notes=notes,
            created_at=now,
            updated_at=now,
        )

    def mark_paid(self, method: PaymentMethod, reference: str) -> None:
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot pay order in status {self.status}")
        self.status = OrderStatus.PAID
        self.payment_method = method
        self.payment_reference = reference
        self.updated_at = datetime.utcnow()

    def cancel(self, reason: str) -> None:
        if self.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValueError("Cannot cancel order already shipped/delivered")
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def mark_shipped(self) -> None:
        self.status = OrderStatus.SHIPPED
        self.updated_at = datetime.utcnow()
