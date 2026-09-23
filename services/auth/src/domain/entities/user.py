from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PROVIDER = "provider"
    CLIENT = "client"


class OAuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"


@dataclass
class User:
    """Auth aggregate root — minimal data needed for authentication."""

    id: str
    tenant_id: str
    email: str
    hashed_password: Optional[str]
    roles: List[UserRole]
    is_active: bool
    oauth_provider: OAuthProvider
    oauth_sub: Optional[str]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(
        tenant_id: str,
        email: str,
        hashed_password: Optional[str] = None,
        roles: Optional[List[UserRole]] = None,
        oauth_provider: OAuthProvider = OAuthProvider.LOCAL,
        oauth_sub: Optional[str] = None,
    ) -> "User":
        now = datetime.utcnow()
        return User(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=email,
            hashed_password=hashed_password,
            roles=roles or [UserRole.CLIENT],
            is_active=True,
            oauth_provider=oauth_provider,
            oauth_sub=oauth_sub,
            created_at=now,
            updated_at=now,
        )

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles
