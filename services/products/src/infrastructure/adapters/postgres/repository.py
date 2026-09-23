from __future__ import annotations
import os
import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select

from src.domain.entities.product import Product, ProductType, ProductStatus, ProductImage

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:secret@localhost:5432/ecommerce")
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "products"}

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    provider_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    product_type = Column(String, nullable=False)
    sku = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    images = Column(JSON, default=[])
    category = Column(String, default="general")
    tags = Column(ARRAY(String), default=[])
    status = Column(String, default="active")
    requires_prescription = Column(Boolean, default=True)
    facturacion_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _to_domain(m: ProductModel) -> Product:
    images = [ProductImage(**img) for img in (m.images or [])]
    return Product(
        id=m.id, tenant_id=m.tenant_id, provider_id=m.provider_id,
        name=m.name, description=m.description,
        product_type=ProductType(m.product_type),
        sku=m.sku, price=m.price, stock=m.stock,
        images=images, category=m.category,
        tags=m.tags or [],
        status=ProductStatus(m.status),
        requires_prescription=m.requires_prescription,
        facturacion_code=m.facturacion_code,
        created_at=m.created_at, updated_at=m.updated_at,
    )


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, p: Product) -> Product:
        m = ProductModel(
            id=p.id, tenant_id=p.tenant_id, provider_id=p.provider_id,
            name=p.name, description=p.description,
            product_type=p.product_type.value, sku=p.sku,
            price=p.price, stock=p.stock,
            images=[vars(img) for img in p.images],
            category=p.category, tags=p.tags,
            status=p.status.value,
            requires_prescription=p.requires_prescription,
            facturacion_code=p.facturacion_code,
        )
        self._s.add(m)
        await self._s.commit()
        await self._s.refresh(m)
        return _to_domain(m)

    async def update(self, p: Product) -> Product:
        r = await self._s.execute(select(ProductModel).where(ProductModel.id == p.id))
        m = r.scalar_one_or_none()
        if not m:
            raise ValueError("Producto no encontrado")
        m.name = p.name
        m.description = p.description
        m.price = p.price
        m.stock = p.stock
        m.status = p.status.value
        m.images = [vars(img) for img in p.images]
        m.category = p.category
        m.tags = p.tags
        m.facturacion_code = p.facturacion_code
        m.updated_at = datetime.utcnow()
        await self._s.commit()
        return _to_domain(m)

    async def find_by_id(self, product_id: str, tenant_id: str) -> Optional[Product]:
        r = await self._s.execute(
            select(ProductModel).where(
                ProductModel.id == product_id,
                ProductModel.tenant_id == tenant_id,
            )
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_ids(self, ids: List[str], tenant_id: str) -> List[Product]:
        r = await self._s.execute(
            select(ProductModel).where(
                ProductModel.id.in_(ids),
                ProductModel.tenant_id == tenant_id,
            )
        )
        return [_to_domain(m) for m in r.scalars().all()]

    async def list_active(self, tenant_id: str, product_type: Optional[str] = None,
                          skip: int = 0, limit: int = 50) -> List[Product]:
        stmt = select(ProductModel).where(
            ProductModel.tenant_id == tenant_id,
            ProductModel.status == "active",
        )
        if product_type:
            stmt = stmt.where(ProductModel.product_type == product_type)
        stmt = stmt.offset(skip).limit(limit)
        r = await self._s.execute(stmt)
        return [_to_domain(m) for m in r.scalars().all()]

    async def list_sin_receta(self, tenant_id: str) -> List[Product]:
        r = await self._s.execute(
            select(ProductModel).where(
                ProductModel.tenant_id == tenant_id,
                ProductModel.requires_prescription == False,
                ProductModel.status == "active",
            )
        )
        return [_to_domain(m) for m in r.scalars().all()]

    async def list_by_provider(self, provider_id: str, tenant_id: str) -> List[Product]:
        r = await self._s.execute(
            select(ProductModel).where(
                ProductModel.provider_id == provider_id,
                ProductModel.tenant_id == tenant_id,
            )
        )
        return [_to_domain(m) for m in r.scalars().all()]
