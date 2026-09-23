from __future__ import annotations
from fastapi import HTTPException, status

from src.domain.entities.user_profile import UserProfile, UserType, Address
from src.domain.ports.repositories import IUserProfileRepository
from src.application.dtos import (
    CreateUserProfileRequest, UpdateUserProfileRequest, UserProfileResponse,
)


class CreateUserProfileUseCase:
    def __init__(self, repo: IUserProfileRepository):
        self._repo = repo

    async def execute(self, req: CreateUserProfileRequest, tenant_id: str) -> UserProfileResponse:
        existing = await self._repo.find_by_auth_user_id(req.auth_user_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Perfil ya existe para este usuario")
        addr = None
        if req.address:
            addr = Address(
                street=req.address.street, city=req.address.city,
                state=req.address.state, zip_code=req.address.zip_code,
                country=req.address.country,
            )
        profile = UserProfile.create(
            tenant_id=tenant_id,
            auth_user_id=req.auth_user_id,
            user_type=UserType(req.user_type),
            first_name=req.first_name,
            last_name=req.last_name,
            email=req.email,
            phone=req.phone,
            cedula=req.cedula,
            address=addr,
            company_name=req.company_name,
            ruc=req.ruc,
        )
        saved = await self._repo.save(profile)
        return UserProfileResponse.from_domain(saved)


class UpdateUserProfileUseCase:
    def __init__(self, repo: IUserProfileRepository):
        self._repo = repo

    async def execute(self, profile_id: str, req: UpdateUserProfileRequest,
                      tenant_id: str) -> UserProfileResponse:
        profile = await self._repo.find_by_id(profile_id, tenant_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
        if req.first_name:
            profile.first_name = req.first_name
        if req.last_name:
            profile.last_name = req.last_name
        if req.phone is not None:
            profile.phone = req.phone
        if req.cedula is not None:
            profile.cedula = req.cedula
        if req.address:
            profile.address = Address(**req.address.model_dump())
        if req.company_name is not None:
            profile.company_name = req.company_name
        if req.ruc is not None:
            profile.ruc = req.ruc
        if req.firma_electronica_url is not None:
            profile.firma_electronica_url = req.firma_electronica_url
        updated = await self._repo.update(profile)
        return UserProfileResponse.from_domain(updated)


class GetUserProfileUseCase:
    def __init__(self, repo: IUserProfileRepository):
        self._repo = repo

    async def execute(self, profile_id: str, tenant_id: str) -> UserProfileResponse:
        profile = await self._repo.find_by_id(profile_id, tenant_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
        return UserProfileResponse.from_domain(profile)


class ListUsersByTypeUseCase:
    def __init__(self, repo: IUserProfileRepository):
        self._repo = repo

    async def execute(self, user_type: str, tenant_id: str):
        profiles = await self._repo.list_by_type(UserType(user_type), tenant_id)
        return [UserProfileResponse.from_domain(p) for p in profiles]
