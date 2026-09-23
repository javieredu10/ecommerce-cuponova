from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class AddressDTO(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "EC"


class CreateUserProfileRequest(BaseModel):
    auth_user_id: str
    user_type: str          # admin | provider | client
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    cedula: Optional[str] = None
    address: Optional[AddressDTO] = None
    company_name: Optional[str] = None
    ruc: Optional[str] = None


class UpdateUserProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    cedula: Optional[str] = None
    address: Optional[AddressDTO] = None
    company_name: Optional[str] = None
    ruc: Optional[str] = None
    firma_electronica_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    tenant_id: str
    auth_user_id: str
    user_type: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    cedula: Optional[str]
    address: Optional[AddressDTO]
    is_active: bool
    company_name: Optional[str]
    ruc: Optional[str]
    firma_electronica_url: Optional[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, p) -> "UserProfileResponse":
        addr = None
        if p.address:
            addr = AddressDTO(
                street=p.address.street, city=p.address.city,
                state=p.address.state, zip_code=p.address.zip_code,
                country=p.address.country,
            )
        return cls(
            id=p.id, tenant_id=p.tenant_id, auth_user_id=p.auth_user_id,
            user_type=p.user_type.value, first_name=p.first_name,
            last_name=p.last_name, email=p.email, phone=p.phone,
            cedula=p.cedula, address=addr, is_active=p.is_active,
            company_name=p.company_name, ruc=p.ruc,
            firma_electronica_url=p.firma_electronica_url,
            created_at=p.created_at,
        )
