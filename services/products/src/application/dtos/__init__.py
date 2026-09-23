from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ProductImageDTO(BaseModel):
    url: str
    alt_text: str = ""
    is_primary: bool = False


class CreateProductRequest(BaseModel):
    name: str
    description: str
    product_type: str           # product | service | sin_receta
    sku: str
    price: float
    stock: int = 0
    category: str = "general"
    tags: List[str] = []
    requires_prescription: bool = True
    facturacion_code: Optional[str] = None
    images: List[ProductImageDTO] = []


class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    facturacion_code: Optional[str] = None
    images: Optional[List[ProductImageDTO]] = None


class StockAdjustRequest(BaseModel):
    quantity: int
    operation: str  # "increase" | "decrease"


class ProductResponse(BaseModel):
    id: str
    tenant_id: str
    provider_id: str
    name: str
    description: str
    product_type: str
    sku: str
    price: float
    stock: int
    images: List[dict]
    category: str
    tags: List[str]
    status: str
    requires_prescription: bool
    facturacion_code: Optional[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, p) -> "ProductResponse":
        return cls(
            id=p.id, tenant_id=p.tenant_id, provider_id=p.provider_id,
            name=p.name, description=p.description,
            product_type=p.product_type.value, sku=p.sku,
            price=p.price, stock=p.stock,
            images=[vars(img) for img in p.images],
            category=p.category, tags=p.tags,
            status=p.status.value,
            requires_prescription=p.requires_prescription,
            facturacion_code=p.facturacion_code,
            created_at=p.created_at,
        )
