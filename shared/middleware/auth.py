import os
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretjwtkey")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


_bearer_scheme = HTTPBearer(auto_error=True)


async def JWTBearer(
    credentials: HTTPAuthorizationCredentials = __import__('fastapi').Depends(_bearer_scheme),
) -> dict:
    """Dependencia JWT — usar como: Depends(JWTBearer)"""
    return decode_token(credentials.credentials)


async def get_tenant_id(request: Request) -> str:
    """Extrae tenant_id del JWT o del header X-Tenant-ID."""
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        tid = payload.get("tenant_id")
        if tid:
            return tid
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="tenant_id requerido"
    )
