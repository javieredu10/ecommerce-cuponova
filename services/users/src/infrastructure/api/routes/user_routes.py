from __future__ import annotations
from fastapi import APIRouter, Depends, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.adapters.postgres.repository import async_session, PostgresUserProfileRepository
from src.application.use_cases.user_use_cases import (
    CreateUserProfileUseCase, UpdateUserProfileUseCase,
    GetUserProfileUseCase, ListUsersByTypeUseCase,
)
from src.application.dtos import (
    CreateUserProfileRequest, UpdateUserProfileRequest, UserProfileResponse,
)
from shared.middleware.auth import JWTBearer

router = APIRouter()


async def get_db():
    async with async_session() as session:
        yield session


@router.post("/", response_model=UserProfileResponse, status_code=201,
             summary="Crear perfil de usuario (Admin/Proveedor/Cliente)")
async def create_profile(
    req: CreateUserProfileRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    uc = CreateUserProfileUseCase(PostgresUserProfileRepository(db))
    return await uc.execute(req, tenant_id=payload["tenant_id"])


@router.get("/me", response_model=UserProfileResponse, summary="Mi perfil")
async def get_my_profile(
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = PostgresUserProfileRepository(db)
    profile = await repo.find_by_auth_user_id(payload["sub"])
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return UserProfileResponse.from_domain(profile)


@router.get("/{profile_id}", response_model=UserProfileResponse)
async def get_profile(
    profile_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    uc = GetUserProfileUseCase(PostgresUserProfileRepository(db))
    return await uc.execute(profile_id, tenant_id=payload["tenant_id"])


@router.put("/{profile_id}", response_model=UserProfileResponse)
async def update_profile(
    profile_id: str,
    req: UpdateUserProfileRequest,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    uc = UpdateUserProfileUseCase(PostgresUserProfileRepository(db))
    return await uc.execute(profile_id, req, tenant_id=payload["tenant_id"])


@router.get("/", response_model=list[UserProfileResponse],
            summary="Listar usuarios por tipo: admin | provider | client")
async def list_users(
    user_type: str = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = PostgresUserProfileRepository(db)
    if user_type:
        uc = ListUsersByTypeUseCase(repo)
        return await uc.execute(user_type, tenant_id=payload["tenant_id"])
    profiles = await repo.list_all(tenant_id=payload["tenant_id"], skip=skip, limit=limit)
    return [UserProfileResponse.from_domain(p) for p in profiles]


@router.delete("/{profile_id}", status_code=204)
async def deactivate_user(
    profile_id: str,
    payload: dict = Depends(JWTBearer),
    db: AsyncSession = Depends(get_db),
):
    repo = PostgresUserProfileRepository(db)
    profile = await repo.find_by_id(profile_id, payload["tenant_id"])
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    profile.is_active = False
    await repo.update(profile)
