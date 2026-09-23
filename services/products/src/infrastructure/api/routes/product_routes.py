from __future__ import annotations
from fastapi import APIRouter, Depends, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.adapters.postgres.repository import async_session, ProductRepository
from src.infrastructure.adapters.redis.cache import ProductCache, get_redis
from src.application.use_cases.product_use_cases import (
    CreateProductUseCase, GetProductUseCase, UpdateProductUseCase, AdjustStockUseCase,
)
from src.application.dtos import (
    CreateProductRequest, UpdateProductRequest, StockAdjustRequest, ProductResponse,
)
from shared.middleware.auth import JWTBearer
from typing import Optional

router = APIRouter()


async def get_db():
    async with async_session() as session:
        yield session


async def get_cache():
    return ProductCache(await get_redis())


@router.post("/", response_model=ProductResponse, status_code=201,
             summary="Crear producto o servicio (Proveedor)")
async def create_product(
    req: CreateProductRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    cache: ProductCache = Depends(get_cache),
):
    uc = CreateProductUseCase(ProductRepository(db), cache)
    return await uc.execute(req, tenant_id=payload["tenant_id"],
                            provider_id=payload["sub"])


@router.get("/sin-receta", response_model=list[ProductResponse],
            summary="Productos Sin Receta disponibles para campaña directa")
async def list_sin_receta(
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = ProductRepository(db)
    products = await repo.list_sin_receta(payload["tenant_id"])
    return [ProductResponse.from_domain(p) for p in products]


@router.get("/", response_model=list[ProductResponse], summary="Listar productos activos")
async def list_products(
    product_type: Optional[str] = Query(None, description="product | service | sin_receta"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    cache: ProductCache = Depends(get_cache),
):
    # Intentar desde cache
    cached = await cache.get_list(payload["tenant_id"], product_type or "all")
    if cached:
        return cached

    repo = ProductRepository(db)
    products = await repo.list_active(
        tenant_id=payload["tenant_id"],
        product_type=product_type,
        skip=skip, limit=limit,
    )
    resp = [ProductResponse.from_domain(p) for p in products]
    await cache.set_list(
        payload["tenant_id"],
        [r.model_dump() for r in resp],
        product_type or "all",
    )
    return resp


@router.get("/provider/{provider_id}", response_model=list[ProductResponse],
            summary="Productos de un proveedor específico")
async def list_by_provider(
    provider_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = ProductRepository(db)
    products = await repo.list_by_provider(provider_id, payload["tenant_id"])
    return [ProductResponse.from_domain(p) for p in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    cache: ProductCache = Depends(get_cache),
):
    uc = GetProductUseCase(ProductRepository(db), cache)
    return await uc.execute(product_id, tenant_id=payload["tenant_id"])


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    req: UpdateProductRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    cache: ProductCache = Depends(get_cache),
):
    uc = UpdateProductUseCase(ProductRepository(db), cache)
    return await uc.execute(product_id, req, tenant_id=payload["tenant_id"])


@router.patch("/{product_id}/stock", response_model=ProductResponse,
              summary="Ajustar stock (increase | decrease)")
async def adjust_stock(
    product_id: str,
    req: StockAdjustRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
    cache: ProductCache = Depends(get_cache),
):
    uc = AdjustStockUseCase(ProductRepository(db), cache)
    return await uc.execute(product_id, req, tenant_id=payload["tenant_id"])
