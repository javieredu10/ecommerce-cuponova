"""
Tests para el Campaigns Service — validación de cupones y descuentos.
"""
import pytest
from datetime import datetime, timedelta


def test_campaign_create_defaults():
    from src.domain.entities.campaign import Campaign, DiscountType, CampaignStatus

    c = Campaign.create(
        tenant_id="t1",
        name="Promo Verano",
        description="20% en medicamentos",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=20.0,
        product_ids=["p1", "p2"],
        service_ids=[],
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        coupon_code="VERANO20",
        max_uses=100,
    )
    assert c.status == CampaignStatus.DRAFT
    assert c.current_uses == 0
    assert c.coupon_code == "VERANO20"


def test_campaign_percentage_discount():
    from src.domain.entities.campaign import Campaign, DiscountType

    c = Campaign.create(
        tenant_id="t1", name="Test", description="",
        discount_type=DiscountType.PERCENTAGE, discount_value=25.0,
        product_ids=[], service_ids=[],
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
    )
    result = c.apply_discount(100.0)
    assert result == 75.0


def test_campaign_fixed_discount():
    from src.domain.entities.campaign import Campaign, DiscountType

    c = Campaign.create(
        tenant_id="t1", name="Test", description="",
        discount_type=DiscountType.FIXED, discount_value=15.0,
        product_ids=[], service_ids=[],
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
    )
    assert c.apply_discount(50.0) == 35.0
    assert c.apply_discount(10.0) == 0.0  # No negativo


def test_campaign_activate():
    from src.domain.entities.campaign import Campaign, DiscountType, CampaignStatus

    c = Campaign.create(
        tenant_id="t1", name="Test", description="",
        discount_type=DiscountType.FIXED, discount_value=5.0,
        product_ids=[], service_ids=[],
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
    )
    c.activate()
    assert c.status == CampaignStatus.ACTIVE


def test_coupon_invalid_when_max_uses_reached():
    from src.domain.entities.campaign import Campaign, DiscountType, CampaignStatus

    c = Campaign.create(
        tenant_id="t1", name="Test", description="",
        discount_type=DiscountType.PERCENTAGE, discount_value=10.0,
        product_ids=[], service_ids=[],
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
        coupon_code="AGOTADO",
        max_uses=5,
    )
    c.activate()
    c.current_uses = 5   # Ya se agotó
    assert c.is_valid_coupon("AGOTADO") is False


def test_coupon_invalid_expired():
    from src.domain.entities.campaign import Campaign, DiscountType, CampaignStatus

    c = Campaign.create(
        tenant_id="t1", name="Test", description="",
        discount_type=DiscountType.PERCENTAGE, discount_value=10.0,
        product_ids=[], service_ids=[],
        start_date=datetime.utcnow() - timedelta(days=10),
        end_date=datetime.utcnow() - timedelta(days=1),  # Ya expiró
        coupon_code="VENCIDO",
    )
    c.activate()
    assert c.is_valid_coupon("VENCIDO") is False
