from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


@dataclass
class CampaignExtra:
    """Lateral extras (yellow box in diagram)."""
    tiempo_horas: int           # Tiempo
    minimo_vender: float        # Minimo Vender
    maximo_vender: float        # Maximo Vender
    contrato_url: Optional[str] = None  # Contrato


@dataclass
class Campaign:
    id: str
    tenant_id: str
    name: str
    description: str
    discount_type: DiscountType
    discount_value: float
    product_ids: List[str]
    service_ids: List[str]
    start_date: datetime
    end_date: datetime
    status: CampaignStatus
    extra: Optional[CampaignExtra]
    coupon_code: Optional[str]
    max_uses: Optional[int]
    current_uses: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        tenant_id: str,
        name: str,
        description: str,
        discount_type: DiscountType,
        discount_value: float,
        product_ids: List[str],
        service_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        extra: Optional[CampaignExtra] = None,
        coupon_code: Optional[str] = None,
        max_uses: Optional[int] = None,
    ) -> "Campaign":
        now = datetime.utcnow()
        return Campaign(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            description=description,
            discount_type=discount_type,
            discount_value=discount_value,
            product_ids=product_ids,
            service_ids=service_ids,
            start_date=start_date,
            end_date=end_date,
            status=CampaignStatus.DRAFT,
            extra=extra,
            coupon_code=coupon_code,
            max_uses=max_uses,
            current_uses=0,
            created_at=now,
            updated_at=now,
        )

    def activate(self) -> None:
        self.status = CampaignStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def apply_discount(self, base_price: float) -> float:
        if self.discount_type == DiscountType.PERCENTAGE:
            return base_price * (1 - self.discount_value / 100)
        return max(0, base_price - self.discount_value)

    def is_valid_coupon(self, code: str) -> bool:
        if self.coupon_code != code:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        if datetime.utcnow() > self.end_date:
            return False
        return self.status == CampaignStatus.ACTIVE
