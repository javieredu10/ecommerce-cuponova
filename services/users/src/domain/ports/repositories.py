from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.user_profile import UserProfile, UserType


class IUserProfileRepository(ABC):

    @abstractmethod
    async def save(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    async def update(self, profile: UserProfile) -> UserProfile: ...

    @abstractmethod
    async def find_by_id(self, profile_id: str, tenant_id: str) -> Optional[UserProfile]: ...

    @abstractmethod
    async def find_by_auth_user_id(self, auth_user_id: str) -> Optional[UserProfile]: ...

    @abstractmethod
    async def find_by_email(self, email: str, tenant_id: str) -> Optional[UserProfile]: ...

    @abstractmethod
    async def list_by_type(self, user_type: UserType, tenant_id: str) -> List[UserProfile]: ...

    @abstractmethod
    async def list_all(self, tenant_id: str, skip: int, limit: int) -> List[UserProfile]: ...
