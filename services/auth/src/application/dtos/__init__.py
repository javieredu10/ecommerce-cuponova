from typing import List, Optional
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str
    roles: Optional[List[str]] = None


class LoginRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    roles: List[str]
    is_active: bool
