from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status

from src.domain.entities.campaign import Campaign, CampaignExtra, DiscountType, CampaignStatus
from src.infrastructure.adapters.postgres.repository import CampaignRepository
from src.infrastructure.adapters.rabbitmq.publisher import CampaignPublisher
from src.infrastructure.adapters.mongo.log_repository import CampaignLogRepository
from src.application.dtos import CreateCampaignRequest, CampaignResponse


class CreateCampaignUseCase:
    def __init__(self, repo: CampaignRepository, publisher: CampaignPublisher, log_repo: CampaignLogRepository):
        self._repo = repo
        self._publisher = publisher
        self._log = log_repo

    async def execute(self, req: CreateCampaignRequest, tenant_id: str) -> CampaignResponse:
        extra = None
        if req.extra:
            extra = CampaignExtra(
                tiempo_horas=req.extra.tiempo_horas,
                minimo_vender=req.extra.minimo_vender,
                maximo_vender=req.extra.maximo_vender,
                contrato_url=req.extra.contrato_url,
            )
        campaign = Campaign.create(
            tenant_id=tenant_id,
            name=req.name,
            description=req.description,
            discount_type=DiscountType(req.discount_type),
            discount_value=req.discount_value,
            product_ids=req.product_ids,
            service_ids=req.service_ids,
            start_date=req.start_date,
            end_date=req.end_date,
            extra=extra,
            coupon_code=req.coupon_code,
            max_uses=req.max_uses,
        )
        saved = await self._repo.save(campaign)
        # Publish domain event
        await self._publisher.publish_campaign_created(saved)
        # Log to MongoDB (non-transactional)
        await self._log.log_action(tenant_id, "campaign_created", {"campaign_id": saved.id})
        return CampaignResponse.from_domain(saved)


class ActivateCampaignUseCase:
    def __init__(self, repo: CampaignRepository, publisher: CampaignPublisher):
        self._repo = repo
        self._publisher = publisher

    async def execute(self, campaign_id: str, tenant_id: str) -> CampaignResponse:
        campaign = await self._repo.find_by_id(campaign_id, tenant_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        campaign.activate()
        saved = await self._repo.update(campaign)
        await self._publisher.publish_campaign_activated(saved)
        return CampaignResponse.from_domain(saved)


class ValidateCouponUseCase:
    def __init__(self, repo: CampaignRepository):
        self._repo = repo

    async def execute(self, coupon_code: str, tenant_id: str, base_price: float) -> dict:
        campaign = await self._repo.find_by_coupon(coupon_code, tenant_id)
        if not campaign or not campaign.is_valid_coupon(coupon_code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired coupon")
        discounted = campaign.apply_discount(base_price)
        return {
            "valid": True,
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "original_price": base_price,
            "discounted_price": discounted,
            "savings": base_price - discounted,
        }
