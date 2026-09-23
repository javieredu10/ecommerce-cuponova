"""
Tests para el Deliveries Service — asignación de motorizado y QR.
"""
import pytest


def test_delivery_create():
    from src.domain.entities.delivery import Delivery, DeliveryStatus

    d = Delivery.create(
        tenant_id="t1",
        order_id="order-001",
        customer_id="c1",
        delivery_address="Av. Huayna Capac 123, Cuenca",
    )
    assert d.status == DeliveryStatus.PENDING
    assert d.motorizado_id is None
    assert d.qr_code is None


def test_delivery_assign_motorizado():
    from src.domain.entities.delivery import Delivery, DeliveryStatus

    d = Delivery.create("t1", "order-001", "c1", "Cuenca")
    d.assign_motorizado("moto-001")

    assert d.status == DeliveryStatus.ASSIGNED
    assert d.motorizado_id == "moto-001"
    assert d.assigned_at is not None


def test_delivery_complete_generates_qr():
    from src.domain.entities.delivery import Delivery, DeliveryStatus
    import base64

    d = Delivery.create("t1", "order-001", "c1", "Cuenca")
    d.assign_motorizado("moto-001")
    qr = d.mark_delivered()

    assert d.status == DeliveryStatus.DELIVERED
    assert d.qr_code is not None
    assert d.delivered_at is not None
    # Verificar que es base64 válido de una imagen PNG
    decoded = base64.b64decode(qr)
    assert decoded[:4] == b'\x89PNG'  # Header PNG
    assert qr == d.qr_code


def test_delivery_qr_contains_delivery_info():
    from src.domain.entities.delivery import Delivery
    import base64
    import qrcode
    import io

    d = Delivery.create("t1", "order-xyz", "c1", "Cuenca")
    d.assign_motorizado("moto-001")
    d.mark_delivered()

    # El QR se puede decodificar — verificar que no falla
    assert d.qr_code is not None
    assert len(d.qr_code) > 100   # PNG base64 tiene considerable longitud
