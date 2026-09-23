from __future__ import annotations
from typing import List
from fastapi import HTTPException, status

from src.domain.entities.order import Order, OrderItem, PaymentMethod
from src.infrastructure.adapters.postgres.repository import OrderRepository, SaleRepository
from src.infrastructure.adapters.rabbitmq.publisher import OrderPublisher
from src.application.dtos import CreateOrderRequest, PayOrderRequest, OrderResponse


class CreateOrderUseCase:
    def __init__(self, repo: OrderRepository, publisher: OrderPublisher):
        self._repo = repo
        self._pub = publisher

    async def execute(self, req: CreateOrderRequest, tenant_id: str, customer_id: str) -> OrderResponse:
        items = [
            OrderItem(
                product_id=i.product_id,
                product_name=i.product_name,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount_applied=i.discount_applied,
            )
            for i in req.items
        ]
        order = Order.create(
            tenant_id=tenant_id,
            customer_id=customer_id,
            items=items,
            delivery_address=req.delivery_address,
            coupon_code=req.coupon_code,
            campaign_id=req.campaign_id,
            notes=req.notes,
        )
        saved = await self._repo.save(order)
        await self._pub.publish_order_created(saved)
        return OrderResponse.from_domain(saved)


class PayOrderUseCase:
    def __init__(self, order_repo: OrderRepository, sale_repo: SaleRepository, publisher: OrderPublisher):
        self._orders = order_repo
        self._sales = sale_repo
        self._pub = publisher

    async def execute(self, order_id: str, req: PayOrderRequest, tenant_id: str) -> OrderResponse:
        order = await self._orders.find_by_id(order_id, tenant_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        order.mark_paid(PaymentMethod(req.payment_method), req.payment_reference)
        # Transactional: update order AND record sale in same Postgres session
        updated = await self._orders.update(order)
        await self._sales.record_sale(updated)
        await self._pub.publish_order_paid(updated)
        return OrderResponse.from_domain(updated)


class CancelOrderUseCase:
    def __init__(self, repo: OrderRepository, publisher: OrderPublisher):
        self._repo = repo
        self._pub = publisher

    async def execute(self, order_id: str, reason: str, tenant_id: str) -> OrderResponse:
        order = await self._repo.find_by_id(order_id, tenant_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        order.cancel(reason)
        updated = await self._repo.update(order)
        await self._pub.publish_order_cancelled(updated, reason)
        return OrderResponse.from_domain(updated)
