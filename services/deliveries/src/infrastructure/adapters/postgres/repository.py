from __future__ import annotations
import os
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select

from src.domain.entities.delivery import Delivery, DeliveryStatus

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:secret@localhost:5432/ecommerce")
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DeliveryModel(Base):
    __tablename__ = "deliveries"
    __table_args__ = {"schema": "deliveries"}

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    order_id = Column(String, nullable=False, unique=True, index=True)
    customer_id = Column(String, nullable=False)
    motorizado_id = Column(String, nullable=True)
    delivery_address = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    qr_code = Column(Text, nullable=True)
    tracking_notes = Column(String, nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _to_domain(m: DeliveryModel) -> Delivery:
    return Delivery(
        id=m.id, tenant_id=m.tenant_id, order_id=m.order_id,
        customer_id=m.customer_id, motorizado_id=m.motorizado_id,
        delivery_address=m.delivery_address,
        status=DeliveryStatus(m.status), qr_code=m.qr_code,
        tracking_notes=m.tracking_notes, assigned_at=m.assigned_at,
        delivered_at=m.delivered_at, created_at=m.created_at,
        updated_at=m.updated_at,
    )


class DeliveryRepository:
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, d: Delivery) -> Delivery:
        m = DeliveryModel(
            id=d.id, tenant_id=d.tenant_id, order_id=d.order_id,
            customer_id=d.customer_id, motorizado_id=d.motorizado_id,
            delivery_address=d.delivery_address, status=d.status.value,
        )
        self._s.add(m)
        await self._s.commit()
        await self._s.refresh(m)
        return _to_domain(m)

    async def update(self, d: Delivery) -> Delivery:
        r = await self._s.execute(select(DeliveryModel).where(DeliveryModel.id == d.id))
        m = r.scalar_one_or_none()
        if not m:
            raise ValueError("Delivery not found")
        m.motorizado_id = d.motorizado_id
        m.status = d.status.value
        m.qr_code = d.qr_code
        m.tracking_notes = d.tracking_notes
        m.assigned_at = d.assigned_at
        m.delivered_at = d.delivered_at
        m.updated_at = datetime.utcnow()
        await self._s.commit()
        return _to_domain(m)

    async def find_by_order(self, order_id: str) -> Optional[Delivery]:
        r = await self._s.execute(
            select(DeliveryModel).where(DeliveryModel.order_id == order_id)
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_pending(self, tenant_id: str) -> List[Delivery]:
        r = await self._s.execute(
            select(DeliveryModel).where(
                DeliveryModel.tenant_id == tenant_id,
                DeliveryModel.status == "pending",
            )
        )
        return [_to_domain(m) for m in r.scalars().all()]
