from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class OrderItemDTO(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    discount_applied: float = 0.0


class CreateOrderRequest(BaseModel):
    items: List[OrderItemDTO]
    delivery_address: str
    coupon_code: Optional[str] = None
    campaign_id: Optional[str] = None
    notes: Optional[str] = None


class PayOrderRequest(BaseModel):
    payment_method: str  # card | transfer | cash
    payment_reference: str


class OrderResponse(BaseModel):
    id: str
    tenant_id: str
    customer_id: str
    items: List[dict]
    status: str
    subtotal: float
    discount_total: float
    total: float
    coupon_code: Optional[str]
    payment_method: Optional[str]
    delivery_address: str
    created_at: datetime

    @classmethod
    def from_domain(cls, o) -> "OrderResponse":
        return cls(
            id=o.id, tenant_id=o.tenant_id, customer_id=o.customer_id,
            items=[vars(i) for i in o.items],
            status=o.status.value,
            subtotal=o.subtotal, discount_total=o.discount_total, total=o.total,
            coupon_code=o.coupon_code,
            payment_method=o.payment_method.value if o.payment_method else None,
            delivery_address=o.delivery_address,
            created_at=o.created_at,
        )
