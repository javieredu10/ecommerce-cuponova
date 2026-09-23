from __future__ import annotations
import uuid
import qrcode
import io
import base64
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class Delivery:
    id: str
    tenant_id: str
    order_id: str
    customer_id: str
    motorizado_id: Optional[str]
    delivery_address: str
    status: DeliveryStatus
    qr_code: Optional[str]   # base64 QR image
    tracking_notes: Optional[str]
    assigned_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        tenant_id: str,
        order_id: str,
        customer_id: str,
        delivery_address: str,
    ) -> "Delivery":
        now = datetime.utcnow()
        return Delivery(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            order_id=order_id,
            customer_id=customer_id,
            motorizado_id=None,
            delivery_address=delivery_address,
            status=DeliveryStatus.PENDING,
            qr_code=None,
            tracking_notes=None,
            assigned_at=None,
            delivered_at=None,
            created_at=now,
            updated_at=now,
        )

    def assign_motorizado(self, motorizado_id: str) -> None:
        self.motorizado_id = motorizado_id
        self.status = DeliveryStatus.ASSIGNED
        self.assigned_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_delivered(self) -> str:
        """Generate QR code, mark delivered, return QR base64."""
        qr_data = f"DELIVERY:{self.id}|ORDER:{self.order_id}|TENANT:{self.tenant_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.qr_code = base64.b64encode(buf.getvalue()).decode()
        self.status = DeliveryStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return self.qr_code
