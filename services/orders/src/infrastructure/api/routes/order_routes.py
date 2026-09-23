from __future__ import annotations
from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.adapters.postgres.repository import async_session, OrderRepository, SaleRepository
from src.infrastructure.adapters.rabbitmq.publisher import get_publisher, OrderPublisher
from src.application.use_cases.order_use_cases import CreateOrderUseCase, PayOrderUseCase, CancelOrderUseCase
from src.application.dtos import CreateOrderRequest, PayOrderRequest, OrderResponse
from shared.middleware.auth import JWTBearer

router = APIRouter()


async def get_db():
    async with async_session() as session:
        yield session


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    req: CreateOrderRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: OrderPublisher = Depends(get_publisher),
):
    uc = CreateOrderUseCase(OrderRepository(db), publisher)
    return await uc.execute(req, tenant_id=payload["tenant_id"], customer_id=payload["sub"])


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def pay_order(
    order_id: str,
    req: PayOrderRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: OrderPublisher = Depends(get_publisher),
):
    uc = PayOrderUseCase(OrderRepository(db), SaleRepository(db), publisher)
    return await uc.execute(order_id, req, tenant_id=payload["tenant_id"])


@router.delete("/{order_id}")
async def cancel_order(
    order_id: str,
    reason: str = "Customer requested cancellation",
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    publisher: OrderPublisher = Depends(get_publisher),
):
    uc = CancelOrderUseCase(OrderRepository(db), publisher)
    return await uc.execute(order_id, reason, tenant_id=payload["tenant_id"])


@router.get("/my-orders", response_model=list[OrderResponse])
async def my_orders(
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    orders = await repo.find_by_customer(payload["sub"], payload["tenant_id"])
    return [OrderResponse.from_domain(o) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = OrderRepository(db)
    order = await repo.find_by_id(order_id, payload["tenant_id"])
    return OrderResponse.from_domain(order)
