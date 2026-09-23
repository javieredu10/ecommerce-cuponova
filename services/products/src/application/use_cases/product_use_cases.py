from __future__ import annotations
from fastapi import HTTPException, status

from src.domain.entities.product import Product, ProductType, ProductImage
from src.infrastructure.adapters.postgres.repository import ProductRepository
from src.infrastructure.adapters.redis.cache import ProductCache
from src.application.dtos import (
    CreateProductRequest, UpdateProductRequest, StockAdjustRequest, ProductResponse,
)


class CreateProductUseCase:
    def __init__(self, repo: ProductRepository, cache: ProductCache):
        self._repo = repo
        self._cache = cache

    async def execute(self, req: CreateProductRequest, tenant_id: str,
                      provider_id: str) -> ProductResponse:
        product = Product.create(
            tenant_id=tenant_id,
            provider_id=provider_id,
            name=req.name,
            description=req.description,
            product_type=ProductType(req.product_type),
            sku=req.sku,
            price=req.price,
            stock=req.stock,
            category=req.category,
            tags=req.tags,
            requires_prescription=req.requires_prescription,
            facturacion_code=req.facturacion_code,
        )
        if req.images:
            product.images = [ProductImage(**img.model_dump()) for img in req.images]
        saved = await self._repo.save(product)
        await self._cache.invalidate(tenant_id, saved.id)
        return ProductResponse.from_domain(saved)


class GetProductUseCase:
    def __init__(self, repo: ProductRepository, cache: ProductCache):
        self._repo = repo
        self._cache = cache

    async def execute(self, product_id: str, tenant_id: str) -> ProductResponse:
        # Primero buscar en cache
        cached = await self._cache.get(tenant_id, product_id)
        if cached:
            return ProductResponse(**cached)
        product = await self._repo.find_by_id(product_id, tenant_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Producto no encontrado")
        resp = ProductResponse.from_domain(product)
        await self._cache.set(tenant_id, product_id, resp.model_dump())
        return resp


class UpdateProductUseCase:
    def __init__(self, repo: ProductRepository, cache: ProductCache):
        self._repo = repo
        self._cache = cache

    async def execute(self, product_id: str, req: UpdateProductRequest,
                      tenant_id: str) -> ProductResponse:
        product = await self._repo.find_by_id(product_id, tenant_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Producto no encontrado")
        if req.name:
            product.name = req.name
        if req.description:
            product.description = req.description
        if req.price is not None:
            product.price = req.price
        if req.stock is not None:
            product.stock = req.stock
        if req.category:
            product.category = req.category
        if req.tags is not None:
            product.tags = req.tags
        if req.facturacion_code is not None:
            product.facturacion_code = req.facturacion_code
        if req.images is not None:
            product.images = [ProductImage(**img.model_dump()) for img in req.images]
        if req.status:
            from src.domain.entities.product import ProductStatus
            product.status = ProductStatus(req.status)
        updated = await self._repo.update(product)
        await self._cache.invalidate(tenant_id, product_id)
        return ProductResponse.from_domain(updated)


class AdjustStockUseCase:
    def __init__(self, repo: ProductRepository, cache: ProductCache):
        self._repo = repo
        self._cache = cache

    async def execute(self, product_id: str, req: StockAdjustRequest,
                      tenant_id: str) -> ProductResponse:
        product = await self._repo.find_by_id(product_id, tenant_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Producto no encontrado")
        if req.operation == "increase":
            product.increase_stock(req.quantity)
        elif req.operation == "decrease":
            try:
                product.decrease_stock(req.quantity)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Operación debe ser 'increase' o 'decrease'")
        updated = await self._repo.update(product)
        await self._cache.invalidate(tenant_id, product_id)
        return ProductResponse.from_domain(updated)
