from __future__ import annotations
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    PROVIDER = "provider"   # Proveedores del diagrama
    CLIENT = "client"       # Clientes del diagrama


@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "EC"


@dataclass
class UserProfile:
    """
    Perfil completo del usuario (distinto del User de auth).
    Relaciones del diagrama:
      Users -> Administrad | Proveedores | Clientes
    """
    id: str
    tenant_id: str
    auth_user_id: str           # FK al auth-service
    user_type: UserType
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    cedula: Optional[str]       # Identificación Ecuador
    address: Optional[Address]
    is_active: bool
    # Solo para Proveedores
    company_name: Optional[str]
    ruc: Optional[str]
    firma_electronica_url: Optional[str]  # Firma Electrónica del diagrama
    created_at: datetime
    updated_at: datetime

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @staticmethod
    def create(
        tenant_id: str,
        auth_user_id: str,
        user_type: UserType,
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str] = None,
        cedula: Optional[str] = None,
        address: Optional[Address] = None,
        company_name: Optional[str] = None,
        ruc: Optional[str] = None,
    ) -> "UserProfile":
        now = datetime.utcnow()
        return UserProfile(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            auth_user_id=auth_user_id,
            user_type=user_type,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            cedula=cedula,
            address=address,
            is_active=True,
            company_name=company_name,
            ruc=ruc,
            firma_electronica_url=None,
            created_at=now,
            updated_at=now,
        )
