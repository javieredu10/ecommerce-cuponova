from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.adapters.postgres.repository import async_session, PostgresUserRepository
from src.infrastructure.adapters.redis.cache import RedisTokenCache, get_redis
from src.application.use_cases.auth_use_cases import (
    RegisterUseCase, LoginUseCase, RefreshTokenUseCase,
)
from src.application.dtos import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse
import redis.asyncio as aioredis

router = APIRouter()


async def get_db():
    async with async_session() as session:
        yield session


async def get_cache():
    return RedisTokenCache(await get_redis())


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisTokenCache = Depends(get_cache),
):
    uc = RegisterUseCase(PostgresUserRepository(db))
    user = await uc.execute(req)
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        roles=[r.value for r in user.roles],
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisTokenCache = Depends(get_cache),
):
    uc = LoginUseCase(PostgresUserRepository(db), cache)
    return await uc.execute(req)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    cache: RedisTokenCache = Depends(get_cache),
):
    uc = RefreshTokenUseCase(PostgresUserRepository(db), cache)
    return await uc.execute(req)


@router.post("/logout")
async def logout(
    user_id: str,
    cache: RedisTokenCache = Depends(get_cache),
):
    await cache.revoke_refresh_token(user_id)
    return {"message": "Logged out successfully"}
