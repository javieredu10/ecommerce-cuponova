from __future__ import annotations
import os
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select

from src.domain.entities.user_profile import UserProfile, UserType, Address
from src.domain.ports.repositories import IUserProfileRepository

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:secret@localhost:5432/ecommerce")
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserProfileModel(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    auth_user_id = Column(String, nullable=False, unique=True, index=True)
    user_type = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    cedula = Column(String, nullable=True)
    address = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    company_name = Column(String, nullable=True)
    ruc = Column(String, nullable=True)
    firma_electronica_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _to_domain(m: UserProfileModel) -> UserProfile:
    addr = None
    if m.address:
        addr = Address(**m.address)
    return UserProfile(
        id=m.id, tenant_id=m.tenant_id, auth_user_id=m.auth_user_id,
        user_type=UserType(m.user_type), first_name=m.first_name,
        last_name=m.last_name, email=m.email, phone=m.phone,
        cedula=m.cedula, address=addr, is_active=m.is_active,
        company_name=m.company_name, ruc=m.ruc,
        firma_electronica_url=m.firma_electronica_url,
        created_at=m.created_at, updated_at=m.updated_at,
    )


class PostgresUserProfileRepository(IUserProfileRepository):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save(self, p: UserProfile) -> UserProfile:
        m = UserProfileModel(
            id=p.id, tenant_id=p.tenant_id, auth_user_id=p.auth_user_id,
            user_type=p.user_type.value, first_name=p.first_name,
            last_name=p.last_name, email=p.email, phone=p.phone,
            cedula=p.cedula,
            address=vars(p.address) if p.address else None,
            is_active=p.is_active, company_name=p.company_name,
            ruc=p.ruc, firma_electronica_url=p.firma_electronica_url,
        )
        self._s.add(m)
        await self._s.commit()
        await self._s.refresh(m)
        return _to_domain(m)

    async def update(self, p: UserProfile) -> UserProfile:
        r = await self._s.execute(select(UserProfileModel).where(UserProfileModel.id == p.id))
        m = r.scalar_one_or_none()
        if not m:
            raise ValueError("UserProfile not found")
        m.first_name = p.first_name
        m.last_name = p.last_name
        m.phone = p.phone
        m.cedula = p.cedula
        m.address = vars(p.address) if p.address else None
        m.is_active = p.is_active
        m.company_name = p.company_name
        m.ruc = p.ruc
        m.firma_electronica_url = p.firma_electronica_url
        m.updated_at = datetime.utcnow()
        await self._s.commit()
        return _to_domain(m)

    async def find_by_id(self, profile_id: str, tenant_id: str) -> Optional[UserProfile]:
        r = await self._s.execute(
            select(UserProfileModel).where(
                UserProfileModel.id == profile_id,
                UserProfileModel.tenant_id == tenant_id,
            )
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_auth_user_id(self, auth_user_id: str) -> Optional[UserProfile]:
        r = await self._s.execute(
            select(UserProfileModel).where(UserProfileModel.auth_user_id == auth_user_id)
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_email(self, email: str, tenant_id: str) -> Optional[UserProfile]:
        r = await self._s.execute(
            select(UserProfileModel).where(
                UserProfileModel.email == email,
                UserProfileModel.tenant_id == tenant_id,
            )
        )
        m = r.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def list_by_type(self, user_type: UserType, tenant_id: str) -> List[UserProfile]:
        r = await self._s.execute(
            select(UserProfileModel).where(
                UserProfileModel.user_type == user_type.value,
                UserProfileModel.tenant_id == tenant_id,
            )
        )
        return [_to_domain(m) for m in r.scalars().all()]

    async def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50) -> List[UserProfile]:
        r = await self._s.execute(
            select(UserProfileModel)
            .where(UserProfileModel.tenant_id == tenant_id)
            .offset(skip).limit(limit)
        )
        return [_to_domain(m) for m in r.scalars().all()]
