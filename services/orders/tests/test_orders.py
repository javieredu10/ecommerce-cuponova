"""
Tests para el Orders Service — flujo transaccional completo.
"""
import pytest
from unittest.mock import AsyncMock


def test_order_create_calculates_totals():
    from src.domain.entities.order import Order, OrderItem

    items = [
        OrderItem("p1", "Producto A", quantity=2, unit_price=10.0, discount_applied=1.0),
        OrderItem("p2", "Producto B", quantity=1, unit_price=20.0, discount_applied=0.0),
    ]
    order = Order.create(
        tenant_id="t1",
        customer_id="c1",
        items=items,
        delivery_address="Av. Solano 123, Cuenca",
        coupon_code="PROMO10",
    )
    assert order.subtotal == 40.0       # (10*2) + (20*1)
    assert order.discount_total == 2.0  # (1.0*2) + (0.0*1)
    assert order.total == 38.0
    assert order.status.value == "pending"
    assert order.coupon_code == "PROMO10"


def test_order_mark_paid():
    from src.domain.entities.order import Order, OrderItem, PaymentMethod, OrderStatus

    items = [OrderItem("p1", "Prod", quantity=1, unit_price=50.0)]
    order = Order.create("t1", "c1", items, "Cuenca")
    order.mark_paid(PaymentMethod.CARD, "REF-12345")

    assert order.status == OrderStatus.PAID
    assert order.payment_method == PaymentMethod.CARD
    assert order.payment_reference == "REF-12345"


def test_order_cancel_pending_ok():
    from src.domain.entities.order import Order, OrderItem, OrderStatus

    items = [OrderItem("p1", "Prod", quantity=1, unit_price=10.0)]
    order = Order.create("t1", "c1", items, "Cuenca")
    order.cancel("Cliente solicitó cancelación")
    assert order.status == OrderStatus.CANCELLED


def test_order_cancel_shipped_raises():
    from src.domain.entities.order import Order, OrderItem, OrderStatus, PaymentMethod

    items = [OrderItem("p1", "Prod", quantity=1, unit_price=10.0)]
    order = Order.create("t1", "c1", items, "Cuenca")
    order.mark_paid(PaymentMethod.TRANSFER, "REF-XYZ")
    order.mark_shipped()

    with pytest.raises(ValueError):
        order.cancel("Intento tardío")


def test_order_cannot_pay_twice():
    from src.domain.entities.order import Order, OrderItem, PaymentMethod

    items = [OrderItem("p1", "Prod", quantity=1, unit_price=10.0)]
    order = Order.create("t1", "c1", items, "Cuenca")
    order.mark_paid(PaymentMethod.CASH, "REF-1")

    with pytest.raises(ValueError):
        order.mark_paid(PaymentMethod.CASH, "REF-2")


@pytest.mark.asyncio
async def test_create_order_use_case():
    from src.application.use_cases.order_use_cases import CreateOrderUseCase
    from src.application.dtos import CreateOrderRequest, OrderItemDTO
    from src.domain.entities.order import Order

    mock_repo = AsyncMock()
    mock_pub = AsyncMock()

    req = CreateOrderRequest(
        items=[OrderItemDTO(
            product_id="p1", product_name="Prod A",
            quantity=2, unit_price=15.0,
        )],
        delivery_address="Cuenca, Ecuador",
    )

    # El repo guarda y devuelve el mismo order
    async def fake_save(order):
        return order
    mock_repo.save.side_effect = fake_save

    uc = CreateOrderUseCase(mock_repo, mock_pub)
    resp = await uc.execute(req, tenant_id="t1", customer_id="c1")

    assert resp.total == 30.0
    assert resp.status == "pending"
    mock_pub.publish_order_created.assert_called_once()
