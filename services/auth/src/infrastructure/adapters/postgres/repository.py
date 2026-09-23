from __future__ import annotations
import os
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, ARRAY, Enum as PgEnum
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.future import select
from datetime import datetime

from src.domain.entities.user import User, UserRole, OAuthProvider
from src.domain.ports.repositories import IUserRepository

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:secret@localhost:5432/ecommerce")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "auth_users"
    __table_args__ = {"schema": "auth"}

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=True)
    roles = Column(ARRAY(String), nullable=False, default=[])
    is_active = Column(Boolean, default=True)
    oauth_provider = Column(String, nullable=False, default="local")
    oauth_sub = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _to_domain(m: UserModel) -> User:
    return User(
        id=m.id,
        tenant_id=m.tenant_id,
        email=m.email,
        hashed_password=m.hashed_password,
        roles=[UserRole(r) for r in (m.roles or [])],
        is_active=m.is_active,
        oauth_provider=OAuthProvider(m.oauth_provider),
        oauth_sub=m.oauth_sub,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _to_model(u: User) -> UserModel:
    return UserModel(
        id=u.id,
        tenant_id=u.tenant_id,
        email=u.email,
        hashed_password=u.hashed_password,
        roles=[r.value for r in u.roles],
        is_active=u.is_active,
        oauth_provider=u.oauth_provider.value,
        oauth_sub=u.oauth_sub,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


class PostgresUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_email(self, email: str, tenant_id: str) -> Optional[User]:
        stmt = select(UserModel).where(
            UserModel.email == email, UserModel.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def find_by_oauth(self, provider: str, sub: str) -> Optional[User]:
        stmt = select(UserModel).where(
            UserModel.oauth_provider == provider, UserModel.oauth_sub == sub
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return _to_domain(m) if m else None

    async def save(self, user: User) -> User:
        m = _to_model(user)
        self._session.add(m)
        await self._session.commit()
        await self._session.refresh(m)
        return _to_domain(m)
