from __future__ import annotations
import os
import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, JSON, Boolean, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select

from src.domain.entities.campaign import Campaign, CampaignExtra, DiscountType, CampaignStatus

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:secret@localhost:5432/ecommerce")
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CampaignModel(Base):
    __tablename__ = "campaigns"
    __table_args__ = {"schema": "campaigns"}

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    discount_type = Column(String, nullable=False)
    discount_value = Column(Float, nullable=False)
    product_ids = Column(ARRAY(String), default=[])
    service_ids = Column(ARRAY(String), default=[])
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String, default="draft")
    extra = Column(JSON, nullable=True)
    coupon_code = Column(String, nullable=True, index=True)
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _to_domain(m: CampaignModel) -> Campaign:
    extra = None
    if m.extra:
        extra = CampaignExtra(**m.extra)
    return Campaign(
        id=m.id, tenant_id=m.tenant_id, name=m.name,
        description=m.description,
        discount_type=DiscountType(m.discount_type),
        discount_value=m.discount_value,
        product_ids=m.product_ids or [],
        service_ids=m.service_ids or [],
        start_date=m.start_date, end_date=m.end_date,
        status=CampaignStatus(m.status), extra=extra,
        coupon_code=m.coupon_code, max_uses=m.max_uses,
        current_uses=m.current_uses or 0,
        created_at=m.created_at, updated_at=m.updated_at,
    )


class CampaignRepository:
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, c: Campaign) -> Campaign:
        m = CampaignModel(
            id=c.id, tenant_id=c.tenant_id, name=c.name,
            description=c.description, discount_type=c.discount_type.value,
            discount_value=c.discount_value, product_ids=c.product_ids,
            service_ids=c.service_ids, start_date=c.start_date,
            end_date=c.end_date, status=c.status.value,
            extra=vars(c.extra) if c.extra else None,
            coupon_code=c.coupon_code, max_uses=c.max_uses,
            current_uses=c.current_uses,
        )
        self._s.add(m)
        await self._s.commit()
        await self._s.refresh(m)
        return _to_domain(m)

    async def update(self, c: Campaign) -> Campaign:
        result = await self._s.execute(select(CampaignModel).where(CampaignModel.id == c.id))
        m = result.scalar_one_or_none()
        if not m:
            raise ValueError("Campaign not found")
        m.status = c.status.value
        m.updated_at = datetime.utcnow()
        await self._s.commit()
        return _to_domain(m)

    async def find_by_id(self, campaign_id: str, tenant_id: str) -> Optional[Campaign]:
        r = await self._s.execute(
            select(CampaignModel).where(
                CampaignModel.id == campaign_id, CampaignModel.tenant_id == tenant_id
            )
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_coupon(self, code: str, tenant_id: str) -> Optional[Campaign]:
        r = await self._s.execute(
            select(CampaignModel).where(
                CampaignModel.coupon_code == code, CampaignModel.tenant_id == tenant_id
            )
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def list_active(self, tenant_id: str) -> List[Campaign]:
        r = await self._s.execute(
            select(CampaignModel).where(
                CampaignModel.tenant_id == tenant_id,
                CampaignModel.status == "active",
            )
        )
        return [_to_domain(m) for m in r.scalars().all()]
