from __future__ import annotations
from typing import Optional, Tuple
from datetime import datetime, timedelta
import os
import jwt
import bcrypt

from src.domain.entities.user import User, UserRole, OAuthProvider
from src.domain.ports.repositories import IUserRepository, ITokenCache
from src.application.dtos import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
)
from fastapi import HTTPException, status

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretjwtkey")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TTL = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_access_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TTL)
    payload = {
        "sub": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "roles": [r.value for r in user.roles],
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _create_refresh_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TTL_DAYS)
    payload = {"sub": user.id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


class RegisterUseCase:
    def __init__(self, user_repo: IUserRepository):
        self._repo = user_repo

    async def execute(self, req: RegisterRequest) -> User:
        existing = await self._repo.find_by_email(req.email, req.tenant_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User.create(
            tenant_id=req.tenant_id,
            email=req.email,
            hashed_password=_hash_password(req.password),
            roles=[UserRole(r) for r in req.roles] if req.roles else [UserRole.CLIENT],
        )
        return await self._repo.save(user)


class LoginUseCase:
    def __init__(self, user_repo: IUserRepository, token_cache: ITokenCache):
        self._repo = user_repo
        self._cache = token_cache

    async def execute(self, req: LoginRequest) -> TokenResponse:
        user = await self._repo.find_by_email(req.email, req.tenant_id)
        if not user or not user.hashed_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not _verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
        access = _create_access_token(user)
        refresh = _create_refresh_token(user)
        await self._cache.set_refresh_token(user.id, refresh, REFRESH_TTL_DAYS * 86400)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=ACCESS_TTL * 60,
        )


class RefreshTokenUseCase:
    def __init__(self, user_repo: IUserRepository, token_cache: ITokenCache):
        self._repo = user_repo
        self._cache = token_cache

    async def execute(self, req: RefreshRequest) -> TokenResponse:
        try:
            payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                raise ValueError
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user_id = payload["sub"]
        stored = await self._cache.get_refresh_token(user_id)
        if stored != req.refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or expired")
        user = await self._repo.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        access = _create_access_token(user)
        refresh = _create_refresh_token(user)
        await self._cache.set_refresh_token(user.id, refresh, REFRESH_TTL_DAYS * 86400)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=ACCESS_TTL * 60,
        )


class OAuthLoginUseCase:
    """Handle Google OAuth2 callback — creates user if first time."""

    def __init__(self, user_repo: IUserRepository, token_cache: ITokenCache):
        self._repo = user_repo
        self._cache = token_cache

    async def execute(self, provider: str, sub: str, email: str, tenant_id: str) -> TokenResponse:
        user = await self._repo.find_by_oauth(provider, sub)
        if not user:
            user = User.create(
                tenant_id=tenant_id,
                email=email,
                hashed_password=None,
                roles=[UserRole.CLIENT],
                oauth_provider=OAuthProvider(provider),
                oauth_sub=sub,
            )
            user = await self._repo.save(user)
        access = _create_access_token(user)
        refresh = _create_refresh_token(user)
        await self._cache.set_refresh_token(user.id, refresh, REFRESH_TTL_DAYS * 86400)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=ACCESS_TTL * 60,
        )
