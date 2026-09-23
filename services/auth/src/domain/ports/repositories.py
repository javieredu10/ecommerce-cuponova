from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.user import User


class IUserRepository(ABC):
    """Port — implemented by Postgres adapter."""

    @abstractmethod
    async def find_by_email(self, email: str, tenant_id: str) -> Optional[User]:
        ...

    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        ...

    @abstractmethod
    async def find_by_oauth(self, provider: str, sub: str) -> Optional[User]:
        ...

    @abstractmethod
    async def save(self, user: User) -> User:
        ...


class ITokenCache(ABC):
    """Port — implemented by Redis adapter for refresh token store."""

    @abstractmethod
    async def set_refresh_token(self, user_id: str, token: str, ttl_seconds: int) -> None:
        ...

    @abstractmethod
    async def get_refresh_token(self, user_id: str) -> Optional[str]:
        ...

    @abstractmethod
    async def revoke_refresh_token(self, user_id: str) -> None:
        ...
