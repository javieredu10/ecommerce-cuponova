from __future__ import annotations
from fastapi import APIRouter, Depends, Security, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.adapters.postgres.repository import async_session, CampaignRepository
from src.infrastructure.adapters.rabbitmq.publisher import get_publisher, CampaignPublisher
from src.infrastructure.adapters.mongo.log_repository import get_log_repo, CampaignLogRepository
from src.application.use_cases.campaign_use_cases import (
    CreateCampaignUseCase, ActivateCampaignUseCase, ValidateCouponUseCase,
)
from src.application.dtos import CreateCampaignRequest, CampaignResponse
from shared.middleware.auth import JWTBearer
from fastapi import Request

router = APIRouter()


async def get_db():
    async with async_session() as session:
        yield session


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    req: CreateCampaignRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: CampaignPublisher = Depends(get_publisher),
    log_repo: CampaignLogRepository = Depends(get_log_repo),
):
    tenant_id = payload["tenant_id"]
    uc = CreateCampaignUseCase(CampaignRepository(db), publisher, log_repo)
    return await uc.execute(req, tenant_id)


@router.patch("/{campaign_id}/activate", response_model=CampaignResponse)
async def activate_campaign(
    campaign_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: CampaignPublisher = Depends(get_publisher),
):
    tenant_id = payload["tenant_id"]
    uc = ActivateCampaignUseCase(CampaignRepository(db), publisher)
    return await uc.execute(campaign_id, tenant_id)


@router.get("/validate-coupon")
async def validate_coupon(
    code: str = Query(...),
    base_price: float = Query(...),
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = payload["tenant_id"]
    uc = ValidateCouponUseCase(CampaignRepository(db))
    return await uc.execute(code, tenant_id, base_price)


@router.get("/", response_model=list[CampaignResponse])
async def list_active(
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = payload["tenant_id"]
    repo = CampaignRepository(db)
    campaigns = await repo.list_active(tenant_id)
    return [CampaignResponse.from_domain(c) for c in campaigns]
