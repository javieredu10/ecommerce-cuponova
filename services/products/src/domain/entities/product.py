from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ProductType(str, Enum):
    PRODUCT = "product"          # Productos del diagrama
    SERVICE = "service"          # Servicios del diagrama
    SIN_RECETA = "sin_receta"    # Producto Servicio Sin Receta del diagrama


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


@dataclass
class ProductImage:
    url: str
    alt_text: str = ""
    is_primary: bool = False


@dataclass
class Product:
    """
    Entidad producto.
    Relaciones del diagrama:
      Campañas -> Productos | Servicios
      Producto Servicio Sin Receta -> Campañas
    """
    id: str
    tenant_id: str
    provider_id: str            # Proveedor dueño del producto
    name: str
    description: str
    product_type: ProductType
    sku: str
    price: float
    stock: int
    images: List[ProductImage]
    category: str
    tags: List[str]
    status: ProductStatus
    requires_prescription: bool  # False = Sin Receta
    facturacion_code: Optional[str]   # Código para Facturación
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        tenant_id: str,
        provider_id: str,
        name: str,
        description: str,
        product_type: ProductType,
        sku: str,
        price: float,
        stock: int = 0,
        category: str = "general",
        tags: Optional[List[str]] = None,
        requires_prescription: bool = True,
        facturacion_code: Optional[str] = None,
    ) -> "Product":
        now = datetime.utcnow()
        return Product(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            provider_id=provider_id,
            name=name,
            description=description,
            product_type=product_type,
            sku=sku,
            price=price,
            stock=stock,
            images=[],
            category=category,
            tags=tags or [],
            status=ProductStatus.ACTIVE if stock > 0 else ProductStatus.OUT_OF_STOCK,
            requires_prescription=requires_prescription,
            facturacion_code=facturacion_code,
            created_at=now,
            updated_at=now,
        )

    def decrease_stock(self, quantity: int) -> None:
        if self.stock < quantity:
            raise ValueError(f"Stock insuficiente: disponible={self.stock}, solicitado={quantity}")
        self.stock -= quantity
        if self.stock == 0:
            self.status = ProductStatus.OUT_OF_STOCK
        self.updated_at = datetime.utcnow()

    def increase_stock(self, quantity: int) -> None:
        self.stock += quantity
        if self.status == ProductStatus.OUT_OF_STOCK:
            self.status = ProductStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def apply_discount(self, pct: float) -> float:
        """Retorna precio con descuento porcentual."""
        return round(self.price * (1 - pct / 100), 2)
