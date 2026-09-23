from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.infrastructure.adapters.postgres.repository import async_session, DeliveryRepository, DeliveryModel, _to_domain
from src.infrastructure.adapters.rabbitmq.publisher import get_publisher, DeliveryPublisher
from shared.middleware.auth import JWTBearer
from pydantic import BaseModel

router = APIRouter()


async def get_db():
    async with async_session() as session:
        yield session


class AssignRequest(BaseModel):
    motorizado_id: str


@router.get("/pending")
async def get_pending(
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = DeliveryRepository(db)
    deliveries = await repo.find_pending(payload["tenant_id"])
    return [
        {
            "id": d.id,
            "order_id": d.order_id,
            "address": d.delivery_address,
            "status": d.status,
        }
        for d in deliveries
    ]


@router.patch("/{delivery_id}/assign")
async def assign(
    delivery_id: str,
    req: AssignRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: DeliveryPublisher = Depends(get_publisher),
):
    from fastapi import HTTPException
    r = await db.execute(select(DeliveryModel).where(DeliveryModel.id == delivery_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    delivery = _to_domain(m)
    delivery.assign_motorizado(req.motorizado_id)
    repo = DeliveryRepository(db)
    updated = await repo.update(delivery)
    await publisher.publish_assigned(updated)
    return {
        "id": updated.id,
        "status": updated.status,
        "motorizado_id": updated.motorizado_id,
    }


@router.patch("/{delivery_id}/complete")
async def complete(
    delivery_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: DeliveryPublisher = Depends(get_publisher),
):
    from fastapi import HTTPException
    r = await db.execute(select(DeliveryModel).where(DeliveryModel.id == delivery_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    delivery = _to_domain(m)
    qr = delivery.mark_delivered()
    repo = DeliveryRepository(db)
    updated = await repo.update(delivery)
    await publisher.publish_completed(updated)
    return {
        "id": updated.id,
        "status": updated.status,
        "qr_code": qr,
    }
