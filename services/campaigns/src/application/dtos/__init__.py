from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class CampaignExtraDTO(BaseModel):
    tiempo_horas: int
    minimo_vender: float
    maximo_vender: float
    contrato_url: Optional[str] = None


class CreateCampaignRequest(BaseModel):
    name: str
    description: str
    discount_type: str  # "percentage" | "fixed"
    discount_value: float
    product_ids: List[str] = []
    service_ids: List[str] = []
    start_date: datetime
    end_date: datetime
    extra: Optional[CampaignExtraDTO] = None
    coupon_code: Optional[str] = None
    max_uses: Optional[int] = None


class CampaignResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str
    discount_type: str
    discount_value: float
    product_ids: List[str]
    service_ids: List[str]
    start_date: datetime
    end_date: datetime
    status: str
    coupon_code: Optional[str]
    max_uses: Optional[int]
    current_uses: int
    created_at: datetime

    @classmethod
    def from_domain(cls, c) -> "CampaignResponse":
        return cls(
            id=c.id, tenant_id=c.tenant_id, name=c.name,
            description=c.description, discount_type=c.discount_type.value,
            discount_value=c.discount_value, product_ids=c.product_ids,
            service_ids=c.service_ids, start_date=c.start_date,
            end_date=c.end_date, status=c.status.value,
            coupon_code=c.coupon_code, max_uses=c.max_uses,
            current_uses=c.current_uses, created_at=c.created_at,
        )
