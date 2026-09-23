from __future__ import annotations
import os
import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, JSON, Index
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select

from src.domain.entities.order import Order, OrderItem, OrderStatus, PaymentMethod

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:secret@localhost:5432/ecommerce")
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=20)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_tenant_customer", "tenant_id", "customer_id"),
        {"schema": "orders"},
    )

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    items = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    coupon_code = Column(String, nullable=True)
    campaign_id = Column(String, nullable=True)
    subtotal = Column(Float, nullable=False)
    discount_total = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False)
    payment_method = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)
    delivery_address = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SaleModel(Base):
    """Sales record — separate table for accounting / reporting."""

    __tablename__ = "sales"
    __table_args__ = {"schema": "orders"}

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=False, unique=True)
    customer_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)
    payment_reference = Column(String, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)


def _items_to_dict(items: List[OrderItem]) -> list:
    return [
        {
            "product_id": i.product_id,
            "product_name": i.product_name,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "discount_applied": i.discount_applied,
        }
        for i in items
    ]


def _dict_to_items(data: list) -> List[OrderItem]:
    return [OrderItem(**d) for d in data]


def _to_domain(m: OrderModel) -> Order:
    return Order(
        id=m.id, tenant_id=m.tenant_id, customer_id=m.customer_id,
        items=_dict_to_items(m.items or []),
        status=OrderStatus(m.status),
        coupon_code=m.coupon_code, campaign_id=m.campaign_id,
        subtotal=m.subtotal, discount_total=m.discount_total, total=m.total,
        payment_method=PaymentMethod(m.payment_method) if m.payment_method else None,
        payment_reference=m.payment_reference,
        delivery_address=m.delivery_address, notes=m.notes,
        created_at=m.created_at, updated_at=m.updated_at,
    )


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, o: Order) -> Order:
        m = OrderModel(
            id=o.id, tenant_id=o.tenant_id, customer_id=o.customer_id,
            items=_items_to_dict(o.items), status=o.status.value,
            coupon_code=o.coupon_code, campaign_id=o.campaign_id,
            subtotal=o.subtotal, discount_total=o.discount_total, total=o.total,
            delivery_address=o.delivery_address, notes=o.notes,
        )
        self._s.add(m)
        await self._s.commit()
        await self._s.refresh(m)
        return _to_domain(m)

    async def update(self, o: Order) -> Order:
        r = await self._s.execute(select(OrderModel).where(OrderModel.id == o.id))
        m = r.scalar_one_or_none()
        if not m:
            raise ValueError("Order not found")
        m.status = o.status.value
        m.payment_method = o.payment_method.value if o.payment_method else None
        m.payment_reference = o.payment_reference
        m.updated_at = datetime.utcnow()
        await self._s.commit()
        return _to_domain(m)

    async def find_by_id(self, order_id: str, tenant_id: str) -> Optional[Order]:
        r = await self._s.execute(
            select(OrderModel).where(OrderModel.id == order_id, OrderModel.tenant_id == tenant_id)
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_customer(self, customer_id: str, tenant_id: str) -> List[Order]:
        r = await self._s.execute(
            select(OrderModel).where(
                OrderModel.customer_id == customer_id,
                OrderModel.tenant_id == tenant_id
            ).order_by(OrderModel.created_at.desc())
        )
        return [_to_domain(m) for m in r.scalars().all()]


class SaleRepository:
    def __init__(self, session: AsyncSession):
        self._s = session

    async def record_sale(self, order: Order) -> SaleModel:
        import uuid
        sale = SaleModel(
            id=str(uuid.uuid4()),
            tenant_id=order.tenant_id,
            order_id=order.id,
            customer_id=order.customer_id,
            amount=order.total,
            payment_method=order.payment_method.value,
            payment_reference=order.payment_reference,
        )
        self._s.add(sale)
        await self._s.commit()
        return sale
